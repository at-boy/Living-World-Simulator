from living_world.state.world_state import WorldState
from living_world.world.location import Location
from living_world.world.connection import Connection

class GraphManager:
    """Owns the location graph. Contains no persistence logic."""

    def __init__(self,state:WorldState):
        self._state=state

    def add_location(self,location:Location)->None:
        self._state.locations[location.id]=location

    def connect(self,connection:Connection)->None:
        self._state.connections.append(connection)
