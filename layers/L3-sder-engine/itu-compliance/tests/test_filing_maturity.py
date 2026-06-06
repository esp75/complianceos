import pytest

from itu_compliance.filing_maturity import (
    FilingMaturity,
    IllegalTransitionError,
    MaturityEvent,
    is_protected,
    transition,
)


def test_full_lifecycle_legal_transitions() -> None:
    state = FilingMaturity.EARLY_STAGE
    state = transition(state, MaturityEvent.ADVANCE_TO_LATE_STAGE)
    assert state is FilingMaturity.LATE_STAGE
    state = transition(state, MaturityEvent.BRING_INTO_USE)
    assert state is FilingMaturity.BROUGHT_INTO_USE
    state = transition(state, MaturityEvent.SUSPEND)
    assert state is FilingMaturity.SUSPENDED
    state = transition(state, MaturityEvent.RESUME)
    assert state is FilingMaturity.BROUGHT_INTO_USE


@pytest.mark.parametrize(
    ("state", "event"),
    [
        (FilingMaturity.EARLY_STAGE, MaturityEvent.BRING_INTO_USE),  # cannot skip late stage
        (FilingMaturity.EARLY_STAGE, MaturityEvent.SUSPEND),
        (FilingMaturity.EARLY_STAGE, MaturityEvent.RESUME),
        (FilingMaturity.LATE_STAGE, MaturityEvent.ADVANCE_TO_LATE_STAGE),  # already late
        (FilingMaturity.LATE_STAGE, MaturityEvent.SUSPEND),
        (FilingMaturity.BROUGHT_INTO_USE, MaturityEvent.BRING_INTO_USE),
        (FilingMaturity.BROUGHT_INTO_USE, MaturityEvent.RESUME),
        (FilingMaturity.SUSPENDED, MaturityEvent.SUSPEND),
        (FilingMaturity.SUSPENDED, MaturityEvent.BRING_INTO_USE),
    ],
)
def test_illegal_transitions_raise(state: FilingMaturity, event: MaturityEvent) -> None:
    with pytest.raises(IllegalTransitionError):
        transition(state, event)


def test_only_brought_into_use_is_protected() -> None:
    assert is_protected(FilingMaturity.BROUGHT_INTO_USE) is True
    assert is_protected(FilingMaturity.EARLY_STAGE) is False
    assert is_protected(FilingMaturity.LATE_STAGE) is False
    assert is_protected(FilingMaturity.SUSPENDED) is False
