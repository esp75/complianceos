from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.api.reggraph.loader import CorpusError, check_graph, load_corpus
from app.api.reggraph.models import Obligation

REPO_REGULATIONS = Path(__file__).resolve().parents[2] / "regulations"


def _ob(ob_id: str, **overrides: object) -> Obligation:
    base: dict[str, object] = {
        "id": ob_id,
        "source": "eu_space_act",
        "jurisdiction": "EU",
        "article": "Art. 1",
        "text": "Test obligation.",
        "rationale_code": "DEBRIS_MITIGATION",
        "effective_date": date(2025, 1, 1),
        "applicability": ["operator"],
        "citation": {"kind": "celex", "celex": "52025PC0335", "article": "1"},
    }
    base.update(overrides)
    return Obligation.model_validate(base)


def test_repo_regulations_load() -> None:
    obligations = load_corpus(REPO_REGULATIONS)
    assert obligations, "repo corpus should have at least the batch-1 EU Space Act entries"


def test_every_eu_space_act_entry_is_marked_proposal_only() -> None:
    # The EU Space Act is a Commission proposal. Nothing from it may read as adopted law.
    eu = [o for o in load_corpus(REPO_REGULATIONS) if o.source == "eu_space_act"]
    assert eu
    for ob in eu:
        assert "proposal-not-adopted" in ob.tags, ob.id
        assert ob.citation.celex == "52025PC0335", ob.id


def test_duplicate_ids_are_reported() -> None:
    problems = check_graph([_ob("A-1"), _ob("A-1")])
    assert any("duplicate" in p for p in problems)


def test_dangling_reference_is_reported() -> None:
    problems = check_graph([_ob("A-1", references=["NOPE-1"])])
    assert any("unknown obligation NOPE-1" in p for p in problems)


def test_supersedes_cycle_is_reported() -> None:
    a = _ob("A-1", supersedes=["A-2"])
    b = _ob("A-2", supersedes=["A-1"])
    assert any("cycle" in p for p in check_graph([a, b]))


def test_acyclic_supersedes_chain_passes() -> None:
    a = _ob("A-1", supersedes=["A-2"])
    b = _ob("A-2", supersedes=["A-3"])
    c = _ob("A-3")
    assert check_graph([a, b, c]) == []


def test_bad_rationale_code_fails_load(tmp_path: Path) -> None:
    for name in ("rationale_codes.yaml", "fcc_22_74.yaml", "itu_filings.yaml", "iso_24113.yaml"):
        (tmp_path / name).write_text(
            (REPO_REGULATIONS / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / "eu_space_act.yaml").write_text(
        """
source: eu_space_act
jurisdiction: EU
obligations:
  - id: EU-SPACE-ACT-ART-1
    source: eu_space_act
    jurisdiction: EU
    article: Art. 1
    text: x
    rationale_code: NOT_A_CODE
    effective_date: 2025-01-01
    applicability: [operator]
    citation: {kind: celex, celex: "52025PC0335", article: "1"}
""",
        encoding="utf-8",
    )
    with pytest.raises(CorpusError) as exc:
        load_corpus(tmp_path)
    assert any("NOT_A_CODE" in p for p in exc.value.problems)
