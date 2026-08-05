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
