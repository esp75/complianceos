# ADR 0020 — The Watch: alert email, PDF sources, publication feeds, advisory triage

**Status**: Accepted — 2026-11-01
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0019](./0019-the-watch-v0.md) (the Watch v0), [ADR-0010](./0010-mvp-llm-policy-claude-only.md)
(Claude only, Anthropic EU), [ADR-0018](./0018-regulatory-path-planner.md) (knowledge pack)

## Context

ADR-0019 shipped change detection and a feed in the web app. It left open: nobody is told when a
source changes (the P2 definition of done is "detected → classified → alerted inside 48 h"), three
cited PDFs were unreadable, and a page diff cannot tell an operator that a new instrument was
published. This ADR covers those four slices.

## Decision

1. **Alert email is a plain SMTP digest.** `python -m app.planner.watch run --alert` sends one email
   per run listing the changes that run found, limited to changes that touch a tracked application.
   Nothing is sent when nothing is affected. The relay, sender and recipients come from
   `CELESTIA_SMTP_*`, `CELESTIA_ALERT_FROM`, `CELESTIA_ALERT_RECIPIENTS` (env only). The operator must
   choose an EU-hosted relay (sovereignty rules). TLS certificates are verified. A failed send exits
   non-zero but loses nothing, because changes are recorded before the email is attempted.
   Recipients are one deployment-wide list: per-workspace recipients need user emails, which the
   planner does not store, and are a follow-up.
2. **PDF sources are read.** The fetcher extracts text with `pypdf` (new dependency, BSD) in a worker
   thread, with a 25 MB cap. An unreadable or scanned PDF stays `unsupported`, not an outage. All three
   cited PDFs now read.
3. **Publication feeds are curated in the pack.** A jurisdiction may list `feeds` (RSS/Atom) with
   `keywords` and the `license_ids` they matter to. Users still cannot add URLs. The first check
   baselines the feed; afterwards each unseen entry whose title or summary contains a keyword is
   recorded as a `published` change on the feed URL and reaches workspaces tracking one of the
   licences. The Watch says something was published, not what it means. XML is parsed with
   `defusedxml`. Two feeds ship, both verified to answer and parse on 2026-11-01:
   legislation.gov.uk new legislation (GB) and the Federal Register's FCC documents (US).
4. **Delta triage by Claude is advisory.** When `CELESTIA_ANTHROPIC_API_KEY` is set, a `changed`
   record gets a label (`substantive`, `editorial`, `unclear`) and a one-sentence summary from the
   Anthropic EU endpoint (ADR-0010). The model sees only the differing passages, is told they are
   untrusted data, and its output is parsed strictly. Any failure leaves the change unclassified. The
   label is shown as "AI-assisted triage, unverified" and never changes the Watch's conclusion, which
   remains "re-verify". Without a key no model is called.

## Consequences

- Closes the alert half of the P2 Watch definition of done. Classification is advisory, not a
  guarantee.
- A feed that lists more new entries between two runs than it returns (legislation.gov.uk returns
  20) can miss some. Daily runs make this unlikely; it is not impossible.
- Keyword matching is coarse and will report some irrelevant publications. It errs towards
  reporting.
- The Légifrance pages (four citations) are still blocked to automated fetches; an official API
  route is a separate decision.
- Still open: signed change history (trust layer), per-workspace alert recipients, more feeds
  (each needs verifying before it enters the pack), usage instrumentation.
