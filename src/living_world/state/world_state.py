from dataclasses import dataclass, field

from living_world.core.entity import Entity
from living_world.core.event import Event
from living_world.core.relationship import Relationship


@dataclass(slots=True)
class WorldState:
    tick: int = 0

    entities: dict[str, Entity] = field(default_factory=dict)

    relationships: dict[str, Relationship] = field(default_factory=dict)

    events: dict[str, Event] = field(default_factory=dict)
