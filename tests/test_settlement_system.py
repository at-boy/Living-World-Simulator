from dataclasses import FrozenInstanceError

import pytest

from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def test_settlement_location_and_ownership_are_graph_derived() -> None:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="region"),
            Definition(key="organization"),
            Definition(key="settlement", systems=("settlement",)),
        )
    )
    region = engine.entities.create(definition_key="region", name="Northreach")
    settlement = engine.entities.create(definition_key="settlement", name="Oakstead")
    owner = engine.entities.create(definition_key="organization", name="Oak Guild")

    engine.relationships.create(
        kind="located_in", source_id=settlement.id, target_id=region.id
    )
    engine.relationships.create(
        kind="owns", source_id=owner.id, target_id=settlement.id
    )

    engine.step()

    assert settlement.attributes["is_located"] is True
    assert settlement.attributes["owner_count"] == 1
    events = tuple(engine.state.events.values())
    assert [(event.kind, event.subject_id) for event in events] == [
        ("settlement_location_changed", settlement.id),
        ("settlement_ownership_changed", settlement.id),
    ]
    with pytest.raises(FrozenInstanceError):
        events[0].tick = 4  # type: ignore[misc]


def test_settlement_ignores_incomplete_or_ambiguous_graph_patterns() -> None:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="region"),
            Definition(key="organization"),
            Definition(key="settlement", systems=("settlement",)),
        )
    )
    first_region = engine.entities.create(definition_key="region", name="Northreach")
    second_region = engine.entities.create(definition_key="region", name="Southreach")
    settlement = engine.entities.create(
        definition_key="settlement",
        name="Oakstead",
        attributes={"is_located": True, "owner_count": 7},
    )
    owner = engine.entities.create(definition_key="organization", name="Oak Guild")

    engine.relationships.create(
        kind="owns", source_id=owner.id, target_id=settlement.id
    )
    engine.relationships.create(
        kind="located_in", source_id=settlement.id, target_id=first_region.id
    )
    engine.relationships.create(
        kind="located_in", source_id=settlement.id, target_id=second_region.id
    )

    engine.step()

    assert settlement.attributes == {"is_located": True, "owner_count": 7}
    assert not engine.state.events
