"""Application tracking: the life of each licence application after the roadmap (ADR-0018).

A small explicit state machine (no status can be set from an arbitrary other status), plus the
dates that follow from what actually happened: once an application is submitted or granted, its
obligations are re-dated from the real dates instead of the plan, and the next action is derived
from where the application stands.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.planner.plan import DatedObligation, RoadmapItem


class AppStatus(StrEnum):
    NOT_STARTED = "not_started"
    PREPARING = "preparing"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INFO_REQUESTED = "info_requested"
    GRANTED = "granted"
    REFUSED = "refused"
    WITHDRAWN = "withdrawn"


_ACTIVE_REVIEW = {AppStatus.SUBMITTED, AppStatus.UNDER_REVIEW, AppStatus.INFO_REQUESTED}

TRANSITIONS: dict[AppStatus, frozenset[AppStatus]] = {
    AppStatus.NOT_STARTED: frozenset({AppStatus.PREPARING, AppStatus.SUBMITTED, AppStatus.WITHDRAWN}),
    AppStatus.PREPARING: frozenset({AppStatus.SUBMITTED, AppStatus.WITHDRAWN}),
    AppStatus.SUBMITTED: frozenset({AppStatus.UNDER_REVIEW, AppStatus.INFO_REQUESTED,
                                    AppStatus.GRANTED, AppStatus.REFUSED, AppStatus.WITHDRAWN}),
    AppStatus.UNDER_REVIEW: frozenset({AppStatus.INFO_REQUESTED, AppStatus.GRANTED,
                                       AppStatus.REFUSED, AppStatus.WITHDRAWN}),
    AppStatus.INFO_REQUESTED: frozenset({AppStatus.UNDER_REVIEW, AppStatus.GRANTED,
                                         AppStatus.REFUSED, AppStatus.WITHDRAWN}),
    AppStatus.GRANTED: frozenset(),
    AppStatus.REFUSED: frozenset({AppStatus.PREPARING}),
    AppStatus.WITHDRAWN: frozenset({AppStatus.PREPARING}),
}


class TransitionError(ValueError):
    """Raised for a status change the state machine does not allow."""


def check_transition(current: AppStatus, new: AppStatus) -> None:
    if new == current:
        return
    if new not in TRANSITIONS[current]:
        allowed = ", ".join(sorted(s.value for s in TRANSITIONS[current])) or "none (final)"
        raise TransitionError(f"cannot move from {current.value} to {new.value}; allowed: {allowed}")


class Application(BaseModel):
    id: str
    mission_id: str
    license_id: str
    status: AppStatus = AppStatus.NOT_STARTED
    submitted_on: dt.date | None = None
    granted_on: dt.date | None = None
    reference: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=5000)
    created_at: dt.datetime
    updated_at: dt.datetime


class ApplicationEvent(BaseModel):
    id: int
    application_id: str
    at: dt.datetime
    kind: Literal["created", "status", "update", "contact"]
    from_status: AppStatus | None = None
    to_status: AppStatus | None = None
    note: str = ""


class ContactIn(BaseModel):
    on_date: dt.date
    channel: Literal["email", "phone", "meeting", "letter", "web_form", "portal", "other"]
    counterpart: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=5000)
    next_step: str = Field(default="", max_length=1000)
    next_step_due: dt.date | None = None


class Contact(ContactIn):
    id: int
    application_id: str
    created_at: dt.datetime


class NextAction(BaseModel):
    title: str
    due: dt.date | None
    overdue: bool


def apply_update(app: Application, *, status: AppStatus | None, submitted_on: dt.date | None,
                 granted_on: dt.date | None, today: dt.date) -> Application:
    """Validate and apply a status/date change. Moving to submitted or granted records today's
    date when no date is given; dates must be in order and not in the future."""
    new_status = status or app.status
    check_transition(app.status, new_status)
    sub = submitted_on or app.submitted_on
    grant = granted_on or app.granted_on
    if new_status in _ACTIVE_REVIEW | {AppStatus.GRANTED, AppStatus.REFUSED} and sub is None:
        sub = today
    if new_status == AppStatus.GRANTED and grant is None:
        grant = today
    for label, d in (("submitted_on", sub), ("granted_on", grant)):
        if d and d > today:
            raise TransitionError(f"{label} cannot be in the future")
    if sub and grant and grant < sub:
        raise TransitionError("granted_on cannot be before submitted_on")
    return app.model_copy(update={"status": new_status, "submitted_on": sub, "granted_on": grant})


def redate_obligations(item: RoadmapItem, app: Application | None) -> list[DatedObligation]:
    """Obligations of a roadmap item, re-anchored on the application's real dates when known."""
    if app is None:
        return list(item.obligations)
    actual = {"submitted": app.submitted_on, "granted": app.granted_on}
    planned = {"submitted": item.earliest_submit, "granted": item.earliest_grant}
    out = []
    for o in item.obligations:
        real = actual.get(o.anchor)
        if real is not None:
            out.append(o.model_copy(update={"due": o.due + (real - planned[o.anchor])}))
        else:
            out.append(o)
    return out


def next_action(item: RoadmapItem, app: Application | None, today: dt.date,
                contact_due: dt.date | None = None) -> NextAction:
    status = app.status if app else AppStatus.NOT_STARTED
    if status in (AppStatus.NOT_STARTED, AppStatus.PREPARING):
        if status == AppStatus.NOT_STARTED and item.start_by > today:
            return NextAction(title="Start preparing", due=item.start_by, overdue=False)
        return NextAction(title="Submit the application", due=item.submit_by,
                          overdue=item.submit_by < today)
    if status == AppStatus.INFO_REQUESTED:
        return NextAction(title="Answer the authority's request", due=contact_due,
                          overdue=bool(contact_due and contact_due < today))
    if status in (AppStatus.SUBMITTED, AppStatus.UNDER_REVIEW):
        expected = (app.submitted_on if app and app.submitted_on else today) + dt.timedelta(
            weeks=item.review.typical_weeks)
        return NextAction(title="Decision expected (typical review time)", due=expected, overdue=False)
    if status == AppStatus.GRANTED:
        upcoming = sorted((o for o in redate_obligations(item, app) if o.due >= today),
                          key=lambda o: o.due)
        if upcoming:
            o = upcoming[0]
            return NextAction(title=o.name, due=o.due, overdue=False)
        return NextAction(title="No upcoming obligations", due=None, overdue=False)
    return NextAction(title="Decide whether to reapply", due=None, overdue=False)
