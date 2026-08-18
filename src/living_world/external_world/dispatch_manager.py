from __future__ import annotations

from dataclasses import replace

from living_world.core.entity import Entity
from living_world.external_world.dispatch import (
    DispatchDirection,
    DispatchStatus,
    ExternalDispatch,
    NPCDispatchPerception,
)
from living_world.external_world.manager import ExternalWorldReferenceManager
from living_world.external_world.model import ContactState
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.resource_system import ResourceSystem


class ExternalDispatchManager:
    """Own durable off-map dispatch lifecycle and local resource reservations."""

    def __init__(
        self,
        state: WorldState,
        entities: EntityManager,
        references: ExternalWorldReferenceManager,
        resources: ResourceSystem,
        events: EventManager,
    ) -> None:
        self._state = state
        self._entities = entities
        self._references = references
        self._resources = resources
        self._events = events
        self._next_id = 1

    def create(
        self,
        *,
        source_entity_id: str,
        reference_id: str,
        direction: DispatchDirection,
        good: str,
        quantity: int,
    ) -> ExternalDispatch:
        self.validate_create(
            source_entity_id=source_entity_id,
            reference_id=reference_id,
            direction=direction,
            good=good,
            quantity=quantity,
        )
        source = self._entities.get(source_entity_id)
        assert source is not None
        reference = self._references.get(reference_id)
        assert reference is not None

        reserved_good = quantity if direction is DispatchDirection.OUTBOUND else 0
        reserved_cost = quantity * reference.cost_per_unit
        dispatch = ExternalDispatch(
            id=self._candidate_id(),
            source_entity_id=source_entity_id,
            reference_id=reference_id,
            direction=direction,
            good=good,
            quantity=quantity,
            reserved_good=reserved_good,
            reserved_cost=reserved_cost,
            status=DispatchStatus.PENDING,
            created_tick=self._state.tick,
        )
        resources_before = dict(source.attributes.get("resources", {}))
        event_ids = frozenset(self._state.events)
        try:
            self._resources.remove(source, good, reserved_good)
            self._resources.remove(source, "coin", reserved_cost)
            self._events.record(
                kind="external_dispatch_created",
                subject_id=dispatch.id,
                attributes=_snapshot(dispatch),
            )
            self._state.external_dispatches[dispatch.id] = dispatch
            self._next_id += 1
        except Exception:
            source.attributes["resources"] = resources_before
            self._state.external_dispatches.pop(dispatch.id, None)
            self._remove_new_events(event_ids)
            raise
        return dispatch

    def validate_create(
        self,
        *,
        source_entity_id: str,
        reference_id: str,
        direction: DispatchDirection,
        good: str,
        quantity: int,
    ) -> None:
        """Validate a proposed dispatch without changing world state."""

        source = self._entities.get(source_entity_id)
        if source is None or source.destroyed_tick is not None:
            raise ValueError("Dispatch source must be a live entity.")
        reference = self._references.get(reference_id)
        if reference is None:
            raise ValueError("Dispatch reference is unknown.")
        if reference.contact_state is not ContactState.CONTACTABLE:
            raise ValueError("Dispatch reference is not contactable.")
        if not isinstance(direction, DispatchDirection):
            raise TypeError("direction must be a DispatchDirection.")
        if not isinstance(good, str):
            raise TypeError("good must be a string.")
        if not good.strip():
            raise ValueError("good cannot be empty.")
        if good == "coin":
            raise ValueError("coin cannot be used as a dispatch good.")
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            raise TypeError("quantity must be an integer.")
        if quantity < 1:
            raise ValueError("quantity must be positive.")
        if quantity > reference.capacity:
            raise ValueError("quantity exceeds external reference capacity.")
        allowed = (
            reference.allowed_imports
            if direction is DispatchDirection.OUTBOUND
            else reference.allowed_exports
        )
        if good not in allowed:
            raise ValueError("good is not allowed for this dispatch direction.")
        reserved_good = quantity if direction is DispatchDirection.OUTBOUND else 0
        reserved_cost = quantity * reference.cost_per_unit
        resources = source.attributes.get("resources", {})
        if not isinstance(resources, dict):
            raise TypeError("'resources' must be a dictionary.")
        good_quantity = resources.get(good, 0)
        coin_quantity = resources.get("coin", 0)
        for label, value in ((good, good_quantity), ("coin", coin_quantity)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"Resource '{label}' must be an integer.")
            if value < 0:
                raise ValueError(f"Resource '{label}' cannot be negative.")
        if good_quantity < reserved_good:
            raise ValueError("source has insufficient goods for dispatch.")
        if coin_quantity < reserved_cost:
            raise ValueError("source has insufficient coin for dispatch.")

    def depart(self, dispatch_id: str) -> ExternalDispatch:
        dispatch = self._required(dispatch_id)
        if dispatch.status is not DispatchStatus.PENDING:
            raise ValueError("Only pending dispatches can depart.")
        self._required_source(dispatch.source_entity_id)
        return self._transition(
            dispatch,
            replace(
                dispatch,
                status=DispatchStatus.IN_TRANSIT,
                departure_tick=self._state.tick,
            ),
            "external_dispatch_departed",
        )

    def reject(self, dispatch_id: str) -> ExternalDispatch:
        dispatch = self._required(dispatch_id)
        if dispatch.status is not DispatchStatus.PENDING:
            raise ValueError("Only pending dispatches can be rejected.")
        source = self._required_source(dispatch.source_entity_id)
        resources_before = dict(source.attributes.get("resources", {}))
        updated = replace(
            dispatch,
            status=DispatchStatus.REJECTED,
            resolution_tick=self._state.tick,
        )
        try:
            self._resources.add(source, dispatch.good, dispatch.reserved_good)
            self._resources.add(source, "coin", dispatch.reserved_cost)
            return self._transition(dispatch, updated, "external_dispatch_rejected")
        except Exception:
            source.attributes["resources"] = resources_before
            raise

    def resolve(self, dispatch_id: str, *, arrived: bool) -> ExternalDispatch:
        dispatch = self._required(dispatch_id)
        if dispatch.status is not DispatchStatus.IN_TRANSIT:
            raise ValueError("Only in-transit dispatches can resolve.")
        if not isinstance(arrived, bool):
            raise TypeError("arrived must be a bool.")
        source = self._required_source(dispatch.source_entity_id)
        resources_before = dict(source.attributes.get("resources", {}))
        status = DispatchStatus.ARRIVED if arrived else DispatchStatus.LOST
        updated = replace(dispatch, status=status, resolution_tick=self._state.tick)
        try:
            if arrived and dispatch.direction is DispatchDirection.INBOUND:
                self._resources.add(source, dispatch.good, dispatch.quantity)
            return self._transition(
                dispatch, updated, f"external_dispatch_{status.value}"
            )
        except Exception:
            source.attributes["resources"] = resources_before
            raise

    def get(self, dispatch_id: str) -> ExternalDispatch | None:
        return self._state.external_dispatches.get(dispatch_id)

    def all(self) -> tuple[ExternalDispatch, ...]:
        return tuple(
            self._state.external_dispatches[key]
            for key in sorted(self._state.external_dispatches)
        )

    def perception(self, dispatch_id: str) -> NPCDispatchPerception:
        dispatch = self._required(dispatch_id)
        reference = self._references.get(dispatch.reference_id)
        if reference is None:
            raise ValueError("Dispatch reference is unknown.")
        descriptions = {
            DispatchStatus.PENDING: "A planned exchange is awaiting departure.",
            DispatchStatus.IN_TRANSIT: "The exchange is currently underway.",
            DispatchStatus.ARRIVED: "The exchange arrived successfully.",
            DispatchStatus.REJECTED: "The exchange was cancelled before departure.",
            DispatchStatus.LOST: "The exchange did not arrive.",
        }
        return NPCDispatchPerception(reference.name, descriptions[dispatch.status])

    def _transition(
        self,
        previous: ExternalDispatch,
        current: ExternalDispatch,
        event_kind: str,
    ) -> ExternalDispatch:
        event_ids = frozenset(self._state.events)
        try:
            self._events.record(
                kind=event_kind,
                subject_id=current.id,
                attributes={
                    "previous_status": previous.status.value,
                    "current_status": current.status.value,
                },
            )
            self._state.external_dispatches[current.id] = current
        except Exception:
            self._state.external_dispatches[previous.id] = previous
            self._remove_new_events(event_ids)
            raise
        return current

    def _required(self, dispatch_id: str) -> ExternalDispatch:
        dispatch = self.get(dispatch_id)
        if dispatch is None:
            raise ValueError("Dispatch is unknown.")
        return dispatch

    def _required_source(self, entity_id: str) -> Entity:
        source = self._entities.get(entity_id)
        if source is None or source.destroyed_tick is not None:
            raise ValueError("Dispatch source must remain a live entity.")
        return source

    def _candidate_id(self) -> str:
        while True:
            identifier = f"external_dispatch_{self._next_id:06d}"
            if identifier not in self._state.external_dispatches:
                return identifier
            self._next_id += 1

    def _remove_new_events(self, before: frozenset[str]) -> None:
        for event_id in set(self._state.events) - before:
            self._state.events.pop(event_id, None)


def _snapshot(dispatch: ExternalDispatch) -> dict[str, object]:
    return {
        "reference_id": dispatch.reference_id,
        "source_entity_id": dispatch.source_entity_id,
        "direction": dispatch.direction.value,
        "good": dispatch.good,
        "quantity": dispatch.quantity,
        "status": dispatch.status.value,
    }
