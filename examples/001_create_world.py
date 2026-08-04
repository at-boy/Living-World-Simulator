from living_world.managers.graph_manager import GraphManager
from living_world.state.world_state import WorldState
from living_world.world.connection import Connection
from living_world.world.location import Location

state=WorldState()
graph=GraphManager(state)

graph.add_location(Location("loc_000001","Village"))
graph.add_location(Location("loc_000002","Forest"))
graph.connect(Connection("loc_000001","loc_000002"))

print("Tick:",state.tick)
print("Locations:",list(state.locations))
print("Connections:",len(state.connections))
