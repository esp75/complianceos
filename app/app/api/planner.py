"""Regulatory path planner API (ADR-0018).

Knowledge (read-only, public): jurisdictions, licences, facilitators.
Missions: create / list / update / delete a mission profile, get its roadmap and brief.
Tracking: applications per licence, status changes, contact log, deadlines, calendar, dossier.
The Watch (ADR-0019): changes in the sources the pack cites, scoped to each workspace's applications.

Authentication depends on ``COMPLIANCEOS_AUTH_MODE``:

- ``local`` (default): one workspace for the person running the server, no login. Only loopback
  clients and networks listed in ``COMPLIANCEOS_LOCAL_ALLOWED_NETWORKS`` are served, so a local
  instance is not accidentally shared.
- ``openlane`` (team mode): the theopenlane user from the bearer token, the workspace from the
  ``X-Workspace`` header (an organization id), and OpenFGA checks at the boundary (ADR-0012):
  ``can_view`` to read, ``can_create_evidence`` to change anything.
"""

from __future__ import annotations

import asyncio
import collections
import datetime as dt
import ipaddress
import time
from dataclasses import dataclass
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.api.deps import (
    assert_can,
    bearer_token,
    current_user,
    get_llm,
    get_openfga,
    get_openlane,
)
from app.api.trust.keystore import KeyStore
from app.clients.openfga import OpenFGAClient
from app.config import get_settings
from app.l4.citations import CitationError
from app.llm.base import LLMError, LLMProvider
from app.planner.alerts import clean_recipients
from app.planner.brief import Brief, build_brief
from app.planner.classify import make_classifier
from app.planner.digest import WatchItem, watch_items
from app.planner.exports import EmailDraft, calendar_ics, dossier_pdf, intro_email, signed_document
from app.planner.history import HistoryDocument, build_history
from app.planner.knowledge import Facilitator, Jurisdiction, KnowledgeBase, License
from app.planner.mission import MissionProfile
from app.planner.plan import Deadline, Roadmap, RoadmapItem, build_roadmap
from app.planner.program import MissionView, Program, ProgramDeadline, build_program
from app.planner.review import dossier_markdown
from app.planner.sample import sample_mission
from app.planner.store import DuplicateError, Mission, PlannerStore
from app.planner.tracker import (
    Application,
    ApplicationEvent,
    AppStatus,
    Contact,
    ContactIn,
    NextAction,
    TransitionError,
    apply_update,
    next_action,
    redate_obligations,
)
from app.planner.watch import (
    HOST_INTERVAL_S,
    Fetcher,
    HttpFetcher,
    RunSummary,
    run_watch,
)

WATCH_MIN_INTERVAL_S = 60.0  # one manual Watch run per minute per process

router = APIRouter(tags=["planner"])


# --- dependencies ---

def get_knowledge(request: Request) -> KnowledgeBase:
    kb = getattr(request.app.state, "knowledge", None)
    if kb is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="knowledge pack failed to load; run `python -m app.planner.knowledge validate`")
    return cast(KnowledgeBase, kb)


def get_store(request: Request) -> PlannerStore:
    return cast(PlannerStore, request.app.state.planner_store)


def get_today() -> dt.date:
    return dt.date.today()


def get_planner_keystore(request: Request) -> KeyStore | None:
    return cast("KeyStore | None", getattr(request.app.state, "trust_keystore", None))


@dataclass(frozen=True)
class Principal:
    workspace: str
    user: str


def _allowed_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    raw = get_settings().local_allowed_networks
    return [ipaddress.ip_network(n.strip(), strict=False) for n in raw.split(",") if n.strip()]


def _trusted(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host.strip())
    except ValueError:
        return False
    return ip.is_loopback or any(ip in net for net in _allowed_networks())


_LOCAL_NAMES = {"localhost", "127.0.0.1", "::1"}
CLIENT_HEADER = "x-complianceos-client"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _host_name(value: str) -> str:
    v = value.strip().lower()
    if v.startswith("["):  # [::1]:3000
        return v[1:v.find("]")] if "]" in v else v
    return v.rsplit(":", 1)[0] if v.count(":") == 1 else v


