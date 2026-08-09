from typing import Protocol

from living_world.state.world_state import WorldState


class SimulationSystem(Protocol):
    """Protocol implemented by systems that advance a world state."""

    def step(self, state: WorldState) -> None:
        """Execute one simulation tick."""
