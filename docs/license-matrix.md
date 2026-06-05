# License Matrix

ComplianceOS v0.2 is distributed under **Apache-2.0**. Every adopted upstream dependency must be license-compatible with closed-source SaaS distribution.

## Vendored dependencies

| Dep | License | Compatibility with Apache-2.0 SaaS | Notes |
|---|---|---|---|
| theopenlane-core | Apache-2.0 | ✅ Compatible | Attribution only |
| orekit | Apache-2.0 | ✅ Compatible | CII-certified |
| ostk | Apache-2.0 | ✅ Compatible | — |
| openmct | Apache-2.0 | ✅ Compatible | NASA provenance |
| lightrag | MIT | ✅ Compatible | Pattern reference only |
| trustgraph | Apache-2.0 | ✅ Compatible | Pattern reference only |
| compliance-nlp | Apache-2.0 | ✅ Compatible | Architecture reference; code may be ported |
| accord-nlp | Apache-2.0 | ✅ Compatible | RASE schema reference |
| itu-compliance-monitor | MIT | ✅ Compatible | Port + extend |
| jeffallan-skills | MIT | ✅ Compatible | 8 skills copied |

## Cherry-picked skills under `.claude/skills/`

All MIT (from jeffallan-skills). ✅ Compatible.

## Explicitly rejected upstreams

| Dep | License | Why rejected |
|---|---|---|
| Comp AI | AGPL-3.0 | ❌ AGPL contaminates closed-source SaaS distribution |
| Neo4j Community | GPLv3 | ❌ Same contamination risk |
| OpenRegs | (no license) | ❌ Legally unsafe to vendor or fork |
| VeritasGraph | (no license despite README claim) | ❌ License absence verified via GitHub API |
| regulatory-intelligence-agent | (no license) | ❌ Legally unsafe |

## Models & weights (future, to be added in Phase 3)

| Asset | License | Source | Sovereignty status |
|---|---|---|---|
| LEGAL-BERT base | MIT | nlpaueb/legal-bert-base-uncased | Mirror to EU storage |
| BAAI/bge-m3 | MIT | BAAI/bge-m3 | Mirror to EU storage |
| BAAI/bge-reranker-v2-m3 | MIT | BAAI/bge-reranker-v2-m3 | Mirror to EU storage |
| LoRA adapters (Celestia-trained) | Apache-2.0 (Celestia) | Trained on Hetzner GPU | Stored EU-only |

## LLM endpoints (future, to be added in Phase 3 + 4)

| Endpoint | Jurisdiction | Use case | Sovereignty status |
|---|---|---|---|
| Anthropic EU | EU | Drafting | ✅ Preferred |
| Mistral (EU) | EU | Fallback drafting | ✅ Preferred |
| Self-hosted Llama 3.x on Hetzner GPU | EU | Sensitive ops | ✅ Preferred (high effort) |
| OpenAI (US) | US | Documented exceptions only — see `docs/THREAT_MODEL.md` | ⚠️ Document each call |

## Process

- New dependency added → license noted in this file → added to `external/VENDOR.md` → ADR opened if license is non-trivially Apache/MIT.
- License audit: quarterly. `scripts/license-audit.sh` (future) scans `external/` for license files and diffs against this matrix.
- AGPL/GPL detection at scan time = hard fail.
