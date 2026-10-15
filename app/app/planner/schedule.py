"""Roadmap scheduling over the licence prerequisite graph (ADR-0018).

Each licence is a task with a preparation time, a review time (submission to grant), a date it is
needed by, and optionally the earliest date a submission may be made. Prerequisites order tasks:
a task's submission waits for its prerequisite to reach a stage (submitted or granted).

Two passes over the DAG:

- forward, from today: the earliest each task can be submitted and granted if work starts now;
- backward, from the need dates: the latest each task can be submitted and still let everything
  downstream be granted in time.

Slack is the gap between the two submission dates. Negative slack means the need date cannot be
met; the tasks with the least slack form the critical path.

Pure and deterministic: dates in, dates out. The domain mapping lives in ``app.planner.plan``.
"""

from __future__ import annotations

import calendar
import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from app.planner.knowledge import Offset

Stage = Literal["submitted", "granted"]

#: Slack under this is flagged as tight, so users see risk before it turns into lateness.
TIGHT_SLACK_DAYS = 28


class ScheduleError(ValueError):
    """Raised when tasks cannot be scheduled (unknown prerequisite or a cycle)."""


@dataclass(frozen=True)
class Task:
    id: str
    prep_days: int
    review_days: int
    need_by: dt.date
    window_opens: dt.date | None = None
    deps: tuple[tuple[str, Stage], ...] = ()


@dataclass(frozen=True)
class Scheduled:
    id: str
    earliest_start: dt.date
    earliest_submit: dt.date
    earliest_grant: dt.date
    latest_start: dt.date
    latest_submit: dt.date
    latest_grant: dt.date
    slack_days: int
    critical: bool

    @property
    def late(self) -> bool:
        return self.slack_days < 0

    @property
    def risk(self) -> Literal["late", "tight", "ok"]:
        if self.slack_days < 0:
            return "late"
        return "tight" if self.slack_days < TIGHT_SLACK_DAYS else "ok"


def topological_order(tasks: Mapping[str, Task]) -> list[str]:
    """Prerequisites before dependents; ties broken by id so output is deterministic."""
    for t in tasks.values():
        for dep, _ in t.deps:
            if dep not in tasks:
                raise ScheduleError(f"task {t.id!r} depends on unknown task {dep!r}")
    indegree = {tid: len(t.deps) for tid, t in tasks.items()}
    dependents: dict[str, list[str]] = {tid: [] for tid in tasks}
    for t in tasks.values():
        for dep, _ in t.deps:
            dependents[dep].append(t.id)
    ready = sorted(tid for tid, n in indegree.items() if n == 0)
    order: list[str] = []
    while ready:
        tid = ready.pop(0)
        order.append(tid)
        for nxt in sorted(dependents[tid]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort()
    if len(order) != len(tasks):
        stuck = sorted(tid for tid, n in indegree.items() if n > 0)
        raise ScheduleError(f"prerequisite cycle among {stuck}")
    return order


def schedule(tasks: Iterable[Task], today: dt.date) -> dict[str, Scheduled]:
    by_id = {t.id: t for t in tasks}
    order = topological_order(by_id)
    day = dt.timedelta

    e_submit: dict[str, dt.date] = {}
    e_grant: dict[str, dt.date] = {}
    for tid in order:
        t = by_id[tid]
        candidates = [today + day(t.prep_days)]
        if t.window_opens:
            candidates.append(t.window_opens)
        for dep, stage in t.deps:
            candidates.append(e_submit[dep] if stage == "submitted" else e_grant[dep])
        e_submit[tid] = max(candidates)
        e_grant[tid] = e_submit[tid] + day(t.review_days)

    l_submit: dict[str, dt.date] = {}
    l_grant: dict[str, dt.date] = {}
    dependents: dict[str, list[tuple[str, Stage]]] = {tid: [] for tid in by_id}
    for t in by_id.values():
        for dep, stage in t.deps:
            dependents[dep].append((t.id, stage))
    for tid in reversed(order):
        t = by_id[tid]
        grant_by = [t.need_by] + [l_submit[d] for d, s in dependents[tid] if s == "granted"]
        l_grant[tid] = min(grant_by)
        submit_by = [l_grant[tid] - day(t.review_days)]
        submit_by += [l_submit[d] for d, s in dependents[tid] if s == "submitted"]
        l_submit[tid] = min(submit_by)

    slack = {tid: (l_submit[tid] - e_submit[tid]).days for tid in by_id}
    least = min(slack.values(), default=0)
    return {
        tid: Scheduled(
            id=tid,
            earliest_start=e_submit[tid] - day(by_id[tid].prep_days),
            earliest_submit=e_submit[tid],
            earliest_grant=e_grant[tid],
            latest_start=l_submit[tid] - day(by_id[tid].prep_days),
            latest_submit=l_submit[tid],
            latest_grant=l_grant[tid],
            slack_days=slack[tid],
            critical=slack[tid] == least,
        )
        for tid in order
    }


def shift(date: dt.date, offset: Offset, sign: int = 1) -> dt.date:
    """Move ``date`` by a calendar offset. Month arithmetic clamps to the month's last day."""
    months = date.month - 1 + sign * (offset.years * 12 + offset.months)
    year, month = date.year + months // 12, months % 12 + 1
    d = dt.date(year, month, min(date.day, calendar.monthrange(year, month)[1]))
    return d + dt.timedelta(days=sign * (offset.weeks * 7 + offset.days))
