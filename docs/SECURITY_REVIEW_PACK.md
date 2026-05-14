# External security review pack

Quarantined surface for the Phase 5 paid external review (Trail of Bits / Quarkslab / Cure53 / Doyensec).

Every file in this pack carries the header:
```
# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
```

## In scope

- `app/api/trust/**` — ed25519 signing chain, Merkle audit log.
- `app/api/rls/**` — Postgres Row-Level Security policies for multi-tenant isolation.
- `app/api/bundle/sign*.py` — PAdES B-LTA signed PDF generation, EU timestamp authority integration.

## Out of scope

Everything else. The reviewer's brief is the trust boundary only; product features are not in scope.

## Constraints

- No file in this pack may be sent to OpenAI Codex, US-jurisdiction LLMs, or any external code-completion service.
- The build agent (Claude Code) running under EU-jurisdiction Anthropic endpoints is permitted to edit these files. All edits to files in this pack must be reviewed in PR by Max before merge.
