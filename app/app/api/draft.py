"""L4 drafting endpoint — closes the Phase-3 DoD.

POST /draft/obligation: given a compliance question for an org, retrieve the applicable L2
obligations (dual-level), gather the org's L1 evidence, draft a one-paragraph assertion citing
>=2 obligations + >=1 evidence, record a Context Core per cited source, and enforce citation
grounding before returning. Gated on can_view (the tetrad's read scope).

v0 drafting is not yet under app/api/trust/ — it migrates there with the MARKED-FOR-EXTERNAL-
REVIEW header when PAdES signing lands (ADR-0014).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import (
    assert_can,
    current_user,
    get_embed,
    get_llm,
    get_openfga,
    get_openlane,
    require_kg,
)
from app.clients.kg import KGClient
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient
from app.kg.embeddings import EmbeddingProvider
from app.l4.citations import CitationError, enforce_citations
from app.l4.drafting import draft_paragraph
from app.l4.provenance import fetch_manifest, record_context_cores
from app.l4.retrieval import retrieve
from app.llm.base import LLMProvider

router = APIRouter(prefix="/draft", tags=["draft"])

_MAX_OBLIGATIONS = 4
_MAX_EVIDENCE = 3


class DraftRequest(BaseModel):
    org_id: str
    query: str


async def _org_evidence(openlane: OpenlaneClient, token: str, org_id: str) -> list[dict[str, Any]]:
    data = await openlane.execute(
        "query($o:ID!){ evidences(where:{ownerID:$o}){ edges{ node{ id displayID name } } } }",
        {"o": org_id}, token=token,
    )
    return [e["node"] for e in data.get("evidences", {}).get("edges", [])]


@router.post("/obligation")
async def draft_obligation(
    body: DraftRequest,
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
    openfga: Annotated[OpenFGAClient, Depends(get_openfga)],
    kg: Annotated[KGClient, Depends(require_kg)],
    embed: Annotated[EmbeddingProvider, Depends(get_embed)],
    llm: Annotated[LLMProvider | None, Depends(get_llm)],
) -> dict[str, Any]:
    await assert_can(openfga, user, "can_view", f"organization:{body.org_id}")

    retrieval = await retrieve(kg, embed, body.query, k=3)
    obligations = retrieval.obligations[:_MAX_OBLIGATIONS]
    evidence = (await _org_evidence(openlane, user["_token"], body.org_id))[:_MAX_EVIDENCE]

    obligation_refs = [o.ref_code for o in obligations]
    evidence_ids = [e["id"] for e in evidence]

    draft_id = uuid.uuid4().hex
    text = await draft_paragraph(body.query, obligations, evidence, llm)

    # Provenance first, then enforce — a draft that fails grounding never reaches output.
    await record_context_cores(
        kg, draft_id, obligation_refs=obligation_refs, evidence_ids=evidence_ids,
        derivation="dual-level-retrieval+drafting",
    )
    cores = await fetch_manifest(kg, draft_id)
    try:
        enforce_citations(obligation_refs, evidence_ids, cores)
    except CitationError as exc:
        raise HTTPException(
            status_code=422,  # Unprocessable Content — draft failed citation grounding
            detail=f"draft failed citation grounding: {exc}",
        ) from exc

    return {
        "draft_id": draft_id,
        "draft": text,
        "citations": {
            "obligations": [{"ref_code": o.ref_code, "framework": o.framework, "level": o.level}
                            for o in obligations],
            "evidence": [{"id": e["id"], "name": e["name"]} for e in evidence],
            "evidence_types": retrieval.evidence_types,
        },
        "context_cores": [
            {"source_type": c["source_type"], "source_ref": c["source_ref"], "derivation": c["derivation"]}
            for c in cores
        ],
    }
