from __future__ import annotations

from collections.abc import Mapping

from living_world.managers.event_manager import EventManager
from living_world.spatial.model import (
    Bounds,
    BoundsKind,
    OverlapPolicy,
    Placement,
    Point,
)
from living_world.state.world_state import WorldState


class SpatialManager:
    """Own placement lifecycle, invariants, ordering, and spatial events."""

    def __init__(self, state: WorldState, events: EventManager) -> None:
        self._state = state
        self._events = events

    def place(
        self,
        *,
        entity_id: str,
        geometry: Point | Bounds,
        containing_entity_id: str | None = None,
        bounds_kind: BoundsKind | None = None,
        overlap_policy: OverlapPolicy = OverlapPolicy.REJECT,
    ) -> Placement:
        if entity_id in self._state.placements:
            raise ValueError(f"Entity '{entity_id}' already has placement state.")
        placement = Placement(
            entity_id,
            geometry,
            containing_entity_id,
            bounds_kind,
            overlap_policy,
        )
        self._validate(placement)
        self._commit("spatial_placement_created", None, placement)
        return placement

    def replace(
        self,
        *,
        entity_id: str,
        geometry: Point | Bounds,
        containing_entity_id: str | None = None,
        bounds_kind: BoundsKind | None = None,
        overlap_policy: OverlapPolicy = OverlapPolicy.REJECT,
    ) -> Placement:
        previous = self._required(entity_id)
        placement = Placement(
            entity_id,
            geometry,
            containing_entity_id,
            bounds_kind,
            overlap_policy,
        )
        self._validate(placement, replacing=entity_id)
        self._validate_children(placement)
        self._commit("spatial_placement_replaced", previous, placement)
        return placement

    def unplace(self, entity_id: str) -> Placement:
        previous = self._required(entity_id)
        if previous.geometry is None:
            raise ValueError(f"Entity '{entity_id}' is already unplaced.")
        self._reject_children(entity_id)
        current = Placement(entity_id, None)
        self._commit("spatial_placement_unplaced", previous, current)
        return current

    def remove(self, entity_id: str) -> Placement:
        previous = self._required(entity_id)
        self._reject_children(entity_id)
        self._commit("spatial_placement_removed", previous, None)
        return previous

    def validate_entity_removal(self, entity_id: str) -> None:
        if entity_id in self._state.placements:
            raise ValueError(
                f"Entity '{entity_id}' cannot be removed while it has placement state."
            )
        self._reject_children(entity_id)

    def get(self, entity_id: str) -> Placement | None:
        return self._state.placements.get(entity_id)

    def all(self) -> tuple[Placement, ...]:
        return tuple(sorted(self._state.placements.values(), key=placement_order_key))

    def for_container(self, entity_id: str | None) -> tuple[Placement, ...]:
        return tuple(
            item for item in self.all() if item.containing_entity_id == entity_id
        )

    def validate_loaded_state(self) -> None:
        """Validate persisted placement invariants without recording events."""

        for placement in self._state.placements.values():
            self._validate(placement, replacing=placement.entity_id)
            self._validate_children(placement)

    def _required(self, entity_id: str) -> Placement:
        placement = self.get(entity_id)
        if placement is None:
            raise ValueError(f"Entity '{entity_id}' has no placement state.")
        return placement

    def _validate(self, placement: Placement, replacing: str | None = None) -> None:
        self._live_entity(placement.entity_id)
        if placement.containing_entity_id == placement.entity_id:
            raise ValueError("A placement cannot contain itself.")
        if placement.containing_entity_id is not None:
            parent_entity_id = placement.containing_entity_id
            self._live_entity(parent_entity_id)
            parent = self._state.placements.get(parent_entity_id)
            if parent is None or not isinstance(parent.geometry, Bounds):
                raise ValueError("A placement container must have bounds.")
            self._reject_cycle(placement.entity_id, parent_entity_id)
            if not parent.geometry.contains(placement.geometry):
                raise ValueError("Placement geometry must lie inside its container.")
            if (
                parent.bounds_kind is BoundsKind.STRUCTURE
                and placement.bounds_kind is BoundsKind.AREA
            ):
                raise ValueError("A structure cannot contain an area.")
        if isinstance(placement.geometry, Bounds):
            for sibling in self._state.placements.values():
                if sibling.entity_id == replacing:
                    continue
                if sibling.containing_entity_id != placement.containing_entity_id:
                    continue
                if not isinstance(sibling.geometry, Bounds):
                    continue
                if placement.geometry.overlaps(sibling.geometry) and not (
                    placement.overlap_policy is OverlapPolicy.ALLOW_SIBLING_OVERLAP
                    and sibling.overlap_policy is OverlapPolicy.ALLOW_SIBLING_OVERLAP
                ):
                    raise ValueError(
                        "Sibling bounds cannot overlap without mutual opt-in."
                    )

    def _validate_children(self, parent: Placement) -> None:
        children = tuple(
            item
            for item in self._state.placements.values()
            if item.containing_entity_id == parent.entity_id
        )
        if children and not isinstance(parent.geometry, Bounds):
            raise ValueError("A parent with children must retain bounds.")
        for child in children:
            if not parent.geometry.contains(child.geometry):
                raise ValueError("Replacement would place a child outside its parent.")
            if (
                parent.bounds_kind is BoundsKind.STRUCTURE
                and child.bounds_kind is BoundsKind.AREA
            ):
                raise ValueError("Replacement structure cannot contain an area.")

    def _reject_children(self, entity_id: str) -> None:
        if any(
            item.containing_entity_id == entity_id
            for item in self._state.placements.values()
        ):
            raise ValueError(
                "A spatial parent with children cannot be removed or unplaced."
            )

    def _reject_cycle(self, entity_id: str, parent_id: str) -> None:
        current: str | None = parent_id
        while current is not None:
            if current == entity_id:
                raise ValueError("Placement containment cannot contain a cycle.")
            placement = self._state.placements.get(current)
            current = None if placement is None else placement.containing_entity_id

    def _live_entity(self, entity_id: str) -> None:
        entity = self._state.entities.get(entity_id)
        if entity is None:
            raise ValueError(f"Unknown entity '{entity_id}'.")
        if entity.destroyed_tick is not None:
            raise ValueError(f"Destroyed entity '{entity_id}' cannot be placed.")

    def _commit(
        self,
        kind: str,
        previous: Placement | None,
        current: Placement | None,
    ) -> None:
        attributes: dict[str, object] = {}
        if previous is not None:
            attributes["previous"] = _placement_snapshot(previous)
        if current is not None:
            attributes["current"] = _placement_snapshot(current)
        before = set(self._state.events)
        try:
            event = self._events.record(
                kind=kind,
                subject_id=(current or previous).entity_id,
                attributes=attributes,
            )
            if event.id not in self._state.events:
                raise RuntimeError("Spatial event was not recorded.")
            if current is None:
                del self._state.placements[previous.entity_id]
            else:
                self._state.placements[current.entity_id] = current
        except Exception:
            for event_id in set(self._state.events) - before:
                self._state.events.pop(event_id, None)
            raise


