import pytest

from risk_scoring.models import RiskBand, RiskInputs
from risk_scoring.scoring import score_satellite


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
    # direct hit -> geometry 100, no speed discount; conjunction 50 + maturity 16
    # + compliance 7.5 + disposal 15 = 88.5
    assert result.score == pytest.approx(88.5)
    assert result.band is RiskBand.HIGH


def test_score_is_monotonic_in_miss_distance() -> None:
    # Closer approach must never lower the score (all else equal).
    scores = [score_satellite(_inputs(min_miss_distance_km=d)).score for d in (0.0, 1.0, 5.0, 25.0, 100.0)]
    assert scores == sorted(scores, reverse=True)


def test_conjunction_decays_to_zero_by_operational_distance() -> None:
    # Exponential decay: a routine multi-km pass contributes ~no conjunction risk,
    # unlike the old linear curve which scored a 25 km pass at 50/100.
    close = score_satellite(_inputs(min_miss_distance_km=0.0)).breakdown["conjunction"]
    routine = score_satellite(_inputs(min_miss_distance_km=20.0)).breakdown["conjunction"]
    assert close == pytest.approx(50.0)  # 0.5 * 100
    assert routine == pytest.approx(0.0, abs=0.01)


def test_relative_speed_raises_conjunction_risk() -> None:
    # Same miss distance: a fast head-on pass is higher-consequence than a slow one.
    slow = score_satellite(_inputs(min_miss_distance_km=1.0, relative_speed_km_s=2.0)).score
    fast = score_satellite(_inputs(min_miss_distance_km=1.0, relative_speed_km_s=14.0)).score
    assert fast > slow


def test_unknown_speed_applies_no_discount() -> None:
    # Unknown speed must be conservative: same as a reference-speed (factor 1.0) pass.
    unknown = score_satellite(_inputs(min_miss_distance_km=1.0)).breakdown["conjunction"]
    full = score_satellite(_inputs(min_miss_distance_km=1.0, relative_speed_km_s=10.0)).breakdown["conjunction"]
    assert unknown == pytest.approx(full)


def test_unknown_maturity_treated_as_early_stage() -> None:
    unknown = score_satellite(_inputs(filing_maturity="something_else")).breakdown["maturity"]
    early = score_satellite(_inputs(filing_maturity="early_stage")).breakdown["maturity"]
    assert unknown == pytest.approx(early)


def test_band_thresholds() -> None:
    # Drive score purely via conjunction (other components zero): score = 0.5 * geometry.
    low = score_satellite(_inputs(min_miss_distance_km=20.0))  # geometry ~0 -> score ~0
    assert low.band is RiskBand.LOW
    # A sub-km miss lands in medium: geometry(0.5)=~77.9 -> score ~38.9
    medium = score_satellite(_inputs(min_miss_distance_km=0.5))
    assert medium.band is RiskBand.MEDIUM
    # Direct hit + non-compliant slot -> high
    high = score_satellite(_inputs(min_miss_distance_km=0.0, itu_compliant=False, disposal_compliant=False))
    assert high.band is RiskBand.HIGH


def test_breakdown_sums_to_score() -> None:
    result = score_satellite(
        _inputs(min_miss_distance_km=1.0, filing_maturity="late_stage", itu_compliant=False)
    )
    assert result.score == pytest.approx(sum(result.breakdown.values()))
