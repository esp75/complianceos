"""Regulator portal — Phase-1 DEV STUB served by the BFF.

A single self-contained HTML page that exercises the audit flow against the BFF on the
same origin (no CORS). The production insurer/regulator portal is Next.js 14 (ADR-0003,
Phase 4); this is only here to make the Phase-1 DoD visible and reproducible.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["portal"])

_PORTAL_HTML = Path(__file__).resolve().parents[1] / "static" / "portal.html"


@router.get("/portal", include_in_schema=False)
async def portal() -> FileResponse:
    return FileResponse(_PORTAL_HTML, media_type="text/html")