def _local_host(value: str) -> bool:
    name = _host_name(value)
    extra = {h.strip().lower() for h in get_settings().local_allowed_hosts.split(",") if h.strip()}
    return name in _LOCAL_NAMES or name.endswith(".localhost") or name in extra or _trusted(name)


def _local_client(request: Request) -> None:
    """Local mode has no login, so every request must provably come from this machine.

    - The direct peer, and every X-Forwarded-For hop when a proxy sets one, must be loopback or in
      COMPLIANCEOS_LOCAL_ALLOWED_NETWORKS. Private ranges are not trusted by default.
    - Host and X-Forwarded-Host must be local names. The Next.js proxy does not send X-Forwarded-For,
      so this is what refuses a browser on another machine (it arrives as http://<lan-ip>:3000) and
      blocks DNS-rebinding pages.
    - Changes need the X-ComplianceOS-Client header. Browsers cannot add it cross-site without a
      CORS grant (never given), so other websites cannot drive a local instance (CSRF)."""
    deny = HTTPException(status.HTTP_403_FORBIDDEN,
                         detail="local mode only serves this machine; use team mode to share")
    peer = request.client.host if request.client else ""
    hops = [h for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    if not (_trusted(peer) and all(_trusted(h) for h in hops)):
        raise deny
    hosts = [request.headers.get("host", "")] + request.headers.getlist("x-forwarded-host")
    if not all(_local_host(h) for h in hosts if h):
        raise deny
    if request.method not in _SAFE_METHODS and not request.headers.get(CLIENT_HEADER):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail=f"missing {CLIENT_HEADER} header (required for changes in local mode)")


async def _principal(request: Request, relation: str,
                     x_workspace: str | None, authorization: str | None) -> Principal:
    if get_settings().auth_mode == "local":
        _local_client(request)
        return Principal(workspace="local", user="local")
    if not x_workspace:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="X-Workspace header required")
    user = await current_user(bearer_token(authorization), get_openlane(request))
    openfga: OpenFGAClient = get_openfga(request)
    await assert_can(openfga, user, relation, f"organization:{x_workspace}")
    return Principal(workspace=x_workspace, user=str(user["id"]))


async def reader(request: Request, x_workspace: Annotated[str | None, Header()] = None,
                 authorization: Annotated[str | None, Header()] = None) -> Principal:
    return await _principal(request, "can_view", x_workspace, authorization)


async def writer(request: Request, x_workspace: Annotated[str | None, Header()] = None,
                 authorization: Annotated[str | None, Header()] = None) -> Principal:
    return await _principal(request, "can_create_evidence", x_workspace, authorization)


Read = Annotated[Principal, Depends(reader)]
Write = Annotated[Principal, Depends(writer)]
KB = Annotated[KnowledgeBase, Depends(get_knowledge)]
Store = Annotated[PlannerStore, Depends(get_store)]
Today = Annotated[dt.date, Depends(get_today)]


async def _mission(store: PlannerStore, p: Principal, mission_id: str) -> Mission:
    m = await store.get_mission(p.workspace, mission_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="mission not found")
    return m


async def _application(store: PlannerStore, p: Principal, app_id: str) -> Application:
    a = await store.get_application(p.workspace, app_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="application not found")
    return a


# --- knowledge ---

class JurisdictionOut(BaseModel):
    jurisdiction: Jurisdiction
    licenses: list[str]


@router.get("/knowledge/jurisdictions")
async def list_jurisdictions(kb: KB) -> list[JurisdictionOut]:
    return [
        JurisdictionOut(jurisdiction=j, licenses=sorted(
            lic.id for lic in kb.licenses.values() if lic.jurisdiction == j.id))
        for j in sorted(kb.jurisdictions.values(), key=lambda j: (j.kind != "international", j.name))
    ]


@router.get("/knowledge/licenses/{license_id}")
async def get_license(license_id: str, kb: KB) -> License:
    lic = kb.licenses.get(license_id)
    if lic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="licence not found")
    return lic


