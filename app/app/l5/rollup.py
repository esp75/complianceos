"""Per-Framework, per-Control compliance-status rollup (ADR-0015).

The Compliance Status panel needs a single payload joining the visible Standards +
Controls (theopenlane) with an organization's Evidence. The join is tenancy- and
authorization-sensitive, so it lives at the BFF, not in the browser. This module is the
pure core of that join: given already-fetched frameworks and evidence, classify each
control and summarize. The router (``app/app/api/compliance.py``) does the I/O.

v0 status is evidence-presence, not an assessment workflow (ADR-0015 §3):
- ``compliant``     — ≥1 linked Evidence in an accepted state
- ``partial``       — linked Evidence exists, none accepted
- ``not_assessed``  — no linked Evidence
"""

from __future__ import annotations

from typing import Any

COMPLIANT = "compliant"
PARTIAL = "partial"
NOT_ASSESSED = "not_assessed"

#: theopenlane Evidence ``status`` values that count as accepted for a control. Compared
#: case-insensitively. Conservative v0 set; widen once real status strings are confirmed
#: against the live substrate (ADR-0015 — open question on assessment workflow).
ACCEPTED_EVIDENCE_STATUSES = frozenset({"ready", "approved", "accepted", "submitted"})


def _control_status(linked: list[dict[str, Any]]) -> str:
    if not linked:
        return NOT_ASSESSED
    if any((e.get("status") or "").lower() in ACCEPTED_EVIDENCE_STATUSES for e in linked):
        return COMPLIANT
    return PARTIAL


def _empty_summary() -> dict[str, int]:
    return {COMPLIANT: 0, PARTIAL: 0, NOT_ASSESSED: 0}


def _percent_compliant(summary: dict[str, int], total: int) -> float:
    return round(100.0 * summary[COMPLIANT] / total, 1) if total else 0.0


def rollup_status(
    frameworks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Roll up control compliance for one organization.

    ``frameworks`` items: ``{"shortName", "framework", "controls": [{"refCode", "title"}]}``.
    ``evidence`` items: ``{"id", "displayID", "name", "status", "controlRefs": [refCode, ...]}``.
        ``controlRefs`` is the list of Control refCodes this Evidence is linked to.

    Returns ``{"frameworks": [...], "summary": {...}}`` with one entry per framework, each
    carrying its controls (status + linked evidence) and a per-framework summary, plus an
    org-level summary. ``org_id`` is added by the caller.
    """
    # refCode -> evidence records linked to it (lightweight projection for the payload).
    by_control: dict[str, list[dict[str, Any]]] = {}
    for ev in evidence:
        record = {
            "id": ev.get("id"),
            "displayID": ev.get("displayID"),
            "name": ev.get("name"),
            "status": ev.get("status"),
        }
        for ref in ev.get("controlRefs", []):
            by_control.setdefault(ref, []).append(record)

    overall = _empty_summary()
    total = 0
    out_frameworks: list[dict[str, Any]] = []

    for fw in frameworks:
        fw_summary = _empty_summary()
        out_controls: list[dict[str, Any]] = []
        for control in fw.get("controls", []):
            ref = control.get("refCode")
            linked = by_control.get(ref, [])
            st = _control_status(linked)
            fw_summary[st] += 1
            out_controls.append({
                "refCode": ref,
                "title": control.get("title"),
                "status": st,
                "evidenceCount": len(linked),
                "evidence": linked,
            })
        total += len(out_controls)
        for key in overall:
            overall[key] += fw_summary[key]
        out_frameworks.append({
            "shortName": fw.get("shortName"),
            "framework": fw.get("framework"),
            "controlCount": len(out_controls),
            "summary": fw_summary,
            "percentCompliant": _percent_compliant(fw_summary, len(out_controls)),
            "controls": out_controls,
        })

    return {
        "frameworks": out_frameworks,
        "summary": {**overall, "total": total, "percentCompliant": _percent_compliant(overall, total)},
    }
