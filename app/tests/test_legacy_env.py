"""The CELESTIA_ prefix keeps working for one deprecation cycle."""

from __future__ import annotations

import logging

import pytest

from app.legacy_env import apply_legacy_env


def test_copies_unset_twins_and_warns_once(caplog: pytest.LogCaptureFixture) -> None:
    env = {"CELESTIA_AUTH_MODE": "local", "CELESTIA_KG_DSN": "postgresql://x", "PATH": "/bin"}
    with caplog.at_level(logging.WARNING, logger="complianceos.config"):
        used = apply_legacy_env(env)
    assert used == ["CELESTIA_AUTH_MODE", "CELESTIA_KG_DSN"]
    assert env["COMPLIANCEOS_AUTH_MODE"] == "local"
    assert env["COMPLIANCEOS_KG_DSN"] == "postgresql://x"
    warnings = [r for r in caplog.records if r.name == "complianceos.config"]
    assert len(warnings) == 1
    assert "CELESTIA_AUTH_MODE, CELESTIA_KG_DSN" in warnings[0].getMessage()


def test_new_prefix_wins() -> None:
    env = {"CELESTIA_AUTH_MODE": "openlane", "COMPLIANCEOS_AUTH_MODE": "local"}
    assert apply_legacy_env(env) == []
    assert env["COMPLIANCEOS_AUTH_MODE"] == "local"


def test_no_old_variables_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="complianceos.config"):
        assert apply_legacy_env({"COMPLIANCEOS_AUTH_MODE": "local"}) == []
    assert not caplog.records
