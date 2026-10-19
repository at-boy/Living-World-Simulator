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
    from living_world.spatial.perception import (
        SpatialPerceptionEngine,
        SpatialPerceptionError,
    )

__all__ = [
    "Bounds",
    "BoundsKind",
    "OverlapPolicy",
    "Placement",
    "Point",
    "SpatialManager",
    "SpatialPerceptionEngine",
    "SpatialPerceptionError",
    "placement_snapshot",
]


def __getattr__(name: str) -> object:
    if name == "SpatialManager":
        from living_world.spatial.manager import SpatialManager

        return SpatialManager
    if name == "placement_snapshot":
        from living_world.spatial.manager import placement_snapshot

        return placement_snapshot
    if name in {"SpatialPerceptionEngine", "SpatialPerceptionError"}:
        from living_world.spatial.perception import (
            SpatialPerceptionEngine,
            SpatialPerceptionError,
        )

        return {
            "SpatialPerceptionEngine": SpatialPerceptionEngine,
            "SpatialPerceptionError": SpatialPerceptionError,
        }[name]
    raise AttributeError(name)
