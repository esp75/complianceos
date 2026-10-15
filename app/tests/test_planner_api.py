"""Planner API tests over the in-memory store: knowledge, missions, roadmap and brief, the full
application lifecycle, exports, and the auth modes. No database or network needed."""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import planner
from app.api.trust.keystore import DerivedKeyStore
from app.api.trust.signing import verify
from app.config import get_settings
from app.planner.brief import build_brief
from app.planner.exports import SIDECAR_NAME, canonical_roadmap, dossier_pdf
from app.planner.knowledge import load_knowledge
from app.planner.plan import build_roadmap
from app.planner.sample import sample_mission
from app.planner.store import MemoryPlannerStore

TODAY = dt.date(2026, 10, 15)
KB = load_knowledge()
CLIENT = {"X-ComplianceOS-Client": "test"}


class FakeLLM:
    def __init__(self, text: str) -> None:
        self.text = text

    async def complete(self, system: str, prompt: str) -> str:
        return self.text


def make_app(*, llm: Any = None, seed: str = "") -> FastAPI:
    app = FastAPI()
    app.state.knowledge = KB
    app.state.planner_store = MemoryPlannerStore()
    app.state.llm = llm
    app.state.trust_keystore = DerivedKeyStore(seed.encode())
    app.include_router(planner.router)
    app.dependency_overrides[planner.get_today] = lambda: TODAY
    return app


@pytest.fixture(autouse=True)
def local_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("CELESTIA_AUTH_MODE", "local")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=make_app(seed="test-seed"))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost", headers=CLIENT) as c:
        yield c


async def sample(c: httpx.AsyncClient) -> str:
    r = await c.post("/missions/sample")
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


# --- knowledge ---

async def test_knowledge_endpoints(client: httpx.AsyncClient) -> None:
    js = (await client.get("/knowledge/jurisdictions")).json()
    assert js[0]["jurisdiction"]["id"] == "itu"
    assert {j["jurisdiction"]["id"] for j in js} == {"itu", "fr", "gb", "lu", "us"}
    lic = await client.get("/knowledge/licenses/fr-los-authorisation")
    assert lic.status_code == 200 and lic.json()["legal_basis"][0]["language"] == "fr"
    assert (await client.get("/knowledge/licenses/nope")).status_code == 404
    lu = (await client.get("/knowledge/facilitators", params={"jurisdiction": "lu"})).json()
    assert [f["id"] for f in lu] == ["arendt-medernach"]


# --- missions, roadmap, brief ---

async def test_mission_crud_and_roadmap(client: httpx.AsyncClient) -> None:
    mid = await sample(client)
    assert [m["id"] for m in (await client.get("/missions")).json()] == [mid]
    road = (await client.get(f"/missions/{mid}/roadmap")).json()
    assert road["critical_path"] and road["citations"]
    profile = road["mission"] | {"operator_country": "FR"}
    updated = await client.put(f"/missions/{mid}", json=profile)
    assert updated.status_code == 200
    ids = {i["license_id"] for i in (await client.get(f"/missions/{mid}/roadmap")).json()["items"]}
    assert "fr-los-authorisation" in ids
    assert (await client.delete(f"/missions/{mid}")).status_code == 204
    assert (await client.get(f"/missions/{mid}")).status_code == 404


async def test_preview_roadmap_without_saving(client: httpx.AsyncClient) -> None:
    profile = sample_mission(TODAY).model_dump(mode="json")
    r = await client.post("/roadmap", json=profile)
    assert r.status_code == 200 and r.json()["items"]
    assert (await client.get("/missions")).json() == []


async def test_invalid_profile_is_422(client: httpx.AsyncClient) -> None:
    bad = sample_mission(TODAY).model_dump(mode="json") | {"operator_country": "Luxembourg"}
    assert (await client.post("/missions", json=bad)).status_code == 422


