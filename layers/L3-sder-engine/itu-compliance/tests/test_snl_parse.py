from pathlib import Path

from itu_compliance.filing_maturity import FilingMaturity
from itu_compliance.snl_client import parse

FIXTURE = Path(__file__).parent / "fixtures" / "networks_sample.csv"


def _filings() -> list:
    return parse(FIXTURE.read_text())


def test_skips_rows_without_usable_longitude() -> None:
    filings = _filings()
    # 6 data rows, but BADLON has longitude "n/a" and is dropped.
    assert len(filings) == 5
    assert all(f.network_name != "BADLON" for f in filings)


def test_maturity_derived_from_date_columns() -> None:
    by_name = {f.network_name: f for f in _filings()}
    assert by_name["ALPHA-1"].maturity is FilingMaturity.BROUGHT_INTO_USE  # has BIU date
    assert by_name["IOTA-9"].maturity is FilingMaturity.LATE_STAGE  # late date, no BIU
    assert by_name["ZETA-6"].maturity is FilingMaturity.EARLY_STAGE  # only early date


def test_planned_flag_and_fields() -> None:
    by_name = {f.network_name: f for f in _filings()}
    assert by_name["IOTA-9"].planned is True
    assert by_name["ALPHA-1"].planned is False
    assert by_name["ALPHA-1"].longitude_deg == 10.0
    assert by_name["THETA-8"].longitude_deg == -179.9
    assert by_name["ALPHA-1"].link == "https://itu.int/alpha"
