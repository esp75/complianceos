"""Context Cores — provenance for every cited source (ADR-0005).

Each source a draft cites (obligation or evidence record) gets a context_core row recording
how it entered the draft, so "every claim has a Context Core" (Phase-3 DoD). v0 granularity is
per-source; per-sentence provenance is a v0.1 refinement (ADR-0014).
"""

from __future__ import annotations

from typing import Any

from app.clients.kg import KGClient


async def record_context_cores(
    kg: KGClient,
    draft_id: str,
    *,
    obligation_refs: list[str],
    evidence_ids: list[str],
    derivation: str,
) -> int:
    """Write one Context Core per cited source. Returns the number written."""
    written = 0
    for ref in obligation_refs:
        await kg.insert_context_core(draft_id, "obligation", ref, derivation)
        written += 1
    for eid in evidence_ids:
        await kg.insert_context_core(draft_id, "evidence", eid, derivation)
        written += 1
    return written


async def fetch_manifest(kg: KGClient, draft_id: str) -> list[dict[str, Any]]:
    """The provenance manifest for a draft (its Context Cores)."""
    return await kg.fetch_context_cores(draft_id)
