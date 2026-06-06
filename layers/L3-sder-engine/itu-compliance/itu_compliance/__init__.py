"""Celestia L3 — ITU SNL compliance port (ADR-0009).

Ported (not vendored) from ITU-Compliance-Assessment-Monitor: SNL parsing, GEO proximity
compliance, and the filing-maturity state machine. v0 is GEO-only (ADR-0013).
"""

from .compliance import (
    NEARBY_TOLERANCE_DEG,
    OrbitRegime,
    RegimeNotSupportedError,
    assess_compliance,
    longitudinal_distance,
    proximity_check,
)
from .filing_maturity import (
    POSTGRES_ENUM_DDL,
    FilingMaturity,
    IllegalTransitionError,
    MaturityEvent,
    is_protected,
    transition,
)
from .models import ComplianceResult, Filing, NearbyFiling
from .snl_client import SNLClient, parse

__all__ = [
    "NEARBY_TOLERANCE_DEG",
    "POSTGRES_ENUM_DDL",
    "ComplianceResult",
    "Filing",
    "FilingMaturity",
    "IllegalTransitionError",
    "MaturityEvent",
    "NearbyFiling",
    "OrbitRegime",
    "RegimeNotSupportedError",
    "SNLClient",
    "assess_compliance",
    "is_protected",
    "longitudinal_distance",
    "parse",
    "proximity_check",
    "transition",
]
