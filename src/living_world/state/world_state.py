from dataclasses import dataclass, field
from living_world.world.location import Location
from living_world.world.connection import Connection

@dataclass
class WorldState:
    tick:int=0
    locations:dict[str,Location]=field(default_factory=dict)
    connections:list[Connection]=field(default_factory=list)
    entities:dict[str,object]=field(default_factory=dict)
    events:list[object]=field(default_factory=list)
