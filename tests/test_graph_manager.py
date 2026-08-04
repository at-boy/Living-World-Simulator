from living_world.state.world_state import WorldState
from living_world.managers.graph_manager import GraphManager
from living_world.world.location import Location

def test_add_location():
    state=WorldState()
    gm=GraphManager(state)
    gm.add_location(Location("loc_1","Village"))
    assert "loc_1" in state.locations
