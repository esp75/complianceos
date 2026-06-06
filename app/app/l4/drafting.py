"""L4 drafting — produce a one-paragraph compliance assertion citing the retrieved
obligations + the org's evidence (Phase-3 DoD).

Uses the LLM provider when configured (Anthropic EU, ADR-0010); offline it templates a
cited paragraph deterministically, so the DoD is demonstrable with no key and no US LLM
call (ADR-0014). Either way the output cites obligations by ref_code and evidence by name,
which the citation enforcer then validates.
"""

from __future__ import annotations

from typing import Any

from app.l4.retrieval import RetrievedObligation
from app.llm.base import LLMProvider

_SYSTEM = (
    "You are a regulatory compliance drafter for satellite operators. Write ONE paragraph "
    "asserting the organization's compliance with the question. Cite every applicable "
    "obligation by its ref_code and every supporting evidence record by name. Make no claim "
    "that is not backed by a cited obligation or evidence record."
)


def _render_obligations(obligations: list[RetrievedObligation]) -> str:
    return "\n".join(f"- {o.ref_code} ({o.framework}): {o.content}" for o in obligations)


def _render_evidence(evidence: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {e['name']} (id {e['id']})" for e in evidence)


async def draft_paragraph(
    query: str,
    obligations: list[RetrievedObligation],
    evidence: list[dict[str, Any]],
    llm: LLMProvider | None,
) -> str:
    if llm is None:
        ob_str = "; ".join(f"{o.ref_code} ({o.framework})" for o in obligations)
        ev_str = ", ".join(e["name"] for e in evidence)
        return (
            f"Regarding '{query}': the applicable obligations are {ob_str}. The organization's "
            f"compliance is evidenced by {ev_str}. Each cited obligation and evidence record is "
            f"traceable to its source via the attached Context Cores."
        )
    prompt = (
        f"Question: {query}\n\nApplicable obligations:\n{_render_obligations(obligations)}\n\n"
        f"Organization evidence:\n{_render_evidence(evidence)}\n\n"
        "Draft a one-paragraph compliance assertion citing >=2 obligations (by ref_code) and "
        ">=1 evidence record (by name)."
    )
    return await llm.complete(_SYSTEM, prompt)
