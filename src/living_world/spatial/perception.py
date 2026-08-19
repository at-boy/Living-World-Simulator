"""NPC-safe qualitative translation of authoritative local geometry."""

from __future__ import annotations

from living_world.core.entity import Entity
from living_world.core.observation import Observation
from living_world.core.relationship import Relationship
from living_world.perception.npc_perception_boundary import (
    DefaultNPCPerceptionBoundary,
    NPCPerceptionBoundary,
)
from living_world.perception.perception_context import PerceptionContext
from living_world.spatial.model import Bounds, Placement, Point
from living_world.state.world_state import WorldState


class SpatialPerceptionError(ValueError):
    """Raised when authoritative state cannot support a spatial perception."""


class SpatialPerceptionEngine:
    """Translate caller-selected local geometry into NPC-readable prose."""

    def __init__(self, boundary: NPCPerceptionBoundary | None = None) -> None:
        self._boundary = (
            DefaultNPCPerceptionBoundary() if boundary is None else boundary
        )

    def perceive(self, context: PerceptionContext) -> Observation:
        """Return one unpersisted qualitative observation."""

        if not isinstance(context, PerceptionContext):
            raise TypeError("Spatial perception context must be a PerceptionContext.")
        if not isinstance(context.world_state, WorldState):
            raise TypeError("Spatial perception world_state must be a WorldState.")
        if not isinstance(context.tick, int) or isinstance(context.tick, bool):
            raise TypeError("Spatial perception tick must be an integer.")
        if context.tick < 0:
            raise ValueError("Spatial perception tick cannot be negative.")
        if not isinstance(context.relationships, tuple):
            raise TypeError("Spatial perception relationships must be a tuple.")
        if not all(
            isinstance(relationship, Relationship)
            for relationship in context.relationships
        ):
            raise TypeError(
                "Spatial perception relationships must contain Relationships."
            )

        observer = self._live_context_entity(context, context.observer, "observer")
        subject = self._live_context_entity(context, context.subject, "subject")
        observer_placement, observer_geometry = self._placed(context, observer)
        subject_placement, subject_geometry = self._placed(context, subject)

        relation_codes: list[str] = []
        clauses: list[str] = []

        containment = self._containment_description(
            context,
            observer,
            subject,
            observer_placement,
            subject_placement,
        )
        if containment is not None:
            code, description = containment
            relation_codes.append(code)
            clauses.append(description)

        direction = self._direction(observer_geometry, subject_geometry)
        relation_codes.append(direction)
        clauses.append(self._direction_description(observer, subject, direction))

        if self._has_direct_road(context, observer.id, subject.id):
            relation_codes.append("direct_road")
            clauses.append(
                f"A road directly connects {observer.name} and {subject.name}."
            )

        observation = Observation(
            id="",
            tick=context.tick,
            observer=observer.id,
            subject=subject.id,
            description=" ".join(clauses),
            confidence=1.0,
            evidence={"spatial_relations": tuple(relation_codes)},
            metadata={"engine": "spatial_perception"},
        )
        self._boundary.visible_description(observation, context=context)
        return observation

    @staticmethod
    def _live_context_entity(
        context: PerceptionContext,
        supplied: Entity,
        role: str,
    ) -> Entity:
        if not isinstance(supplied, Entity):
            raise TypeError(f"Spatial perception {role} must be an Entity.")
        authoritative = context.world_state.entities.get(supplied.id)
        if authoritative is None:
            raise SpatialPerceptionError(
                f"Spatial perception {role} must identify a known entity."
            )
        if authoritative is not supplied:
            raise SpatialPerceptionError(
                f"Spatial perception {role} must match authoritative state."
            )
        if authoritative.destroyed_tick is not None:
            raise SpatialPerceptionError(
                f"Spatial perception {role} must identify a live entity."
            )
        return authoritative

    @staticmethod
    def _placed(
        context: PerceptionContext,
        entity: Entity,
    ) -> tuple[Placement, Point | Bounds]:
        placement = context.world_state.placements.get(entity.id)
        if placement is None or not isinstance(placement, Placement):
            raise SpatialPerceptionError(
                "Spatial perception requires authoritative placement records."
            )
        if not isinstance(placement.geometry, Point | Bounds):
            raise SpatialPerceptionError(
                "Spatial perception requires placed observer and subject entities."
            )
        if placement.entity_id != entity.id:
            raise SpatialPerceptionError(
                "Spatial perception placement must match authoritative state."
            )
        return placement, placement.geometry

    @classmethod
    def _containment_description(
        cls,
        context: PerceptionContext,
        observer: Entity,
        subject: Entity,
        observer_placement: Placement,
        subject_placement: Placement,
    ) -> tuple[str, str] | None:
        observer_container = observer_placement.containing_entity_id
        subject_container = subject_placement.containing_entity_id
        if subject_container is not None and subject_container == observer_container:
            container = cls._live_bounded_container(context, subject_container)
            return (
                "shared_container",
                f"{subject.name} and {observer.name} are inside {container.name}.",
            )
        if subject_container is not None:
            container = cls._live_bounded_container(context, subject_container)
            return (
                "subject_inside_container",
                f"{subject.name} is inside {container.name}.",
            )
        if observer_container == subject.id:
            return (
                "subject_contains_observer",
                f"{subject.name} contains {observer.name}.",
            )
        return None

    @staticmethod
    def _live_bounded_container(
        context: PerceptionContext,
        entity_id: str,
    ) -> Entity:
        container = context.world_state.entities.get(entity_id)
        if container is None or container.destroyed_tick is not None:
            raise SpatialPerceptionError(
                "Spatial perception container must identify a live entity."
            )
        placement = context.world_state.placements.get(entity_id)
        if not isinstance(placement, Placement) or not isinstance(
            placement.geometry,
            Bounds,
        ):
            raise SpatialPerceptionError(
                "Spatial perception container must have authoritative bounds."
            )
        if placement.entity_id != entity_id:
            raise SpatialPerceptionError(
                "Spatial perception container placement must match authoritative state."
            )
        return container

    @classmethod
    def _direction(cls, observer: Point | Bounds, subject: Point | Bounds) -> str:
        observer_x, observer_y = cls._doubled_center(observer)
        subject_x, subject_y = cls._doubled_center(subject)
        horizontal = cls._axis_direction(subject_x - observer_x, "east", "west")
        vertical = cls._axis_direction(subject_y - observer_y, "north", "south")
        if vertical and horizontal:
            return f"{vertical}_{horizontal}"
        return vertical or horizontal or "co_located"

    @staticmethod
    def _doubled_center(geometry: Point | Bounds) -> tuple[int, int]:
        if isinstance(geometry, Point):
            return geometry.x * 2, geometry.y * 2
        return geometry.x * 2 + geometry.width, geometry.y * 2 + geometry.height

    @staticmethod
    def _axis_direction(delta: int, positive: str, negative: str) -> str:
        if delta > 0:
            return positive
        if delta < 0:
            return negative
        return ""

    @staticmethod
    def _direction_description(
        observer: Entity,
        subject: Entity,
        direction: str,
    ) -> str:
        if direction == "co_located":
            return f"{subject.name} occupies the same place as {observer.name}."
        return f"{subject.name} is {direction.replace('_', '-')} of {observer.name}."

    @staticmethod
    def _has_direct_road(
        context: PerceptionContext,
        observer_id: str,
        subject_id: str,
    ) -> bool:
        endpoints = {observer_id, subject_id}
        for relationship in context.relationships:
            authoritative = context.world_state.relationships.get(relationship.id)
            if authoritative is not relationship:
                continue
            if relationship.kind != "road":
                continue
            if relationship.created_tick > context.tick:
                continue
            if relationship.destroyed_tick is not None:
                continue
            if {relationship.source_id, relationship.target_id} == endpoints:
                return True
        return False
