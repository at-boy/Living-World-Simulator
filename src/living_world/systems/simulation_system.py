from living_world.state.world_state import WorldState

class SimulationSystem:
    """Base class for simulation systems."""

    def update(self,state:WorldState)->None:
        raise NotImplementedError
