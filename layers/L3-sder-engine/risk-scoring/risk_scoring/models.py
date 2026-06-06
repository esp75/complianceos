"""Typed inputs/outputs for risk-scoring v0. See METHODOLOGY.md."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskInputs(BaseModel):
    """Signals fed into the v0 score.

    ``filing_maturity`` is the string value of ``itu_compliance.FilingMaturity`` (the
    package is kept decoupled — see METHODOLOGY.md); unknown values are treated
    conservatively as ``early_stage``.
    """

    min_miss_distance_km: float = Field(ge=0.0)
    filing_maturity: str
    itu_compliant: bool
    disposal_compliant: bool = True


class RiskScore(BaseModel):
    """The v0 risk score: 0–100 (higher = riskier), a coarse band, and a per-component
    breakdown of the weighted contributions so the portal can explain the number."""

    score: float = Field(ge=0.0, le=100.0)
    band: RiskBand
    breakdown: dict[str, float]
