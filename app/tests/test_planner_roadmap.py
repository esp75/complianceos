"""Planner scenarios on the shipped knowledge pack: which licences a mission gets and why, the
roadmap's shape for the sample mission, and the brief's citation grounding (including a model that
tries to invent a citation)."""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any

import pytest

from app.l4.citations import CitationError, extract_cited_ids
from app.planner.brief import build_brief
from app.planner.knowledge import Rule, load_knowledge
from app.planner.mission import MissionProfile
from app.planner.plan import build_roadmap
from app.planner.rules import evaluate, required_licenses

KB = load_knowledge()
TODAY = dt.date(2026, 10, 15)


def mission(**over: Any) -> MissionProfile:
    base: dict[str, Any] = {
        "name": "Test mission", "operator_country": "LU", "orbit": "LEO", "altitude_km": 550,
        "satellite_count": 8, "services": ["earth_exploration_satellite"],
        "frequency_bands": ["S", "X"], "target_launch_date": dt.date(2029, 6, 1),
    }
    base.update(over)
    return MissionProfile(**base)


def ids(m: MissionProfile) -> set[str]:
    return {r.license.id for r in required_licenses(KB, m)}


# --- rule operators ---

@pytest.mark.parametrize(("rule", "facts", "expected"), [
    ({"field": "orbit", "eq": "GEO"}, {"orbit": "GEO"}, True),
    ({"field": "orbit", "eq": "GEO"}, {"orbit": "LEO"}, False),
    ({"field": "orbit", "in": ["LEO", "MEO"]}, {"orbit": "MEO"}, True),
    ({"field": "service_countries", "contains": "US"}, {"service_countries": ["FR", "US"]}, True),
    ({"field": "service_countries", "contains": "US"}, {"service_countries": []}, False),
    ({"field": "services", "intersects": ["fixed_satellite"]}, {"services": ["fixed_satellite"]}, True),
    ({"field": "satellite_count", "lte": 10}, {"satellite_count": 10}, True),
    ({"field": "satellite_count", "gte": 11}, {"satellite_count": 10}, False),
    ({"field": "altitude_km", "lte": 600}, {"altitude_km": None}, False),
    ({"field": "launch_country", "present": False}, {"launch_country": None}, True),
    ({"not": {"field": "orbit", "eq": "GEO"}}, {"orbit": "LEO"}, True),
    ({"always": True}, {}, True),
])
def test_rule_operators(rule: dict, facts: dict, expected: bool) -> None:
    assert evaluate(Rule.model_validate(rule), facts).matched is expected


def test_reasons_come_only_from_matching_branches() -> None:
    rule = Rule.model_validate({"any": [
        {"field": "launch_country", "eq": "FR", "because": "launch"},
        {"field": "operator_country", "eq": "FR", "because": "operator"},
    ], "cite": ["c1"]})
    m = evaluate(rule, {"launch_country": None, "operator_country": "FR"})
    assert [r.text for r in m.reasons] == ["operator"]
    assert m.reasons[0].cite == ("c1",)


# --- which licences apply ---

def test_luxembourg_operator_gets_space_authorisation_and_concession() -> None:
    got = ids(mission())
    assert {"lu-space-activity-authorisation", "lu-satellite-system-concession",
            "itu-advance-publication", "itu-notification"} <= got
    assert "itu-coordination-request" not in got
    assert not any(i.startswith(("fr-", "gb-", "us-")) for i in got)


def test_french_operator_gets_los_anfr_and_frequency_authorisation() -> None:
    got = ids(mission(operator_country="FR"))
    assert {"fr-los-authorisation", "fr-anfr-satellite-frequency-filing",
            "fr-satellite-frequency-operating-authorisation"} <= got


def test_launching_from_france_needs_los_whoever_operates() -> None:
    assert "fr-los-authorisation" in ids(mission(launch_country="FR"))


def test_uk_control_centre_triggers_caa_licence_for_a_foreign_operator() -> None:
    assert "gb-orbital-operator-licence" in ids(mission(control_country="GB"))


def test_geo_broadband_goes_through_coordination_not_api() -> None:
    got = ids(mission(orbit="GEO", altitude_km=35786, satellite_count=1,
                      services=["fixed_satellite"], frequency_bands=["Ka"]))
    assert "itu-coordination-request" in got and "itu-advance-publication" not in got


def test_us_small_satellite_vs_standard_route() -> None:
    small = ids(mission(operator_country="US", satellite_count=4, altitude_km=500))
    large = ids(mission(operator_country="US", satellite_count=40, altitude_km=500))
    assert "us-fcc-small-satellite-licence" in small and "us-fcc-space-station-licence" not in small
    assert "us-fcc-space-station-licence" in large and "us-fcc-small-satellite-licence" not in large


def test_serving_the_us_with_a_foreign_licence_needs_market_access() -> None:
    assert "us-fcc-market-access" in ids(mission(service_countries=["US"]))
    assert "us-fcc-market-access" not in ids(mission(operator_country="US", service_countries=["US"]))


def test_us_imaging_operator_needs_noaa_licence() -> None:
    assert "us-noaa-remote-sensing-licence" in ids(mission(operator_country="US",
                                                           earth_observation_imaging=True))
    assert "us-noaa-remote-sensing-licence" not in ids(mission(earth_observation_imaging=True))


