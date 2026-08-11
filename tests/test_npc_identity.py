from collections.abc import Callable
from typing import cast

import pytest

from living_world.npc.identity import NPCIdentity
from living_world.npc.occupation import Occupation
from living_world.npc.schedule import (
    ScheduleEntry,
    schedule_from_attribute,
    schedule_to_attribute,
)


def test_npc_identity_round_trips_without_an_entity_identifier() -> None:
    identity = NPCIdentity(
        name="Mira",
        description="A dependable village woodcutter.",
        capability_descriptions=("Experienced woodcutter",),
    )

    attribute = identity.to_attribute()

    assert attribute == {
        "name": "Mira",
        "description": "A dependable village woodcutter.",
        "capability_descriptions": ["Experienced woodcutter"],
    }
    assert "entity_" not in str(attribute)
    assert NPCIdentity.from_attribute(attribute) == identity


def test_npc_identity_rejects_numeric_capability_data() -> None:
    with pytest.raises(TypeError, match="list of strings"):
        NPCIdentity.from_attribute(
            {
                "name": "Mira",
                "description": "A dependable village woodcutter.",
                "capability_descriptions": [90],
            }
        )


@pytest.mark.parametrize(
    "identity",
    [
        lambda: NPCIdentity(name=cast(str, 1), description="A description."),
        lambda: NPCIdentity(name="Mira", description=cast(str, 1)),
        lambda: NPCIdentity(
            name="Mira",
            description="A description.",
            capability_descriptions=cast(tuple[str, ...], ["Experienced woodcutter"]),
        ),
        lambda: NPCIdentity(
            name="Mira",
            description="A description.",
            capability_descriptions=cast(tuple[str, ...], "Experienced woodcutter"),
        ),
        lambda: NPCIdentity(
            name="Mira",
            description="A description.",
            capability_descriptions=cast(
                tuple[str, ...],
                ("Experienced woodcutter", 90),
            ),
        ),
    ],
)
def test_npc_identity_direct_construction_rejects_invalid_field_types(
    identity: Callable[[], NPCIdentity],
) -> None:
    with pytest.raises(TypeError):
        identity()


@pytest.mark.parametrize(
    "occupation",
    [
        lambda: Occupation(title=cast(str, 1), description="A description."),
        lambda: Occupation(title="Woodcutter", description=cast(str, 1)),
    ],
)
def test_occupation_direct_construction_rejects_invalid_field_types(
    occupation: Callable[[], Occupation],
) -> None:
    with pytest.raises(TypeError):
        occupation()


def test_occupation_round_trips_through_its_attribute_form() -> None:
    occupation = Occupation(
        title="Woodcutter",
        description="Harvests and prepares timber for the settlement.",
    )

    assert Occupation.from_attribute(occupation.to_attribute()) == occupation


def test_schedule_round_trips_in_canonical_order() -> None:
    entries = (
        ScheduleEntry(start_tick=8, end_tick=12, activity="harvesting"),
        ScheduleEntry(start_tick=0, end_tick=8, activity="resting"),
    )

    attribute = schedule_to_attribute(entries)

    assert attribute == [
        {"start_tick": 0, "end_tick": 8, "activity": "resting"},
        {"start_tick": 8, "end_tick": 12, "activity": "harvesting"},
    ]
    assert schedule_from_attribute(attribute) == (
        ScheduleEntry(start_tick=0, end_tick=8, activity="resting"),
        ScheduleEntry(start_tick=8, end_tick=12, activity="harvesting"),
    )


@pytest.mark.parametrize(
    "entries",
    [
        (
            ScheduleEntry(start_tick=0, end_tick=4, activity="resting"),
            ScheduleEntry(start_tick=3, end_tick=8, activity="working"),
        ),
        (
            ScheduleEntry(start_tick=0, end_tick=4, activity="resting"),
            ScheduleEntry(start_tick=0, end_tick=4, activity="working"),
        ),
    ],
)
def test_schedule_rejects_overlapping_entries(
    entries: tuple[ScheduleEntry, ScheduleEntry],
) -> None:
    with pytest.raises(ValueError, match="cannot overlap"):
        schedule_to_attribute(entries)


@pytest.mark.parametrize(
    ("start_tick", "end_tick", "activity"),
    [
        (-1, 1, "resting"),
        (2, 2, "resting"),
        (3, 2, "resting"),
        (0, 1, ""),
    ],
)
def test_schedule_entry_rejects_invalid_intervals_or_activity(
    start_tick: int,
    end_tick: int,
    activity: str,
) -> None:
    with pytest.raises(ValueError):
        ScheduleEntry(
            start_tick=start_tick,
            end_tick=end_tick,
            activity=activity,
        )
