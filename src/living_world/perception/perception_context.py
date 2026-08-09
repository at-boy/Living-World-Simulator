from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.state.world_state import WorldState


@dataclass(frozen=True)
class PerceptionContext:
    """Information available to a perception engine when producing an observation."""

    observer: Entity
    subject: Entity
    world_state: WorldState
    capabilities: Mapping[str, object]
    relationships: tuple[Relationship, ...]
    tick: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capabilities",
            MappingProxyType(dict(self.capabilities)),
        )
