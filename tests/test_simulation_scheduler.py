from living_world.simulation.simulation_scheduler import SimulationScheduler
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class CountingSystem(SimulationSystem):
    def __init__(self) -> None:
        self.calls = 0

    def update(self) -> None:
        self.calls += 1


def test_scheduler_step() -> None:
    state = WorldState()

    scheduler = SimulationScheduler(state)

    system = CountingSystem()

    scheduler.register(system)

    scheduler.step()

    assert state.tick == 1

    assert system.calls == 1


def test_scheduler_run() -> None:
    state = WorldState()

    scheduler = SimulationScheduler(state)

    system = CountingSystem()

    scheduler.register(system)

    scheduler.run(5)

    assert state.tick == 5

    assert system.calls == 5
