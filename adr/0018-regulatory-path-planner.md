# ADR 0018 — Regulatory path planner: open knowledge pack, deterministic planning, lite run mode

**Status**: Accepted — 2026-10-15
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0017](./0017-first-product-refocus.md) (licensing / market access as the first
product), [ADR-0014](./0014-claude-extractor-mvp-l2-l4-first-slice.md) (citation-or-422),
[ADR-0010](./0010-mvp-llm-policy-claude-only.md) (Claude only), [ADR-0012](./0012-fastapi-theopenlane-contract.md)
(BFF ↔ theopenlane), [ADR-0016](./0016-trust-bundle-first-slice.md) (signed exports)

## Context

ADR-0017 made licensing and market access the first product. Operators need four things the repo
did not have:

1. which licences a mission needs in each country, and why;
2. the order and dates, working back from a launch date;
3. the law behind each requirement;
4. a way to track applications and reach the right authority or adviser.

ComplianceOS is also being released as open source so any operator can use it. That changes three
things: the data has to be inspectable and correctable by people outside the project, a first run
has to work on an ordinary laptop, and accuracy claims have to be checkable by anyone.

## Decision

**1. Regulatory knowledge is open data in the repository (`knowledge/`).** Licences, authorities,
contacts and facilitators are YAML files validated by strict pydantic models
(`app/app/planner/knowledge.py`). Every licence carries citations with an official URL, a
retrieval date and a verbatim excerpt, plus an English rendering when the source is not in
English. Durations say whether they are statutory, published practice or an estimate. Records stay
`draft` until a practitioner reviews them. Contributions arrive as pull requests and CI runs the
validator. The data is CC BY 4.0 (`knowledge/LICENSE.md`) and the code stays Apache-2.0.
Rejected: keeping the data in the knowledge graph as the source of truth (contributors could not
review it) and LLM extraction at request time (citations could not be reproduced).

**2. Planning is deterministic. The LLM writes prose and nothing else.**
- `rules.py` evaluates a small declarative rule language (no `eval`) and explains each match with
  the `because` text and citations of the branches that fired.
- `schedule.py` runs a forward and a backward pass over the prerequisite DAG, giving earliest
  dates, latest dates, slack and the critical path. It is property-tested with hypothesis.
- `plan.py` joins the two into a roadmap; `brief.py` writes the "senior regulatory-affairs" brief
  from it.
- With Claude configured, only the executive summary is model-written. It must cite ids already in
  the roadmap, in every paragraph, or it is rejected.

The same text-level check (`enforce_text_citations`) now guards `/draft/obligation`. Before this,
that endpoint validated the retrieval list rather than the generated text.

**3. Lite run mode: the planner does not need theopenlane.** The planner API runs on FastAPI plus
Postgres (the existing kg-postgres image). In `AUTH_MODE=local` (the default) there is a single
workspace and the server binds to loopback only. The full theopenlane + OpenFGA + Dex stack
(`cross-cutting/deploy/`) remains the multi-tenant "team mode", where planner routes use the
existing tetrad checks. Reason: theopenlane's `core` image is amd64-only and the full stack is seven
or more containers, which is too much for a first run.

**4. Contacts are institutional.** Authority contacts are channels the authority publishes itself
(web forms, functional mailboxes, phone lines), each with a source and a date. Facilitators are
listed neutrally, in their own words, with no ranking. No personal data is collected from
third-party sources.

## Consequences

- Accuracy is reviewable line by line, and `knowledge/VERIFICATION.md` records how each part was
  checked and what still needs a human.
- Coverage starts small (ITU, France, Luxembourg, the UK, the US). Roadmaps name the countries in a
  mission that have no data yet, rather than staying silent.
- Durations without a statutory basis are estimates and are labelled as such everywhere they
  appear.
- The planner can later feed the KG for semantic search over law text without changing the pack's
  role as the source of truth.
