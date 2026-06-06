"""L4 dual-level retrieval tests with a stub KG (no live kg-postgres)."""

from __future__ import annotations

from typing import Any

import pytest

from app.kg.embeddings import HashingEmbedding
from app.l4.retrieval import retrieve


class StubKG:
    async def search_obligations(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        return [
            {"ref_code": "ISO 24113 §6.4", "framework": "iso-24113",
             "content": "Prevention of on-orbit collisions", "distance": 0.30},
            {"ref_code": "ISO 24113 §6.2", "framework": "iso-24113",
             "content": "Post-mission disposal", "distance": 0.50},
        ]

    async def cited_neighbors(self, ref_codes: list[str]) -> list[str]:
        # §6.4 CITES §6.2 (already local) and EU-SA Art.5 (new global neighbor)
        return ["ISO 24113 §6.2", "EU-SA Art.5"]

    async def fetch_obligations(self, ref_codes: list[str]) -> list[dict[str, Any]]:
        rows = {"EU-SA Art.5": {"ref_code": "EU-SA Art.5", "framework": "eu-space-act",
                                "content": "Debris mitigation and collision avoidance duties"}}
        return [rows[r] for r in ref_codes if r in rows]

    async def evidence_types_for(self, ref_codes: list[str]) -> list[str]:
        return ["conjunction-report", "disposal-telemetry", "conjunction-report"]


@pytest.mark.asyncio
async def test_dual_level_fuses_local_and_global() -> None:
    result = await retrieve(StubKG(), HashingEmbedding(), "collision avoidance evidence", k=2)
    refs = [o.ref_code for o in result.obligations]
    # 2 local vector hits + 1 graph-expanded neighbor (the already-local §6.2 is not duplicated)
    assert refs == ["ISO 24113 §6.4", "ISO 24113 §6.2", "EU-SA Art.5"]
    levels = {o.ref_code: o.level for o in result.obligations}
    assert levels["ISO 24113 §6.4"] == "local"
    assert levels["EU-SA Art.5"] == "global"


@pytest.mark.asyncio
async def test_local_hits_outrank_global_neighbors() -> None:
    result = await retrieve(StubKG(), HashingEmbedding(), "collision", k=2)
    local_scores = [o.score for o in result.obligations if o.level == "local"]
    global_scores = [o.score for o in result.obligations if o.level == "global"]
    assert min(local_scores) > max(global_scores)


@pytest.mark.asyncio
async def test_evidence_types_deduplicated_and_sorted() -> None:
    result = await retrieve(StubKG(), HashingEmbedding(), "disposal", k=2)
    assert result.evidence_types == ["conjunction-report", "disposal-telemetry"]
