from living_world.state.world_state import WorldState
from living_world.managers.graph_manager import GraphManager
from living_world.world.location import Location

world=WorldState()
graph=GraphManager(world)

graph.add_location(Location(id="loc_000001",name="Village"))
graph.add_location(Location(id="loc_000002",name="Forest"))

print("Locations:")
for loc in world.locations.values():
    print("-",loc.id,loc.name)
