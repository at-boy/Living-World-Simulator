from living_world.simulation.simulation_engine import SimulationEngine
from living_world.systems.simulation_system import SimulationSystem


class CountingSystem(SimulationSystem):
    def __init__(self) -> None:
        self.calls = 0

    def update(self) -> None:
        self.calls += 1


def test_engine_step() -> None:
    engine = SimulationEngine()

    system = CountingSystem()

    engine.register_system(system)

    engine.step()

    assert engine.state.tick == 1

    assert system.calls == 1


def test_engine_run() -> None:
    engine = SimulationEngine()

    system = CountingSystem()

    engine.register_system(system)

    engine.run(5)

    assert engine.state.tick == 5

    assert system.calls == 5
