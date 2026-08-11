from __future__ import annotations

import pytest

from living_world.cognition.council import CouncilAgenda, CouncilCall, CouncilService
from living_world.cognition.npc_cognition_client import ActionOption


def _call(*, turn_order_offset: object = 0) -> CouncilCall:
    return CouncilCall(
        "npc_1",
        "council",
        ("npc_2", "npc_3"),
        CouncilAgenda("a route", (ActionOption("wait", "Wait."),)),
        4,
        turn_order_offset=turn_order_offset,  # type: ignore[arg-type]
    )


def test_zero_offset_preserves_caller_first_round_robin() -> None:
    assert CouncilService._schedule((), ("npc_1", "npc_2", "npc_3"), 5, 0) == (
        "npc_1",
        "npc_2",
        "npc_3",
        "npc_1",
        "npc_2",
    )


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (1, ("npc_2", "npc_3", "npc_1", "npc_2")),
        (2, ("npc_3", "npc_1", "npc_2", "npc_3")),
        (4, ("npc_2", "npc_3", "npc_1", "npc_2")),
    ],
)
def test_offset_rotates_confirmed_attendees_deterministically(
    offset: int, expected: tuple[str, ...]
) -> None:
    assert (
        CouncilService._schedule((), ("npc_1", "npc_2", "npc_3"), 4, offset) == expected
    )


def test_automatic_schedule_is_bounded_by_max_rounds() -> None:
    assert CouncilService._schedule((), ("npc_1", "npc_3"), 3, 1) == (
        "npc_3",
        "npc_1",
        "npc_3",
    )
    assert CouncilService._schedule((), ("npc_1", "npc_3"), 0, 1) == ()


def test_explicit_schedule_overrides_offset_without_adding_absent_attendees() -> None:
    assert CouncilService._schedule(("npc_3", "npc_1"), ("npc_1", "npc_3"), 2, 1) == (
        "npc_3",
        "npc_1",
    )

    with pytest.raises(ValueError, match="called speakers must attend the council"):
        CouncilService._schedule(("npc_2",), ("npc_1", "npc_3"), 2, 1)


@pytest.mark.parametrize("value", [True, False, 1.5, "1", None])
def test_turn_order_offset_rejects_non_integer_values(value: object) -> None:
    with pytest.raises(
        TypeError, match="turn_order_offset must be a non-boolean integer"
    ):
        _call(turn_order_offset=value)


def test_turn_order_offset_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="turn_order_offset cannot be negative"):
        _call(turn_order_offset=-1)
