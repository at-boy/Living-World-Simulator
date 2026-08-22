from living_world.simulation.simulation_engine import SimulationEngine
from living_world.simulation.simulation_scheduler import SimulationScheduler
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class CountingSystem(SimulationSystem):
    def __init__(self) -> None:
        self.calls = 0

    def step(self, state: WorldState) -> None:
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


def test_task_twenty_adds_no_work_system_or_scheduler_mutation() -> None:
    engine = SimulationEngine()
    assert all(
        type(system).__module__ != "living_world.work"
        for system in engine._registered_systems
    )
    assert all(
        type(system).__module__ != "living_world.work.action"
        for system in engine._registered_systems
    )
    assert not hasattr(engine, "work_action_handler")
    before = (
        dict(engine.state.work_definitions),
        dict(engine.state.work_states),
        dict(engine.state.work_reservations),
    )
    engine.step()
    assert (
        engine.state.work_definitions,
        engine.state.work_states,
        engine.state.work_reservations,
    ) == before
