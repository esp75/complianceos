"""Signed program history (ADR-0021): export, offline verification, tamper detection, chaining."""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
from fastapi import FastAPI

from app.api import planner
from app.api.trust.keystore import DerivedKeyStore
from app.config import get_settings
from app.planner.history import HistoryDocument, build_history, verify_history
from app.planner.knowledge import load_knowledge
from app.planner.sample import sample_mission
from app.planner.store import MemoryPlannerStore
from app.planner.tracker import AppStatus

KB = load_knowledge()
NOW = dt.datetime(2026, 11, 1, 9, 0, tzinfo=dt.UTC)
LICENSE = "lu-space-activity-authorisation"
CLIENT = {"X-ComplianceOS-Client": "test"}
KEYS = DerivedKeyStore(b"s" * 32)


async def _store_with_history() -> tuple[MemoryPlannerStore, str]:
    store = MemoryPlannerStore()
    mission = await store.create_mission("local", sample_mission(NOW.date()))
    app = await store.create_application("local", mission.id, LICENSE)
    before = app.status
    app.status = AppStatus.PREPARING
    await store.save_application("local", app, "status", before, "starting")
    return store, mission.id


async def test_export_verifies_offline_and_is_signed() -> None:
    store, _ = await _store_with_history()
    doc = await build_history(store, "local", KEYS, NOW)
    assert doc.signed and doc.manifest["event_count"] == 2
    assert verify_history(HistoryDocument.model_validate(doc.model_dump())) == []


async def test_tampering_with_an_event_or_the_signature_is_detected() -> None:
    store, _ = await _store_with_history()
    doc = await build_history(store, "local", KEYS, NOW)

    edited = doc.model_copy(deep=True)
    edited.manifest["events"][1]["note"] = "never happened"
    problems = verify_history(edited)
    assert any("merkle_root" in p for p in problems) and any("signature" in p for p in problems)

    dropped = doc.model_copy(deep=True)
    dropped.manifest["events"].pop()
    assert verify_history(dropped)

    forged = doc.model_copy(deep=True)
    forged.signature_hex = "00" * 64
    assert "signature does not verify" in verify_history(forged)


async def test_each_workspace_export_names_the_previous_root() -> None:
    store, _ = await _store_with_history()
    first = await build_history(store, "local", KEYS, NOW)
    second = await build_history(store, "local", KEYS, NOW + dt.timedelta(days=1))
    assert first.manifest["previous_root"] is None
    assert second.manifest["previous_root"] == first.manifest["merkle_root"]


async def test_unsigned_server_exports_but_does_not_checkpoint_or_verify() -> None:
    store, _ = await _store_with_history()
    doc = await build_history(store, "local", DerivedKeyStore(b""), NOW)
    assert not doc.signed and "Unsigned" in doc.note
    assert await store.last_history_root("local") is None
    assert "document is not signed" in verify_history(doc)


async def test_workspaces_do_not_see_each_others_events() -> None:
    store, _ = await _store_with_history()
    other = await build_history(store, "someone-else", KEYS, NOW)
    assert other.manifest["event_count"] == 0


@pytest.fixture(autouse=True)
def local_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("COMPLIANCEOS_AUTH_MODE", "local")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI()
    app.state.knowledge = KB
    app.state.planner_store = MemoryPlannerStore()
    app.state.llm = None
    app.state.trust_keystore = KEYS
    app.include_router(planner.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://localhost", headers=CLIENT) as c:
        yield c


async def test_api_exports_workspace_and_mission_history(client: httpx.AsyncClient) -> None:
    mid = (await client.post("/missions/sample")).json()["id"]
    await client.post(f"/missions/{mid}/applications", json={"license_id": LICENSE})

    ws = await client.post("/history/export")
    assert ws.status_code == 200 and ws.json()["manifest"]["event_count"] == 1
    assert verify_history(HistoryDocument.model_validate(ws.json())) == []

    one = await client.get(f"/missions/{mid}/history")
    assert one.status_code == 200 and one.json()["manifest"]["scope"] == mid
    assert one.json()["manifest"]["previous_root"] is None  # a mission view is not chained
    assert (await client.get("/missions/nope/history")).status_code == 404
    bare = await client.post("/history/export", headers={"X-ComplianceOS-Client": ""})
    assert bare.status_code in (400, 401, 403)


async def test_usage_events_are_counted_per_kind_and_validated(client: httpx.AsyncClient) -> None:
    for kind in ("session_start", "watch_viewed", "watch_viewed"):
        assert (await client.post("/usage", json={"kind": kind})).status_code == 204
    assert (await client.post("/usage", json={"kind": "free text"})).status_code == 422
    out = (await client.get("/usage/summary?days=7")).json()
    assert out["counts"] == {"session_start": 1, "watch_viewed": 2} and out["active_days"] == 1


async def test_api_serves_the_review_package(client: httpx.AsyncClient) -> None:
    mid = (await client.post("/missions/sample")).json()["id"]
    res = await client.get(f"/missions/{mid}/dossier.md")
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/markdown")
    assert "Reviewer sign-off" in res.text
    assert (await client.get("/missions/nope/dossier.md")).status_code == 404


async def test_a_history_signed_with_someone_elses_key_fails_the_pinned_fingerprint() -> None:
    """Security review: the key is embedded, so a forger's self-signed document verified."""
    store, _ = await _store_with_history()
    real = await build_history(store, "local", KEYS, NOW)
    forged = await build_history(store, "local", DerivedKeyStore(b"x" * 32), NOW)

    assert verify_history(forged) == []  # internally consistent: integrity only
    assert verify_history(real, real.fingerprint) == []
    assert any("different key" in p for p in verify_history(forged, real.fingerprint))

    swapped = real.model_copy(deep=True)
    swapped.fingerprint = forged.fingerprint  # fingerprint claim not matching the embedded key
    assert any("fingerprint does not match" in p for p in verify_history(swapped))
