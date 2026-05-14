# Architecture

Placeholder. Will be filled in during Phase 2 after the reg-graph YAML is complete.

Components:
- `app/api/ingest` — CDM ingest from ESA/SDA/USSF.
- `app/api/rag` — citation-forced retrieval over the reg-graph KG.
- `app/api/trust` — ed25519 signing + Merkle audit chain. **MARKED-FOR-EXTERNAL-REVIEW.**
- `app/api/rls` — multi-tenant Postgres RLS. **MARKED-FOR-EXTERNAL-REVIEW.**
- `app/api/bundle` — signed PAdES PDF evidence bundles. **MARKED-FOR-EXTERNAL-REVIEW.**
- `app/web` — Next.js operator dashboard + read-only authority view.
- `mcps/*` — custom MCP servers used by the build agent.
