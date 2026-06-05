# Post-Phase-0 Status — 2026-05-15

This is a supplement to [`STATUS.md`](./STATUS.md), written after the
next-3-tasks attempt. Refer to STATUS.md for the Phase 0 inventory.

## Open questions — resolved

All 5 open questions from STATUS.md are resolved. Outcomes:

1. Go-service-behind-FastAPI → **Kept** (ADR-0001 stands).
2. openmct + Next.js dual frontend → **Kept** (ADR-0003 stands).
3. EU LLM endpoint plan → **MVP = Claude only** (Anthropic EU). Mistral
   deferred behind provider-router interface. See [ADR-0010](./adr/0010-mvp-llm-policy-claude-only.md).
4. ComplianceNLP corpus → **Solo-bootstrap small (~100 provisions) first**;
   contracted annotator option documented for later. ROADMAP risk-register
   addition recommended in the eng review (see below).
5. External security review vendor → **Quarkslab (FR) primary, Cure53 (DE)
   backup.** Trail of Bits dropped (US-jurisdiction conflict). See
   [ADR-0011](./adr/0011-external-security-review-quarkslab.md).

CLAUDE.md amendments referenced — apply manually next session (see
"Sandbox blocker" below).

## Next-3-tasks attempt summary

### Task 1 — `/gstack-upgrade` + `/sync-gbrain`

- ✅ **/gstack-upgrade**: gstack upgraded **1.35.0.0 → 1.39.0.0**, migrations
  1.37.0.0 and 1.38.1.0 ran cleanly. Notable new skills now available:
  `document-generate` (Diataxis-framework docs from scratch),
  `connect-chrome` (per the upgrade output).
