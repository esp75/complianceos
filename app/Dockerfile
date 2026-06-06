# Celestia BFF / orchestration layer (FastAPI). Python 3.12 per CLAUDE.md.
#
# Build context is the REPO ROOT (see cross-cutting/deploy/docker-compose.yml) because
# the BFF depends on the L3 packages under layers/ as uv path deps. They are placed at
# /layers so the `../layers/...` paths in app/pyproject.toml's [tool.uv.sources] resolve
# from the app project root at /srv.
FROM python:3.12-slim

# uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /srv

# L3 path deps first (they change less often than app code).
COPY layers/L3-sder-engine/itu-compliance /layers/L3-sder-engine/itu-compliance
COPY layers/L3-sder-engine/risk-scoring /layers/L3-sder-engine/risk-scoring

# Dependency manifest + lock next, for layer caching.
COPY app/pyproject.toml app/uv.lock ./
RUN uv sync --no-dev --no-install-project

# L1 framework YAMLs that L2 ingest reads (ADR-0014). CELESTIA_FRAMEWORKS_DIR points here.
COPY layers/L1-substrate/frameworks ./frameworks

# App source last.
COPY app/app ./app

ENV PATH="/srv/.venv/bin:$PATH"
ENV CELESTIA_FRAMEWORKS_DIR=/srv/frameworks
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
