from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.managers.entity_manager import EntityManager
from living_world.state.world_state import WorldState

state = WorldState()

entities = EntityManager(state)

entities.add(
    Entity(
        id="entity_000001",
        definition_key="location",
        name="Village",
    )
)

entities.add(
    Entity(
        id="entity_000002",
        definition_key="location",
        name="Forest",
    )
)

state.relationships["relationship_000001"] = Relationship(
    id="relationship_000001",
    kind="road",
    source_id="entity_000001",
    target_id="entity_000002",
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
