from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.relationship_manager import RelationshipManager
from living_world.state.world_state import WorldState
from living_world.managers.event_manager import EventManager

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

relationships = RelationshipManager(
    state,
    entities,
)

events = EventManager(state)

village = entities.create(
    definition_key="location",
    name="Village",
)

events.record(
    kind="location_created",
    subject_id=village.id,
)

forest = entities.create(
    definition_key="location",
    name="Forest",
)

events.record(
    kind="location_created",
    subject_id=forest.id,
)

road = relationships.create(
    kind="road",
    source_id=village.id,
    target_id=forest.id,
)

events.record(
    kind="road_created",
    subject_id=road.id,
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

print()

print("Events")

for event in state.events.values():
    print(
        event.tick,
        event.kind,
        event.subject_id,
    )