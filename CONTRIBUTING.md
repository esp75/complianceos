# Contributing

Thanks for helping. The most valuable contributions are usually not code: they are corrections and
additions to the licensing data, and reviews by people who do this work for a living.

## Ways to help

| You are… | You can… |
|---|---|
| An operator or engineer | Report what's wrong or missing in your roadmap ([data correction](.github/ISSUE_TEMPLATE/data-correction.yml)). |
| A licensing practitioner or lawyer | Review records for your jurisdiction and mark them `reviewed`. |
| Anyone who can read a statute | Add a licence or a country to `knowledge/` (see below). |
| A developer | Pick an issue, improve the planner, the UI, or the tests. |

## Run it locally

```bash
docker compose up --build          # http://localhost:3000, then "Open the sample mission"
```

Or run the pieces yourself:

```bash
cd app && uv sync && uv run uvicorn app.main:app --port 8001   # API (in-memory store if no Postgres)
cd web && bun install && bun run dev                           # web on http://localhost:3000
```

## Adding or correcting licensing data

Data lives in [`knowledge/`](knowledge/README.md): one YAML file per licence, plus one file per
jurisdiction for its authorities. The rules:

1. **Quote the law.** Every citation's `excerpt` is copied from the legal text, not paraphrased,
   with the official URL (legislation portal, official journal, regulator) and the date you
   retrieved it. Add `excerpt_en` for non-English texts and mark it as an unofficial translation.
2. **Never guess.** If you can't verify something, leave it out. Durations without a legal time
   limit or published guidance are marked `basis: estimate`.
3. **Explain applicability.** `applies_when` says which missions need the licence; give each branch
   a `because` in plain language and the citation that supports it.
4. **Contacts are institutional.** Only channels the authority publishes itself (web forms,
   functional mailboxes, switchboards), each with its source. No personal contact details gathered
   from other sites.
5. **Facilitators describe themselves.** A firm's `description` comes from its own website, linked
   in `source`. No rankings, no paid placement. Firms can ask to be added, corrected or removed by
   issue or pull request.
6. **Status.** New or changed records are `draft`. A practitioner reviewing a record sets
   `status: reviewed` and `reviewed_by` (an organisation, not a person).

Check your change before opening the pull request:

```bash
cd app && uv run python -m app.planner.knowledge validate
```

It reports every problem at once: schema errors, unknown authorities or citations, missing
prerequisites, cycles. Add what you verified, and how, to
[`knowledge/VERIFICATION.md`](knowledge/VERIFICATION.md).

## Code contributions

- **Backend** (`app/`): Python 3.12, FastAPI, pydantic v2. `uv run ruff check .`,
  `uv run mypy app` (strict), `uv run pytest`.
- **Web** (`web/`): Next.js 14, TypeScript strict, Tailwind. `bun run typecheck`, `bun run lint`,
  `bun test`, `bun run build`. After API changes, `bun run gen:api` regenerates the types.
- Planning logic stays deterministic and testable; the LLM only writes prose and must pass the
  citation check (ADR-0018).
- Architectural changes get an ADR in [`adr/`](adr/).
- Files marked `# MARKED-FOR-EXTERNAL-REVIEW` (the trust layer) are frozen for external security
  review. Propose changes in an issue first.
- Follow [DESIGN.md](DESIGN.md) for UI work: plain language, every claim cited, red only for late or
  overdue.

## Licensing of contributions

Code contributions are accepted under Apache-2.0 and data contributions under CC BY 4.0, the same
licences the project uses (inbound = outbound). By opening a pull request you confirm you have the
right to contribute it.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
