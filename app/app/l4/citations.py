"""Citation enforcement.

Two checks, both of which must pass before generated text reaches a user:

- :func:`enforce_text_citations` reads the generated text itself. Every source it cites must be one
  the caller retrieved (no invented references) and, by default, every paragraph must cite
  something (no unsupported claims). Citations are inline markers: ``[cite:<id>]``.
- :func:`enforce_citations` checks grounding of what the text cites (Phase-3 DoD): >=2 L2
  obligations + >=1 L1 evidence record, each backed by a Context Core (ADR-0014).

A draft that fails either check never reaches output.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from typing import Any

MIN_OBLIGATIONS = 2
MIN_EVIDENCE = 1

#: ``[cite:<id>]``; ids may contain spaces and punctuation (e.g. ``ISO 24113 §6.4``) but not ``]``.
CITE_MARKER = re.compile(r"\[cite:([^\]]+)\]")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


class CitationError(ValueError):
    """Raised when a draft does not meet the citation-grounding requirements."""


def extract_cited_ids(text: str) -> list[str]:
    """Cited ids in order of first appearance, without duplicates."""
    seen: dict[str, None] = {}
    for m in CITE_MARKER.finditer(text):
        seen.setdefault(m.group(1).strip(), None)
    return list(seen)


def enforce_text_citations(
    text: str, allowed_ids: Collection[str], *, every_paragraph: bool = True
) -> list[str]:
    """Validate the citations written in ``text`` and return them.

    Raises :class:`CitationError` if the text cites an id outside ``allowed_ids``, cites nothing,
    or (with ``every_paragraph``) has a paragraph without a citation.
    """
    cited = extract_cited_ids(text)
    unknown = [c for c in cited if c not in allowed_ids]
    if unknown:
        raise CitationError(f"draft cites source(s) that were not retrieved: {unknown}")
    if not cited:
        raise CitationError("draft cites no source")
    if every_paragraph:
        paragraphs = [p for p in _PARAGRAPH_SPLIT.split(text.strip()) if p.strip()]
        for n, para in enumerate(paragraphs, start=1):
            if not CITE_MARKER.search(para):
                raise CitationError(f"paragraph {n} makes claims without a citation")
    return cited


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
