"""L4 drafting tests: the citation enforcer (pure) + the /draft/obligation endpoint with a
stub KG, openlane, and openfga. LLM is offline (deterministic template). No live services."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import draft
from app.kg.embeddings import HashingEmbedding
from app.l4.citations import CitationError, enforce_citations

AUTH = {"Authorization": "Bearer good"}


# --- citation enforcer (pure) ---

def _cores(*pairs: tuple[str, str]) -> list[dict[str, Any]]:
    return [{"source_type": t, "source_ref": r} for t, r in pairs]


def test_enforce_passes_with_two_obligations_one_evidence() -> None:
    enforce_citations(
        ["A", "B"], ["E1"],
        _cores(("obligation", "A"), ("obligation", "B"), ("evidence", "E1")),
    )


def test_enforce_fails_with_one_obligation() -> None:
    with pytest.raises(CitationError, match="obligation"):
        enforce_citations(["A"], ["E1"], _cores(("obligation", "A"), ("evidence", "E1")))


def test_enforce_fails_with_no_evidence() -> None:
    with pytest.raises(CitationError, match="evidence"):
        enforce_citations(["A", "B"], [], _cores(("obligation", "A"), ("obligation", "B")))


def test_enforce_fails_when_context_core_missing() -> None:
    with pytest.raises(CitationError, match="Context Core"):
        enforce_citations(["A", "B"], ["E1"], _cores(("obligation", "A"), ("evidence", "E1")))


# --- endpoint ---

class StubOpenlane:
    def __init__(self, *, evidence: list[dict[str, Any]]) -> None:
        self._evidence = evidence

    async def get_self(self, token: str) -> dict[str, Any]:
        return {"id": "01U", "email": "u@celestia.eu"} if token == "good" else {}

    async def execute(self, query: str, variables: dict | None = None, *, token: str | None = None) -> dict[str, Any]:
        if "evidences(where" in query:
            return {"evidences": {"edges": [{"node": e} for e in self._evidence]}}
        return {}


class StubOpenFGA:
    def __init__(self, allow: bool) -> None:
        self._allow = allow

    async def check(self, user: str, relation: str, obj: str, *, context: dict | None = None) -> bool:
        return self._allow


class StubKG:
    def __init__(self) -> None:
        self.cores: list[dict[str, Any]] = []

    async def ping(self) -> bool:
        return True

    async def search_obligations(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        return [
            {"ref_code": "ISO 24113 §6.4", "framework": "iso-24113", "content": "collisions", "distance": 0.3},
            {"ref_code": "ISO 24113 §6.2", "framework": "iso-24113", "content": "disposal", "distance": 0.5},
        ]

    async def cited_neighbors(self, ref_codes: list[str]) -> list[str]:
        return []

    async def fetch_obligations(self, ref_codes: list[str]) -> list[dict[str, Any]]:
        return []

    async def evidence_types_for(self, ref_codes: list[str]) -> list[str]:
        return ["conjunction-report"]

    async def insert_context_core(self, draft_id, source_type, source_ref, derivation):  # noqa: ANN001
        self.cores.append({"draft_id": draft_id, "source_type": source_type,
                           "source_ref": source_ref, "derivation": derivation})

    async def fetch_context_cores(self, draft_id: str) -> list[dict[str, Any]]:
        return [c for c in self.cores if c["draft_id"] == draft_id]


def _client(*, allow: bool, evidence: list[dict[str, Any]]) -> httpx.AsyncClient:
    app = FastAPI()
    app.state.openlane = StubOpenlane(evidence=evidence)
    app.state.openfga = StubOpenFGA(allow)
    app.state.kg = StubKG()
    app.state.embed = HashingEmbedding()
    app.state.llm = None
    app.include_router(draft.router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


_EVIDENCE = [{"id": "01E", "displayID": "EVD-1", "name": "conjunction_report 2026"}]


@pytest.mark.asyncio
async def test_draft_cites_obligations_and_evidence_with_context_cores() -> None:
    async with _client(allow=True, evidence=_EVIDENCE) as c:
        r = await c.post("/draft/obligation",
                         json={"org_id": "01O", "query": "is the operator collision-compliant"}, headers=AUTH)
        assert r.status_code == 200, r.text
        out = r.json()
        assert len(out["citations"]["obligations"]) >= 2
        assert len(out["citations"]["evidence"]) >= 1
        # every cited source has a Context Core
        cored = {(c["source_type"], c["source_ref"]) for c in out["context_cores"]}
        for o in out["citations"]["obligations"]:
            assert ("obligation", o["ref_code"]) in cored
        assert ("evidence", "01E") in cored
        # the draft text cites the obligations
        assert "ISO 24113 §6.4" in out["draft"]


@pytest.mark.asyncio
async def test_draft_denied_without_view() -> None:
    async with _client(allow=False, evidence=_EVIDENCE) as c:
        r = await c.post("/draft/obligation", json={"org_id": "01O", "query": "x"}, headers=AUTH)
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_draft_422_when_no_evidence_to_ground_claim() -> None:
    async with _client(allow=True, evidence=[]) as c:
        r = await c.post("/draft/obligation", json={"org_id": "01O", "query": "x"}, headers=AUTH)
        assert r.status_code == 422
        assert "citation grounding" in r.json()["detail"]
