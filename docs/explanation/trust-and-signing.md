# Trust, signing and the threat model

The planner's outputs are meant to be shared: with an insurer, a regulator's pre-application contact, or
a co-founder. Someone receiving a dossier should be able to tell whether it was changed after it was
issued. The trust layer provides that.

## What is signed

- **Dossier PDFs** carry an Ed25519 signature when a signing seed is configured. Without a seed the
  dossier is exported unsigned, and the export says so.
- **Evidence bundles** are sealed with a SHA-256 Merkle audit chain. Each control status and evidence
  record is a canonical-hashed leaf; the root commits to all of them. The bundle's manifest is signed
  with a detached Ed25519 signature.

## How keys are derived

A single master seed derives a separate Ed25519 key per organisation, using HKDF-SHA256 with the
organisation's identifier as context. The derived key is not stored. A derived key reveals nothing about
the master seed or about other organisations' keys, because HKDF is one-way.

In development the seed comes from `.env`. The configuration notes a production target of a key
management service hosted in the EU. How to set the seed is in
[how to enable signed dossiers](../how-to/enable-signed-dossiers.md).

## Threat model

The threat model for the trust layer is in [`docs/THREAT_MODEL.md`](../../docs/THREAT_MODEL.md). It
covers the adversaries considered, what the signatures do and do not prove, and the open risks.

Two points are worth stating here:

- A valid signature proves the content was produced by a holder of the key, and that it has not changed
  since. It does not prove the content is legally correct. That is what the citations are for.
- The signing code is reserved for external security review before production use. Its files are marked
  with a header so that changes are reviewed, and they are excluded from automated review tools that
  send code to third parties.

## Data residency

Signing happens inside the API, on infrastructure you run. Nothing is sent to a third party to sign.
The only optional outbound call is the Claude summary, described in
[the Claude how-to](../how-to/enable-claude-summaries.md).
