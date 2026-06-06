"""Risk-scoring v0 — a deterministic, pure-function single-satellite score.

STUB methodology (see METHODOLOGY.md): not insurer-grade, pending actuarial review.
No I/O; deterministic in its inputs so it is trivially testable and reproducible for
regulator-facing runs.
"""

from __future__ import annotations

from .models import RiskBand, RiskInputs, RiskScore

# Component tuning (METHODOLOGY.md).
SAFE_KM = 50.0  # separation at/above which conjunction risk is zero

_MATURITY_RISK: dict[str, float] = {
    "brought_into_use": 0.0,
    "late_stage": 30.0,
    "early_stage": 60.0,
    "suspended": 80.0,
}
_UNKNOWN_MATURITY_RISK = _MATURITY_RISK["early_stage"]  # conservative default

# Weights — sum to 1.0 so the score stays in [0, 100].
_W_CONJUNCTION = 0.50
_W_MATURITY = 0.20
_W_COMPLIANCE = 0.15
_W_DISPOSAL = 0.15

_BAND_LOW_MAX = 34.0
_BAND_MEDIUM_MAX = 67.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _conjunction_risk(min_miss_distance_km: float) -> float:
    return _clamp(100.0 * (1.0 - min_miss_distance_km / SAFE_KM), 0.0, 100.0)


def _band(score: float) -> RiskBand:
    if score < _BAND_LOW_MAX:
        return RiskBand.LOW
    if score < _BAND_MEDIUM_MAX:
        return RiskBand.MEDIUM
    return RiskBand.HIGH


def score_satellite(inputs: RiskInputs) -> RiskScore:
    """Compute the v0 risk score and its weighted component breakdown."""
    conjunction = _conjunction_risk(inputs.min_miss_distance_km)
    maturity = _MATURITY_RISK.get(inputs.filing_maturity, _UNKNOWN_MATURITY_RISK)
    compliance = 0.0 if inputs.itu_compliant else 50.0
    disposal = 0.0 if inputs.disposal_compliant else 100.0

    breakdown = {
        "conjunction": round(_W_CONJUNCTION * conjunction, 2),
        "maturity": round(_W_MATURITY * maturity, 2),
        "compliance": round(_W_COMPLIANCE * compliance, 2),
        "disposal": round(_W_DISPOSAL * disposal, 2),
    }
    score = round(sum(breakdown.values()), 2)
    return RiskScore(score=score, band=_band(score), breakdown=breakdown)
