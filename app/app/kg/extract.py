"""Claude-as-extractor (ADR-0014): turn unstructured regulation text into typed RASE
obligations. Uses the LLM provider when configured; offline it does a deterministic naive
extraction so the capability is exercisable with no key.

This is the v0 stand-in for the ADR-0006 LEGAL-BERT three-head pipeline (deferred). The KG
population for the drafting DoD comes from the structured-framework ingest (ingest.py); this
path demonstrates extraction from raw text.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from app.llm.base import LLMError, LLMProvider

_DEONTIC_RE = re.compile(r"\b(SHALL NOT|MUST NOT|SHALL|MUST|SHOULD|MAY)\b", re.IGNORECASE)

_SYSTEM = (
    "You are a regulatory-NLP extractor for space law. Extract obligations using the RASE "
    "scheme (Requirement, Applicability, Selection, Exception) and deontic modality "
    "(SHALL/MUST/SHOULD/MAY/MUST_NOT). Return ONLY a JSON array, no prose."
)


class ExtractedObligation(BaseModel):
    ref_code: str
    framework: str
    title: str
    deontic: str = ""
    requirement: str = ""
    applicability: str = ""
    selection: str = ""
    exception: str = ""
    evidence_types: list[str] = Field(default_factory=list)


def _guess_deontic(text: str) -> str:
    m = _DEONTIC_RE.search(text)
    return m.group(1).upper().replace(" ", "_") if m else ""


def _first_sentence(text: str) -> str:
    s = text.strip().split(".", 1)[0]
    return (s[:117] + "...") if len(s) > 120 else s


def _strip_code_fence(out: str) -> str:
    out = out.strip()
    if out.startswith("```"):
        out = re.sub(r"^```[a-z]*\n?|\n?```$", "", out)
    return out.strip()


async def extract_obligations(
    text: str, *, framework: str, llm: LLMProvider | None
) -> list[ExtractedObligation]:
    if not text.strip():
        return []
    if llm is None:
        # Deterministic offline extraction: one obligation from the passage.
        return [
            ExtractedObligation(
                ref_code=f"{framework}::extracted-1",
                framework=framework,
                title=_first_sentence(text),
                deontic=_guess_deontic(text),
                requirement=text.strip(),
            )
        ]
    prompt = (
        f"Framework: {framework}\nText:\n{text}\n\n"
        'Return a JSON array of objects with keys: ref_code, title, deontic, requirement, '
        "applicability, selection, exception, evidence_types (array)."
    )
    raw = await llm.complete(_SYSTEM, prompt)
    try:
        data = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise LLMError(f"extractor returned non-JSON: {exc}") from exc
    return [ExtractedObligation(framework=framework, **{k: v for k, v in o.items() if k != "framework"}) for o in data]
