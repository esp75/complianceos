# The 4-role tetrad (operator / insurer / regulator / admin)

How Celestia realizes its four audience roles on top of theopenlane's embedded
OpenFGA model **without patching the upstream model** (ADR-0001, ADR-0012).

theopenlane's `organization` type ships `admin / member / owner` plus an
object-creator pattern: `<obj>_creator: [group#member]` and
`can_create_<obj>: can_edit or <obj>_creator`. We map the tetrad onto these
primitives using **Groups + relationship tuples**, and enforce what the model
can't express (cross-org insurer/regulator scoping) at the **BFF boundary**.

## Mapping

| Tetrad role | Org membership | Group | Extra tuple | Net OpenFGA capability |
|---|---|---|---|---|
| **admin** | `ADMIN` | Administrators | — | `can_edit` ⇒ `can_create_*`, `audit_log_viewer`, manage org |
| **operator** | `MEMBER` | Operators (wired as `evidence/control/standard_creator`) | — | `can_create_evidence/control/standard`, `can_view`; **not** `can_edit` |
| **insurer** | `MEMBER` | Insurers | — | `can_view` only (read); creation denied. BFF scopes to underwritten orgs. |
| **regulator** | `MEMBER` | Regulators | `user:<id> audit_log_viewer organization:<id>` | `can_view` + `audit_log_viewer`; creation denied. BFF scopes by jurisdiction. |

Why groups for `operator` (not a direct grant): the model only accepts
`[group#member]` for `<obj>_creator`. Adding a user to the Operators group — which is
wired onto the org via `updateOrganization(addEvidenceCreatorIDs/...)` — grants
`can_create_*` through `evidence_creator`, no `can_edit` needed.

Why a direct tuple for `regulator`: `audit_log_viewer` accepts `[user, service]`
directly and theopenlane exposes no mutation for it, so the seeder writes the tuple
to the same FGA store via the OpenFGA write API.

## Enforcement split (ADR-0012)

- **In OpenFGA**: create vs read vs admin capability, per the table above.
- **At the BFF** (`app/api/...`, `app/clients/openfga.py`): cross-org scoping the
  upstream model has no concept of — which orgs an insurer may underwrite, which
  jurisdiction/orgs a regulator may audit. This is trust-critical authorization in
  Python; flag it for the Phase 5 external review even though it is not under
  `app/api/trust/**`.

## Verification

`app/app/auth/seed_tetrad.py` builds a demo org + the four groups + demo users and
asserts the matrix via OpenFGA `/check`:

- operator → `can_create_evidence` = allowed; `audit_log_viewer` = denied
- insurer → `can_create_evidence` = denied; `can_view` = allowed
- regulator → `audit_log_viewer` = allowed; `can_create_evidence` = denied
- admin → `can_create_evidence` = allowed; `audit_log_viewer` = allowed

See `seed-tuples.yaml` for the declarative role→group→relation summary.

## SSO note

Login is theopenlane built-in auth (email/password) for dev. Dex SSO requires
per-org enforcement config and is not wired for the dev bootstrap; a self-hosted
EU IdP (Authentik/Keycloak) is the Phase 4 production path (ADR-0012).
