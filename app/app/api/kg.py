"""L2 knowledge-graph endpoints (ADR-0014).

- POST /kg/ingest    materialize the loaded frameworks into the KG (idempotent).
- POST /kg/extract   Claude-as-extractor over raw regulation text -> RASE obligations.
- GET  /kg/obligations?q=  pgvector ANN search over obligations.

Authenticated; platform-admin scoping is a Phase-4 hardening (the KG holds framework data,
not tenant data). All three 503 when the `kg` profile is not running.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import current_user, get_embed, get_llm, require_kg
from app.clients.kg import KGClient
from app.config import get_settings
from app.kg.embeddings import EmbeddingProvider
from app.kg.extract import ExtractedObligation, extract_obligations
from app.kg.ingest import ingest_frameworks
from app.llm.base import LLMProvider

router = APIRouter(prefix="/kg", tags=["kg"])


class ExtractRequest(BaseModel):
    text: str
    framework: str = "adhoc"


@router.post("/ingest")
async def ingest(
    user: Annotated[dict[str, Any], Depends(current_user)],
    kg: Annotated[KGClient, Depends(require_kg)],
    embed: Annotated[EmbeddingProvider, Depends(get_embed)],
) -> dict[str, Any]:
    return await ingest_frameworks(kg, embed, frameworks_dir=get_settings().frameworks_dir or None)


@router.post("/extract")
async def extract(
    body: ExtractRequest,
    user: Annotated[dict[str, Any], Depends(current_user)],
    llm: Annotated[LLMProvider | None, Depends(get_llm)],
) -> list[ExtractedObligation]:
    return await extract_obligations(body.text, framework=body.framework, llm=llm)


@router.get("/obligations")
async def search_obligations(
    user: Annotated[dict[str, Any], Depends(current_user)],
    kg: Annotated[KGClient, Depends(require_kg)],
    embed: Annotated[EmbeddingProvider, Depends(get_embed)],
    q: Annotated[str, Query(description="natural-language query")],
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[dict[str, Any]]:
    hits = await kg.search_obligations(embed.embed(q), limit)
    return [
        {"ref_code": h["ref_code"], "framework": h["framework"], "content": h["content"],
         "distance": round(float(h["distance"]), 4)}
        for h in hits
    ]
