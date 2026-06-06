"""Citation enforcer (Phase-3 DoD): a draft must cite >=2 L2 obligations + >=1 L1 evidence
record, and every cited source must be backed by a Context Core. A draft that fails
validation never reaches output (ADR-0014).
"""

from __future__ import annotations

from typing import Any

MIN_OBLIGATIONS = 2
MIN_EVIDENCE = 1


class CitationError(ValueError):
    """Raised when a draft does not meet the citation-grounding requirements."""


def enforce_citations(
    obligation_refs: list[str], evidence_ids: list[str], context_cores: list[dict[str, Any]]
) -> None:
    if len(obligation_refs) < MIN_OBLIGATIONS:
        raise CitationError(
            f"draft cites {len(obligation_refs)} obligation(s); >= {MIN_OBLIGATIONS} required"
        )
    if len(evidence_ids) < MIN_EVIDENCE:
        raise CitationError(
            f"draft cites {len(evidence_ids)} evidence record(s); >= {MIN_EVIDENCE} required"
        )
    backed = {(c["source_type"], c["source_ref"]) for c in context_cores}
    for ref in obligation_refs:
        if ("obligation", ref) not in backed:
            raise CitationError(f"no Context Core for cited obligation {ref!r}")
    for eid in evidence_ids:
        if ("evidence", eid) not in backed:
            raise CitationError(f"no Context Core for cited evidence {eid!r}")
