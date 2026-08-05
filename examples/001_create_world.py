from living_world.core.definition import Definition
from living_world.core.relationship import Relationship
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.state.world_state import WorldState

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

state.relationships["relationship_000001"] = Relationship(
    id="relationship_000001",
    kind="road",
    source_id=village.id,
    target_id=forest.id,
)

print("Tick:", state.tick)

print("Entities")

for entity in state.entities.values():
    print(entity.id, entity.name)

print()

print("Relationships")

for relationship in state.relationships.values():
    print(
        relationship.kind,
        relationship.source_id,
        "->",
        relationship.target_id,
    )