"""SDER (L3) endpoints — closes the Phase-2 DoD.

POST /sder/conjunction-check is the vertical slice: operator TLE → Orekit conjunction
screening → optional ITU GEO proximity → risk score → a ``conjunction_report`` Evidence
written back through the L1 path (ADR-0012), linked to an ISO 24113 control. The tetrad
gates it (operator/admin only) exactly like the evidence router.

GET /sder/risk-score is a pure recompute-on-demand calculator for the portal panel.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query, status
from itu_compliance import Filing, FilingMaturity, proximity_check
from pydantic import BaseModel
from risk_scoring import RiskInputs, score_satellite

from app.api.deps import assert_can, current_user, get_openfga, get_openlane, get_orekit
from app.api.evidence import _resolve_control
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient
from app.clients.orekit import OrekitClient
from app.config import get_settings

router = APIRouter(prefix="/sder", tags=["sder"])


class TleModel(BaseModel):
    line1: str
    line2: str


class WindowModel(BaseModel):
    start: str
    end: str
    stepSeconds: float = 60.0


class FilingInput(BaseModel):
    network_name: str
    longitude_deg: float
    itu_administration: str = ""
    planned: bool = False
    maturity: str = "early_stage"


class ConjunctionCheckRequest(BaseModel):
    org_id: str
    tle1: TleModel
    tle2: TleModel
    window: WindowModel
    # Optional ITU GEO proximity inputs. When a longitude is given, the supplied filings
    # are screened; absent these, ITU contributes no risk (not assessed).
    satellite_longitude_deg: float | None = None
    filings: list[FilingInput] | None = None
    disposal_compliant: bool = True
    control_ref: str = "ISO 24113 §6.4"  # collision-avoidance control (resolves if loaded)


def _itu_assessment(
    longitude: float | None, filings: list[FilingInput] | None
) -> tuple[bool, str, dict[str, Any] | None]:
    """Run the GEO proximity check if a longitude is supplied. Returns
    (itu_compliant, filing_maturity, summary-or-None)."""
    if longitude is None:
        # Not assessed → neutral inputs (no ITU risk contribution).
        return True, FilingMaturity.BROUGHT_INTO_USE.value, None
    parsed = [Filing(**f.model_dump()) for f in (filings or [])]
    result = proximity_check(longitude, parsed)
    if result.best_match is not None:
        maturity = result.best_match.maturity.value
    elif result.nearby:
        maturity = result.nearby[0].filing.maturity.value
    else:
        maturity = FilingMaturity.EARLY_STAGE.value
    return result.compliant, maturity, {"compliant": result.compliant, "note": result.note}


@router.post("/conjunction-check", status_code=status.HTTP_201_CREATED)
async def conjunction_check(
    body: ConjunctionCheckRequest,
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
    openfga: Annotated[OpenFGAClient, Depends(get_openfga)],
    orekit: Annotated[OrekitClient, Depends(get_orekit)],
) -> dict[str, Any]:
    # Tetrad: only operator/admin may create evidence — insurer/regulator blocked here.
    await assert_can(openfga, user, "can_create_evidence", f"organization:{body.org_id}")

    settings = get_settings()
    conj = await orekit.conjunction(
        body.tle1.model_dump(),
        body.tle2.model_dump(),
        body.window.model_dump(),
        threshold_km=settings.orekit_conjunction_threshold_km,
    )
    min_miss = float(conj["minMissDistanceKm"])
    events = conj.get("events", [])
    # Relative speed at the closest flagged approach, if any (consequence input to the
    # risk score). None when no local minimum dipped below the reporting threshold.
    rel_speed = float(events[0]["relativeSpeedKmS"]) if events else None

    itu_compliant, maturity, itu_summary = _itu_assessment(body.satellite_longitude_deg, body.filings)

    risk = score_satellite(
        RiskInputs(
            min_miss_distance_km=min_miss,
            filing_maturity=maturity,
            itu_compliant=itu_compliant,
            disposal_compliant=body.disposal_compliant,
            relative_speed_km_s=rel_speed,
        )
    )

    epoch_label = events[0]["epoch"] if events else body.window.start
    source = json.dumps(
        {
            "type": "conjunction_report",
            "min_miss_distance_km": min_miss,
            "events": events,
            "risk": {"score": risk.score, "band": risk.band.value, "breakdown": risk.breakdown},
            "itu": itu_summary,
        }
    )

    # Write back via the L1 createEvidence path (ADR-0012). Control linkage is best-effort:
    # if the ISO 24113 control is not loaded, still record the evidence (don't 404 the slice).
    inp: dict[str, Any] = {"name": f"conjunction_report {epoch_label}", "ownerID": body.org_id, "source": source}
    cid = await _resolve_control(openlane, user["_token"], body.control_ref)
    if cid is not None:
        inp["controlIDs"] = [cid]

    data = await openlane.execute(
        "mutation($i:CreateEvidenceInput!){ createEvidence(input:$i){ evidence{ id displayID name } } }",
        {"i": inp},
        token=user["_token"],
    )
    ev = cast("dict[str, Any]", data["createEvidence"]["evidence"])
    return {
        "evidence_id": ev["id"],
        "display_id": ev.get("displayID"),
        "min_miss_distance_km": min_miss,
        "risk_score": risk.score,
        "band": risk.band.value,
        "itu_compliant": itu_compliant,
        "control_linked": cid is not None,
    }


@router.get("/risk-score")
async def risk_score(
    user: Annotated[dict[str, Any], Depends(current_user)],
    min_miss_distance_km: Annotated[float, Query(ge=0.0)],
    filing_maturity: str = "brought_into_use",
    itu_compliant: bool = True,
    disposal_compliant: bool = True,
    relative_speed_km_s: Annotated[float | None, Query(ge=0.0)] = None,
) -> dict[str, Any]:
    """Pure recompute-on-demand score for the portal — no Orekit call, no write."""
    score = score_satellite(
        RiskInputs(
            min_miss_distance_km=min_miss_distance_km,
            filing_maturity=filing_maturity,
            itu_compliant=itu_compliant,
            disposal_compliant=disposal_compliant,
            relative_speed_km_s=relative_speed_km_s,
        )
    )
    return {"score": score.score, "band": score.band.value, "breakdown": score.breakdown}
