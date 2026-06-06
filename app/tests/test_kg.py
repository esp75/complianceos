"""L2 KG-router tests: ingest parses the real framework YAMLs into a stub KG; extract runs
the deterministic offline path; search returns stub ANN hits. No live kg-postgres."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import kg
from app.kg.embeddings import HashingEmbedding

AUTH = {"Authorization": "Bearer good"}


class StubOpenlane:
    async def get_self(self, token: str) -> dict[str, Any]:
        return {"id": "01U", "email": "u@celestia.eu"} if token == "good" else {}


class StubKG:
    def __init__(self) -> None:
        self.nodes: list[str] = []
        self.evidence_edges: list[tuple[str, str]] = []
        self.cites_edges: list[tuple[str, str]] = []
        self.embeddings: list[str] = []

    async def ping(self) -> bool:
        return True

    async def upsert_obligation_embedding(self, ref_code, framework, content, embedding):  # noqa: ANN001
        self.embeddings.append(ref_code)

    async def merge_obligation_node(self, ref_code, framework, title, deontic):  # noqa: ANN001
        self.nodes.append(ref_code)

    async def merge_evidence_edge(self, ref_code, evidence_type, framework):  # noqa: ANN001
        self.evidence_edges.append((ref_code, evidence_type))

    async def merge_cites_edge(self, ref_code, cites_ref):  # noqa: ANN001
        self.cites_edges.append((ref_code, cites_ref))

    async def search_obligations(self, query_embedding, limit=5):  # noqa: ANN001
        return [
            {"ref_code": "ISO 24113 §6.2", "framework": "iso-24113",
             "content": "Post-mission disposal ...", "distance": 0.42}
        ]


def _client(*, kg_stub: StubKG | None = None) -> tuple[httpx.AsyncClient, StubKG]:
    app = FastAPI()
    stub = kg_stub or StubKG()
    app.state.openlane = StubOpenlane()
    app.state.kg = stub
    app.state.embed = HashingEmbedding()
    app.state.llm = None
    app.include_router(kg.router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t"), stub


@pytest.mark.asyncio
async def test_ingest_materializes_loaded_frameworks() -> None:
    client, stub = _client()
    async with client as c:
        r = await c.post("/kg/ingest", headers=AUTH)
        assert r.status_code == 200
        out = r.json()
        assert out["obligations"] > 0
        assert out["frameworks"] >= 3  # iso-24113, itu, eu-space-act
    # nodes + embeddings written; ISO 24113 obligations present
    assert any(n.startswith("ISO 24113") for n in stub.nodes)
    assert len(stub.embeddings) == out["obligations"]
    assert stub.evidence_edges  # REQUIRES_EVIDENCE edges materialized


@pytest.mark.asyncio
async def test_extract_offline_returns_one_obligation() -> None:
    client, _ = _client()
    async with client as c:
        r = await c.post("/kg/extract", json={"text": "The operator SHALL dispose of the satellite.",
                                              "framework": "iso-24113"}, headers=AUTH)
        assert r.status_code == 200
        obs = r.json()
        assert len(obs) == 1
        assert obs[0]["deontic"] == "SHALL"
        assert "dispose" in obs[0]["requirement"]


@pytest.mark.asyncio
async def test_search_returns_ann_hits() -> None:
    client, _ = _client()
    async with client as c:
        r = await c.get("/kg/obligations", params={"q": "how is disposal evidenced"}, headers=AUTH)
        assert r.status_code == 200
        assert r.json()[0]["ref_code"] == "ISO 24113 §6.2"


@pytest.mark.asyncio
async def test_kg_endpoints_503_when_kg_down() -> None:
    class DownKG(StubKG):
        async def ping(self) -> bool:
            return False

    client, _ = _client(kg_stub=DownKG())
    async with client as c:
        r = await c.post("/kg/ingest", headers=AUTH)
        assert r.status_code == 503
