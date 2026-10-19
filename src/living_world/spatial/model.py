from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    return value


class BoundsKind(str, Enum):
    AREA = "area"
    STRUCTURE = "structure"


class OverlapPolicy(str, Enum):
    REJECT = "reject"
    ALLOW_SIBLING_OVERLAP = "allow_sibling_overlap"


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int

    def __post_init__(self) -> None:
        _integer(self.x, "x")
        _integer(self.y, "y")


@dataclass(frozen=True, slots=True)
class Bounds:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        _integer(self.x, "x")
        _integer(self.y, "y")
        _integer(self.width, "width")
        _integer(self.height, "height")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Bounds width and height must be positive.")

    def contains(self, geometry: Point | Bounds) -> bool:
        if isinstance(geometry, Point):
            return (
                self.x <= geometry.x < self.x + self.width
                and self.y <= geometry.y < self.y + self.height
            )
        if not isinstance(geometry, Bounds):
            raise TypeError("geometry must be a Point or Bounds.")
        return (
            self.x <= geometry.x
            and self.y <= geometry.y
            and geometry.x + geometry.width <= self.x + self.width
            and geometry.y + geometry.height <= self.y + self.height
        )

    def overlaps(self, other: Bounds) -> bool:
        return (
            self.x < other.x + other.width
            and other.x < self.x + self.width
            and self.y < other.y + other.height
            and other.y < self.y + self.height
        )


@dataclass(frozen=True, slots=True)
class Placement:
    entity_id: str
    geometry: Point | Bounds | None
    containing_entity_id: str | None = None
    bounds_kind: BoundsKind | None = None
    overlap_policy: OverlapPolicy = OverlapPolicy.REJECT

    def __post_init__(self) -> None:
        if not isinstance(self.entity_id, str):
            raise TypeError("Placement entity_id must be a string.")
        if not self.entity_id.strip():
            raise ValueError("Placement entity_id cannot be empty.")
        if self.containing_entity_id is not None:
            if not isinstance(self.containing_entity_id, str):
                raise TypeError("Placement containing_entity_id must be a string.")
            if not self.containing_entity_id.strip():
                raise ValueError("Placement containing_entity_id cannot be empty.")
        if self.bounds_kind is not None and not isinstance(
            self.bounds_kind, BoundsKind
        ):
            raise TypeError("Placement bounds_kind must be a BoundsKind or None.")
        if not isinstance(self.overlap_policy, OverlapPolicy):
            raise TypeError("Placement overlap_policy must be an OverlapPolicy.")
        if self.geometry is not None and not isinstance(self.geometry, Point | Bounds):
            raise TypeError("Placement geometry must be a Point, Bounds, or None.")
        if self.geometry is None:
            if self.containing_entity_id is not None or self.bounds_kind is not None:
                raise ValueError(
                    "Unplaced state cannot have a container or bounds kind."
                )
            if self.overlap_policy is not OverlapPolicy.REJECT:
                raise ValueError("Unplaced state must reject sibling overlap.")
        elif isinstance(self.geometry, Point):
            if self.bounds_kind is not None:
                raise ValueError("Point placement cannot have a bounds kind.")
            if self.overlap_policy is not OverlapPolicy.REJECT:
                raise ValueError("Point placement must reject sibling overlap.")
        elif self.bounds_kind is None:
            raise ValueError("Bounds placement requires a bounds kind.")
