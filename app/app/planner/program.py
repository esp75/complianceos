"""One client, many markets: the workspace's missions folded into a per-jurisdiction picture.

Pure aggregation over what the planner already computes (roadmaps, tracked applications and
deadlines); nothing new is stored. A licence that appears in several missions counts once per
mission, since each mission has its own application to track."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from app.planner.plan import Deadline, Roadmap
from app.planner.tracker import Application, AppStatus

UPCOMING = 8
_DONE = {AppStatus.GRANTED, AppStatus.REFUSED, AppStatus.WITHDRAWN}


class ProgramDeadline(Deadline):
    mission_id: str
    mission_name: str
    jurisdiction: str
    overdue: bool


class ProgramMarket(BaseModel):
    jurisdiction: str
    name: str
    kind: str
    licences: int  # licences the missions need here
    tracked: int
    granted: int
    in_progress: int
    overdue: int
    next_deadline: ProgramDeadline | None


class Program(BaseModel):
    missions: int
    markets: list[ProgramMarket]
    upcoming: list[ProgramDeadline]


class MissionView(BaseModel):
    """What the aggregation needs from one mission."""

    mission_id: str
    mission_name: str
    roadmap: Roadmap
    applications: list[Application]
    deadlines: list[ProgramDeadline]


def build_program(views: list[MissionView], today: dt.date) -> Program:
    names: dict[str, tuple[str, str]] = {}
    rows: dict[str, dict[str, int]] = {}
    nxt: dict[str, ProgramDeadline] = {}
    for v in views:
        for j in v.roadmap.jurisdictions:
            names[j.id] = (j.name, j.kind)
        by_license = {a.license_id: a for a in v.applications}
        for item in v.roadmap.items:
            r = rows.setdefault(item.jurisdiction, {"licences": 0, "tracked": 0, "granted": 0,
                                                    "in_progress": 0, "overdue": 0})
            r["licences"] += 1
            a = by_license.get(item.license_id)
            if a is not None:
                r["tracked"] += 1
                r["granted"] += a.status == AppStatus.GRANTED
                r["in_progress"] += a.status not in _DONE and a.status != AppStatus.NOT_STARTED
        for d in v.deadlines:
            if d.overdue:
                rows.setdefault(d.jurisdiction, {"licences": 0, "tracked": 0, "granted": 0,
                                                 "in_progress": 0, "overdue": 0})["overdue"] += 1
            cur = nxt.get(d.jurisdiction)
            if not d.overdue and (cur is None or d.date < cur.date):
                nxt[d.jurisdiction] = d
    markets = [
        ProgramMarket(jurisdiction=j, name=names.get(j, (j, "national"))[0],
                      kind=names.get(j, (j, "national"))[1], next_deadline=nxt.get(j), **r)
        for j, r in rows.items()
    ]
    # Overdue first, then the nearest next deadline, so the page leads with what needs attention.
    markets.sort(key=lambda m: (-m.overdue, m.next_deadline.date if m.next_deadline else dt.date.max,
                                m.name))
    upcoming = sorted((d for v in views for d in v.deadlines if not d.overdue),
                      key=lambda d: (d.date, d.mission_name, d.license_id))[:UPCOMING]
    return Program(missions=len(views), markets=markets, upcoming=upcoming)
