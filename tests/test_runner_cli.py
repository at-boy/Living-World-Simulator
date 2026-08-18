from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from living_world.cli import (
    INCOMPATIBLE_SAVE,
    INVALID_CONFIGURATION,
    PERSISTENCE_FAILURE,
    SIMULATION_FAILURE,
    SignalStopControl,
    main,
)
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.running import (
    CheckpointControl,
    RunConfiguration,
    RunPersistenceError,
    RunSimulationError,
    ScenarioRunner,
    StopReason,
)
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState


def _scenario(
    tmp_path: Path,
    *,
    max_ticks: int = 4,
    seed: int = 7,
    progress: object = 0,
    conditions: str = "[]",
) -> Path:
    (tmp_path / "world.yaml").write_text(
        "definitions:\n  - key: project\n", encoding="utf-8"
    )
    path = tmp_path / "scenario.yaml"
    path.write_text(
        f"""schema_version: 1
key: runner-test
seed: {seed}
definitions: world.yaml
run:
  max_ticks: {max_ticks}
  terminal_conditions: {conditions}
entities:
  - label: project
    definition: project
    name: Project
    attributes:
      progress: {progress}
      progress_rate: 1
relationships: []
""",
        encoding="utf-8",
    )
    return path


class RecordingRepository:
    def __init__(self, state: WorldState | None = None) -> None:
        self.state = state or WorldState()
        self.saved_ticks: list[int] = []

    def load_world(self) -> WorldState:
        return self.state

    def save_world(self, state: WorldState) -> None:
        self.saved_ticks.append(state.tick)


@dataclass
class TickStopControl:
    state: WorldState
    stop_tick: int

    def stop_requested(self) -> bool:
        return self.state.tick >= self.stop_tick


class NeverCheckpointControl(CheckpointControl):
    def checkpoint_due(self, completed_ticks: int) -> bool:
        return False


def test_bounded_default_override_and_checkpoint_cadence(tmp_path: Path) -> None:
    repository = RecordingRepository()
    engine = SimulationEngine(repository)

    result = ScenarioRunner(engine).run(
        _scenario(tmp_path, max_ticks=5),
        RunConfiguration(save_every=2),
    )

    assert result.start_tick == 0
    assert result.end_tick == 5
    assert result.stop_reason is StopReason.TICK_LIMIT
    assert repository.saved_ticks == [2, 4, 5]

    other = SimulationEngine(RecordingRepository())
    override = ScenarioRunner(other).run(
        _scenario(tmp_path, max_ticks=5),
        RunConfiguration(max_ticks=2),
    )
    assert override.end_tick == 2


def test_continuous_mode_uses_injected_stop_without_time_or_signals(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    engine = SimulationEngine(repository)
    result = ScenarioRunner(engine).run(
        _scenario(tmp_path),
        RunConfiguration(continuous=True, save_every=2),
        stop_control=TickStopControl(engine.state, 3),
        checkpoint_control=NeverCheckpointControl(),
    )

    assert result.end_tick == 3
    assert result.stop_reason is StopReason.OPERATOR_STOP
    assert repository.saved_ticks == [3]


def test_run_configuration_rejects_invalid_and_contradictory_values() -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        RunConfiguration(max_ticks=1, continuous=True)
    with pytest.raises(ValueError, match="non-negative"):
        RunConfiguration(max_ticks=-1)
    with pytest.raises(ValueError, match="positive"):
        RunConfiguration(save_every=0)
    with pytest.raises(TypeError, match="integer"):
        RunConfiguration(max_ticks=True)
    with pytest.raises(TypeError, match="integer"):
        RunConfiguration(save_every=True)


def test_new_then_resumed_run_does_not_duplicate_initialization(tmp_path: Path) -> None:
    database = tmp_path / "world.sqlite3"
    scenario = _scenario(tmp_path)
    first = ScenarioRunner(SimulationEngine(SQLiteRepository(str(database)))).run(
        scenario, RunConfiguration(max_ticks=2)
    )
    resumed_engine = SimulationEngine(SQLiteRepository(str(database)))
    second = ScenarioRunner(resumed_engine).run(scenario, RunConfiguration(max_ticks=2))

    assert first.resumed is False
    assert second.resumed is True
    assert (first.start_tick, first.end_tick) == (0, 2)
    assert (second.start_tick, second.end_tick) == (2, 4)
    assert len(resumed_engine.state.entities) == 1


def test_uninterrupted_and_resumed_runs_are_state_equivalent(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path)
    uninterrupted_database = tmp_path / "uninterrupted.sqlite3"
    uninterrupted_repository = SQLiteRepository(str(uninterrupted_database))
    uninterrupted = SimulationEngine(uninterrupted_repository)
    ScenarioRunner(uninterrupted).run(scenario, RunConfiguration(max_ticks=4))

    resumed_database = tmp_path / "resumed.sqlite3"
    first = SimulationEngine(SQLiteRepository(str(resumed_database)))
    ScenarioRunner(first).run(scenario, RunConfiguration(max_ticks=2))
    resumed_repository = SQLiteRepository(str(resumed_database))
    resumed = SimulationEngine(resumed_repository)
    ScenarioRunner(resumed).run(scenario, RunConfiguration(max_ticks=2))

    assert resumed.state.tick == uninterrupted.state.tick
    assert resumed.state.entities == uninterrupted.state.entities
    assert resumed.state.relationships == uninterrupted.state.relationships
    assert resumed.state.events == uninterrupted.state.events


class FailingSystem:
    def step(self, state: WorldState) -> None:
        if state.tick == 1:
            state.tick = 99
            raise RuntimeError("broken tick")


def test_failed_tick_does_not_replace_last_valid_checkpoint(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "atomic.sqlite3"))
    engine = SimulationEngine(repository)
    engine.register_system(FailingSystem())

    with pytest.raises(RunSimulationError, match="Simulation failed"):
        ScenarioRunner(engine).run(_scenario(tmp_path), RunConfiguration())

    persisted = repository.load_world()
    assert persisted.tick == 1
    assert persisted.entities["entity_000001"].attributes["progress"] == 1


