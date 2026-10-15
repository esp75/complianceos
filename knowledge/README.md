# Knowledge pack

Open, cited data about satellite licensing. The planner reads it to work out which licences a
mission needs, why, in what order and by when. Every requirement points to the text of the law it
comes from.

```
jurisdictions/<id>/jurisdiction.yaml    the authorities and their official contact channels
jurisdictions/<id>/licenses/<id>.yaml   one licence, authorisation or filing per file
facilitators/<id>.yaml                  firms that help operators through licensing
schema/                                 JSON Schema for editor autocompletion
VERIFICATION.md                         how each part was checked, and what still needs a human
```

Jurisdiction ids are lower-case ISO 3166-1 codes (`gb` for the United Kingdom), plus `itu`.

## A licence file, in short

| Field | What it holds |
|---|---|
| `applies_when` | A rule over the mission profile. Each branch can say `because` and `cite`, which is what the user sees as "why this applies to you". |
| `legal_basis` | Citations: instrument, provision, official URL, date retrieved, and a short verbatim `excerpt` (plus `excerpt_en` when the text is not in English). |
| `prerequisites` | Licences this one waits for. Only applied when both are in the plan, so you can list each country's alternative. |
| `preparation`, `review` | Weeks (min / typical / max) and where the numbers come from: `statutory`, `practice` or `estimate`. |
| `submission_window` | The earliest you may file, counted back from when the licence is needed. |
| `obligations` | Dated duties that follow: hard deadlines, renewals, recurring fees, milestones. |
| `requires_local_presence` | `true` if a local company or representative is needed, `null` if not established. |

Rule operators: `all`, `any`, `not`, `always`, and field tests with exactly one of `eq`, `in`,
`contains`, `intersects`, `gte`, `lte`, `present`. Fields are those of the mission profile (see
`app/app/planner/mission.py`).

## Check your change

```bash
cd app && uv run python -m app.planner.knowledge validate
```

The validator reports every problem at once: schema errors, unknown authorities or citations,
missing prerequisites and prerequisite cycles. CI runs it on every pull request.

## Ground rules

1. Quote the law; don't paraphrase it in `excerpt`. Link the official publisher.
2. If you can't verify something, leave it out or mark the duration `estimate`. Never guess a
   citation.
3. Contacts are institutional channels the authority publishes itself. No personal data scraped
   from elsewhere.
4. Facilitators describe themselves in their own words; no rankings.

Data licence: [LICENSE.md](./LICENSE.md) (CC BY 4.0 for our content; quoted texts keep their own
terms).
