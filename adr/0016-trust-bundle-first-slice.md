# ADR 0016 — Trust/bundle first slice: Ed25519-HKDF derivation, SHA-256 Merkle chain, detached-signature PDF (PAdES deferred)

**Status**: Accepted — 2026-06-07
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0011](./0011-external-security-review-quarkslab.md) (Quarkslab external review),
[ADR-0014](./0014-claude-extractor-mvp-l2-l4-first-slice.md) (first-slice discipline),
[ADR-0015](./0015-openmct-first-slice-compliance-status-panel.md) (Phase 4 first slice),
[ADR-0007](./0007-postgres-age-pgvector-as-production-kg-substrate.md) (single Postgres substrate)

## Context

Phase 4's regulator-facing differentiator (ROADMAP DoD) is a **downloadable, signed compliance
evidence bundle**. The trust layer (`app/app/api/trust/`) and bundle layer were empty stubs reserved
for paid external review (ADR-0011). Following the first-slice discipline of ADR-0014/0015, this
slice builds a thin, offline/CI-safe, deterministic vertical — Ed25519 keypair per Org + a SHA-256
Merkle audit chain + a signed bundle PDF + `POST /bundle/sign` — with the heavy/risky pieces behind
interfaces so the marked surface stays small and reviewable by Quarkslab.

Three design questions had to be settled.

## Decision

**1. Per-Org Ed25519 keys are *derived*, not stored — HKDF-SHA256 from a master seed, behind a
`KeyStore` interface.** Each org's keypair is `HKDF(master_seed, salt="celestia-trust-v0",
info=org_id, len=32) → Ed25519`. No private key is ever persisted; only the public key + fingerprint
are recorded (`trust_org_key`). This is offline, deterministic (CI-stable), per-org isolated (HKDF is
one-way), and swap-ready: an EU KMS/HSM-backed `KeyStore` replaces derivation later without touching
callers. The master seed is the single high-value secret — env-only (`CELESTIA_TRUST_SIGNING_SEED`)
in v0, EU-side; when unset the endpoint 503s rather than signing with a degenerate key. Rejected:
generate-and-persist-per-org (private-keys-at-rest problem; non-deterministic for tests).

**2. Merkle is a pure tree over the bundle's leaves PLUS a cross-bundle append-only hash chain.**
`merkle.py` is pure and domain-separated (`0x00` leaf / `0x01` node prefixes — second-preimage
defence). The leaf set is every control status then every evidence record, each canonical-hashed, in
a fixed order (controls by refCode, then evidence by id) so any verifier reproduces the root. A
`TrustStore` (its own asyncpg pool on `trust_dsn`→`kg_dsn`, its DDL inside the marked surface, wired
tolerantly in the lifespan like the KG, gated by `require_trust`) appends each signed bundle with
`chain_hash = sha256(prev_root || merkle_root || signature)`, making the sequence of issued bundles
per org tamper-evident. No second store (ADR-0007): the trust tables share the kg-postgres.

**3. The bundle PDF is v0 detached-Ed25519 behind a `BundleSigner` interface; full PAdES deferred.**
The signer renders a human-readable summary and embeds a self-verifying sidecar (canonical manifest
+ detached Ed25519 signature + raw public key) as a PDF attachment, so a regulator can verify offline
with the org's public key alone. This is real cryptography over a canonical manifest, fully offline
and deterministic (PDF dates pinned from `issued_at`). It is **not yet** PAdES-B-LT (CMS/X.509/RFC-8419
EdDSA-in-CMS/timestamp); that upgrade lands behind the same `BundleSigner` interface before the
Quarkslab review (pyca/cryptography + pyhanko, both EU-acceptable). Rejected for this slice: pyhanko
PAdES now — large dependency surface and TSA/revocation needs conflict with the strict offline/CI
constraint and the "small, reviewable in isolation" goal.

**4. The endpoint reuses the existing compliance path and is gated by `can_view`.** `gather_status`
is factored out of `compliance.py` (GraphQL ownership stays there, ADR-0012) and reused by the bundle
signer. `/bundle/sign` gates on `can_view` — the same data `/compliance/status` exposes. A dedicated
`can_export_bundle` relation (export is a stronger action than viewing) is a named hardening
follow-up, not built in this slice.

## Consequences

**Positive**
- The first regulator-facing trust artifact is real and end-to-end: compliance data → Merkle seal →
  Ed25519 signature → self-verifying PDF → tamper-evident chain, fully offline and CI-safe.
- The marked review surface is small, pure where possible, and self-contained — ideal for Quarkslab's
  Ed25519 + Merkle + PAdES wheelhouse.
- `KeyStore` and `BundleSigner` seams isolate the two heavy upgrades (KMS, full PAdES) to
  implementation swaps.

**Negative**
- v0 is not PAdES-conformant; a verifier needs the sidecar + the org public key, not a standard PDF
  signature viewer. Tracked as the pre-audit upgrade.
- A single master seed is a concentrated secret; rotation re-keys all orgs in lockstep until per-org
  KMS lands. Documented in `docs/THREAT_MODEL.md`.

**EU sovereignty check**
- pyca/cryptography + fpdf2 are pure-local, no US-hosted service, no runtime network. The master seed
  stays EU-side. Verification needs only the publishable public key. ✓

## Out of scope for v0 (pre-audit / later slices)
- Full PAdES-B-LT (CMS, X.509 cert chain, RFC-8419 EdDSA-in-CMS, RFC-3161 timestamp, revocation info).
- EU KMS/HSM-backed `KeyStore`; per-org key rotation + versioning.
- Dedicated `can_export_bundle` relation; Postgres RLS (`app/api/rls/**`).
- Merkle inclusion-proof export endpoint for single-record disclosure.

## Action items
- Phase 4: freeze the trust/bundle surface and tag `pre-audit-v0` before the Quarkslab window
  (ADR-0011).
- Add the upgrade items above to the Quarkslab RFP scope.
