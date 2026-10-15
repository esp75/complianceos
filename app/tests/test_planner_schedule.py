"""Scheduler tests: hand-checked cases plus hypothesis properties over random prerequisite DAGs.

The properties are the guarantees the roadmap relies on: dependencies are respected in both
passes, review times are honoured, slack is the gap between the passes, a chain of prerequisites
can never finish sooner than the sum of its parts, and cycles are refused.
"""

from __future__ import annotations

import datetime as dt

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.planner.knowledge import Offset
from app.planner.schedule import ScheduleError, Task, schedule, shift, topological_order

TODAY = dt.date(2026, 10, 15)


def test_single_task_starts_today_and_counts_slack_to_need_date() -> None:
    need = TODAY + dt.timedelta(days=200)
    s = schedule([Task("a", prep_days=14, review_days=30, need_by=need)], TODAY)["a"]
    assert s.earliest_submit == TODAY + dt.timedelta(days=14)
    assert s.earliest_grant == TODAY + dt.timedelta(days=44)
    assert s.latest_grant == need
    assert s.latest_submit == need - dt.timedelta(days=30)
    assert s.slack_days == 200 - 44
    assert s.risk == "ok" and s.critical


def test_granted_prerequisite_delays_submission() -> None:
    need = TODAY + dt.timedelta(days=365)
    out = schedule([
        Task("api", prep_days=10, review_days=100, need_by=need),
        Task("note", prep_days=5, review_days=50, need_by=need, deps=(("api", "granted"),)),
    ], TODAY)
    assert out["note"].earliest_submit == out["api"].earliest_grant
    # Backward pass: api must be granted before note's latest submission.
    assert out["api"].latest_grant == out["note"].latest_submit


def test_submitted_prerequisite_only_waits_for_submission() -> None:
    need = TODAY + dt.timedelta(days=365)
    out = schedule([
        Task("filing", prep_days=30, review_days=200, need_by=need),
        Task("access", prep_days=5, review_days=20, need_by=need, deps=(("filing", "submitted"),)),
    ], TODAY)
    assert out["access"].earliest_submit == out["filing"].earliest_submit


def test_window_holds_back_early_submission() -> None:
    need = TODAY + dt.timedelta(days=5000)
    opens = shift(need, Offset(years=3), -1)
    s = schedule([Task("n", prep_days=7, review_days=30, need_by=need, window_opens=opens)], TODAY)["n"]
    assert s.earliest_submit == opens


def test_late_when_need_date_is_too_close() -> None:
    s = schedule([Task("x", prep_days=30, review_days=60, need_by=TODAY + dt.timedelta(days=50))],
                 TODAY)["x"]
    assert s.late and s.risk == "late" and s.slack_days == 50 - 90


def test_cycle_is_refused() -> None:
    need = TODAY + dt.timedelta(days=100)
    with pytest.raises(ScheduleError, match="cycle"):
        schedule([
            Task("a", 1, 1, need, deps=(("b", "granted"),)),
            Task("b", 1, 1, need, deps=(("a", "granted"),)),
        ], TODAY)


def test_unknown_prerequisite_is_refused() -> None:
    with pytest.raises(ScheduleError, match="unknown"):
        schedule([Task("a", 1, 1, TODAY, deps=(("ghost", "granted"),))], TODAY)


@pytest.mark.parametrize(("start", "offset", "sign", "expected"), [
    (dt.date(2026, 1, 31), Offset(months=1), 1, dt.date(2026, 2, 28)),
    (dt.date(2028, 2, 29), Offset(years=1), 1, dt.date(2029, 2, 28)),
    (dt.date(2030, 3, 15), Offset(years=7), -1, dt.date(2023, 3, 15)),
    (dt.date(2026, 10, 15), Offset(years=9, days=30), 1, dt.date(2035, 11, 14)),
])
def test_shift(start: dt.date, offset: Offset, sign: int, expected: dt.date) -> None:
    assert shift(start, offset, sign) == expected


# --- properties over random DAGs ---

@st.composite
def dags(draw: st.DrawFn) -> list[Task]:
    n = draw(st.integers(min_value=1, max_value=12))
    tasks = []
    for i in range(n):
        # Only earlier tasks can be prerequisites, so the graph is acyclic by construction.
        deps = draw(st.lists(
            st.tuples(st.integers(0, i - 1).map(str), st.sampled_from(["submitted", "granted"])),
            max_size=min(i, 3), unique_by=lambda d: d[0],
        )) if i else []
        tasks.append(Task(
            id=str(i),
            prep_days=draw(st.integers(0, 120)),
            review_days=draw(st.integers(0, 400)),
            need_by=TODAY + dt.timedelta(days=draw(st.integers(-30, 2000))),
            window_opens=(TODAY + dt.timedelta(days=draw(st.integers(-100, 1500))))
            if draw(st.booleans()) else None,
            deps=tuple(deps),
        ))
    return tasks


@settings(max_examples=300, deadline=None)
@given(dags())
def test_dependencies_respected_in_both_passes(tasks: list[Task]) -> None:
    out = schedule(tasks, TODAY)
    for t in tasks:
        for dep, stage in t.deps:
            d = out[dep]
            if stage == "granted":
                assert out[t.id].earliest_submit >= d.earliest_grant
                assert d.latest_grant <= out[t.id].latest_submit
            else:
                assert out[t.id].earliest_submit >= d.earliest_submit
                assert d.latest_submit <= out[t.id].latest_submit


@settings(max_examples=300, deadline=None)
@given(dags())
def test_durations_slack_and_critical(tasks: list[Task]) -> None:
    out = schedule(tasks, TODAY)
    by_id = {t.id: t for t in tasks}
    least = min(s.slack_days for s in out.values())
    for tid, s in out.items():
        t = by_id[tid]
        assert s.earliest_submit >= TODAY + dt.timedelta(days=t.prep_days)
        assert (s.earliest_grant - s.earliest_submit).days == t.review_days
        assert (s.latest_grant - s.latest_submit).days >= t.review_days
        assert s.latest_grant <= t.need_by
        assert s.slack_days == (s.latest_submit - s.earliest_submit).days
        assert s.critical == (s.slack_days == least)
        if t.window_opens:
            assert s.earliest_submit >= t.window_opens


@settings(max_examples=300, deadline=None)
@given(dags())
def test_a_chain_never_finishes_sooner_than_its_parts(tasks: list[Task]) -> None:
    """Follow 'granted' links back from each task: its earliest grant is at least the first task's
    preparation plus every review along the chain."""
    out = schedule(tasks, TODAY)
    by_id = {t.id: t for t in tasks}
    for t in tasks:
        chain, cur = [t], t
        while granted := [d for d, s in cur.deps if s == "granted"]:
            cur = by_id[granted[0]]
            chain.append(cur)
        floor = TODAY + dt.timedelta(days=chain[-1].prep_days + sum(c.review_days for c in chain))
        assert out[t.id].earliest_grant >= floor


@settings(max_examples=100, deadline=None)
@given(dags())
def test_order_is_topological_and_deterministic(tasks: list[Task]) -> None:
    by_id = {t.id: t for t in tasks}
    order = topological_order(by_id)
    pos = {tid: n for n, tid in enumerate(order)}
    assert all(pos[d] < pos[t.id] for t in tasks for d, _ in t.deps)
    assert order == topological_order(dict(reversed(list(by_id.items()))))
