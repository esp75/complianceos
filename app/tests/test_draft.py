"""L4 drafting tests: the citation enforcer (pure) + the /draft/obligation endpoint with a
stub KG, openlane, and openfga. LLM is offline (deterministic template). No live services."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import draft
from app.kg.embeddings import HashingEmbedding
from app.l4.citations import CitationError, enforce_citations, enforce_text_citations, extract_cited_ids

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


# --- text citation enforcer (pure) ---

def test_extract_cited_ids_in_order_without_duplicates() -> None:
    text = "A [cite:ISO 24113 §6.4] and [cite:evidence:01E], again [cite:ISO 24113 §6.4]."
    assert extract_cited_ids(text) == ["ISO 24113 §6.4", "evidence:01E"]


def test_text_enforcer_rejects_invented_source() -> None:
    with pytest.raises(CitationError, match="not retrieved"):
        enforce_text_citations("Claim [cite:made-up §1].", {"real §1"})


def test_text_enforcer_rejects_uncited_text() -> None:
    with pytest.raises(CitationError, match="no source"):
        enforce_text_citations("A confident claim with no source.", {"real §1"})


def test_text_enforcer_rejects_uncited_paragraph() -> None:
    text = "First claim [cite:real §1].\n\nSecond claim with nothing behind it."
    with pytest.raises(CitationError, match="paragraph 2"):
        enforce_text_citations(text, {"real §1"})


def test_text_enforcer_accepts_cited_paragraphs() -> None:
    text = "First [cite:a].\n\nSecond [cite:b] and [cite:a]."
    assert enforce_text_citations(text, {"a", "b"}) == ["a", "b"]


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


class StubLLM:
    """Returns a fixed completion, to simulate what a live model might write."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def complete(self, system: str, prompt: str) -> str:
        return self._text


def _client(*, allow: bool, evidence: list[dict[str, Any]], llm: StubLLM | None = None) -> httpx.AsyncClient:
    app = FastAPI()
    app.state.openlane = StubOpenlane(evidence=evidence)
    app.state.openfga = StubOpenFGA(allow)
    app.state.kg = StubKG()
    app.state.embed = HashingEmbedding()
    app.state.llm = llm
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


@pytest.mark.asyncio
async def test_draft_422_when_model_invents_a_citation() -> None:
    invented = StubLLM(
        "Compliant per [cite:ISO 24113 §6.4], [cite:ISO 24113 §6.2] and [cite:FCC 47 CFR 25.283] "
        "as shown by [cite:evidence:01E]."
    )
    async with _client(allow=True, evidence=_EVIDENCE, llm=invented) as c:
        r = await c.post("/draft/obligation", json={"org_id": "01O", "query": "x"}, headers=AUTH)
        assert r.status_code == 422
        assert "not retrieved" in r.json()["detail"]


@pytest.mark.asyncio
async def test_draft_422_when_model_cites_nothing() -> None:
    uncited = StubLLM("The operator is fully compliant with every applicable obligation.")
    async with _client(allow=True, evidence=_EVIDENCE, llm=uncited) as c:
        r = await c.post("/draft/obligation", json={"org_id": "01O", "query": "x"}, headers=AUTH)
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_draft_returns_only_what_the_text_cites() -> None:
    partial = StubLLM(
        "Disposal and collision duties apply [cite:ISO 24113 §6.4] [cite:ISO 24113 §6.2], "
        "evidenced by [cite:evidence:01E]."
    )
    async with _client(allow=True, evidence=_EVIDENCE, llm=partial) as c:
        r = await c.post("/draft/obligation", json={"org_id": "01O", "query": "x"}, headers=AUTH)
        assert r.status_code == 200, r.text
        refs = {o["ref_code"] for o in r.json()["citations"]["obligations"]}
        assert refs == {"ISO 24113 §6.4", "ISO 24113 §6.2"}
