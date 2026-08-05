from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.relationship_manager import RelationshipManager
from living_world.state.world_state import WorldState


def test_create_relationship():
    state = WorldState()

    definitions = DefinitionManager()

    definitions.register(
        Definition(
            key="location",
        )
    )

    entities = EntityManager(
        state,
        definitions,
    )

    village = entities.create(
        definition_key="location",
        name="Village",
    )

    forest = entities.create(
        definition_key="location",
        name="Forest",
    )

    relationships = RelationshipManager(
        state,
        entities,
    )

    relationship = relationships.create(
        kind="road",
        source_id=village.id,
        target_id=forest.id,
    )

    assert relationship.id == "relationship_000001"

    assert relationship.kind == "road"

    assert relationship.source_id == village.id

    assert relationship.target_id == forest.id

    assert relationships.exists(relationship.id)
