from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def test_housing_allocates_completed_capacity_without_changing_other_edges() -> None:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="person"),
            Definition(key="house", systems=("housing",)),
        )
    )
    dwelling = engine.entities.create(
        definition_key="house",
        name="Longhouse",
        attributes={"is_constructed": True, "housing_capacity": 2},
    )
    residents = tuple(
        engine.entities.create(definition_key="person", name=name)
        for name in ("Ari", "Bea", "Cal")
    )
    for resident in residents:
        engine.relationships.create(
            kind="housed_in", source_id=resident.id, target_id=dwelling.id
        )
    unrelated = engine.relationships.create(
        kind="knows", source_id=residents[0].id, target_id=residents[1].id
    )

    engine.step()

    assert dwelling.attributes["housing_allocated"] == 2
    assert engine.relationships.get(unrelated.id) is unrelated
    event = next(iter(engine.state.events.values()))
    assert event.kind == "housing_allocation_changed"
    assert event.attributes == {"previous": 0, "allocated": 2}


def test_housing_ignores_unconstructed_dwellings() -> None:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (Definition(key="person"), Definition(key="house", systems=("housing",)))
    )
    dwelling = engine.entities.create(
        definition_key="house",
        name="Longhouse",
        attributes={"is_constructed": False, "housing_capacity": 2},
    )
    resident = engine.entities.create(definition_key="person", name="Ari")
    engine.relationships.create(
        kind="housed_in", source_id=resident.id, target_id=dwelling.id
    )

    engine.step()

    assert "housing_allocated" not in dwelling.attributes
    assert not engine.state.events