@router.get("/knowledge/facilitators")
async def list_facilitators(kb: KB, jurisdiction: str | None = None) -> list[Facilitator]:
    return [f for f in sorted(kb.facilitators.values(), key=lambda f: f.name)
            if jurisdiction is None or jurisdiction in f.jurisdictions]


# --- missions ---

@router.post("/roadmap")
async def preview_roadmap(profile: MissionProfile, kb: KB, today: Today) -> Roadmap:
    """Roadmap for a profile without saving it (for the mission wizard's live preview)."""
    return build_roadmap(kb, profile, today)


@router.get("/missions")
async def list_missions(p: Read, store: Store) -> list[Mission]:
    return await store.list_missions(p.workspace)


@router.post("/missions", status_code=status.HTTP_201_CREATED)
async def create_mission(profile: MissionProfile, p: Write, store: Store) -> Mission:
    return await store.create_mission(p.workspace, profile)


@router.post("/missions/sample", status_code=status.HTTP_201_CREATED)
async def create_sample_mission(p: Write, store: Store, today: Today) -> Mission:
    return await store.create_mission(p.workspace, sample_mission(today))


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str, p: Read, store: Store) -> Mission:
    return await _mission(store, p, mission_id)


@router.put("/missions/{mission_id}")
async def update_mission(mission_id: str, profile: MissionProfile, p: Write, store: Store) -> Mission:
    m = await store.update_mission(p.workspace, mission_id, profile)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="mission not found")
    return m


@router.delete("/missions/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mission(mission_id: str, p: Write, store: Store) -> Response:
    if not await store.delete_mission(p.workspace, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="mission not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/missions/{mission_id}/roadmap")
async def mission_roadmap(mission_id: str, p: Read, store: Store, kb: KB, today: Today) -> Roadmap:
    m = await _mission(store, p, mission_id)
    return build_roadmap(kb, m.profile, today)


#: Claude-written briefs allowed per workspace per minute (each one is a paid LLM call).
AI_BRIEFS_PER_MINUTE = 6


def _allow_ai_brief(state: Any, workspace: str, now: float) -> bool:
    """Sliding one-minute window per workspace, per process (same model as the Watch limit)."""
    limit = int(getattr(state, "ai_briefs_per_minute", AI_BRIEFS_PER_MINUTE))
    windows = cast("dict[str, collections.deque[float]]",
                   state.__dict__.setdefault("ai_brief_calls", {}))
    calls = windows.setdefault(workspace, collections.deque())
    while calls and now - calls[0] >= 60.0:
        calls.popleft()
    if len(calls) >= limit:
        return False
    calls.append(now)
    return True


@router.post("/missions/{mission_id}/brief")
async def mission_brief(
    mission_id: str, request: Request, p: Read, store: Store, kb: KB, today: Today,
    llm: Annotated[LLMProvider | None, Depends(get_llm)],
    ai: Annotated[bool, Query(description="let Claude write the executive summary")] = False,
    x_workspace: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Brief:
    """The deterministic brief needs read access. ``ai=true`` makes a paid Claude call, so it
    needs write access (``can_create_evidence``) and is rate-limited per workspace."""
    m = await _mission(store, p, mission_id)
    roadmap = build_roadmap(kb, m.profile, today)
    if ai:
        await writer(request, x_workspace, authorization)
        if llm is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="no LLM configured (set COMPLIANCEOS_ANTHROPIC_API_KEY)")
        if not _allow_ai_brief(request.app.state, p.workspace, time.monotonic()):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="too many Claude-written briefs this minute; try again shortly")
    try:
        return await build_brief(roadmap, llm if ai else None)
    except CitationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"brief failed citation grounding: {exc}") from exc
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"LLM call failed: {exc}") from exc


# --- tracking ---

class TrackedApplication(BaseModel):
    application: Application
    item: RoadmapItem | None
    next_action: NextAction
    contacts: int


class ApplicationCreate(BaseModel):
    license_id: str


class ApplicationPatch(BaseModel):
    status: AppStatus | None = None
    submitted_on: dt.date | None = None
    granted_on: dt.date | None = None
    reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)
    owner: str | None = Field(default=None, max_length=200, description="who runs this application")
    note: str = Field(default="", max_length=1000, description="why — recorded in the event log")


