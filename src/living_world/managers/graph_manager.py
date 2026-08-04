from living_world.state.world_state import WorldState
from living_world.world.connection import Connection
from living_world.world.location import Location


class GraphManager:
    """Manage the world graph."""

    def __init__(self, state: WorldState) -> None:
        self._state = state

    def add_location(self, location: Location) -> None:
        self._state.locations[location.id] = location

    def connect(self, connection: Connection) -> None:
        self._state.connections.append(connection)
