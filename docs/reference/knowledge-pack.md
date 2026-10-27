# Knowledge pack reference

The knowledge pack is the open, cited licensing dataset the planner reads. Its full description,
including the field table and the rule language, is in
[`knowledge/README.md`](../../knowledge/README.md). This page lists the schema at a glance.

## Layout

```
knowledge/
  jurisdictions/<id>/jurisdiction.yaml    authorities and official contact channels
  jurisdictions/<id>/licenses/<id>.yaml   one licence, authorisation or filing
  facilitators/<id>.yaml                  licensing firms
  schema/                                 JSON Schema files
  VERIFICATION.md                         how each record was checked
  LICENSE.md                              CC BY 4.0 for the data
```

## Licence record

Schema: [`knowledge/schema/license.schema.json`](../../knowledge/schema/license.schema.json).

| Field | Type | Meaning |
|---|---|---|
| `id`, `jurisdiction`, `name`, `name_local` | string | Identity |
| `authority` | string | Issuing body (must exist in the jurisdiction file) |
| `category` | string | Kind of instrument |
| `summary` | string | Plain-language description |
| `applies_when` | rule | When the licence is needed. Each branch can carry `because` and `cite` |
| `legal_basis` | citation[] | Sources quoted in the record |
| `prerequisites` | prerequisite[] | Licences this one waits for, with a `stage` |
| `needed_by` | string | When the licence is needed in the mission |
| `submission_window` | object | Earliest filing, counted back from need |
| `preparation`, `review` | duration | Weeks, with `basis` |
| `documents`, `fees` | object | Required documents and fee information |
| `obligations` | obligation[] | Dated duties that follow |
| `requires_local_presence`, `local_presence_note` | boolean, string | Whether a local entity is needed |
| `status` | string | `draft` until reviewed |
| `last_verified`, `reviewed_by`, `sources` | | Verification trail |

### Citation

| Field | Meaning |
|---|---|
| `instrument`, `provision` | The text and the article |
| `url` | Official source |
| `retrieved` | Date the text was checked |
| `language` | Language of the quoted text |
| `excerpt` | Verbatim quote |
| `excerpt_en` | English rendering, for non-English texts. Mark it as an unofficial translation |

### Duration

| Field | Meaning |
|---|---|
| `min_weeks`, `typical_weeks`, `max_weeks` | Range |
| `basis` | `statutory`, `practice` or `estimate` |
| `note`, `cite`, `source` | Explanation and where it comes from |

## Validation

```bash
cd app && uv run python -m app.planner.knowledge validate
```

The validator checks the schema, that every authority and citation resolves, that prerequisites exist,
and that the prerequisite graph has no cycles.
