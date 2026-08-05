from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class SimulationScheduler:
    """Executes simulation systems in deterministic order."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._systems: list[SimulationSystem] = []

    def register(
        self,
        system: SimulationSystem,
    ) -> None:
        """Register a simulation system."""

        self._systems.append(system)

    def step(self) -> None:
        """Execute one simulation tick."""

        for system in self._systems:
            system.update()

        self._state.tick += 1

    def run(
        self,
        steps: int,
    ) -> None:
        """Execute multiple simulation ticks."""

        if steps < 0:
            raise ValueError("steps must be non-negative.")

        for _ in range(steps):
            self.step()
