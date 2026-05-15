# Accounts and credentials Max needs to create

`[NEEDS-MAX]` on every line. Until these are confirmed, the build can't progress past Phase 0 → Phase 1.

## Phase 0 — Required to start coding

| Service | Why | Cost | Link |
|---|---|---|---|
| **Hetzner Cloud** account | Production compute. Create a CCX23 in Falkenstein or Nuremberg. EU jurisdiction. | ~€20/mo | https://www.hetzner.com/cloud |
| **Domain registration** (celestiadynamics.com or .eu) | Customer-facing; mandatory for PAdES timestamp authority and Coolify HTTPS | ~€15/yr | any EU registrar (Gandi, OVH) |
| **Cloudflare** account (free tier) | DNS only. Enable "EU-only data residency" in dashboard if available on your plan. | €0 | https://cloudflare.com |
| **Anthropic API key** | Build agent — Claude Code. EU endpoint via `https://api.anthropic.com` (Anthropic has Ireland and Germany infra). | per-use | already have |
| **Docker Desktop** | Local dev only (Postgres + AGE). Not strictly required if you SSH into Hetzner from day one, but recommended. | €0 personal use | https://www.docker.com/products/docker-desktop |

## Phase 0 — Identity

| Service | Why | Cost | Link |
|---|---|---|---|
| **Zitadel** — choose: Cloud (Switzerland-resident) OR self-host via Coolify on Hetzner | Customer auth + B2B SSO. Self-host gives you full sovereignty; Cloud gives you a faster start. Pick one and commit before Phase 2. | Cloud: free tier then ~€9/mo; self-host: just Hetzner cost | https://zitadel.com |

## Phase 2 — MCP credentials

| Service | Why | Cost | Link |
|---|---|---|---|
| **ITU TIES account** | Required by `mcps/itu_sps` to query Space Network Systems filings. | ITU members free; non-members request a quote. | https://www.itu.int/en/ties-services |

## Phase 5 — Paid external security review

Get quotes from at least three firms before committing.

| Firm | Specialty | Indicative range |
|---|---|---|
| Trail of Bits | Cryptography review, smart contracts, blockchain. Strong on signing-chain audits. | $25–80k |
| Quarkslab (France) | EU-based, strong on cryptography and embedded. | €30–80k |
| Cure53 (Germany) | EU-based, strong on web app + supply chain. | €30–60k |
| Doyensec | Multi-cloud, AppSec focus. | $20–60k |

Scope: only the `# MARKED-FOR-EXTERNAL-REVIEW` files (`app/api/trust/**`, `app/api/rls/**`, `app/api/bundle/sign*.py`).

## Phase 6 — EU timestamp authority

For PAdES B-LTA you need a qualified EU TSA.

| TSA | Jurisdiction | Indicative cost |
|---|---|---|
| Sectigo (Switzerland) | EU + EEA-recognised | ~€500/yr for low-volume |
| GlobalSign (Belgium) | EU qualified | ~€500–1500/yr |

Request quotes during Phase 5 so you can integrate in Phase 6.

## Optional

| Service | Why |
|---|---|
| **OpenAI API key** | Only if you want `/codex` for second-opinion review on non-trust-layer files. Trust-layer code is hard-blocked from `/codex`. Skip if you'd rather rely on the paid Phase 5 review alone. |

---

**Action**: edit this file in place as you create each account; replace `[NEEDS-MAX]` with the date and the account ID (not the password). The completed file becomes evidence for the security review pack in Phase 5.
