"""ITU filing-maturity state machine (ADR-0009).

The ITU Space Network List (SNL) tracks a filing through a lifecycle. The upstream
ITU-Compliance-Assessment-Monitor encodes maturity implicitly through filing-type
codes (A < P < C < N < U) plus a scatter of date columns. We re-express it here as
an explicit, typed state machine: the four states ADR-0009 calls for, plus the legal
transitions between them. Pure logic, no I/O — this is the lowest-risk, highest-certainty
piece of the L3 port and the canonical maturity vocabulary for the rest of the system.
"""

from __future__ import annotations

from enum import StrEnum


class FilingMaturity(StrEnum):
    """Lifecycle state of an ITU space-network filing.

    - EARLY_STAGE: advance publication information filed; not yet coordination-complete.
    - LATE_STAGE: coordination/notification filed; eligible to be brought into use.
    - BROUGHT_INTO_USE: the network has been brought into use within the regulatory window.
    - SUSPENDED: a brought-into-use network whose operation is currently suspended.
    """

    EARLY_STAGE = "early_stage"
    LATE_STAGE = "late_stage"
    BROUGHT_INTO_USE = "brought_into_use"
    SUSPENDED = "suspended"


class MaturityEvent(StrEnum):
    """Events that advance (or regress) a filing's maturity."""

    ADVANCE_TO_LATE_STAGE = "advance_to_late_stage"
    BRING_INTO_USE = "bring_into_use"
    SUSPEND = "suspend"
    RESUME = "resume"


# The only legal (state, event) -> state transitions. Anything not listed is illegal:
# you cannot bring an early-stage filing into use without first reaching late stage,
# you cannot suspend a filing that was never brought into use, etc.
_TRANSITIONS: dict[tuple[FilingMaturity, MaturityEvent], FilingMaturity] = {
    (FilingMaturity.EARLY_STAGE, MaturityEvent.ADVANCE_TO_LATE_STAGE): FilingMaturity.LATE_STAGE,
    (FilingMaturity.LATE_STAGE, MaturityEvent.BRING_INTO_USE): FilingMaturity.BROUGHT_INTO_USE,
    (FilingMaturity.BROUGHT_INTO_USE, MaturityEvent.SUSPEND): FilingMaturity.SUSPENDED,
    (FilingMaturity.SUSPENDED, MaturityEvent.RESUME): FilingMaturity.BROUGHT_INTO_USE,
}


class IllegalTransitionError(ValueError):
    """Raised when an event is applied to a state that does not permit it."""


def transition(current: FilingMaturity, event: MaturityEvent) -> FilingMaturity:
    """Apply ``event`` to ``current`` and return the new maturity state.

    Raises :class:`IllegalTransitionError` if the transition is not permitted.
    """
    try:
        return _TRANSITIONS[(current, event)]
    except KeyError:
        raise IllegalTransitionError(
            f"cannot apply {event.value!r} to a filing in state {current.value!r}"
        ) from None


def is_protected(maturity: FilingMaturity) -> bool:
    """Whether a filing in this state confers protection from harmful interference.

    Only a brought-into-use (and not currently suspended) network is protected — the
    compliance check (compliance.py) keys off this.
    """
    return maturity is FilingMaturity.BROUGHT_INTO_USE


# Postgres ENUM equivalent (ADR-0009: "typed Python enums and Postgres ENUM equivalents").
# Applied to the L2 KG / evidence schema when filings are persisted (Phase 3); kept here
# next to the source-of-truth enum so the two never drift.
POSTGRES_ENUM_DDL = (
    "CREATE TYPE filing_maturity AS ENUM "
    "('early_stage', 'late_stage', 'brought_into_use', 'suspended');"
)
