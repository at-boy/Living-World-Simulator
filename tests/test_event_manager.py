from collections.abc import MutableMapping, MutableSequence
from typing import cast

import pytest

from living_world.core.event import Event
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState


def test_record_event():
    state = WorldState()

    manager = EventManager(state)

    event = manager.record(
        kind="world_created",
    )

    assert event.id == "event_000001"

    assert event.tick == 0

    assert event.kind == "world_created"

    assert manager.get(event.id) == event


def test_event_recursively_freezes_attributes_and_detaches_input() -> None:
    attributes = {
        "journey": {
            "stages": [
                {"name": "departure", "tags": {"travel", "morning"}},
            ]
        }
    }

    event = Event(
        id="event-1",
        tick=1,
        kind="journey_started",
        attributes=attributes,
    )

    attributes["journey"]["stages"][0]["name"] = "changed"

    journey = cast(MutableMapping[str, object], event.attributes["journey"])
    stages = cast(MutableSequence[object], journey["stages"])
    stage = cast(MutableMapping[str, object], stages[0])
    tags = cast(set[str], stage["tags"])

    assert stage["name"] == "departure"
    with pytest.raises(TypeError):
        event_attributes = cast(MutableMapping[str, object], event.attributes)
        event_attributes["new"] = "value"
    with pytest.raises(TypeError):
        journey["new"] = "value"
    with pytest.raises(TypeError):
        stages[0] = "changed"
    with pytest.raises(TypeError):
        stage["name"] = "changed"
    with pytest.raises(AttributeError):
        tags.add("changed")


def test_record_event_recursively_freezes_and_detaches_attributes() -> None:
    state = WorldState()
    manager = EventManager(state)
    attributes = {"details": {"participants": ["ari", "bea"]}}

    event = manager.record(kind="meeting", attributes=attributes)

    attributes["details"]["participants"].append("cal")
    details = cast(MutableMapping[str, object], event.attributes["details"])
    participants = cast(MutableSequence[str], details["participants"])

    assert participants == ("ari", "bea")
    with pytest.raises(TypeError):
        participants[0] = "cal"
