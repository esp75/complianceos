# ADR 0021 — Signed program history and pilot usage events

**Status**: Accepted — 2026-11-01
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0016](./0016-trust-bundle-first-slice.md) (trust layer), [ADR-0018](./0018-regulatory-path-planner.md)
(tracker and event log), [ADR-0020](./0020-the-watch-alerts-pdf-feeds-triage.md)

## Context

ROADMAP P2 asks for "signed program history" (state changes on a tamper-evident chain) and for
"pilot instrumentation" (usage events, so MoU success criteria are measured). The planner already
keeps an append-only event log per application and signs its dossier with a per-workspace key.

## Decision

1. **Program history is a signed, checkpointed export, built outside the trust layer.**
   `app/planner/history.py` canonicalises every application event of a workspace, hashes the ordered
   events into the trust layer's Merkle tree, and signs the manifest with the workspace's Ed25519
   key (the dossier's key). It imports the trust primitives and does not edit any file marked
   `MARKED-FOR-EXTERNAL-REVIEW`, so the frozen review surface is unchanged.
   `verify_history` checks the Merkle root and the signature from the document alone. The document
   embeds its public key, so that proves integrity, not origin: pass the signer's fingerprint,
   obtained out of band, as `trusted_fingerprint` to pin who signed it.
2. **Exports chain.** A workspace export is stored as a checkpoint and names the previous
   checkpoint's root in its signed manifest. A later export therefore cannot drop earlier events
   without the break being visible to anyone holding the earlier export. A per-mission export is a
   view of part of the history and is not chained. With no signing key the export is returned
   unsigned and is not checkpointed.
3. **Not anchored in `trust_bundle`.** The checkpoints live in the planner database, so someone with
   write access to that database can rewrite both events and checkpoints. The guarantee is "holders
   of an earlier signed export can detect rewriting", not protection against a database
   administrator. Anchoring checkpoints in the trust layer's bundle chain is a follow-up for after
   the external review, because it needs a trust-layer change.
4. **Deleting a mission deletes its events** (existing behaviour). Export before deleting.
5. **Usage events record the feature, not the content.** `POST /usage` accepts a fixed set of kinds
   (`session_start`, `mission_viewed`, `watch_viewed`, `alert_opened`, `dossier_exported`); the store
   keeps workspace, actor, kind and time. `GET /usage/summary` returns counts and active days. Alert
   emails link to `/?from=alert`; there is no tracking pixel and nothing leaves the deployment.
   `dossier_exported` is accepted but the web app does not send it yet.

## Consequences

- P2's two remaining items have a working first slice. "Alert opens" are measured by link click,
  which undercounts people who read the alert and open the app another way.
- Local mode has a single workspace and user, so usage there describes one person.
- The signed history carries free-text notes the client wrote; it is the client's own export.
