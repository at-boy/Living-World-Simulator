from living_world.core.entity import Entity
from living_world.managers.entity_manager import EntityManager
from living_world.state.world_state import WorldState


def test_add_entity():
    state = WorldState()

    manager = EntityManager(state)

    manager.add(
        Entity(
            id="entity_1",
            definition_key="location",
            name="Village",
        )
    )

    assert "entity_1" in state.entities