async def test_brief_deterministic_and_ai_modes() -> None:
    good = FakeLLM("Start with the Luxembourg concession [cite:lu.media1991.art-20].")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(llm=good)),
                                 base_url="http://localhost", headers=CLIENT) as c:
        mid = await sample(c)
        assert (await c.post(f"/missions/{mid}/brief")).json()["mode"] == "deterministic"
        assert (await c.post(f"/missions/{mid}/brief", params={"ai": True})).json()["mode"] == "llm"
    invented = FakeLLM("Everything is approved [cite:fr.made-up.art-99].")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(llm=invented)),
                                 base_url="http://localhost", headers=CLIENT) as c:
        mid = await sample(c)
        r = await c.post(f"/missions/{mid}/brief", params={"ai": True})
        assert r.status_code == 422 and "citation grounding" in r.json()["detail"]


async def test_ai_brief_without_llm_is_503(client: httpx.AsyncClient) -> None:
    mid = await sample(client)
    assert (await client.post(f"/missions/{mid}/brief", params={"ai": True})).status_code == 503


# --- tracking lifecycle ---

async def test_application_lifecycle(client: httpx.AsyncClient) -> None:
    mid = await sample(client)
    lic = "lu-space-activity-authorisation"
    assert (await client.post(f"/missions/{mid}/applications",
                              json={"license_id": "fr-los-authorisation"})).status_code == 422
    created = await client.post(f"/missions/{mid}/applications", json={"license_id": lic})
    assert created.status_code == 201
    app_id = created.json()["application"]["id"]
    assert (await client.post(f"/missions/{mid}/applications",
                              json={"license_id": lic})).status_code == 409

    illegal = await client.patch(f"/applications/{app_id}", json={"status": "granted"})
    assert illegal.status_code == 422 and "allowed" in illegal.json()["detail"]

    sub = await client.patch(f"/applications/{app_id}",
                             json={"status": "submitted", "submitted_on": "2026-09-01",
                                   "reference": "LSA-2026-17", "note": "filed by email"})
    assert sub.status_code == 200, sub.text
    assert sub.json()["application"]["submitted_on"] == "2026-09-01"
    assert "Decision expected" in sub.json()["next_action"]["title"]

    future = await client.patch(f"/applications/{app_id}", json={"status": "granted",
                                                                  "granted_on": "2027-01-01"})
    assert future.status_code == 422

    granted = await client.patch(f"/applications/{app_id}", json={"status": "granted",
                                                                   "granted_on": "2026-10-01"})
    assert granted.json()["application"]["status"] == "granted"

    deadlines = (await client.get(f"/missions/{mid}/deadlines")).json()
    use = next(d for d in deadlines if d["title"] == "Use the authorisation within 36 months")
    assert use["date"] == "2029-10-01"  # re-dated from the real grant date

    contact = await client.post(f"/applications/{app_id}/contacts", json={
        "on_date": "2026-10-10", "channel": "meeting", "counterpart": "LSA",
        "summary": "Kick-off call", "next_step": "Send risk assessment", "next_step_due": "2026-11-01"})
    assert contact.status_code == 201
    assert len((await client.get(f"/applications/{app_id}/contacts")).json()) == 1
    kinds = [e["kind"] for e in (await client.get(f"/applications/{app_id}/events")).json()]
    assert kinds == ["created", "status", "status", "contact"]
    assert any(d["title"] == "Send risk assessment (LSA)"
               for d in (await client.get(f"/missions/{mid}/deadlines")).json())


# --- exports ---

async def test_calendar_is_valid_ics(client: httpx.AsyncClient) -> None:
    mid = await sample(client)
    r = await client.get(f"/missions/{mid}/calendar.ics")
    assert r.headers["content-type"].startswith("text/calendar")
    text = r.text
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n")
    assert text.count("BEGIN:VEVENT") == text.count("END:VEVENT") > 5
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))


