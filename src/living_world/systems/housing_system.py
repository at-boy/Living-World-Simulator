from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class HousingSystem(SimulationSystem):
    """Derive completed housing allocation from ``housed_in`` relationships."""

    system_name = "housing"
    occupancy_kind = "housed_in"

    def __init__(
        self,
        definitions: DefinitionManager,
        entities: EntityManager,
        events: EventManager,
    ) -> None:
        self._definitions = definitions
        self._entities = entities
        self._events = events

    def step(self, state: WorldState) -> None:
        for dwelling in sorted(self._entities.all(), key=lambda item: item.id):
            if not self._participates(dwelling) or not self._is_constructed(dwelling):
                continue

            capacity = self._capacity(dwelling)
            occupants = self._occupants(state, dwelling.id)
            allocated = min(len(occupants), capacity)
            previous = self._allocated(dwelling)
            if previous == allocated:
                continue

            self._entities.set_attribute(
                entity_id=dwelling.id,
                key="housing_allocated",
                value=allocated,
            )
            self._events.record(
                kind="housing_allocation_changed",
                subject_id=dwelling.id,
                attributes={"previous": previous, "allocated": allocated},
            )

    def _participates(self, entity: Entity) -> bool:
        return self.system_name in self._definitions.get(entity.definition_key).systems

    def _is_constructed(self, entity: Entity) -> bool:
        value = entity.attributes.get("is_constructed", False)
        if not isinstance(value, bool):
            raise TypeError("'is_constructed' must be a boolean.")
        return value

    def _capacity(self, dwelling: Entity) -> int:
        value = dwelling.attributes.get("housing_capacity")
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise TypeError("'housing_capacity' must be a non-negative integer.")
        return value

    def _allocated(self, dwelling: Entity) -> int:
        value = dwelling.attributes.get("housing_allocated", 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise TypeError("'housing_allocated' must be a non-negative integer.")
        return value

    def _occupants(self, state: WorldState, dwelling_id: str) -> set[str]:
        return {
            relationship.source_id
            for relationship in state.relationships.values()
            if self._is_valid_occupancy(relationship, dwelling_id)
        }

    def _is_valid_occupancy(
        self,
        relationship: Relationship,
        dwelling_id: str,
    ) -> bool:
        return (
            relationship.kind == self.occupancy_kind
            and relationship.target_id == dwelling_id
            and relationship.source_id != dwelling_id
            and self._entities.exists(relationship.source_id)
        )