def _item(roadmap: Roadmap, license_id: str) -> RoadmapItem | None:
    return next((i for i in roadmap.items if i.license_id == license_id), None)


async def _tracked(store: PlannerStore, p: Principal, roadmap: Roadmap, a: Application,
                   today: dt.date) -> TrackedApplication:
    item = _item(roadmap, a.license_id)
    contacts = await store.list_contacts(p.workspace, a.id)
    latest = next((c for c in reversed(contacts) if c.next_step_due), None)
    due = latest.next_step_due if latest else None
    action = (next_action(item, a, today, due) if item else
              NextAction(title="This licence no longer applies to the mission profile", due=None,
                         overdue=False))
    return TrackedApplication(application=a, item=item, next_action=action, contacts=len(contacts))


@router.get("/missions/{mission_id}/applications")
async def list_applications(mission_id: str, p: Read, store: Store, kb: KB,
                            today: Today) -> list[TrackedApplication]:
    m = await _mission(store, p, mission_id)
    roadmap = build_roadmap(kb, m.profile, today)
    return [await _tracked(store, p, roadmap, a, today)
            for a in await store.list_applications(p.workspace, mission_id)]


@router.post("/missions/{mission_id}/applications", status_code=status.HTTP_201_CREATED)
async def create_application(mission_id: str, body: ApplicationCreate, p: Write, store: Store,
                             kb: KB, today: Today) -> TrackedApplication:
    m = await _mission(store, p, mission_id)
    roadmap = build_roadmap(kb, m.profile, today)
    if _item(roadmap, body.license_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"{body.license_id!r} is not in this mission's roadmap")
    try:
        a = await store.create_application(p.workspace, mission_id, body.license_id)
    except DuplicateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="already tracked") from exc
    return await _tracked(store, p, roadmap, a, today)


@router.patch("/applications/{app_id}")
async def update_application(app_id: str, body: ApplicationPatch, p: Write, store: Store,
                             kb: KB, today: Today) -> TrackedApplication:
    a = await _application(store, p, app_id)
    try:
        updated = apply_update(a, status=body.status, submitted_on=body.submitted_on,
                               granted_on=body.granted_on, today=today)
    except TransitionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    changes: dict[str, Any] = {}
    if body.reference is not None:
        changes["reference"] = body.reference
    if body.notes is not None:
        changes["notes"] = body.notes
    if body.owner is not None:
        changes["owner"] = body.owner.strip()
    updated = updated.model_copy(update=changes)
    kind: Literal["status", "update"] = "status" if updated.status != a.status else "update"
    saved = await store.save_application(p.workspace, updated, kind, a.status, body.note)
    m = await _mission(store, p, saved.mission_id)
    return await _tracked(store, p, build_roadmap(kb, m.profile, today), saved, today)


@router.get("/applications/{app_id}/events")
async def list_events(app_id: str, p: Read, store: Store) -> list[ApplicationEvent]:
    await _application(store, p, app_id)
    return await store.list_events(p.workspace, app_id)


@router.get("/applications/{app_id}/contacts")
async def list_contacts(app_id: str, p: Read, store: Store) -> list[Contact]:
    await _application(store, p, app_id)
    return await store.list_contacts(p.workspace, app_id)


@router.post("/applications/{app_id}/contacts", status_code=status.HTTP_201_CREATED)
async def add_contact(app_id: str, body: ContactIn, p: Write, store: Store) -> Contact:
    await _application(store, p, app_id)
    return await store.add_contact(p.workspace, app_id, body)


class DeadlineOut(Deadline):
    overdue: bool
    tracked: bool


