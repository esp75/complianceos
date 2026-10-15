# Agent instructions

The project rules for coding agents live in [`CLAUDE.md`](./CLAUDE.md). They apply to every agent
working in this repo, whichever tool or provider runs it. Read that file first; this one only adds
the rule that differs by provider.

## Agents backed by a non-Anthropic provider (e.g. Codex / OpenAI)

Files that start with the header below are reserved for paid external security review:

```
# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
```

They live under `app/app/api/trust/**`, `app/app/api/rls/**`, and `app/app/api/bundle/sign*.py`.
Do not read, send, or edit them from an agent whose model runs outside the EU-jurisdiction
Anthropic endpoint. Leave changes to those paths for a human or for Claude Code, and say so in
your output.

The product's runtime LLM policy (ADR-0010: Claude only, via the Anthropic EU endpoint) is about
what the application calls, not which coding agent you are. Do not change it.