def test_selected_terminal_condition_stops_and_is_reported(tmp_path: Path) -> None:
    repository = RecordingRepository()
    engine = SimulationEngine(repository)
    result = ScenarioRunner(engine).run(
        _scenario(tmp_path, max_ticks=2, conditions="[tick_limit]"),
        RunConfiguration(save_every=3),
    )

    assert result.end_tick == 2
    assert result.stop_reason is StopReason.TERMINAL_CONDITION
    assert result.terminal_condition == "tick_limit"
    assert repository.saved_ticks == [2]


class FailingSaveRepository(RecordingRepository):
    def save_world(self, state: WorldState) -> None:
        raise RuntimeError("disk unavailable")


def test_persistence_failure_is_typed(tmp_path: Path) -> None:
    engine = SimulationEngine(FailingSaveRepository())
    with pytest.raises(RunPersistenceError, match="checkpoint"):
        ScenarioRunner(engine).run(_scenario(tmp_path), RunConfiguration(max_ticks=0))


def test_runner_rejects_an_engine_without_persistence_before_loading(
    tmp_path: Path,
) -> None:
    engine = SimulationEngine()
    with pytest.raises(RunPersistenceError, match="persistence-backed"):
        ScenarioRunner(engine).run(_scenario(tmp_path), RunConfiguration(max_ticks=0))
    assert engine.state.run_metadata is None
    assert engine.state.entities == {}


def test_cli_summary_resume_and_failure_exit_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario = _scenario(tmp_path, max_ticks=1)
    database = tmp_path / "cli.sqlite3"
    arguments = [
        "run",
        str(scenario),
        "--database",
        str(database),
    ]
    assert main(arguments) == 0
    assert (
        capsys.readouterr().out
        == "scenario=runner-test status=new start_tick=0 end_tick=1 "
        "stop_reason=tick_limit\n"
    )
    assert main(arguments) == 0
    assert "status=resumed start_tick=1 end_tick=2" in capsys.readouterr().out

    missing = tmp_path / "missing.yaml"
    assert (
        main(
            [
                "run",
                str(missing),
                "--database",
                str(tmp_path / "missing-scenario.sqlite3"),
            ]
        )
        == INVALID_CONFIGURATION
    )
    _scenario(tmp_path, seed=8)
    assert main(arguments) == INCOMPATIBLE_SAVE

    bad_database = tmp_path / "missing" / "world.sqlite3"
    assert (
        main(["run", str(scenario), "--database", str(bad_database)])
        == PERSISTENCE_FAILURE
    )

    failing_scenario = _scenario(tmp_path, progress="bad")
    assert (
        main(
            [
                "run",
                str(failing_scenario),
                "--database",
                str(tmp_path / "failure.sqlite3"),
            ]
        )
        == SIMULATION_FAILURE
    )


def test_cli_rejects_contradictory_flags() -> None:
    with pytest.raises(SystemExit) as error:
        main(["run", "scenario.yaml", "--max-ticks", "1", "--continuous"])
    assert error.value.code == INVALID_CONFIGURATION


def test_signal_control_requests_a_cooperative_stop() -> None:
    control = SignalStopControl()
    assert control.stop_requested() is False
    control.handle_signal(2, None)
    assert control.stop_requested() is True


def test_unknown_terminal_condition_is_invalid_configuration(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path, conditions="[unknown]")
    with pytest.raises(ValueError, match="Unsupported terminal condition"):
        ScenarioRunner(SimulationEngine(RecordingRepository())).run(
            scenario, RunConfiguration()
        )
