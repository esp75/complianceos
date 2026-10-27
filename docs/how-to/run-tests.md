# How to run the test suites

The API and the web app have separate suites. CI runs both, plus the knowledge-pack validator and a
secret scan.

## API (Python 3.12, FastAPI)

```bash
cd app
uv sync
uv run ruff check .
uv run mypy app
uv run pytest
uv run python -m app.planner.knowledge validate
```

- Property-based tests (hypothesis) check the scheduler over random prerequisite graphs.
- `tests/test_planner_store.py` needs a Postgres instance. Set `CELESTIA_PG_TEST_DSN` to run it;
  otherwise it is skipped. CI provides one.

## Web (Next.js 14, TypeScript)

```bash
cd web
bun install
bun run typecheck
bun run lint
bun test
bun run build
```

## Knowledge pack

```bash
cd app && uv run python -m app.planner.knowledge validate
```

This runs schema validation, cross-reference checks and prerequisite-cycle detection. It is the first
thing to run after editing anything in `knowledge/`.

## Secret scan

CI runs gitleaks with the configuration in [`.gitleaks.toml`](../../.gitleaks.toml). Run it locally
before pushing if you have gitleaks installed:

```bash
gitleaks detect --config .gitleaks.toml --redact
```
