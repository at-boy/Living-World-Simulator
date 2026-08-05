from living_world.core.definition import Definition
from living_world.core.entity import Entity
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.systems.resource_system import ResourceSystem


def create_engine() -> SimulationEngine:
    engine = SimulationEngine()

    engine.definitions.register(
        Definition(
            key="test",
        )
    )

    return engine


def create_entity(
    engine: SimulationEngine,
) -> Entity:
    return engine.entities.create(
        definition_key="test",
        name="Entity",
    )


def test_add_resource() -> None:
    engine = create_engine()

    entity = create_entity(engine)

    resources = ResourceSystem()

    resources.add(
        entity,
        "wood",
        10,
    )

    assert (
        resources.get(
            entity,
            "wood",
        )
        == 10
    )


def test_remove_resource() -> None:
    engine = create_engine()

    entity = create_entity(engine)

    resources = ResourceSystem()

    resources.add(
        entity,
        "wood",
        10,
    )

    resources.remove(
        entity,
        "wood",
        4,
    )

    assert (
        resources.get(
            entity,
            "wood",
        )
        == 6
    )


def test_transfer_resource() -> None:
    engine = create_engine()

    source = create_entity(engine)

    target = create_entity(engine)

    resources = ResourceSystem()

    resources.add(
        source,
        "wood",
        10,
    )

    resources.transfer(
        source,
        target,
        "wood",
        4,
    )

    assert (
        resources.get(
            source,
            "wood",
        )
        == 6
    )

    assert (
        resources.get(
            target,
            "wood",
        )
        == 4
    )


def test_missing_resource_defaults_to_zero() -> None:
    engine = create_engine()

    entity = create_entity(engine)

    resources = ResourceSystem()

    assert (
        resources.get(
            entity,
            "stone",
        )
        == 0
    )


def test_add_creates_resources_dictionary() -> None:
    engine = create_engine()

    entity = create_entity(engine)

    assert "resources" not in entity.attributes

    resources = ResourceSystem()

    resources.add(
        entity,
        "water",
        5,
    )

    assert "resources" in entity.attributes

    assert (
        resources.get(
            entity,
            "water",
        )
        == 5
    )
