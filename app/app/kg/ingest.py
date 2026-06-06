"""L2 ingest: materialize the loaded framework YAMLs into the knowledge graph (ADR-0014).

v0 reads the same authored YAMLs L1 was loaded from (reusing the framework loader's parser)
and writes Obligation nodes + embeddings + CITES/REQUIRES_EVIDENCE edges. Deterministic, no
LLM — this is what populates the KG for the drafting DoD. The Claude extractor (extract.py)
handles unstructured text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.clients.kg import KGClient
from app.kg.embeddings import EmbeddingProvider
from app.loaders.framework_loader import FRAMEWORKS_DIR, load_framework_dir
from app.loaders.schema import ControlDoc


def obligation_content(ctrl: ControlDoc) -> str:
    """The text a compliance question matches against: title + requirement + applicability
    (falling back to the description). See RASE-celestia.md."""
    rase = ctrl.spec.rase
    parts = [ctrl.metadata.display_name]
    if rase and rase.requirement:
        parts.append(rase.requirement)
    if rase and rase.applicability:
        parts.append(rase.applicability)
    if len(parts) == 1:
        parts.append(ctrl.spec.description)
    return " ".join(p.strip() for p in parts if p)


def _discover(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    return sorted(d for d in base.iterdir() if (d / "framework.yaml").exists())


async def ingest_frameworks(
    kg: KGClient, emb: EmbeddingProvider, *, frameworks_dir: str | None = None
) -> dict[str, Any]:
    """Ingest every framework dir into the KG. Idempotent (MERGE + upsert)."""
    base = Path(frameworks_dir) if frameworks_dir else FRAMEWORKS_DIR
    dirs = _discover(base)
    obligations = 0
    for d in dirs:
        _, controls, _ = load_framework_dir(d)
        for ctrl in controls:
            ref = ctrl.metadata.citation
            framework = ctrl.metadata.framework
            content = obligation_content(ctrl)
            await kg.upsert_obligation_embedding(ref, framework, content, emb.embed(content))
            await kg.merge_obligation_node(
                ref, framework, ctrl.metadata.display_name, ctrl.spec.deontic_modality or ""
            )
            evidence_types = sorted({e for sub in ctrl.spec.controls for e in sub.evidence_required})
            for et in evidence_types:
                await kg.merge_evidence_edge(ref, et, framework)
            for xref in ctrl.spec.cross_references:
                await kg.merge_cites_edge(ref, xref)
            obligations += 1
    return {"frameworks": len(dirs), "obligations": obligations, "source": str(base)}
