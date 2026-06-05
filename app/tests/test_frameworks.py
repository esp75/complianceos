"""Offline tests for the framework loader: the hand-authored YAML under
layers/L1-substrate/frameworks/ must validate against the openlane.io/v1 schema
and parse to the expected control/subcontrol counts. No network/theopenlane needed.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.loaders.framework_loader import discover_framework_dirs, load_framework_dir
from app.loaders.schema import ControlDoc

# expected (controls, subcontrols) per framework short_name
EXPECTED = {
    "EU-SA": (5, 11),
    "ISO-24113": (4, 6),
    "ITU-RR": (4, 5),
}


def test_three_frameworks_discovered() -> None:
    dirs = discover_framework_dirs()
    assert {d.name for d in dirs} == {"eu-space-act", "iso-24113", "itu"}


def test_frameworks_parse_with_expected_counts() -> None:
    seen: dict[str, tuple[int, int]] = {}
    for d in discover_framework_dirs():
        fw, controls, ev_count = load_framework_dir(d)
        assert fw.kind == "Framework"
        assert fw.metadata.short_name
        subs = sum(len(c.spec.controls) for c in controls)
        seen[fw.metadata.short_name] = (len(controls), subs)
        assert ev_count >= 1  # every framework declares an evidence-type set
    assert seen == EXPECTED


def test_every_control_has_required_fields() -> None:
    for d in discover_framework_dirs():
        _fw, controls, _ = load_framework_dir(d)
        for c in controls:
            assert c.metadata.citation  # -> refCode (required by theopenlane)
            assert c.metadata.display_name  # -> title
            assert c.spec.description
            for sub in c.spec.controls:
                assert sub.id and sub.description  # -> subcontrol refCode + description


def test_schema_rejects_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        ControlDoc.model_validate({"apiVersion": "openlane.io/v1", "kind": "Control",
                                   "metadata": {"name": "x"}, "spec": {"description": "d"}})
