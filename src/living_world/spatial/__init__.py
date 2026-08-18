from typing import TYPE_CHECKING

from living_world.spatial.model import (
    Bounds,
    BoundsKind,
    OverlapPolicy,
    Placement,
    Point,
)

if TYPE_CHECKING:
    from living_world.spatial.manager import SpatialManager

__all__ = [
    "Bounds",
    "BoundsKind",
    "OverlapPolicy",
    "Placement",
    "Point",
    "SpatialManager",
    "placement_snapshot",
]


def __getattr__(name: str) -> object:
    if name == "SpatialManager":
        from living_world.spatial.manager import SpatialManager

        return SpatialManager
    if name == "placement_snapshot":
        from living_world.spatial.manager import placement_snapshot

        return placement_snapshot
    raise AttributeError(name)
