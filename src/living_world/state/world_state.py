from dataclasses import dataclass, field

from living_world.world.connection import Connection
from living_world.world.location import Location


@dataclass(slots=True)
class WorldState:
    tick: int = 0
    locations: dict[str, Location] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
