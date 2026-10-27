"""FastAPI entrypoint: health probe and obligation list backed by Postgres.

Run locally:  uv run uvicorn main:app --app-dir app/api --reload
Container CMD (app/api/Dockerfile) runs the same module.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.api.auth import Principal, current_principal

OBLIGATIONS_SQL = """
    SELECT id, source, jurisdiction, article, text, rationale_code,
           effective_date, valid_to, review_status
    FROM obligations
    ORDER BY source, id
    LIMIT $1 OFFSET $2
"""


class ObligationOut(BaseModel):
    id: str
    source: str
    jurisdiction: str
    article: str
    text: str
    rationale_code: str
    effective_date: str
    valid_to: str | None
    review_status: str


class ObligationPage(BaseModel):
    items: list[ObligationOut]
    limit: int
    offset: int


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        # asyncpg wants a plain postgresql:// DSN; strip the SQLAlchemy driver suffix.
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
        app.state.pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    else:
        app.state.pool = None

    issuer = os.environ.get("ZITADEL_ISSUER")
    app.state.zitadel_issuer = issuer
    app.state.zitadel_audience = os.environ.get("ZITADEL_AUDIENCE")
    # Short timeout so a stalled issuer cannot hold request workers open.
    app.state.jwks_client = (
        jwt.PyJWKClient(f"{issuer.rstrip('/')}/oauth/v2/keys", timeout=5) if issuer else None
    )
    try:
        yield
    finally:
        if app.state.pool is not None:
            await app.state.pool.close()


app = FastAPI(title="complianceOS API", version="0.2.0", lifespan=lifespan)


def get_pool(request: Request) -> Any:
    # asyncpg.Pool is not subscriptable at runtime and FastAPI evaluates annotations,
    # so the pool is typed Any here. Narrow it again if asyncpg ships stubs.
    pool: Any = request.app.state.pool
    if pool is None:
        raise HTTPException(status_code=503, detail="database not configured")
    return pool


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/obligations", response_model=ObligationPage)
async def list_obligations(
    limit: int = 50,
    offset: int = 0,
    principal: Principal = Depends(current_principal),
    pool: Any = Depends(get_pool),
) -> ObligationPage:
    # principal.tenant is available here for the RLS step. The policy is not written yet.
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be >= 0")
    async with pool.acquire() as conn:
        rows = await conn.fetch(OBLIGATIONS_SQL, limit, offset)
    items = [
        ObligationOut(
            id=r["id"],
            source=r["source"],
            jurisdiction=r["jurisdiction"],
            article=r["article"],
            text=r["text"],
            rationale_code=r["rationale_code"],
            effective_date=r["effective_date"].isoformat(),
            valid_to=r["valid_to"].isoformat() if r["valid_to"] else None,
            review_status=r["review_status"],
        )
        for r in rows
    ]
    return ObligationPage(items=items, limit=limit, offset=offset)
