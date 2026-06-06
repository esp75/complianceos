from pathlib import Path

import pytest

from itu_compliance.compliance import (
    OrbitRegime,
    RegimeNotSupportedError,
    assess_compliance,
    longitudinal_distance,
    proximity_check,
)
from itu_compliance.snl_client import parse

FIXTURE = Path(__file__).parent / "fixtures" / "networks_sample.csv"
FILINGS = parse(FIXTURE.read_text())


def test_longitudinal_distance_wraps_antimeridian() -> None:
    assert longitudinal_distance(10.0, 10.0) == 0.0
    assert longitudinal_distance(10.0, 11.0) == pytest.approx(1.0)
    # 179.8 and -179.9 are 0.3 deg apart, not 359.7.
    assert longitudinal_distance(179.8, -179.9) == pytest.approx(0.3)


def test_compliant_when_brought_into_use_filing_within_threshold() -> None:
    # Satellite at 10.0: ALPHA-1 (non-planned, brought into use) is co-located.
    result = proximity_check(10.0, FILINGS)
    assert result.compliant is True
    assert result.best_match is not None
    assert result.best_match.network_name == "ALPHA-1"


def test_not_compliant_when_only_early_stage_nearby() -> None:
    # Satellite at 50.0: ZETA-6 is co-located but only early-stage.
    result = proximity_check(50.0, FILINGS)
    assert result.compliant is False
    assert result.best_match is None
    assert any(n.filing.network_name == "ZETA-6" for n in result.nearby)


def test_not_compliant_when_brought_into_use_but_outside_threshold() -> None:
    # Satellite at 100.0: ETA-7 is brought into use but 0.7 deg away (> 0.5 non-planned).
    result = proximity_check(100.0, FILINGS)
    assert result.compliant is False
    assert any(n.filing.network_name == "ETA-7" for n in result.nearby)


def test_wraparound_compliance_near_antimeridian() -> None:
    # Satellite at 179.8: THETA-8 at -179.9 is 0.3 deg away, brought into use.
    result = proximity_check(179.8, FILINGS)
    assert result.compliant is True
    assert result.best_match is not None
    assert result.best_match.network_name == "THETA-8"


def test_no_nearby_filings_is_not_compliant() -> None:
    result = proximity_check(0.0, FILINGS)
    assert result.compliant is False
    assert result.nearby == []
    assert "No space networks" in result.note


def test_non_geo_regime_not_supported() -> None:
    for regime in (OrbitRegime.LEO, OrbitRegime.MEO, OrbitRegime.HEO):
        with pytest.raises(RegimeNotSupportedError):
            assess_compliance(10.0, FILINGS, regime=regime)
