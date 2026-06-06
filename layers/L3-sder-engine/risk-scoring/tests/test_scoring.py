import pytest

from risk_scoring.models import RiskBand, RiskInputs
from risk_scoring.scoring import SAFE_KM, score_satellite


def _inputs(**kw: object) -> RiskInputs:
    base: dict[str, object] = {
        "min_miss_distance_km": 100.0,
        "filing_maturity": "brought_into_use",
        "itu_compliant": True,
        "disposal_compliant": True,
    }
    base.update(kw)
    return RiskInputs(**base)  # type: ignore[arg-type]


def test_best_case_is_low_risk() -> None:
    # Far miss, brought into use, compliant, disposal ok -> ~0.
    result = score_satellite(_inputs())
    assert result.score == pytest.approx(0.0)
    assert result.band is RiskBand.LOW


def test_worst_case_is_high_risk() -> None:
    result = score_satellite(
        _inputs(
            min_miss_distance_km=0.0,
            filing_maturity="suspended",
            itu_compliant=False,
            disposal_compliant=False,
        )
    )
    # conjunction 50 + maturity 16 + compliance 7.5 + disposal 15 = 88.5
    assert result.score == pytest.approx(88.5)
    assert result.band is RiskBand.HIGH


def test_score_is_monotonic_in_miss_distance() -> None:
    # Closer approach must never lower the score (all else equal).
    scores = [score_satellite(_inputs(min_miss_distance_km=d)).score for d in (0.0, 10.0, 25.0, 50.0, 100.0)]
    assert scores == sorted(scores, reverse=True)


def test_conjunction_zero_at_or_beyond_safe_distance() -> None:
    at_safe = score_satellite(_inputs(min_miss_distance_km=SAFE_KM)).breakdown["conjunction"]
    beyond = score_satellite(_inputs(min_miss_distance_km=SAFE_KM * 2)).breakdown["conjunction"]
    assert at_safe == pytest.approx(0.0)
    assert beyond == pytest.approx(0.0)


def test_unknown_maturity_treated_as_early_stage() -> None:
    unknown = score_satellite(_inputs(filing_maturity="something_else")).breakdown["maturity"]
    early = score_satellite(_inputs(filing_maturity="early_stage")).breakdown["maturity"]
    assert unknown == pytest.approx(early)


def test_band_thresholds() -> None:
    # Drive score purely via conjunction (other components zero): score = 0.5 * conjunction.
    low = score_satellite(_inputs(min_miss_distance_km=40.0))  # conj=20 -> score 10
    assert low.band is RiskBand.LOW
    # conj such that score lands in medium: miss=15 -> conj=70 -> score 35
    medium = score_satellite(_inputs(min_miss_distance_km=15.0))
    assert medium.band is RiskBand.MEDIUM
    # miss=0 -> conj=100 -> score 50 (medium); push to high with a non-compliant slot
    high = score_satellite(_inputs(min_miss_distance_km=0.0, itu_compliant=False, disposal_compliant=False))
    assert high.band is RiskBand.HIGH


def test_breakdown_sums_to_score() -> None:
    result = score_satellite(
        _inputs(min_miss_distance_km=10.0, filing_maturity="late_stage", itu_compliant=False)
    )
    assert result.score == pytest.approx(sum(result.breakdown.values()))
