# How to enable signed dossiers

By default, PDF dossiers are exported unsigned, and the export says so. Setting a signing seed makes
the dossier carry an Ed25519 signature.

## 1. Generate a seed

```bash
openssl rand -hex 32
```

Keep the output private. Anyone with the seed can produce signatures from the same key.

## 2. Set it

In the `.env` file next to `compose.yaml`:

```bash
TRUST_SIGNING_SEED=<the 64 hex characters>
```

Docker Compose passes it to the API as `CELESTIA_TRUST_SIGNING_SEED`. Restart the stack:

```bash
docker compose up -d
```

## 3. Export

Export a dossier from a mission's **Dossier** tab. It is now signed.

## Notes

- `.env` is git-ignored. Never commit a seed.
- The seed is a development setting. The trust-layer design targets an EU-hosted KMS for production;
  see [trust, signing and the threat model](../explanation/trust-and-signing.md).
- Signing code is reserved for external security review. Changes to it follow the review rules in
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
- The bundle format is self-verifying: the [engineering log](../explanation/engineering-log.md)
  describes the embedded sidecar and manifest. A step-by-step verification guide is not written yet.
