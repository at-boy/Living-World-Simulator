import pytest

from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def create_engine() -> SimulationEngine:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="person"))
    return engine


def create_npc(engine: SimulationEngine):
    return engine.entities.create(
        definition_key="person",
        name="Mira",
        attributes={
            "npc_identity": {
                "name": "Mira",
                "description": "A dependable village woodcutter.",
                "capability_descriptions": ["Experienced woodcutter"],
            },
            "occupation": {
                "title": "Woodcutter",
                "description": "Harvests and prepares timber for the settlement.",
            },
            "schedule": [
                {"start_tick": 0, "end_tick": 2, "activity": "resting"},
                {"start_tick": 2, "end_tick": 4, "activity": "harvesting"},
            ],
            "active_activity": None,
            "woodcraft": 90,
        },
    )


def test_schedule_system_selects_the_active_entry_at_the_current_tick() -> None:
    engine = create_engine()
    npc = create_npc(engine)

    engine.step()
    assert npc.attributes["active_activity"] == "resting"

    engine.step()
    assert npc.attributes["active_activity"] == "resting"

    engine.step()
    assert npc.attributes["active_activity"] == "harvesting"


def test_schedule_system_records_only_material_activity_transitions() -> None:
    engine = create_engine()
    npc = create_npc(engine)

    engine.step()
    engine.step()
    engine.step()
    engine.step()
    engine.step()

    events = tuple(engine.state.events.values())

    assert npc.attributes["active_activity"] is None
    assert [event.kind for event in events] == [
        "npc_activity_changed",
        "npc_activity_changed",
        "npc_activity_changed",
    ]
    assert [event.attributes["active_activity"] for event in events] == [
        "resting",
        "harvesting",
        None,
    ]
    assert all(event.subject_id == npc.id for event in events)


def test_schedule_system_rejects_invalid_npc_schedule_before_mutating_state() -> None:
    engine = create_engine()
    npc = create_npc(engine)
    engine.entities.set_attribute(
        entity_id=npc.id,
        key="schedule",
        value=[
            {"start_tick": 0, "end_tick": 3, "activity": "resting"},
            {"start_tick": 2, "end_tick": 4, "activity": "working"},
        ],
    )

    with pytest.raises(ValueError, match="cannot overlap"):
        engine.step()

    assert npc.attributes["active_activity"] is None
    assert not engine.state.events


def test_schedule_system_ignores_entities_without_an_npc_identity() -> None:
    engine = create_engine()
    entity = engine.entities.create(
        definition_key="person",
        name="Not an NPC",
        attributes={"schedule": [{"start_tick": 0, "end_tick": 1, "activity": "idle"}]},
    )

    engine.step()

    assert "active_activity" not in entity.attributes
    assert not engine.state.events