def test_res35_milestones_only_for_ngso_broadband_in_listed_bands() -> None:
    constellation = mission(services=["fixed_satellite"], frequency_bands=["Ka"], satellite_count=200)
    req = {r.license.id: r for r in required_licenses(KB, constellation)}
    obligations = {o.id for o in req["itu-coordination-request"].obligations}
    assert {"itu-res35-milestone-1", "itu-res35-milestone-3"} <= obligations
    geo = mission(orbit="GEO", services=["fixed_satellite"], frequency_bands=["Ka"], satellite_count=1)
    geo_req = {r.license.id: r for r in required_licenses(KB, geo)}
    assert not any(o.id.startswith("itu-res35")
                   for o in geo_req["itu-coordination-request"].obligations)


# --- roadmap ---

SAMPLE = mission(name="Sample EO constellation", ground_station_countries=["GB", "US"],
                 service_countries=["FR", "GB", "US"], earth_observation_imaging=True,
                 services=["earth_exploration_satellite", "space_operation"],
                 target_launch_date=dt.date(2028, 9, 1))


def test_sample_roadmap_golden() -> None:
    r = build_roadmap(KB, SAMPLE, TODAY)
    assert [i.license_id for i in r.items] == [
        "lu-satellite-system-concession", "itu-advance-publication", "us-fcc-market-access",
        "lu-space-activity-authorisation", "us-fcc-earth-station-licence", "itu-notification",
        "gb-ofcom-earth-station-licence",
    ]
    assert r.critical_path == ["lu-satellite-system-concession", "itu-advance-publication",
                               "itu-notification"]
    assert [j.id for j in r.jurisdictions] == ["itu", "lu", "gb", "us"]
    assert all(i.risk != "late" for i in r.items)
    assert any("Launch site not chosen" in w for w in r.warnings)


def test_roadmap_ships_every_citation_it_references() -> None:
    r = build_roadmap(KB, SAMPLE, TODAY)
    referenced = {c for i in r.items for c in i.legal_basis}
    referenced |= {c for i in r.items for reason in i.reasons for c in reason.cite}
    referenced |= {c for i in r.items for o in i.obligations for c in o.cite}
    assert referenced <= set(r.citations)


def test_launch_too_soon_is_flagged_late() -> None:
    soon = SAMPLE.model_copy(update={"target_launch_date": dt.date(2027, 6, 1)})
    r = build_roadmap(KB, soon, TODAY)
    assert any(i.risk == "late" for i in r.items)
    assert any("cannot be granted" in w for w in r.warnings)


def test_uncovered_countries_are_named_in_warnings() -> None:
    r = build_roadmap(KB, SAMPLE.model_copy(update={"service_countries": ["BR", "JP"]}), TODAY)
    assert any("BR" in w for w in r.warnings) and any("JP" in w for w in r.warnings)


def test_lu_obligations_are_dated() -> None:
    r = build_roadmap(KB, SAMPLE, TODAY)
    lu = next(i for i in r.items if i.license_id == "lu-space-activity-authorisation")
    use = next(o for o in lu.obligations if o.id == "lu-use-within-36-months")
    assert use.when == "36 months after grant"
    assert use.due == dt.date(lu.earliest_grant.year + 3, lu.earliest_grant.month, lu.earliest_grant.day)
    annual = [o for o in lu.obligations if o.id == "lu-annual-fee"]
    assert len(annual) == 10 and annual[1].due.year == annual[0].due.year + 1


# --- brief ---

class FakeLLM:
    def __init__(self, text: str) -> None:
        self.text = text

    async def complete(self, system: str, prompt: str) -> str:
        return self.text


def test_deterministic_brief_is_grounded() -> None:
    r = build_roadmap(KB, SAMPLE, TODAY)
    b = asyncio.run(build_brief(r))
    assert b.mode == "deterministic"
    grounded = [s for s in b.sections if s.grounded]
    assert grounded and all(s.paragraphs for s in grounded if s.id != "risks")
    for s in grounded:
        for p in s.paragraphs:
            assert extract_cited_ids(p), (s.id, p)
            assert set(extract_cited_ids(p)) <= set(b.citations)


def test_llm_brief_with_valid_citations_is_used() -> None:
    r = build_roadmap(KB, SAMPLE, TODAY)
    text = ("Start with the Luxembourg concession [cite:lu.media1991.art-20].\n\n"
            "Then the ITU advance publication [cite:itu.rr.9-1].")
    b = asyncio.run(build_brief(r, FakeLLM(text)))
    assert b.mode == "llm" and len(b.sections[0].paragraphs) == 2


def test_llm_brief_with_invented_citation_is_rejected() -> None:
    r = build_roadmap(KB, SAMPLE, TODAY)
    with pytest.raises(CitationError, match="not retrieved"):
        asyncio.run(build_brief(r, FakeLLM("All set [cite:us.cfr47.25-999].")))


def test_llm_brief_with_uncited_paragraph_is_rejected() -> None:
    r = build_roadmap(KB, SAMPLE, TODAY)
    with pytest.raises(CitationError, match="paragraph 2"):
        asyncio.run(build_brief(r, FakeLLM("Fine [cite:itu.rr.9-1].\n\nNo licence is needed in France.")))