async def test_dossier_pdf_signed_and_verifiable(client: httpx.AsyncClient) -> None:
    mid = await sample(client)
    r = await client.get(f"/missions/{mid}/dossier.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert r.headers["x-roadmap-signed"] == "true"
    assert SIDECAR_NAME.encode() in r.content

    roadmap = build_roadmap(KB, sample_mission(TODAY), TODAY)
    keystore = DerivedKeyStore(b"test-seed")
    pdf, info = dossier_pdf(roadmap, await build_brief(roadmap), workspace="local", keystore=keystore)
    assert info.signed and info.fingerprint == keystore.fingerprint("workspace:local")
    from app.planner.exports import _sign

    _, sig = _sign(canonical_roadmap(roadmap), keystore, "local")
    assert verify(canonical_roadmap(roadmap), bytes.fromhex(sig["signature_hex"]),
                  keystore.public_key("workspace:local"))


async def test_dossier_unsigned_without_key() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(seed="")),
                                 base_url="http://localhost", headers=CLIENT) as c:
        mid = await sample(c)
        r = await c.get(f"/missions/{mid}/dossier.pdf")
        assert r.status_code == 200 and r.headers["x-roadmap-signed"] == "false"


async def test_intro_emails(client: httpx.AsyncClient) -> None:
    mid = await sample(client)
    lic = "lu-space-activity-authorisation"
    to_lsa = (await client.post(f"/missions/{mid}/intro-email",
                                json={"license_id": lic, "recipient": "lu-lsa"})).json()
    assert to_lsa["to"] == "info@space-agency.lu" and "Pre-application" in to_lsa["subject"]
    to_firm = (await client.post(f"/missions/{mid}/intro-email",
                                 json={"license_id": lic, "recipient": "arendt-medernach"})).json()
    assert "Arendt" in to_firm["body"]
    bad = await client.post(f"/missions/{mid}/intro-email",
                            json={"license_id": lic, "recipient": "nobody"})
    assert bad.status_code == 422


# --- auth modes ---

async def test_local_mode_refuses_public_clients() -> None:
    transport = httpx.ASGITransport(app=make_app(), client=("8.8.8.8", 4242))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost", headers=CLIENT) as c:
        r = await c.get("/missions")
        assert r.status_code == 403 and "local mode" in r.json()["detail"]


async def test_store_isolates_workspaces() -> None:
    store = MemoryPlannerStore()
    m = await store.create_mission("a", sample_mission(TODAY))
    assert await store.get_mission("b", m.id) is None
    assert await store.list_missions("b") == []
    app = await store.create_application("a", m.id, "lu-space-activity-authorisation")
    assert await store.get_application("b", app.id) is None
    assert not await store.delete_mission("b", m.id)


class _Openlane:
    async def get_self(self, token: str) -> dict[str, Any]:
        return {"id": "01U", "email": "u@example.org"} if token == "good" else {}


class _FGA:
    def __init__(self, allow: bool) -> None:
        self.allow = allow
        self.calls: list[str] = []

    async def check(self, user: str, relation: str, obj: str, *, context: dict | None = None) -> bool:
        self.calls.append(relation)
        return self.allow


async def test_team_mode_requires_workspace_token_and_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CELESTIA_AUTH_MODE", "openlane")
    get_settings.cache_clear()
    for allow, expected in ((True, 200), (False, 403)):
        app = make_app()
        app.state.openlane = _Openlane()
        app.state.openfga = fga = _FGA(allow)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost", headers=CLIENT) as c:
            assert (await c.get("/missions")).status_code == 400
            assert (await c.get("/missions", headers={"X-Workspace": "01O"})).status_code == 401
            r = await c.get("/missions", headers={"X-Workspace": "01O", "Authorization": "Bearer good"})
            assert r.status_code == expected
            await c.post("/missions/sample", headers={"X-Workspace": "01O", "Authorization": "Bearer good"})
        assert fga.calls[0] == "can_view" and fga.calls[-1] == "can_create_evidence"


async def test_local_mode_does_not_trust_private_networks_by_default(
        monkeypatch: pytest.MonkeyPatch) -> None:
    transport = httpx.ASGITransport(app=make_app(), client=("10.0.0.5", 4242))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost", headers=CLIENT) as c:
        assert (await c.get("/missions")).status_code == 403
    monkeypatch.setenv("CELESTIA_LOCAL_ALLOWED_NETWORKS", "10.0.0.0/24, 172.30.0.0/24")
    get_settings.cache_clear()
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost", headers=CLIENT) as c:
        assert (await c.get("/missions")).status_code == 200
    other = httpx.ASGITransport(app=make_app(), client=("10.0.1.5", 4242))
    async with httpx.AsyncClient(transport=other, base_url="http://localhost", headers=CLIENT) as c:
        assert (await c.get("/missions")).status_code == 403


