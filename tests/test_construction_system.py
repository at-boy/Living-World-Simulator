from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def test_construction_completes_after_bounded_progress_and_payment() -> None:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="region"),
            Definition(key="building", systems=("construction",)),
        )
    )
    region = engine.entities.create(definition_key="region", name="Northreach")
    building = engine.entities.create(
        definition_key="building",
        name="Workshop",
        attributes={
            "progress": 90,
            "progress_rate": 20,
            "progress_max": 100,
            "construction_requirements": {"wood": 4},
            "resources": {"wood": 4},
        },
    )
    road = engine.relationships.create(
        kind="road", source_id=building.id, target_id=region.id
    )

    engine.step()

    assert building.attributes["progress"] == 100
    assert building.attributes["is_constructed"] is True
    assert building.attributes["resources"] == {"wood": 0}
    assert engine.relationships.get(road.id) is road
    event = next(iter(engine.state.events.values()))
    assert event.kind == "construction_completed"
    assert event.subject_id == building.id


def test_construction_waits_for_required_resources() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="building", systems=("construction",)))
    building = engine.entities.create(
        definition_key="building",
        name="Workshop",
        attributes={
            "progress": 100,
            "progress_rate": 5,
            "progress_max": 100,
            "construction_requirements": {"wood": 4},
            "resources": {"wood": 3},
        },
    )

    engine.step()

    assert building.attributes["progress"] == 100
    assert "is_constructed" not in building.attributes
    assert building.attributes["resources"] == {"wood": 3}
    assert not engine.state.events
