import pytest

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


def test_work_execution_phase_precedes_consequences_needs_and_goals() -> None:
    engine = SimulationEngine()
    names = [type(system).__name__ for system in engine._scheduler._systems]
    assert names[-5:] == [
        "WorkExecutionSystem",
        "ConsequenceSystem",
        "NeedAssessmentSystem",
        "GoalEvaluationSystem",
        "SettlementStageEvaluationSystem",
    ]
    assert not hasattr(engine, "work_action_handler")


def test_named_registration_replaces_in_place_and_rejects_invalid() -> None:
    import pytest

    engine = SimulationEngine()
    old, following, replacement = CountingSystem(), CountingSystem(), CountingSystem()
    engine.register_system(old, key="canonical_founders")
    engine.register_system(following)
    engine.register_system(replacement, key="canonical_founders")
    engine.step()
    assert (old.calls, following.calls, replacement.calls) == (0, 1, 1)
    assert engine._registered_systems[-2:] == [replacement, following]
    for key in ("", 2):
        with pytest.raises((TypeError, ValueError)):
            engine.register_system(CountingSystem(), key=key)
    with pytest.raises(TypeError):
        engine.register_system(object(), key="bad")


def test_keyed_registration_rebuild_failure_restores_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pytest

    engine = SimulationEngine()
    old = CountingSystem()
    engine.register_system(old, key="canonical_founders")
    before = engine._scheduler

    def fail() -> None:
        raise ValueError("rebuild rejected")

    monkeypatch.setattr(engine, "_rebuild_scheduler", fail)
    with pytest.raises(ValueError, match="rebuild rejected"):
        engine.register_system(CountingSystem(), key="canonical_founders")
    assert engine._scheduler is before
    assert engine._registered_systems[-1] is old
    assert (
        engine._system_keys["canonical_founders"] == len(engine._registered_systems) - 1
    )
