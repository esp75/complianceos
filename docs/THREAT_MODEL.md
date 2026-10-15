# Threat model — trust layer (Phase 4, v0)

Scope: the signed compliance evidence bundle (`POST /bundle/sign`) and its trust primitives —
per-Organization Ed25519 keys, the SHA-256 Merkle audit chain, and the bundle PDF. See
[ADR-0016](../adr/0016-trust-bundle-first-slice.md). This surface is reserved for paid external
review (Quarkslab/Cure53, [ADR-0011](../adr/0011-external-security-review-quarkslab.md)); this
document is the pre-review baseline and will be revised against findings.

## Assets

- **Master signing seed** (`CELESTIA_TRUST_SIGNING_SEED`) — derives every org's private key. Highest-
  value secret in the system.
- **Per-Org Ed25519 private keys** — derived on demand, never persisted.
- **Issued bundles + the per-org chain** (`trust_bundle`) — the tamper-evidence record.
- **Org public keys** (`trust_org_key`) — publishable verification material (not secret).

## Key-storage model

- **No private keys at rest.** Each org's key is `HKDF-SHA256(master_seed, salt="celestia-trust-v0",
  info=org_id, len=32) → Ed25519`. HKDF is one-way, so a derived org key reveals neither the master
  seed nor another org's key.
- **Master-seed handling.** Env-only, never committed, EU-side. Production target is an EU KMS/HSM
  behind the `KeyStore` interface (the derivation impl becomes a thin KMS adapter). When the seed is
  unset, `/bundle/sign` returns 503 — it never signs with a degenerate/zero key.
- **Rotation.** Today rotation = change the master seed (or bump the HKDF salt suffix), which re-keys
  all orgs in lockstep; `trust_org_key` records the current public key + fingerprint so verifiers can
  detect the change. Per-org rotation + key versioning is a pre-audit upgrade (ADR-0016 out-of-scope).

## Tamper-evidence properties

- **Merkle seal.** Every control status and evidence record is a canonical-hashed leaf; the root
  seals the bundle's contents. Domain separation (`0x00` leaf / `0x01` node) blocks second-preimage /
  leaf-as-node attacks. Inclusion proofs allow single-record disclosure without revealing the rest.
- **Chain.** Each bundle stores `chain_hash = sha256(prev_root || merkle_root || signature)` linking
  to the previous bundle's root, so deletion/reordering/substitution in the per-org sequence is
  detectable.
- **Signature.** The detached Ed25519 signature covers `canonical_bytes(manifest)`; the bundle PDF
  embeds a self-verifying sidecar (manifest + signature + public key) so any holder re-verifies
  offline with the org's public key alone — no master seed, no server.

## Trust boundary

- The bundle packages only data the caller is authorized to read (`can_view`); export is gated at the
  BFF before theopenlane is hit. A stronger `can_export_bundle` relation is a named follow-up.
- Verification requires only the **public** key; compromise of a published public key does not enable
  forgery.

## Known limitations / out of scope for v0 (to address pre-audit)

- Not yet PAdES-B-LT: no CMS/X.509 chain, no RFC-3161 timestamp, no revocation info — a standard PDF
  signature viewer will not show a signature; verification uses the embedded sidecar.
- Single concentrated master seed (see Rotation); no EU KMS/HSM yet.
- No Postgres RLS on the trust tables yet (`app/api/rls/**` reserved); tenancy is enforced at the BFF.
- No rate-limiting / per-export audit-log entry on bundle generation.

## Open findings (security review, 2026-10-15) — fix before anything depends on `/bundle/sign`

1. **Chain fork under concurrency.** `TrustStore.last_root()` and `append_bundle()` run as separate
   statements with no transaction or lock, so two concurrent signs for one org can both read the
   same head and both append, forking the chain. Fix: read the head and insert inside one
   transaction under `pg_advisory_xact_lock` keyed on the org, and add a unique index on
   `(org_id, prev_root)` plus a partial unique index for the genesis row so a fork cannot persist.
2. **Signing gated by a read relation.** `/bundle/sign` checks `can_view`, so any viewer (insurer,
   regulator) can make the org's key sign and append to the org's chain. Fix: add a
   `can_export_bundle` relation to the FGA model and gate on it.
3. **Unrecorded filtering.** The optional `framework` query filter yields an org-signed bundle that
   omits frameworks without saying so. Fix: record the applied filter in the signed manifest (and
   render it on the PDF) so a partial bundle cannot pass as a full one.

## Documented US LLM dependencies

None. The trust/bundle path makes no LLM call and no external network call. (Section retained per
CLAUDE.md for any future US-jurisdiction LLM usage elsewhere.)
