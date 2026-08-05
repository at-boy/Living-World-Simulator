from living_world.core.definition import Definition
from living_world.core.resource_definition import ResourceDefinition
from living_world.simulation.simulation_engine import SimulationEngine


def create_engine() -> SimulationEngine:
    engine = SimulationEngine()

    engine.resource_definitions.register(
        ResourceDefinition(
            key="wood",
        )
    )

    engine.resource_definitions.register(
        ResourceDefinition(
            key="water",
        )
    )

    engine.definitions.register(
        Definition(
            key="tree",
        )
    )

    return engine


def test_entity_can_store_resources():
    engine = create_engine()

    tree = engine.entities.create(
        definition_key="tree",
        name="Oak",
        attributes={
            "resources": {
                "wood": 120,
                "water": 35,
            }
        },
    )

    resources = tree.attributes["resources"]

    assert isinstance(resources, dict)

    assert resources["wood"] == 120
    assert resources["water"] == 35


def test_resource_dictionary_is_independent_between_entities():
    engine = create_engine()

    tree1 = engine.entities.create(
        definition_key="tree",
        name="Oak",
        attributes={
            "resources": {
                "wood": 120,
            }
        },
    )

    tree2 = engine.entities.create(
        definition_key="tree",
        name="Pine",
        attributes={
            "resources": {
                "wood": 80,
            }
        },
    )

    resources1 = tree1.attributes["resources"]
    resources2 = tree2.attributes["resources"]

    assert isinstance(resources1, dict)
    assert isinstance(resources2, dict)

    assert resources1["wood"] == 120
    assert resources2["wood"] == 80
