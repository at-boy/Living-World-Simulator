from dataclasses import FrozenInstanceError

import pytest

from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def test_organization_membership_is_graph_derived_and_records_an_event() -> None:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="person"),
            Definition(key="organization", systems=("organization",)),
        )
    )
    guild = engine.entities.create(definition_key="organization", name="Carpenters")
    alice = engine.entities.create(definition_key="person", name="Alice")
    bob = engine.entities.create(definition_key="person", name="Bob")

    engine.relationships.create(
        kind="member_of", source_id=alice.id, target_id=guild.id
    )
    engine.relationships.create(kind="member_of", source_id=bob.id, target_id=guild.id)
    engine.relationships.create(
        kind="member_of", source_id=alice.id, target_id=guild.id
    )

    engine.step()

    assert guild.attributes["member_count"] == 2
    event = next(iter(engine.state.events.values()))
    assert event.kind == "organization_membership_changed"
    assert event.subject_id == guild.id
    assert event.attributes == {"previous": 0, "member_count": 2}
    with pytest.raises(FrozenInstanceError):
        event.kind = "changed"  # type: ignore[misc]


def test_organization_ignores_invalid_membership_patterns() -> None:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="person"),
            Definition(key="organization", systems=("organization",)),
        )
    )
    guild = engine.entities.create(definition_key="organization", name="Carpenters")
    person = engine.entities.create(definition_key="person", name="Alice")

    engine.relationships.create(kind="owns", source_id=person.id, target_id=guild.id)
    engine.relationships.create(
        kind="member_of", source_id=guild.id, target_id=guild.id
    )

    engine.step()

    assert "member_count" not in guild.attributes
    assert not engine.state.events