async def _deadlines(store: PlannerStore, p: Principal, roadmap: Roadmap, mission_id: str,
                     today: dt.date) -> list[DeadlineOut]:
    apps = {a.license_id: a for a in await store.list_applications(p.workspace, mission_id)}
    out: list[DeadlineOut] = []
    for item in roadmap.items:
        a = apps.get(item.license_id)
        started = a is not None and a.status != AppStatus.NOT_STARTED
        submitted = a is not None and a.submitted_on is not None
        if not started:
            out.append(DeadlineOut(date=item.start_by, kind="start", license_id=item.license_id,
                                   title=f"Start preparing: {item.name}", hard=False,
                                   overdue=item.start_by < today, tracked=a is not None))
        if not submitted:
            out.append(DeadlineOut(date=item.submit_by, kind="submit", license_id=item.license_id,
                                   title=f"Submit: {item.name}", hard=item.critical,
                                   overdue=item.submit_by < today, tracked=a is not None))
        for o in redate_obligations(item, a):
            out.append(DeadlineOut(date=o.due, kind="obligation", license_id=item.license_id,
                                   title=o.name, hard=o.kind == "hard", overdue=o.due < today,
                                   tracked=a is not None))
        if a is not None:
            for c in await store.list_contacts(p.workspace, a.id):
                if c.next_step and c.next_step_due:
                    out.append(DeadlineOut(date=c.next_step_due, kind="obligation",
                                           license_id=item.license_id,
                                           title=f"{c.next_step} ({c.counterpart})", hard=False,
                                           overdue=c.next_step_due < today, tracked=True))
    out.sort(key=lambda d: (d.date, d.license_id, d.kind))
    return out


@router.get("/program")
async def program(p: Read, store: Store, kb: KB, today: Today) -> Program:
    """The workspace's missions folded into one picture per jurisdiction: how many licences each
    market needs, how many are tracked, granted or overdue, and the next dates across all missions."""
    views: list[MissionView] = []
    for m in await store.list_missions(p.workspace):
        roadmap = build_roadmap(kb, m.profile, today)
        deadlines = [
            ProgramDeadline(**d.model_dump(), mission_id=m.id, mission_name=m.profile.name,
                            jurisdiction=next((i.jurisdiction for i in roadmap.items
                                               if i.license_id == d.license_id), ""))
            for d in await _deadlines(store, p, roadmap, m.id, today)]
        views.append(MissionView(mission_id=m.id, mission_name=m.profile.name, roadmap=roadmap,
                                 applications=await store.list_applications(p.workspace, m.id),
                                 deadlines=deadlines))
    return build_program(views, today)


@router.get("/missions/{mission_id}/deadlines")
async def mission_deadlines(mission_id: str, p: Read, store: Store, kb: KB,
                            today: Today) -> list[DeadlineOut]:
    m = await _mission(store, p, mission_id)
    return await _deadlines(store, p, build_roadmap(kb, m.profile, today), mission_id, today)


