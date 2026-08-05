from copy import deepcopy

from living_world.core.relationship import Relationship
from living_world.managers.entity_manager import EntityManager
from living_world.state.world_state import WorldState


class RelationshipManager:
    """Owns the lifecycle of relationships."""

    def __init__(
        self,
        state: WorldState,
        entity_manager: EntityManager,
    ) -> None:
        self._state = state
        self._entities = entity_manager
        self._next_relationship_id = 1

    def create(
        self,
        *,
        kind: str,
        source_id: str,
        target_id: str,
        attributes: dict[str, object] | None = None,
    ) -> Relationship:
        """Create and register a new relationship."""

        if not kind.strip():
            raise ValueError("Relationship kind cannot be empty.")

        if not self._entities.exists(source_id):
            raise ValueError(f"Unknown source entity '{source_id}'.")

        if not self._entities.exists(target_id):
            raise ValueError(f"Unknown target entity '{target_id}'.")

        relationship = Relationship(
            id=self._generate_id(),
            kind=kind,
            source_id=source_id,
            target_id=target_id,
            attributes=deepcopy(attributes or {}),
            created_tick=self._state.tick,
        )

        self.add(relationship)

        return relationship

    def add(self, relationship: Relationship) -> None:
        self._state.relationships[relationship.id] = relationship

    def get(self, relationship_id: str) -> Relationship | None:
        return self._state.relationships.get(relationship_id)

    def exists(self, relationship_id: str) -> bool:
        return relationship_id in self._state.relationships

    def remove(self, relationship_id: str) -> None:
        self._state.relationships.pop(relationship_id, None)

    def _generate_id(self) -> str:
        while True:
            relationship_id = f"relationship_{self._next_relationship_id:06d}"
            self._next_relationship_id += 1

            if relationship_id not in self._state.relationships:
                return relationship_id
