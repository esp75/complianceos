# Threat model

STRIDE per component. Filled in during Phase 5 ahead of external review.

## Sovereignty assumptions

- All production data is at rest and in transit inside the EU.
- Identity provider is EU-resident (Zitadel Cloud — Switzerland, or self-hosted Zitadel on Hetzner).
- LLM calls: prefer EU-jurisdiction endpoints. Any US-jurisdiction LLM call must be documented below with the data flow, contents, and mitigations.

### Documented US LLM dependencies

| Component | Endpoint | Data sent | Mitigation |
|---|---|---|---|
| _none yet_ | | | |

### Documented US-jurisdiction service dependencies (non-LLM)

| Service | Purpose | Data exposed | Mitigation |
|---|---|---|---|
| GitHub (Microsoft) | Source code hosting + CI. Repo: `sillysponsor/celestia-complianceos` (private). | Entire codebase including trust-layer source (once written). Issues, PRs, commit history. | (1) Private repo. (2) Production secrets never committed (see `.gitignore`). (3) Trust-layer files marked `# MARKED-FOR-EXTERNAL-REVIEW` are still hosted on GitHub — exposure is "Microsoft as code-host", not "Microsoft as runtime". Production deploys go to Hetzner directly, not via GitHub Actions writing to prod. (4) Reassess at Phase 5; consider Codeberg, Forgejo on Hetzner, or GitLab.com self-host if EU code residency becomes contractually required. |

## STRIDE per component

To be populated.