@router.get("/missions/{mission_id}/calendar.ics")
async def mission_calendar(mission_id: str, p: Read, store: Store, kb: KB, today: Today) -> Response:
    m = await _mission(store, p, mission_id)
    roadmap = build_roadmap(kb, m.profile, today)
    deadlines = await _deadlines(store, p, roadmap, mission_id, today)
    body = calendar_ics(roadmap, mission_id, [Deadline(**d.model_dump(exclude={"overdue", "tracked"}))
                                              for d in deadlines])
    return Response(content=body, media_type="text/calendar; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="licensing-{mission_id[:8]}.ics"'})


@router.get("/missions/{mission_id}/dossier.pdf")
async def mission_dossier(
    mission_id: str, p: Read, store: Store, kb: KB, today: Today,
    keystore: Annotated[KeyStore | None, Depends(get_planner_keystore)],
) -> Response:
    m = await _mission(store, p, mission_id)
    roadmap = build_roadmap(kb, m.profile, today)
    brief = await build_brief(roadmap)
    pdf, info = dossier_pdf(roadmap, brief, workspace=p.workspace, keystore=keystore)
    headers = {
        "Content-Disposition": f'attachment; filename="licensing-roadmap-{mission_id[:8]}.pdf"',
        "X-Roadmap-SHA256": info.sha256,
        "X-Roadmap-Signed": "true" if info.signed else "false",
    }
    if info.fingerprint:
        headers["X-Roadmap-Key-Fingerprint"] = info.fingerprint
    return Response(content=pdf, media_type="application/pdf", headers=headers)


@router.get("/missions/{mission_id}/dossier.signed.json")
async def mission_signed_dossier(
    mission_id: str, p: Read, store: Store, kb: KB, today: Today,
    keystore: Annotated[KeyStore | None, Depends(get_planner_keystore)],
) -> Response:
    """The signed deliverable on its own: roadmap and brief, SHA-256, and (with a key configured)
    the Ed25519 signature and public key. Check it offline against the key fingerprint you were
    given separately; the embedded key alone proves integrity, not who signed."""
    m = await _mission(store, p, mission_id)
    roadmap = build_roadmap(kb, m.profile, today)
    sidecar, info, _ = signed_document(roadmap, await build_brief(roadmap),
                                       workspace=p.workspace, keystore=keystore)
    headers = {"Content-Disposition": f'attachment; filename="dossier-signed-{mission_id[:8]}.json"',
               "X-Dossier-Signed": "true" if info.signed else "false"}
    if info.fingerprint:
        headers["X-Dossier-Key-Fingerprint"] = info.fingerprint
    return Response(content=sidecar, media_type="application/json", headers=headers)


@router.get("/missions/{mission_id}/dossier.md")
async def mission_review_package(
    mission_id: str, p: Read, store: Store, kb: KB, today: Today,
    keystore: Annotated[KeyStore | None, Depends(get_planner_keystore)],
) -> Response:
    """The dossier as Markdown with a reviewer checklist, stable between exports (ADR-0022). Ends
    with the SHA-256 and signature of the dossier the text was rendered from."""
    m = await _mission(store, p, mission_id)
    roadmap = build_roadmap(kb, m.profile, today)
    brief = await build_brief(roadmap)
    _, info, sig = signed_document(roadmap, brief, workspace=p.workspace, keystore=keystore)
    integrity = ["", "## Integrity", "",
                 "The signature covers the dossier data (roadmap and brief) this text was rendered "
                 "from, not the Markdown itself. Compare the fingerprint with one you were given "
                 "separately; fetch `dossier.signed.json` to verify it offline.", "",
                 f"- SHA-256: `{info.sha256}`"]
    if info.signed:
        integrity += [f"- Ed25519 key fingerprint: `{info.fingerprint}`",
                      f"- Signature: `{sig['signature_hex']}`"]
    else:
        integrity.append("- Unsigned: no signing key is configured on this server.")
    body = dossier_markdown(roadmap, brief).rstrip("\n") + "\n" + "\n".join(integrity) + "\n"
    return Response(content=body, media_type="text/markdown; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="licensing-review-{mission_id[:8]}.md"'})


class EmailRequest(BaseModel):
    license_id: str
    recipient: str = Field(description="authority id or facilitator id")


@router.post("/missions/{mission_id}/intro-email")
async def draft_intro_email(mission_id: str, body: EmailRequest, p: Read, store: Store, kb: KB,
                            today: Today) -> EmailDraft:
    m = await _mission(store, p, mission_id)
    roadmap = build_roadmap(kb, m.profile, today)
    item = _item(roadmap, body.license_id)
    if item is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="licence not in roadmap")
    try:
        return intro_email(roadmap, item, body.recipient)
    except KeyError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="recipient is not an authority or facilitator in this roadmap") from exc


# --- the Watch (ADR-0019) ---

@router.get("/watch/changes")
async def watch_changes(p: Read, store: Store, kb: KB) -> list[WatchItem]:
    """Source changes that touch this workspace's tracked applications, newest first."""
    return await watch_items(store, p.workspace, kb, None)


@router.get("/missions/{mission_id}/watch")
async def mission_watch(mission_id: str, p: Read, store: Store, kb: KB) -> list[WatchItem]:
    await _mission(store, p, mission_id)
    return await watch_items(store, p.workspace, kb, [mission_id])


