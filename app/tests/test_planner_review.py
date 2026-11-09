"""Dossier sections added for pilots (friction, decision makers, labels) and the reviewer package."""

from __future__ import annotations

import datetime as dt

from app.l4.citations import CitationError
from app.planner.brief import build_brief
from app.planner.knowledge import load_knowledge
from app.planner.plan import build_roadmap
from app.planner.review import dossier_markdown
from app.planner.sample import sample_mission

KB = load_knowledge()
TODAY = dt.date(2026, 11, 1)
ROADMAP = build_roadmap(KB, sample_mission(TODAY), TODAY)


async def test_new_sections_exist_and_every_paragraph_cites_a_pack_citation() -> None:
    brief = await build_brief(ROADMAP)
    by_id = {s.id: s for s in brief.sections}
    for sid in ("friction", "decision_makers"):
        sec = by_id[sid]
        assert sec.grounded and sec.paragraphs
        assert all("[cite:" in p for p in sec.paragraphs)
        assert len(sec.labels) == len(sec.paragraphs)
    cited = {c for s in brief.sections for p in s.paragraphs
             for c in __import__("re").findall(r"\[cite:([^\]]+)\]", p)}
    assert cited <= set(ROADMAP.citations)


async def test_every_labelled_paragraph_has_a_known_basis() -> None:
    brief = await build_brief(ROADMAP)
    for s in brief.sections:
        if s.labels:
            assert len(s.labels) == len(s.paragraphs)
            assert set(s.labels) <= {"statute", "practice", "estimate", "derived"}


async def test_friction_does_not_pretend_to_know_past_objections() -> None:
    brief = await build_brief(ROADMAP)
    text = " ".join(next(s for s in brief.sections if s.id == "friction").paragraphs).lower()
    assert "objected" not in text and "historically" not in text


async def test_review_package_is_stable_and_has_checklist_and_zero_uncited() -> None:
    brief = await build_brief(ROADMAP)
    first = dossier_markdown(ROADMAP, brief)
    assert first == dossier_markdown(ROADMAP, brief)
    assert "Reviewer checklist" in first and "- [ ] Each quoted provision matches the source" in first
    assert "without a citation: 0" in first
    assert "[cite:" not in first  # markers are rendered as plain ids for a human reader
    for item in ROADMAP.items:
        for cid in item.legal_basis:
            assert f"`{cid}`" in first and str(ROADMAP.citations[cid].url) in first


def test_citation_error_is_still_exported() -> None:
    assert issubclass(CitationError, Exception)
