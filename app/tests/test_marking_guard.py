"""Guard: every file in the external-review surface carries the marking header (CLAUDE.md, ADR-0011).

Files under app/api/trust/**, app/api/rls/**, and app/api/bundle/sign*.py are reserved for paid
external review and excluded from /codex. This test fails if any such file loses the exact header.
"""

from __future__ import annotations

from pathlib import Path

HEADER = "# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53"

_API = Path(__file__).resolve().parent.parent / "app" / "api"


def _marked_files() -> list[Path]:
    files: list[Path] = []
    files += sorted((_API / "trust").rglob("*.py"))
    files += sorted((_API / "rls").rglob("*.py"))
    files += sorted((_API / "bundle").glob("sign*.py"))
    return files


def test_external_review_files_have_marking_header() -> None:
    files = _marked_files()
    assert files, "expected marked files under trust/ and bundle/"
    for path in files:
        first = path.read_text(encoding="utf-8").splitlines()[0] if path.read_text() else ""
        assert first == HEADER, f"missing/incorrect marking header: {path}"
