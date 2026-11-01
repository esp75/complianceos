# ADR 0019 — The Watch v0: change detection on cited sources

**Status**: Accepted — 2026-11-01
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0018](./0018-regulatory-path-planner.md) (knowledge pack, planner),
[ADR-0010](./0010-mvp-llm-policy-claude-only.md) (LLM policy), [ADR-0014](./0014-claude-extractor-mvp-l2-l4-first-slice.md)
(citation-or-422), [ADR-0017](./0017-first-product-refocus.md) (the Watch as the retention product)

## Context

The planner's value rests on citations: every obligation points at a provision and a URL, with a
`retrieved` date. Laws change after that date and nothing tells the operator. ROADMAP P2 calls for
"The Watch": scheduled monitoring of the sources, change detection, and an alert tied to the
operator's tracked applications. Email alerts, a signed change history and classification with an
LLM are later slices. The first slice needs to find out what changed, and for whom.

## Decision

1. **The watch list is derived from the pack.** Every distinct `citation.url` in `knowledge/` is
   watched. Nothing else is fetched, and no user can add a URL, so there is no SSRF surface and no
   second list to maintain. A test asserts the source set equals the pack's citation URLs.
2. **Change means a changed hash of normalised visible text.** Scripts, styles, `nav`, `header` and
   `footer` are dropped and whitespace collapsed, so markup and navigation churn does not count.
   SHA-256 of the full normalised text is the change signal. A bounded excerpt (60k characters) is
   kept for a word-level diff: "+N / −M words".
3. **Three outcomes are never confused.** `changed` is a hash difference against the last good
   check. `unreachable` (HTTP error, timeout, redirect off https, oversize) is an outage and keeps the
   last good hash, so recovery is compared with it. `unsupported` means the source is not HTML (a
   PDF): it is reachable, we cannot read it, and it raises no alert.
4. **The first successful check is a baseline, not a change.** The Watch's baseline is its own first
   check. A change made before the Watch first ran is not detected. The pack's `retrieved` date is
   not used as a baseline, because the Watch has no copy of the text at that date.
5. **The Watch concludes nothing.** A change record says the text differs and that the cited
   provision must be re-verified. It never edits the pack and never says what a change means in law.
6. **Changes are global, views are per workspace.** Source states and changes concern public sources,
   so they are stored once. `GET /watch/changes` and `GET /missions/{id}/watch` return only changes
   whose source is cited by a licence the workspace tracks, so one workspace never sees another's
   applications.
7. **Fetching is deliberately conservative.** https only (a redirect that leaves https is an
   outage); a 20 s timeout; a 5 MB body cap checked while streaming; the content type checked before
   the body is read; requests to one host spaced 1 s apart; hosts run in parallel; a fixed,
   identifiable User-Agent. The Watch does not try to get around bot blocks.
8. **No LLM in v0.** Classification is rule-based. Any LLM-assisted classification in a later slice
   must use the Claude EU endpoint (ADR-0010) and must not be the only signal.
9. **Scheduling is external.** `python -m app.planner.watch run` is meant for cron or a compose
   job. `POST /watch/run` exists for manual checks. Both use the same code path.

## Consequences

- Operators get a feed of "this cited source changed; these of your applications cite it". The
  Watch does not replace reading the law.
- **Coverage is partial.** On the first live pass over the pack (2026-11-01), 16 of 23 cited URLs
  were watchable. Four Légifrance pages (French codes) returned HTTP 403 to automated requests, and
  three PDFs are unsupported (two ITU history documents, one Luxembourg Mémorial). Seven sources
  (about 30%) are not watched in v0. Légifrance coverage needs an official route (its API under
  PISTE, requiring registration), which is a follow-up decision, not a workaround in the fetcher.
- A change is only as good as the baseline. Until the Watch has run once, it reports nothing.
- Persistence is in `planner_watch_source` and `planner_watch_change` (Postgres). The in-memory
  store implements the same contract, so local mode works, but the CLI needs Postgres.
- The Postgres store has a contract test that runs when `CELESTIA_PG_TEST_DSN` is set. It was not
  run in the first slice's environment, so the SQL is verified by review only until it is.

## Not in this slice (next Watch slices)

- Email alerts and a signed program history (Merkle chain, ADR-0016 seams).
- Official-journal and RSS adapters for sources that PDF or block scraping.
- Route for Légifrance through its official API.
- Delta classification with Claude (EU endpoint), kept advisory.
- Usage instrumentation for MoU Annex A success criteria (ROADMAP P2).
