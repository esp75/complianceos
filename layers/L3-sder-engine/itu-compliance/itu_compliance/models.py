"""Typed models for the ITU compliance port (ADR-0009).

Replaces the upstream's pandas-dataframe-as-everything with explicit pydantic models
so the SDER router and risk-scoring consume typed objects, not positional CSV rows.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .filing_maturity import FilingMaturity


class Filing(BaseModel):
    """One ITU space-network filing, as parsed from the SNL networks export.

    Longitude is the GEO nominal orbital position in degrees East (negative = West),
    in the range [-180, 180]. ``maturity`` is the highest maturity the filing has
    reached (see :class:`FilingMaturity`).
    """

    network_name: str
    longitude_deg: float = Field(ge=-180.0, le=180.0)
    itu_administration: str
    planned: bool = False
    maturity: FilingMaturity = FilingMaturity.EARLY_STAGE
    link: str | None = None


class NearbyFiling(BaseModel):
    """A filing found within tolerance of a satellite, plus its longitudinal distance."""

    filing: Filing
    longitudinal_distance_deg: float = Field(ge=0.0)


class ComplianceResult(BaseModel):
    """Outcome of a GEO proximity / compliance check for one satellite.

    ``compliant`` is the headline verdict. ``best_match`` is the protecting filing
    (if any), and ``nearby`` is the full shortlist within tolerance, nearest first.
    ``note`` is a human-readable explanation suitable for an evidence record.
    """

    compliant: bool
    satellite_longitude_deg: float
    best_match: Filing | None = None
    nearby: list[NearbyFiling] = Field(default_factory=list)
    note: str
