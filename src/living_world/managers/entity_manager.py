from copy import deepcopy

from living_world.core.entity import Entity
from living_world.managers.definition_manager import DefinitionManager
from living_world.state.world_state import WorldState


class EntityManager:
    """Owns the lifecycle of entities."""

    def __init__(
        self,
        state: WorldState,
        definition_manager: DefinitionManager,
    ) -> None:
        self._state = state
        self._definitions = definition_manager
        self._next_entity_id = 1

    def create(
        self,
        *,
        definition_key: str,
        name: str,
        attributes: dict[str, object] | None = None,
    ) -> Entity:
        """
        Create and register a new entity.
        """

        if not self._definitions.exists(definition_key):
            raise ValueError(f"Unknown definition '{definition_key}'.")

        if not name.strip():
            raise ValueError("Entity name cannot be empty.")

        definition = self._definitions.get(definition_key)

        entity_id = self._generate_id()

        initial_attributes = deepcopy(definition.initial_attributes)

        if attributes:
            initial_attributes.update(attributes)

        entity = Entity(
            id=entity_id,
            definition_key=definition_key,
            name=name,
            attributes=initial_attributes,
            created_tick=self._state.tick,
        )

        self._state.entities[entity.id] = entity

        return entity

    def get(self, entity_id: str) -> Entity | None:
        return self._state.entities.get(entity_id)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._state.entities

    def remove(self, entity_id: str) -> None:
        self._state.entities.pop(entity_id, None)

    def set_attribute(
        self,
        *,
        entity_id: str,
        key: str,
        value: object,
    ) -> None:
        """Set a runtime entity attribute through the entity lifecycle boundary."""

        entity = self.get(entity_id)

        if entity is None:
            raise ValueError(f"Unknown entity '{entity_id}'.")

        if not key.strip():
            raise ValueError("Entity attribute key cannot be empty.")

        entity.attributes[key] = deepcopy(value)

    def _generate_id(self) -> str:
        while True:
            entity_id = f"entity_{self._next_entity_id:06d}"
            self._next_entity_id += 1

            if entity_id not in self._state.entities:
                return entity_id

    def all(self) -> tuple[Entity, ...]:
        return tuple(self._state.entities.values())
