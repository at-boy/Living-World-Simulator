from living_world.core.entity import Entity
from living_world.state.world_state import WorldState


class EntityManager:
    """Owns the lifecycle of entities."""

    def __init__(self, state: WorldState):
        self._state = state

    def add(self, entity: Entity) -> None:
        self._state.entities[entity.id] = entity

    def get(self, entity_id: str) -> Entity | None:
        return self._state.entities.get(entity_id)

    def remove(self, entity_id: str) -> None:
        self._state.entities.pop(entity_id, None)