@router.post("/watch/run")
async def run_watch_now(request: Request, p: Write, store: Store, kb: KB) -> RunSummary:
    """Check every source in the pack once. Same trust model as every other change: local mode
    needs the client header; team mode needs ``can_create_evidence`` on the workspace. Scheduling
    with ``python -m app.planner.watch run`` is the recommended path."""
    state = request.app.state
    lock = cast("asyncio.Lock", state.__dict__.setdefault("watch_lock", asyncio.Lock()))
    if lock.locked():
        raise HTTPException(status.HTTP_409_CONFLICT, "a Watch run is already in progress")
    cooldown = float(getattr(state, "watch_min_interval", WATCH_MIN_INTERVAL_S))
    last = getattr(state, "watch_last_run", None)
    now = dt.datetime.now(dt.UTC)
    if last is not None and (now - last).total_seconds() < cooldown:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "the Watch ran moments ago; try again shortly")
    fetcher = cast("Fetcher | None", getattr(state, "watch_fetcher", None))
    interval = float(getattr(state, "watch_host_interval", HOST_INTERVAL_S))
    llm = cast("LLMProvider | None", getattr(state, "llm", None))
    async with lock:
        state.watch_last_run = now
        return await run_watch(kb, store, fetcher or HttpFetcher(), now, host_interval=interval,
                               classifier=make_classifier(llm) if llm else None)


# --- signed program history (ADR-0021) ---

@router.post("/history/export")
async def export_history(p: Write, store: Store,
                         keystore: Annotated[KeyStore | None, Depends(get_planner_keystore)],
                         ) -> HistoryDocument:
    """Signed export of every application event in this workspace. Each export records a
    checkpoint and names the previous export's Merkle root, so earlier history cannot be dropped
    unnoticed. Unsigned (and not checkpointed) when the server has no signing key."""
    return await build_history(store, p.workspace, keystore, dt.datetime.now(dt.UTC))


@router.get("/missions/{mission_id}/history")
async def mission_history(mission_id: str, p: Read, store: Store,
                          keystore: Annotated[KeyStore | None, Depends(get_planner_keystore)],
                          ) -> HistoryDocument:
    """Signed export of one mission's events. A view of part of the history: it is not chained."""
    await _mission(store, p, mission_id)
    return await build_history(store, p.workspace, keystore, dt.datetime.now(dt.UTC), mission_id)


# --- pilot usage (ADR-0021) ---

UsageKind = Literal["session_start", "mission_viewed", "watch_viewed", "alert_opened",
                    "dossier_exported"]


class RecipientsIn(BaseModel):
    recipients: list[str]


class RecipientsOut(BaseModel):
    recipients: list[str]
    fallback_to_deployment_list: bool


@router.get("/alerts/recipients")
async def get_alert_recipients(p: Read, store: Store) -> RecipientsOut:
    """Who receives this workspace's Watch digest. Empty means the deployment-wide list is used."""
    own = await store.alert_recipients(p.workspace)
    return RecipientsOut(recipients=own, fallback_to_deployment_list=not own)


@router.put("/alerts/recipients")
async def set_alert_recipients(body: RecipientsIn, p: Write, store: Store) -> RecipientsOut:
    try:
        cleaned = clean_recipients(body.recipients)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    await store.set_alert_recipients(p.workspace, cleaned)
    return RecipientsOut(recipients=cleaned, fallback_to_deployment_list=not cleaned)


class UsageIn(BaseModel):
    kind: UsageKind


class UsageSummary(BaseModel):
    since: dt.datetime
    days: int
    counts: dict[str, int]
    active_days: int


@router.post("/usage", status_code=status.HTTP_204_NO_CONTENT)
async def record_usage(body: UsageIn, p: Write, store: Store) -> Response:
    """Record that something was used. Only the kind, workspace, actor and time are stored."""
    await store.add_usage_event(p.workspace, p.user, body.kind, dt.datetime.now(dt.UTC))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/usage/summary")
async def usage_summary(p: Read, store: Store, days: Annotated[int, Query(ge=1, le=365)] = 30,
                        ) -> UsageSummary:
    """Counts per kind and the number of days with any activity, for the last ``days`` days."""
    since = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
    events = await store.usage_events(p.workspace, since)
    counts: dict[str, int] = {}
    for kind, _ in events:
        counts[kind] = counts.get(kind, 0) + 1
    return UsageSummary(since=since, days=days, counts=counts,
                        active_days=len({at.astimezone(dt.UTC).date() for _, at in events}))