def _placement_snapshot(placement: Placement) -> Mapping[str, object]:
    geometry: Mapping[str, object] | None
    if isinstance(placement.geometry, Point):
        geometry = {
            "kind": "point",
            "x": placement.geometry.x,
            "y": placement.geometry.y,
        }
    elif isinstance(placement.geometry, Bounds):
        geometry = {
            "kind": "bounds",
            "x": placement.geometry.x,
            "y": placement.geometry.y,
            "width": placement.geometry.width,
            "height": placement.geometry.height,
        }
    else:
        geometry = None
    return {
        "geometry": geometry,
        "containing_entity_id": placement.containing_entity_id,
        "bounds_kind": (
            None if placement.bounds_kind is None else placement.bounds_kind.value
        ),
        "overlap_policy": placement.overlap_policy.value,
    }


def placement_snapshot(placement: Placement) -> Mapping[str, object]:
    """Return a detached operator-safe placement shape without the subject ID."""
    return _placement_snapshot(placement)


def placement_order_key(placement: Placement) -> tuple[object, ...]:
    container = placement.containing_entity_id
    geometry = placement.geometry
    if isinstance(geometry, Point):
        x, y, geometry_rank, width, height = geometry.x, geometry.y, 0, 0, 0
    elif isinstance(geometry, Bounds):
        rank = 1 if placement.bounds_kind is BoundsKind.AREA else 2
        x, y, geometry_rank, width, height = (
            geometry.x,
            geometry.y,
            rank,
            geometry.width,
            geometry.height,
        )
    else:
        x, y, geometry_rank, width, height = 0, 0, 3, 0, 0
    return (
        0 if container is None else 1,
        container or "",
        1 if geometry is None else 0,
        x,
        y,
        geometry_rank,
        width,
        height,
        placement.entity_id,
    )
