"""Knowledge pack tests: the shipped pack validates, and the validator catches the mistakes a
contributor is likely to make (it reports all of them at once)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.planner.knowledge import (
    Citation,
    Duration,
    KnowledgeError,
    Rule,
    export_json_schema,
    load_knowledge,
)


def test_shipped_pack_is_valid() -> None:
    kb = load_knowledge()
    assert {"itu", "fr", "gb", "lu", "us"} <= set(kb.jurisdictions)
    assert len(kb.licenses) >= 15
    for lic in kb.licenses.values():
        assert lic.legal_basis, lic.id
        for c in lic.legal_basis:
            assert str(c.url).startswith("https://"), c.id
            assert c.excerpt.strip(), c.id


def test_every_citation_has_english_text() -> None:
    for c in load_knowledge().citations.values():
        assert c.language == "en" or c.excerpt_en, c.id


def _write(base: Path, rel: str, data: dict) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


_CITE = {"id": "xx.law.art-1", "instrument": "Law", "provision": "Art. 1",
         "url": "https://example.org/law", "retrieved": "2026-10-15", "language": "en",
         "excerpt": "An operator shall hold a licence."}
_DUR = {"min_weeks": 1, "typical_weeks": 2, "max_weeks": 3, "basis": "estimate"}


def _jurisdiction() -> dict:
    return {"id": "xx", "name": "Exampleland", "kind": "national", "country": "XX",
            "summary": "s", "status": "draft", "last_verified": "2026-10-15",
            "authorities": [{"id": "xx-reg", "name": "Regulator", "roles": ["space_activity_licensing"],
                             "website": "https://example.org"}]}


def _licence(lid: str, **over: object) -> dict:
    base = {"id": lid, "jurisdiction": "xx", "name": lid, "authority": "xx-reg",
            "category": "space_activity", "summary": "s",
            "applies_when": {"field": "operator_country", "eq": "XX", "cite": ["xx.law.art-1"]},
            "legal_basis": [{**_CITE, "id": f"xx.{lid}"}], "preparation": _DUR, "review": _DUR,
            "status": "draft", "last_verified": "2026-10-15"}
    base.update(over)
    return base


def test_validator_reports_all_cross_reference_problems(tmp_path: Path) -> None:
    _write(tmp_path, "jurisdictions/xx/jurisdiction.yaml", _jurisdiction())
    _write(tmp_path, "jurisdictions/xx/licenses/a.yaml",
           _licence("a", authority="nobody", prerequisites=[{"license": "b"}]))
    _write(tmp_path, "jurisdictions/xx/licenses/b.yaml",
           _licence("b", prerequisites=[{"license": "a"}, {"license": "ghost"}]))
    with pytest.raises(KnowledgeError) as exc:
        load_knowledge(tmp_path)
    text = str(exc.value)
    assert "unknown authority 'nobody'" in text
    assert "prerequisite 'ghost' does not exist" in text
    assert "prerequisite cycle" in text
    assert "unknown citation 'xx.law.art-1'" in text
    assert len(exc.value.problems) >= 4


def test_file_name_must_match_id(tmp_path: Path) -> None:
    _write(tmp_path, "jurisdictions/xx/jurisdiction.yaml", _jurisdiction())
    _write(tmp_path, "jurisdictions/xx/licenses/wrong-name.yaml", _licence("a"))
    with pytest.raises(KnowledgeError, match="must match its file name"):
        load_knowledge(tmp_path)


def test_unknown_keys_are_errors_not_silently_dropped(tmp_path: Path) -> None:
    _write(tmp_path, "jurisdictions/xx/jurisdiction.yaml", _jurisdiction())
    _write(tmp_path, "jurisdictions/xx/licenses/a.yaml", _licence("a", aplies_when={"always": True}))
    with pytest.raises(KnowledgeError, match="aplies_when"):
        load_knowledge(tmp_path)


@pytest.mark.parametrize("rule", [
    {},
    {"field": "orbit"},
    {"field": "orbit", "eq": "GEO", "in": ["LEO"]},
    {"field": "nonexistent", "eq": "x"},
    {"field": "orbit", "contains": "GEO"},
    {"field": "services", "eq": "fixed_satellite"},
    {"all": [], "field": "orbit", "eq": "GEO"},
])
def test_malformed_rules_are_rejected(rule: dict) -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(rule)


def test_non_english_citation_needs_translation() -> None:
    with pytest.raises(ValidationError, match="excerpt_en"):
        Citation.model_validate({**_CITE, "language": "fr"})


def test_duration_must_be_ordered_and_sourced() -> None:
    with pytest.raises(ValidationError, match="min_weeks"):
        Duration.model_validate({**_DUR, "min_weeks": 5})
    with pytest.raises(ValidationError, match="cite or a source"):
        Duration.model_validate({**_DUR, "basis": "statutory"})


def test_json_schema_export(tmp_path: Path) -> None:
    paths = export_json_schema(tmp_path)
    assert {p.name for p in paths} == {"jurisdiction.schema.json", "license.schema.json",
                                       "facilitator.schema.json"}
    assert '"applies_when"' in (tmp_path / "license.schema.json").read_text()


@pytest.mark.parametrize(("kind", "value"), [
    ("web_form", "javascript:alert(document.cookie)"),
    ("web", "http://example.org/not-https"),
    ("portal", "data:text/html,<script>x</script>"),
    ("email", "javascript:alert(1)//@x.org"),
    ("email", "not-an-email"),
    ("phone", "call me maybe"),
])
def test_contact_values_must_match_their_kind(kind: str, value: str) -> None:
    from app.planner.knowledge import ContactChannel

    with pytest.raises(ValidationError):
        ContactChannel.model_validate({"kind": kind, "value": value, "purpose": "p", "source": {
            "title": "t", "url": "https://example.org", "retrieved": "2026-10-15"}})


def test_valid_contact_values_pass() -> None:
    from app.planner.knowledge import ContactChannel

    src = {"title": "t", "url": "https://example.org", "retrieved": "2026-10-15"}
    for kind, value in (("web_form", "https://spacecare.cnes.fr/contact/"), ("email", "info@space-agency.lu"),
                        ("phone", "+352 288 482 10"), ("postal", "12C Impasse Drosbach, L-1882 Luxembourg")):
        ContactChannel.model_validate({"kind": kind, "value": value, "purpose": "p", "source": src})
