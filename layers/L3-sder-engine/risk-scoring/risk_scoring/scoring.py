"""Risk-scoring v0.1 — a deterministic, pure-function single-satellite score.

STUB methodology (see METHODOLOGY.md): not insurer-grade, pending actuarial review.
No I/O; deterministic in its inputs so it is trivially testable and reproducible for
regulator-facing runs.

v0.1 (post-review): the conjunction component now decays exponentially with miss
distance (collision risk is not linear in separation) at a realistic characteristic
distance, and folds in relative speed as a consequence multiplier.
"""

from __future__ import annotations

import math

from .models import RiskBand, RiskInputs, RiskScore

# Conjunction tuning (METHODOLOGY.md). Geometry risk = 100 * exp(-miss / CHAR_KM):
# 100 at a direct hit, ~37 at CHAR_KM, ~0 by ~5x CHAR_KM. CHAR_KM ~ a few km matches
# operational screening volumes (km-scale), unlike the old 50 km linear cutoff.
CHAR_KM = 2.0
# Relative-speed consequence multiplier: a fast (head-on LEO) pass is worse than a slow
# co-planar one. Scales geometry by [MIN_SPEED_FACTOR, 1.0] around a reference speed.
REF_SPEED_KMS = 10.0
MIN_SPEED_FACTOR = 0.3

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


def _speed_factor(relative_speed_km_s: float | None) -> float:
    """Consequence multiplier in [MIN_SPEED_FACTOR, 1.0]. Unknown speed → 1.0 (no
    discount, conservative)."""
    if relative_speed_km_s is None:
        return 1.0
    return _clamp(relative_speed_km_s / REF_SPEED_KMS, MIN_SPEED_FACTOR, 1.0)


def _conjunction_risk(min_miss_distance_km: float, relative_speed_km_s: float | None) -> float:
    geometry = 100.0 * math.exp(-min_miss_distance_km / CHAR_KM)
    return geometry * _speed_factor(relative_speed_km_s)


def _band(score: float) -> RiskBand:
    if score < _BAND_LOW_MAX:
        return RiskBand.LOW
    if score < _BAND_MEDIUM_MAX:
        return RiskBand.MEDIUM
    return RiskBand.HIGH


def score_satellite(inputs: RiskInputs) -> RiskScore:
    """Compute the v0.1 risk score and its weighted component breakdown."""
    conjunction = _conjunction_risk(inputs.min_miss_distance_km, inputs.relative_speed_km_s)
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
