"""The standalone verifier (verifier/complianceos_verify.py) agrees with the server's own output."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
from typing import Any

import httpx

from app.api.trust.keys import key_fingerprint, public_raw
from app.api.trust.keystore import DerivedKeyStore
from app.planner.history import build_history
from app.planner.sample import sample_mission
from app.planner.store import MemoryPlannerStore
from tests.test_planner_api import CLIENT, local_mode, make_app, sample  # noqa: F401

_SPEC = importlib.util.spec_from_file_location(
    "complianceos_verify", Path(__file__).parents[2] / "verifier" / "complianceos_verify.py")
assert _SPEC and _SPEC.loader
V = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(V)

NOW = dt.datetime(2026, 11, 1, 9, 0, tzinfo=dt.UTC)
KEYS = DerivedKeyStore(b"s" * 32)
FP = key_fingerprint(public_raw(KEYS.signing_key("workspace:local")))


async def test_verifies_a_real_signed_dossier_and_rejects_edits() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(seed="test-seed")),
                                 base_url="http://localhost", headers=CLIENT) as c:
        mid = await sample(c)
        doc: dict[str, Any] = (await c.get(f"/missions/{mid}/dossier.signed.json")).json()
    problems, fp = V.verify_dossier(doc, None)
    assert problems == [] and len(fp) == 64
    assert V.verify_dossier(doc, fp)[0] == []
    assert any("pinned" in p for p in V.verify_dossier(doc, "00" * 32)[0])

    doc["brief"]["sections"][0]["paragraphs"][0] += " edited"
    assert V.verify_dossier(doc, fp)[0]


async def test_verifies_history_chain_and_detects_forgery_and_dropped_events() -> None:
    store = MemoryPlannerStore()
    m = await store.create_mission("local", sample_mission(NOW.date()))
    await store.create_application("local", m.id, "lu-space-activity-authorisation")
    first = (await build_history(store, "local", KEYS, NOW)).model_dump()
    second = (await build_history(store, "local", KEYS, NOW + dt.timedelta(days=1))).model_dump()

    assert V.verify_history(first, FP)[0] == []
    assert V.verify_history(second, FP, previous=first)[0] == []
    assert V.verify_history(first, FP, previous=second)[0]  # wrong order breaks the chain

    forged = (await build_history(store, "local", DerivedKeyStore(b"x" * 32), NOW)).model_dump()
    assert V.verify_history(forged, None)[0] == []  # intact...
    assert any("pinned" in p for p in V.verify_history(forged, FP)[0])  # ...but not our signer

    forged_edit = json.loads(json.dumps(first))
    forged_edit["manifest"]["events"].pop()
    assert V.verify_history(forged_edit, FP)[0]


def test_unpinned_exit_code(tmp_path: Path) -> None:
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"format": "nope"}))
    assert V.main([str(f)]) == 1
