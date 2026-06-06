"""GEO ITU proximity / compliance check (ADR-0009, ported from compliance_daily.py).

The upstream issues a compliance rating for a GEO satellite given its longitude by
scanning ITU filings for a nearby, sufficiently-mature, administration-matched network.
This port keeps the defensible geometric core — longitudinal proximity with antimeridian
wraparound and the planned/non-planned station-keeping thresholds — and the maturity gate
(a protecting filing must be brought into use, not suspended).

v0 scope (ADR-0013): GEO only. Administration-match and due-diligence scoring (which need
SpaceTrack country tables) are deferred. LEO/MEO/HEO proximity has no authoritative ITU
data source yet (ADR-0009 open question) and raises :class:`RegimeNotSupportedError`.
"""

from __future__ import annotations

from enum import StrEnum

from .filing_maturity import is_protected
from .models import ComplianceResult, Filing, NearbyFiling

# Station-keeping tolerances from ITU Radio Regulations Article 22, Section III, as used
# by the upstream monitor.
NEARBY_TOLERANCE_DEG = 1.0  # shortlist any filing within 1.0 deg
PLANNED_THRESHOLD_DEG = 0.1  # a Planned network protects within 0.1 deg (22.6-22.8)
NONPLANNED_THRESHOLD_DEG = 0.5  # a Non-Planned network protects within 0.5 deg (22.11-22.13)


class OrbitRegime(StrEnum):
    """Orbital regime of the satellite under assessment."""

    GEO = "geo"
    LEO = "leo"
    MEO = "meo"
    HEO = "heo"


class RegimeNotSupportedError(NotImplementedError):
    """Raised when compliance is requested for a regime not assessed in v0 (non-GEO)."""


def longitudinal_distance(a_deg: float, b_deg: float) -> float:
    """Absolute angular distance in degrees between two GEO longitudes, with
    antimeridian wraparound (so 179 and -179 are 2 deg apart, not 358)."""
    d = abs(a_deg - b_deg)
    if d > 180.0:
        d = 360.0 - d
    return d


def _protection_threshold(filing: Filing) -> float:
    return PLANNED_THRESHOLD_DEG if filing.planned else NONPLANNED_THRESHOLD_DEG


def proximity_check(
    satellite_longitude_deg: float,
    filings: list[Filing],
    *,
    tolerance_deg: float = NEARBY_TOLERANCE_DEG,
) -> ComplianceResult:
    """Assess a GEO satellite's ITU compliance from its longitude and the SNL filings.

    Returns a :class:`ComplianceResult`: ``compliant`` is True iff some filing within its
    station-keeping threshold is brought into use (and not suspended). ``nearby`` is every
    filing within ``tolerance_deg``, nearest first.
    """
    nearby = sorted(
        (
            NearbyFiling(
                filing=f,
                longitudinal_distance_deg=longitudinal_distance(satellite_longitude_deg, f.longitude_deg),
            )
            for f in filings
            if longitudinal_distance(satellite_longitude_deg, f.longitude_deg) <= tolerance_deg
        ),
        key=lambda n: n.longitudinal_distance_deg,
    )

    # A protecting filing must be brought-into-use (not suspended) AND within its
    # type-appropriate threshold. Pick the closest such filing.
    protectors = [
        n
        for n in nearby
        if is_protected(n.filing.maturity)
        and n.longitudinal_distance_deg <= _protection_threshold(n.filing)
    ]

    if protectors:
        best = protectors[0]
        kind = "planned" if best.filing.planned else "non-planned"
        return ComplianceResult(
            compliant=True,
            satellite_longitude_deg=satellite_longitude_deg,
            best_match=best.filing,
            nearby=nearby,
            note=(
                f"A {kind} space network ({best.filing.network_name}) within "
                f"{best.longitudinal_distance_deg:.3f} deg is brought into use, complying with "
                "ITU Radio Regulations Article 22, Section III."
            ),
        )

    if not nearby:
        note = (
            "No space networks within station-keeping requirements; this satellite is not "
            "protected from harmful interference."
        )
    else:
        note = (
            "Nearby space networks exist but none within the station-keeping threshold are "
            "brought into use; this satellite is not protected from harmful interference."
        )
    return ComplianceResult(
        compliant=False,
        satellite_longitude_deg=satellite_longitude_deg,
        best_match=None,
        nearby=nearby,
        note=note,
    )


def assess_compliance(
    satellite_longitude_deg: float,
    filings: list[Filing],
    *,
    regime: OrbitRegime = OrbitRegime.GEO,
    tolerance_deg: float = NEARBY_TOLERANCE_DEG,
) -> ComplianceResult:
    """Regime-aware entry point. GEO is assessed; other regimes are not supported in v0."""
    if regime is not OrbitRegime.GEO:
        raise RegimeNotSupportedError(
            f"{regime.value.upper()} compliance is not assessed in v0 (GEO only) — see ADR-0009"
        )
    return proximity_check(satellite_longitude_deg, filings, tolerance_deg=tolerance_deg)
