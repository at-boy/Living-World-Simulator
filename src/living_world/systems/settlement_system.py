from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class SettlementSystem(SimulationSystem):
    """Maintain graph-derived location and ownership summaries for settlements."""

    system_name = "settlement"
    location_kind = "located_in"
    ownership_kind = "owns"

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
        """Synchronize valid settlement graph summaries in stable identifier order."""

        for settlement in sorted(self._entities.all(), key=lambda item: item.id):
            if not self._participates(settlement):
                continue

            if not self._has_one_valid_location(state, settlement):
                continue

            self._update_location_status(settlement)
            self._update_owner_count(state, settlement)

    def _participates(self, entity: Entity) -> bool:
        definition = self._definitions.get(entity.definition_key)
        return self.system_name in definition.systems

    def _has_one_valid_location(self, state: WorldState, settlement: Entity) -> bool:
        locations = {
            relationship.target_id
            for relationship in state.relationships.values()
            if self._is_valid_location(relationship, settlement.id)
        }
        return len(locations) == 1

    def _is_valid_location(
        self,
        relationship: Relationship,
        settlement_id: str,
    ) -> bool:
        return (
            relationship.kind == self.location_kind
            and relationship.source_id == settlement_id
            and relationship.target_id != settlement_id
            and self._entities.exists(relationship.target_id)
        )

    def _update_location_status(self, settlement: Entity) -> None:
        previous_status = self._location_status(settlement)

        if previous_status:
            return

        self._entities.set_attribute(
            entity_id=settlement.id,
            key="is_located",
            value=True,
        )
        self._events.record(
            kind="settlement_location_changed",
            subject_id=settlement.id,
            attributes={"previous": previous_status, "is_located": True},
        )

    def _update_owner_count(self, state: WorldState, settlement: Entity) -> None:
        owner_count = self._owner_count(state, settlement)
        previous_count = self._owner_count_attribute(settlement)

        if previous_count == owner_count:
            return

        self._entities.set_attribute(
            entity_id=settlement.id,
            key="owner_count",
            value=owner_count,
        )
        self._events.record(
            kind="settlement_ownership_changed",
            subject_id=settlement.id,
            attributes={"previous": previous_count, "owner_count": owner_count},
        )

    def _owner_count(self, state: WorldState, settlement: Entity) -> int:
        owners = {
            relationship.source_id
            for relationship in state.relationships.values()
            if self._is_valid_ownership(relationship, settlement.id)
        }
        return len(owners)

    def _is_valid_ownership(
        self,
        relationship: Relationship,
        settlement_id: str,
    ) -> bool:
        return (
            relationship.kind == self.ownership_kind
            and relationship.target_id == settlement_id
            and relationship.source_id != settlement_id
            and self._entities.exists(relationship.source_id)
        )

    def _location_status(self, settlement: Entity) -> bool:
        value = settlement.attributes.get("is_located", False)

        if not isinstance(value, bool):
            raise TypeError("'is_located' must be a boolean.")

        return value

    def _owner_count_attribute(self, settlement: Entity) -> int:
        value = settlement.attributes.get("owner_count", 0)

        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise TypeError("'owner_count' must be a non-negative integer.")

        return value
