from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.state.world_state import WorldState


def test_create_entity():
    state = WorldState()

    definitions = DefinitionManager()

    definitions.register(
        Definition(
            key="location",
        )
    )

    manager = EntityManager(
        state,
        definitions,
    )

    entity = manager.create(
        definition_key="location",
        name="Village",
    )

    assert entity.id == "entity_000001"

    assert entity.definition_key == "location"

    assert entity.name == "Village"

    assert manager.exists(entity.id)
