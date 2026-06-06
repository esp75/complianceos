"""ITU Space Network List client (ADR-0009, ported from snl.py).

The upstream assembles its ``networks_[date].csv`` by shelling out to five scrape
scripts (``os.system('python3 snl_*_scrape.py')``) and gluing the results with pandas.
This port keeps ``fetch`` and ``parse`` separable and side-effect free: ``parse`` turns a
networks-export CSV into typed :class:`Filing` objects with stdlib ``csv`` (testable on a
fixture, no network), and ``fetch`` is a thin retrieval over httpx.

v0 scope (ADR-0013): the live multi-page SNL assembly pipeline is deferred; in v0 a
pre-assembled networks export is supplied (by the operator/loader) and parsed. SNL data
originates from itu.int (Geneva) — EU-compatible, no US-hosted dependency.
"""

from __future__ import annotations

import csv
import io

import httpx

from .filing_maturity import FilingMaturity
from .models import Filing

# Column headers of the upstream networks_[date].csv export.
_COL_NAME = "Network Name"
_COL_LONGITUDE = "Longitude"
_COL_ADMIN = "ITU Administration"
_COL_PLANNED = "Planned or Non-Planned"
_COL_BIU = "Brought-into-Use Date"
_COL_LATE = "Late-Stage Filing Date"
_COL_LINK = "Link"

_NA_VALUES = {"", "n/a", "N/A", "0"}


def _present(value: str | None) -> bool:
    return value is not None and value.strip() not in _NA_VALUES


def _derive_maturity(row: dict[str, str]) -> FilingMaturity:
    """Highest maturity implied by the export's date columns (suspension state is not
    derivable from this export alone and is deferred — v0 never marks SUSPENDED here)."""
    if _present(row.get(_COL_BIU)):
        return FilingMaturity.BROUGHT_INTO_USE
    if _present(row.get(_COL_LATE)):
        return FilingMaturity.LATE_STAGE
    return FilingMaturity.EARLY_STAGE


def parse(csv_text: str) -> list[Filing]:
    """Parse a networks-export CSV into :class:`Filing` objects.

    Rows without a usable numeric longitude are skipped (the upstream initializes the
    column to 0 and back-fills, leaving some rows unfilled).
    """
    filings: list[Filing] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        raw_lon = (row.get(_COL_LONGITUDE) or "").strip()
        if raw_lon in _NA_VALUES:
            continue
        try:
            longitude = float(raw_lon)
        except ValueError:
            continue
        if not -180.0 <= longitude <= 180.0:
            continue
        name = (row.get(_COL_NAME) or "").strip()
        if not name:
            continue
        planned = (row.get(_COL_PLANNED) or "").strip().lower() == "planned"
        link = (row.get(_COL_LINK) or "").strip()
        filings.append(
            Filing(
                network_name=name,
                longitude_deg=longitude,
                itu_administration=(row.get(_COL_ADMIN) or "").strip(),
                planned=planned,
                maturity=_derive_maturity(row),
                link=link or None,
            )
        )
    return filings


class SNLClient:
    """Retrieves and parses ITU SNL network exports.

    ``fetch`` performs a thin GET against a configured export URL; ``parse`` (module-level,
    reused here) does the typed conversion. Keeping them separate lets the parser be unit
    tested on a fixture without the network.
    """

    def __init__(self, export_url: str, *, timeout_seconds: float = 30.0) -> None:
        self._export_url = export_url
        self._timeout = timeout_seconds

    async def fetch(self) -> list[Filing]:
        """Fetch the networks export over HTTP and parse it into filings."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(self._export_url)
            resp.raise_for_status()
            return parse(resp.text)

    @staticmethod
    def parse(csv_text: str) -> list[Filing]:
        return parse(csv_text)
