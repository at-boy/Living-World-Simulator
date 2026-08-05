from living_world.core.resource_definition import ResourceDefinition
from living_world.managers.resource_definition_manager import (
    ResourceDefinitionManager,
)


def test_register_and_get_definition():
    manager = ResourceDefinitionManager()

    definition = ResourceDefinition(
        key="water",
    )

    manager.register(definition)

    assert manager.get("water") is definition


def test_exists_returns_true_for_registered_definition():
    manager = ResourceDefinitionManager()

    manager.register(
        ResourceDefinition(
            key="wood",
        )
    )

    assert manager.exists("wood")


def test_exists_returns_false_for_unknown_definition():
    manager = ResourceDefinitionManager()

    assert not manager.exists("gold")
