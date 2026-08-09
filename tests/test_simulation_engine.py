from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class CountingSystem(SimulationSystem):
    def __init__(self) -> None:
        self.calls = 0

    def step(self, state: WorldState) -> None:
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


def test_engine_exposes_observation_manager() -> None:
    engine = SimulationEngine()

    observation = engine.observations.record(
        observer="entity_000001",
        subject="entity_000002",
        description="The tree appears healthy.",
        confidence=0.8,
    )

    assert observation.id == "observation_000001"
    assert engine.observations.get(observation.id) is observation
