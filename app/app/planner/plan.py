"""Build a licensing roadmap for a mission (ADR-0018).

Joins the three deterministic steps — which licences apply (``rules``), when to do them
(``schedule``), and what follows from them (obligations) — into one serialisable ``Roadmap``.
Every reason, duration and obligation carries the ids of the citations behind it, and the roadmap
ships those citations, so any claim on screen can be traced to the text of the law.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel

from app.planner.knowledge import (
    Authority,
    Citation,
    Duration,
    Facilitator,
    KnowledgeBase,
    License,
    Obligation,
    Offset,
    ReviewStatus,
)
from app.planner.mission import MissionProfile
from app.planner.rules import RequiredLicense, required_licenses
from app.planner.schedule import Scheduled, Task, schedule, shift

#: Recurring obligations are expanded this many times at most.
MAX_OCCURRENCES = 10


class ReasonOut(BaseModel):
    text: str
    cite: list[str]


class PrerequisiteOut(BaseModel):
    license_id: str
    stage: Literal["submitted", "granted"]


class DatedObligation(BaseModel):
    id: str
    license_id: str
    name: str
    description: str
    kind: Literal["hard", "soft"]
    anchor: Literal["submitted", "granted", "launch", "service_start"]
    #: When the clock runs, in words ("36 months after grant"). Dates anchored on submission or
    #: grant assume work starts now, so the real date can only be the same or later.
    when: str
    due: dt.date
    occurrence: int
    recurring: bool
    cite: list[str]


class RoadmapItem(BaseModel):
    license_id: str
    name: str
    name_local: str | None
    jurisdiction: str
    category: str
    authority_id: str
    summary: str
    reasons: list[ReasonOut]
    legal_basis: list[str]
    prerequisites: list[PrerequisiteOut]
    needed_by: dt.date
    needed_for: Literal["launch", "service_start"]
    preparation: Duration
    review: Duration
    start_by: dt.date
    submit_by: dt.date
    earliest_submit: dt.date
    earliest_grant: dt.date
    slack_days: int
    risk: Literal["late", "tight", "ok"]
    critical: bool
    documents: list[str]
    fees: str | None
    requires_local_presence: bool | None
    local_presence_note: str | None
    obligations: list[DatedObligation]
    facilitators: list[str]
    status: ReviewStatus
    last_verified: dt.date


class AuthorityOut(BaseModel):
    jurisdiction: str
    authority: Authority


class JurisdictionSummary(BaseModel):
    id: str
    name: str
    kind: Literal["national", "international"]
    licence_count: int
    earliest_start_by: dt.date
    late_count: int
    authority_ids: list[str]


class Deadline(BaseModel):
    date: dt.date
    kind: Literal["start", "submit", "obligation"]
    license_id: str
    title: str
    hard: bool


class Roadmap(BaseModel):
    mission: MissionProfile
    generated_on: dt.date
    items: list[RoadmapItem]
    jurisdictions: list[JurisdictionSummary]
    authorities: dict[str, AuthorityOut]
    deadlines: list[Deadline]
    critical_path: list[str]
    citations: dict[str, Citation]
    facilitators: dict[str, Facilitator]
    warnings: list[str]
    data_status: dict[str, int]


def _weeks(n: int) -> int:
    return n * 7


def _task(req: RequiredLicense, mission: MissionProfile, in_plan: set[str]) -> Task:
    lic = req.license
    need = mission.target_launch_date if lic.needed_by == "launch" else mission.effective_service_start
    window = shift(need, lic.submission_window.opens_before_need, -1) if lic.submission_window else None
    deps = tuple((p.license, p.stage) for p in lic.prerequisites if p.license in in_plan)
    return Task(
        id=lic.id,
        prep_days=_weeks(lic.preparation.typical_weeks),
        review_days=_weeks(lic.review.typical_weeks),
        need_by=need,
        window_opens=window,
        deps=deps,
    )


def _anchor_date(o: Obligation, s: Scheduled, mission: MissionProfile) -> dt.date:
    return {
        "submitted": s.earliest_submit,
        "granted": s.earliest_grant,
        "launch": mission.target_launch_date,
        "service_start": mission.effective_service_start,
    }[o.anchor]


_ANCHOR_WORDS = {"submitted": "submission", "granted": "grant", "launch": "launch",
                 "service_start": "service start"}


def describe_offset(offset: Offset) -> str:
    parts = [(offset.years, "year"), (offset.months, "month"), (offset.weeks, "week"), (offset.days, "day")]
    words = [f"{n} {unit}{'s' if n != 1 else ''}" for n, unit in parts if n]
    return ", ".join(words)


def _when(o: Obligation) -> str:
    anchor = _ANCHOR_WORDS[o.anchor]
    span = describe_offset(o.offset)
    text = f"{span} after {anchor}" if span else f"at {anchor}"
    return f"{text}, then every {describe_offset(o.repeat_every)}" if o.repeat_every else text


def _dated(lic: License, obligations: tuple[Obligation, ...], s: Scheduled,
           mission: MissionProfile) -> list[DatedObligation]:
    out = []
    for o in obligations:
        due = shift(_anchor_date(o, s, mission), o.offset)
        count = MAX_OCCURRENCES if o.repeat_every else 1
        for n in range(count):
            out.append(DatedObligation(
                id=o.id, license_id=lic.id, name=o.name, description=o.description.strip(),
                kind=o.kind, anchor=o.anchor, when=_when(o), due=due, occurrence=n + 1,
                recurring=o.repeat_every is not None, cite=list(o.cite),
            ))
            if o.repeat_every:
                due = shift(due, o.repeat_every)
    return out


def _cited_ids(req: RequiredLicense) -> list[str]:
    lic = req.license
    ids = [c.id for c in lic.legal_basis]
    ids += [c for r in req.reasons for c in r.cite]
    ids += lic.preparation.cite + lic.review.cite
    ids += lic.submission_window.cite if lic.submission_window else []
    ids += [c for o in req.obligations for c in o.cite]
    return list(dict.fromkeys(ids))


def _coverage_warnings(kb: KnowledgeBase, mission: MissionProfile) -> list[str]:
    covered = {j.country for j in kb.jurisdictions.values() if j.country}
    facts = mission.facts()
    named: dict[str, list[str]] = {}
    for key, label in (
        ("operator_country", "operator"),
        ("filing_administration", "ITU filing administration"),
        ("control_country", "mission control"),
        ("launch_country", "launch site"),
    ):
        if facts[key]:
            named.setdefault(facts[key], []).append(label)
    for cc in facts["ground_station_countries"]:
        named.setdefault(cc, []).append("ground station")
    for cc in facts["service_countries"]:
        named.setdefault(cc, []).append("service market")
    warnings = [
        f"No licensing data for {cc} yet ({', '.join(roles)}). Requirements there are not in this "
        "roadmap; the knowledge pack welcomes contributions."
        for cc, roles in sorted(named.items()) if cc not in covered
    ]
    if mission.launch_country is None:
        warnings.append("Launch site not chosen yet: launch-state authorisations are not checked.")
    return warnings


def build_roadmap(kb: KnowledgeBase, mission: MissionProfile, today: dt.date) -> Roadmap:
    required = required_licenses(kb, mission)
    in_plan = {r.license.id for r in required}
    sched = schedule([_task(r, mission, in_plan) for r in required], today)

    items: list[RoadmapItem] = []
    cited: dict[str, None] = {}
    for req in required:
        lic, s = req.license, sched[req.license.id]
        need = mission.target_launch_date if lic.needed_by == "launch" else mission.effective_service_start
        cited.update(dict.fromkeys(_cited_ids(req)))
        items.append(RoadmapItem(
            license_id=lic.id, name=lic.name, name_local=lic.name_local,
            jurisdiction=lic.jurisdiction, category=lic.category.value,
            authority_id=lic.authority, summary=lic.summary.strip(),
            reasons=[ReasonOut(text=r.text.strip(), cite=list(r.cite)) for r in req.reasons],
            legal_basis=[c.id for c in lic.legal_basis],
            prerequisites=[PrerequisiteOut(license_id=p.license, stage=p.stage)
                           for p in lic.prerequisites if p.license in in_plan],
            needed_by=need, needed_for=lic.needed_by,
            preparation=lic.preparation, review=lic.review,
            start_by=s.latest_start, submit_by=s.latest_submit,
            earliest_submit=s.earliest_submit, earliest_grant=s.earliest_grant,
            slack_days=s.slack_days, risk=s.risk, critical=s.critical,
            documents=list(lic.documents), fees=lic.fees.strip() if lic.fees else None,
            requires_local_presence=lic.requires_local_presence,
            local_presence_note=lic.local_presence_note.strip() if lic.local_presence_note else None,
            obligations=_dated(lic, req.obligations, s, mission),
            facilitators=[f.id for f in kb.facilitators_for(lic.jurisdiction, lic.category)],
            status=lic.status, last_verified=lic.last_verified,
        ))
    items.sort(key=lambda i: (i.start_by, i.license_id))

    all_citations = kb.citations
    names = {j.id: j.name for j in kb.jurisdictions.values()}
    jurisdictions = []
    for jid in sorted({i.jurisdiction for i in items}, key=lambda j: (j != "itu", names[j])):
        mine = [i for i in items if i.jurisdiction == jid]
        jurisdictions.append(JurisdictionSummary(
            id=jid, name=names[jid], kind=kb.jurisdictions[jid].kind, licence_count=len(mine),
            earliest_start_by=min(i.start_by for i in mine),
            late_count=sum(1 for i in mine if i.risk == "late"),
            authority_ids=list(dict.fromkeys(i.authority_id for i in mine)),
        ))
    authorities = {}
    for i in items:
        found = kb.authority(i.authority_id)
        if found:
            authorities[i.authority_id] = AuthorityOut(jurisdiction=found[0].id, authority=found[1])

    deadlines = []
    for i in items:
        deadlines.append(Deadline(date=i.start_by, kind="start", license_id=i.license_id,
                                  title=f"Start preparing: {i.name}", hard=False))
        deadlines.append(Deadline(date=i.submit_by, kind="submit", license_id=i.license_id,
                                  title=f"Submit: {i.name}", hard=i.critical))
        deadlines += [Deadline(date=o.due, kind="obligation", license_id=i.license_id,
                               title=o.name, hard=o.kind == "hard") for o in i.obligations]
    deadlines.sort(key=lambda d: (d.date, d.license_id, d.kind))

    warnings = _coverage_warnings(kb, mission)
    for i in items:
        if i.risk == "late":
            weeks = -i.slack_days // 7 + (1 if -i.slack_days % 7 else 0)
            warnings.append(
                f"{i.name}: even starting today, it cannot be granted by {i.needed_by.isoformat()} "
                f"(about {weeks} week(s) short). Consider moving the date or asking the authority "
                "about expedited review."
            )

    used_facilitators = {f for i in items for f in i.facilitators}
    status_counts = {s.value: sum(1 for i in items if i.status == s) for s in ReviewStatus}
    return Roadmap(
        mission=mission,
        generated_on=today,
        items=items,
        jurisdictions=jurisdictions,
        authorities=authorities,
        deadlines=deadlines,
        critical_path=[i.license_id for i in items if i.critical],
        citations={cid: all_citations[cid] for cid in cited if cid in all_citations},
        facilitators={fid: kb.facilitators[fid] for fid in sorted(used_facilitators)},
        warnings=warnings,
        data_status=status_counts,
    )
