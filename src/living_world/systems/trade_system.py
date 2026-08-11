from living_world.core.relationship import Relationship
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.resource_system import ResourceSystem
from living_world.systems.simulation_system import SimulationSystem


class TradeSystem(SimulationSystem):
    """Execute valid trade relationships that are connected by a road."""

    trade_kind = "trade"
    road_kind = "road"

    def __init__(
        self,
        entities: EntityManager,
        events: EventManager,
        resources: ResourceSystem,
    ) -> None:
        self._entities = entities
        self._events = events
        self._resources = resources

    def step(self, state: WorldState) -> None:
        for relationship in sorted(
            state.relationships.values(), key=lambda item: item.id
        ):
            if not self._is_valid_trade(state, relationship):
                continue

            resource, amount = self._trade_terms(relationship)
            source = self._entities.get(relationship.source_id)
            target = self._entities.get(relationship.target_id)
            if source is None or target is None:
                continue
            if self._resources.get(source, resource) < amount:
                continue

            self._resources.transfer(source, target, resource, amount)
            self._events.record(
                kind="trade_completed",
                subject_id=relationship.id,
                attributes={
                    "source_id": source.id,
                    "target_id": target.id,
                    "resource": resource,
                    "amount": amount,
                },
            )

    def _is_valid_trade(self, state: WorldState, relationship: Relationship) -> bool:
        return (
            relationship.kind == self.trade_kind
            and relationship.source_id != relationship.target_id
            and self._entities.exists(relationship.source_id)
            and self._entities.exists(relationship.target_id)
            and self._has_road(state, relationship.source_id, relationship.target_id)
        )

    def _has_road(self, state: WorldState, source_id: str, target_id: str) -> bool:
        endpoints = {source_id, target_id}
        return any(
            relationship.kind == self.road_kind
            and {relationship.source_id, relationship.target_id} == endpoints
            for relationship in state.relationships.values()
        )

    def _trade_terms(self, relationship: Relationship) -> tuple[str, int]:
        resource = relationship.attributes.get("resource")
        amount = relationship.attributes.get("amount")
        if not isinstance(resource, str) or not resource.strip():
            raise TypeError("Trade relationship 'resource' must be a non-empty string.")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise TypeError(
                "Trade relationship 'amount' must be a non-negative integer."
            )
        return resource, amount