async def test_calendar_cannot_be_injected_through_user_text(client: httpx.AsyncClient) -> None:
    profile = sample_mission(TODAY).model_dump(mode="json")
    profile["name"] = "Evil\rBEGIN:VALARM ATTACH:http://x\nEND:VALARM\x00"
    mid = (await client.post("/missions", json=profile)).json()["id"]
    app_id = (await client.post(f"/missions/{mid}/applications",
                                json={"license_id": "lu-space-activity-authorisation"})).json()[
        "application"]["id"]
    await client.post(f"/applications/{app_id}/contacts", json={
        "on_date": "2026-10-10", "channel": "email", "counterpart": "LSA\r\nATTACH:x",
        "summary": "s", "next_step": "reply\rBEGIN:VALARM", "next_step_due": "2026-11-01"})
    text = (await client.get(f"/missions/{mid}/calendar.ics")).text
    lines = text.split("\r\n")
    assert "\r" not in text.replace("\r\n", "") and "\n" not in text.replace("\r\n", "")
    assert not any(line.startswith(("BEGIN:VALARM", "ATTACH:", "END:VALARM")) for line in lines)
    assert " " not in text and "\x00" not in text


async def test_email_subject_is_single_line(client: httpx.AsyncClient) -> None:
    profile = sample_mission(TODAY).model_dump(mode="json") | {"name": "A\r\nBcc: x@example.org"}
    mid = (await client.post("/missions", json=profile)).json()["id"]
    draft = (await client.post(f"/missions/{mid}/intro-email", json={
        "license_id": "lu-space-activity-authorisation", "recipient": "lu-lsa"})).json()
    assert "\r" not in draft["subject"] and "\n" not in draft["subject"]


async def test_local_mode_checks_every_forwarded_hop() -> None:
    """A proxy on loopback (the Next server) must not launder an outside client into local."""
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost", headers=CLIENT) as c:
        assert (await c.get("/missions", headers={"X-Forwarded-For": "192.168.1.23"})).status_code == 403
        assert (await c.get("/missions", headers={"X-Forwarded-For": "127.0.0.1, 8.8.8.8"})).status_code == 403
        assert (await c.get("/missions", headers={"X-Forwarded-For": "not-an-ip"})).status_code == 403
        assert (await c.get("/missions", headers={"X-Forwarded-For": "127.0.0.1"})).status_code == 200
        assert (await c.get("/missions", headers={"X-Forwarded-For": "::1"})).status_code == 200


async def test_local_mode_refuses_non_local_hosts_and_rebinding() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()), base_url="http://localhost") as c:
        # A browser on another machine, through the Next proxy (no X-Forwarded-For, LAN host).
        assert (await c.get("/missions", headers={"X-Forwarded-Host": "192.168.1.5:3000"})).status_code == 403
        # A DNS-rebinding page: the browser sends the attacker's host name.
        assert (await c.get("/missions", headers={"Host": "evil.example:8001"})).status_code == 403
        assert (await c.get("/missions", headers={"X-Forwarded-Host": "localhost:3000"})).status_code == 200
        assert (await c.get("/missions", headers={"Host": "[::1]:8001"})).status_code == 200


async def test_local_mode_changes_need_the_client_header() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()), base_url="http://localhost") as c:
        r = await c.post("/missions/sample")
        assert r.status_code == 403 and "x-complianceos-client" in r.json()["detail"]
        assert (await c.get("/missions")).status_code == 200
        assert (await c.post("/missions/sample", headers=CLIENT)).status_code == 201


async def test_compose_service_name_is_an_allowed_host(monkeypatch: pytest.MonkeyPatch) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()), base_url="http://api:8000") as c:
        assert (await c.get("/missions")).status_code == 403
    monkeypatch.setenv("CELESTIA_LOCAL_ALLOWED_HOSTS", "api")
    get_settings.cache_clear()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()), base_url="http://api:8000") as c:
        assert (await c.get("/missions")).status_code == 200