- ⚠️ **/sync-gbrain**: BLOCKED at the orchestrator's Bash flow by a
  **macOS TCC sandbox revoke** that the upgrade triggered (the Playwright
  chromium-headless-shell install side-effect dropped Terminal's
  `~/Documents/` access). The `mcp__gbrain__*` MCP tools still work
  (Phase 0's 16-page ingest is intact); only the Bash-shelling skill flow
  is blocked. See "Sandbox blocker" below for the user-side fix.
- Manual equivalent of /sync-gbrain's CLAUDE.md GBrain Search Guidance
  block is recorded in this file (below in "GBrain Search Guidance — apply
  to CLAUDE.md manually"). Copy into CLAUDE.md next session.

### Task 2 — `/plan-eng-review` on ROADMAP.md + `/codex consult` on ADR-0001

- ✅ **Eng-review on ROADMAP.md**: completed manually (interactive Skill
  wrapper is also blocked by the same Bash sandbox issue). Findings written
  to [`adr/REVIEW-2026-05-15-eng-review.md`](./adr/REVIEW-2026-05-15-eng-review.md).
  Verdict: **APPROVED with 6 changes** (none are ADR reversals; 3 added
  risks, 2 added performance SLAs, 1 new ADR-0012 needed). Estimated impact
  on 16-week timeline: +1 week (Phase 0.5 spike), revised 17-week MVP.
- ⚠️ **/codex consult on ADR-0001**: SKIPPED. Reasons documented at the
  end of the eng review. TL;DR: codex shells out to OpenAI Codex CLI which
  is sandbox-blocked, and Claude-only MVP rule (ADR-0010) makes an
  OpenAI second-opinion less load-bearing during MVP. Path forward: if a
  second opinion on ADR-0001 is still wanted, re-run after the sandbox
  fix, or ask Claude in a fresh session to adversarially argue the
  opposite ("re-implement theopenlane data model in FastAPI").

### Task 3 — EU Space Act Articles 1–5 YAMLs

- ✅ **Authored**. Five article YAMLs under `layers/L1-substrate/frameworks/eu-space-act/articles/`
  plus `framework.yaml` (Openlane Framework manifest), `evidence-types.yaml`
  (5 Celestia-defined Evidence types referenced by these Articles), and a
  per-framework `README.md`. Every Control carries the RASE slots
  (Requirement / Applicability / Selection / Exception). All marked
  `validation_status: draft` until reviewed against OJ-final text in
  Phase 1 week 3.

## Sandbox blocker — user action required

**Symptom**: Bash tool returns "Operation not permitted" on every command
under `~/Documents/`. Edit and Read tools intermittently EPERM on existing
files. Write tool can still create new files. The `mcp__gbrain__*` MCP
tools work fine.

**Cause**: the gstack v1.39 upgrade's Playwright `chromium-headless-shell`
install triggered macOS TCC to re-prompt for Documents folder access.
The prompt was denied or dismissed in the background, and Terminal lost
its `~/Documents/` permission.

**Fix** (manual, ~30s):

1. **System Settings → Privacy & Security → Files and Folders**
2. Locate the Terminal app the harness uses (`Terminal.app`, `iTerm2`,
   or your shell wrapper).
3. Re-enable **Documents Folder** access for that app.
4. Restart the shell session (close & reopen the terminal / Claude Code
   tab).

After the fix, the following will work again:

- `/sync-gbrain` (the full orchestrator + code-index pass)
- `/codex review` / `/codex challenge` / `/codex consult`
- `/cso`, `/qa`, `/ship`, `/land-and-deploy`
- Any skill or Bash command that needs to list/read files under `~/Documents/`

## GBrain Search Guidance — apply to CLAUDE.md manually

The `/sync-gbrain` skill would normally inject this section into CLAUDE.md.
Until the sandbox is restored, paste this block into `CLAUDE.md` just before
the "## Reference docs" section:

```markdown
## GBrain Search Guidance
<!-- gstack-gbrain-search-guidance:start -->

GBrain is configured on this machine. Production state for L1/L2/L4 stays
in Postgres + AGE + pgvector per [ADR-0007](./adr/0007-postgres-age-pgvector-as-production-kg-substrate.md);
gbrain is **agent memory only**.

This repo's architecture is ingested as gbrain pages: `complianceos-overview`,
`layer-l1-substrate` … `layer-cross-cutting` (7 layer pages), and `adr-0001`
… `adr-0011` (11 ADR pages), wired with `contains` / `governed_by` /
`affects` edges.

Prefer gbrain over Grep when the question is semantic ("which ADR governs
L4 retrieval?", "which layer does Orekit serve?") or when you don't know
the exact identifier yet:

- `gbrain search "<terms>"` or `gbrain query "<question>"`
- `gbrain code-def <symbol>` / `code-refs` / `code-callers` / `code-callees`

Grep is still right for known exact strings, regex, multiline patterns,
and file globs. Run `/sync-gbrain` after meaningful code changes.

<!-- gstack-gbrain-search-guidance:end -->
```

## Eng-review findings to apply

Full review: [`adr/REVIEW-2026-05-15-eng-review.md`](./adr/REVIEW-2026-05-15-eng-review.md).

**6 actions to apply to ROADMAP.md before Phase 1 begins**:

1. **Add ADR-0012** — FastAPI ↔ theopenlane GraphQL contract (1 page;
   Phase 1 week 1 deliverable).
2. **Lock Orekit gRPC in Phase 1** (not Phase 2) and document a placeholder
   contract.
3. **Schedule Phase 0.5** — openmct hello-world plugin spike + cross-frontend
   auth-session spike. Time-box 3 days. If spike fails, scope-cut Phase 4
   to 2 plugins instead of 4.
4. **Append 3 risks to ROADMAP risk register**:
   - M-1 LLM cost overrun during Phase 3 retrieval iteration (budget €600–€2400)
   - M-2 Annotation Inter-Annotator Agreement gap (contract a second
     annotator on a 50-provision sample for IAA; budget €1,500)
   - M-3 openmct ↔ Next.js shared session not de-risked
5. **Append performance SLAs**:
   - P-1 differentiate batch retrieval (≤30s p99) from realtime retrieval (≤500ms p99)
   - P-2 embedding regeneration €100–€300/month
6. **Define held-out test set sources** for L2 extractor (T-1) and the
   L4 citation-fidelity automated CI gate (T-2).

## Task status (final)

| Task | Status | Notes |
|---|---|---|
| #11 Resolve open Qs + ADRs 0010/0011 | ✅ Done | ADRs written, gbrain-ingested, CHANGELOG updated |
| #12 EU Space Act Articles 1–5 YAMLs | ✅ Done | 5 articles + framework manifest + evidence-types + README |
| #13 /gstack-upgrade + /sync-gbrain | ⚠️ Partial | gstack-upgrade DONE; sync-gbrain BLOCKED on TCC; GBrain Search Guidance block delivered manually above |
| #14 /plan-eng-review + /codex consult | ⚠️ Partial | Eng-review DONE_WITH_CONCERNS (6 actions); codex SKIPPED with documented path forward |

## Next session

1. Resolve the sandbox blocker (~30s in System Settings).
2. Paste the GBrain Search Guidance block into CLAUDE.md.
3. Apply the 6 eng-review actions to ROADMAP.md, open ADR-0012.
4. Optionally run `/sync-gbrain --full` to backfill the v0.2 repo into
   gbrain's local code-index (the MCP page ingest is already done; this
   is the symbol-aware code-search index, separate concern).
5. Optionally run `/codex consult` on ADR-0001 if a second opinion still
   feels load-bearing post-eng-review.
6. Phase 0.5 spike: openmct hello-world plugin + cross-frontend auth.

Then Phase 1 begins.
