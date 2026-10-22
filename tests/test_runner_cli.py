from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

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


def test_custom_terminal_checks_before_zero_budget_and_copies_mapping(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    engine = SimulationEngine(repository)
    conditions = {"founding_failure": lambda engine: True}
    runner = ScenarioRunner(engine, terminal_conditions=conditions)
    conditions.clear()
    result = runner.run(
        _scenario(tmp_path, conditions="[founding_failure]"),
        RunConfiguration(max_ticks=0),
    )
    assert result.end_tick == 0
    assert result.terminal_condition == "founding_failure"
    assert result.stop_reason is StopReason.TERMINAL_CONDITION


def test_terminal_callback_failure_does_not_save_or_poison(tmp_path: Path) -> None:
    repository = RecordingRepository()
    engine = SimulationEngine(repository)
    runner = ScenarioRunner(engine, terminal_conditions={"custom": lambda engine: 1})
    with pytest.raises(
        RunSimulationError, match="Terminal condition evaluation failed"
    ) as error:
        runner.run(_scenario(tmp_path, conditions="[custom]"), RunConfiguration())
    assert isinstance(error.value.__cause__, TypeError)
    assert repository.saved_ticks == []
    assert engine.state.tick == 0
    engine.step()


def test_custom_terminal_runs_once_per_complete_boundary_and_before_checkpoints(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    engine = SimulationEngine(repository)
    calls = []

    def terminal(engine: SimulationEngine) -> bool:
        calls.append(engine.state.tick)
        return engine.state.tick == 2

    result = ScenarioRunner(engine, terminal_conditions={"custom": terminal}).run(
        _scenario(tmp_path, conditions="[custom]"),
        RunConfiguration(max_ticks=4, save_every=1),
    )
    assert calls == [0, 1, 2]
    assert repository.saved_ticks == [1, 2]
    assert result.end_tick == 2


@pytest.mark.parametrize(
    "conditions",
    [
        {"tick_limit": lambda engine: False},
        {"": lambda engine: False},
        {"Upper": lambda engine: False},
        {"valid": None},
    ],
)
def test_custom_terminal_rejects_invalid_registry(
    conditions: Mapping[str, object],
) -> None:
    with pytest.raises(ValueError):
        ScenarioRunner(
            SimulationEngine(RecordingRepository()),
            terminal_conditions=cast(
                Mapping[str, Callable[[SimulationEngine], bool]], conditions
            ),
        )


def test_pre_step_operator_stop_precedes_custom_callback(tmp_path: Path) -> None:
    repository = RecordingRepository()
    engine = SimulationEngine(repository)

    def forbidden(engine: SimulationEngine) -> bool:
        raise AssertionError("must not evaluate")

    result = ScenarioRunner(engine, terminal_conditions={"custom": forbidden}).run(
        _scenario(tmp_path, conditions="[custom]"),
        RunConfiguration(),
        stop_control=TickStopControl(engine.state, 0),
    )
    assert result.stop_reason is StopReason.OPERATOR_STOP
    assert result.end_tick == 0


def test_callback_exception_after_complete_tick_preserves_last_checkpoint_and_tick(
    tmp_path: Path,
) -> None:
    database = tmp_path / "callback.sqlite3"
    engine = SimulationEngine(SQLiteRepository(str(database)))
    failure = RuntimeError("private callback payload")

    def terminal(current: SimulationEngine) -> bool:
        if current.state.tick == 2:
            raise failure
        return False

    with pytest.raises(RunSimulationError) as caught:
        ScenarioRunner(engine, terminal_conditions={"custom": terminal}).run(
            _scenario(tmp_path, conditions="[custom]"), RunConfiguration()
        )
    assert str(caught.value) == "Terminal condition evaluation failed."
    assert caught.value.__cause__ is failure
    assert engine.state.tick == 2
    assert SQLiteRepository(str(database), read_only=True).load_world().tick == 1
    engine.step()
    assert engine.state.tick == 3


def test_selected_custom_order_precedes_legacy_terminal_and_after_tick_operator(
    tmp_path: Path,
) -> None:
    engine = SimulationEngine(RecordingRepository())
    result = ScenarioRunner(
        engine,
        terminal_conditions={
            "first": lambda current: current.state.tick == 1,
            "second": lambda current: current.state.tick == 1,
        },
    ).run(
        _scenario(tmp_path, conditions="[tick_limit, first, second, operator_stop]"),
        RunConfiguration(max_ticks=1),
        stop_control=TickStopControl(engine.state, 1),
    )
    assert result.terminal_condition == "first"
    assert result.end_tick == 1


def test_cli_automatically_archives_every_tick(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from living_world.archives import RunCatalog

    root = tmp_path / "archives"
    assert (
        main(
            [
                "run",
                str(_scenario(tmp_path)),
                "--database",
                str(tmp_path / "world.db"),
                "--archive-root",
                str(root),
                "--save-every",
                "3",
            ]
        )
        == 0
    )
    (summary,) = RunCatalog(root).attempts()
    assert summary.lifecycle == "completed"
    assert summary.last_revision == 4
    assert (
        f"attempt={summary.ref.attempt_id} archive={summary.ref.directory}"
        in capsys.readouterr().err
    )


def test_cli_missing_scenario_metadata_attempt(tmp_path: Path) -> None:
    from living_world.archives import RunCatalog

    root = tmp_path / "archives"
    assert (
        main(["run", str(tmp_path / "missing.yaml"), "--archive-root", str(root)])
        == INVALID_CONFIGURATION
    )
    (summary,) = RunCatalog(root).attempts()
    assert summary.scenario == "uninitialized"
    assert summary.lifecycle == "failed"
    assert summary.last_revision is None


def test_cli_resume_keeps_original_engine_state_and_thread(tmp_path: Path) -> None:
    import threading

    from living_world.archives import RunCatalog

    path = _scenario(tmp_path)
    root = tmp_path / "archives"
    database = tmp_path / "world.db"
    args = ["run", str(path), "--database", str(database), "--archive-root", str(root)]
    assert main([*args, "--max-ticks", "1"]) == 0
    calls: list[SimulationEngine] = []
    invoking_thread = threading.get_ident()
    control = TickStopControl(WorldState(), 3)

    def factory(repository: SQLiteRepository) -> SimulationEngine:
        assert threading.get_ident() == invoking_thread
        assert repository.load_world().tick == 1
        engine = SimulationEngine(repository)
        calls.append(engine)
        control.state = engine.state
        return engine

    assert (
        main([*args, "--max-ticks", "9"], engine_factory=factory, stop_control=control)
        == 0
    )
    assert len(calls) == 1
    assert control.state is calls[0].state
    assert control.state.tick == 3
    summaries = RunCatalog(root).attempts()
    assert len(summaries) == 2
    resumed = next(summary for summary in summaries if summary.lifecycle == "stopped")
    assert resumed.parent is None
    assert resumed.last_revision == 2
    with RunCatalog(root).open_attempt(resumed.ref.attempt_id) as archive:
        assert archive.checkpoint(0).driver_cursor["next_tick"] == 1


def test_cli_factory_failure_is_discoverable_and_releases_lease(tmp_path: Path) -> None:
    from living_world.archives import AttemptLease, RunCatalog

    root = tmp_path / "archives"

    def factory(repository: SQLiteRepository) -> SimulationEngine:
        raise ValueError("private factory")

    assert (
        main(
            ["run", str(_scenario(tmp_path)), "--archive-root", str(root)],
            engine_factory=factory,
        )
        == INVALID_CONFIGURATION
    )
    (summary,) = RunCatalog(root).attempts()
    assert summary.scenario == "runner-test"
    assert summary.lifecycle == "failed"
    assert summary.last_revision is None
    assert not AttemptLease.is_owned(summary.ref)


def test_parser_errors_never_reserve_and_inspect_never_reserves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from living_world import cli
    from living_world.archives import RunCatalog

    root = RunCatalog.default_root()
    with pytest.raises(SystemExit):
        main(["run", "--archive-root", str(root)])
    assert not root.exists()
    path = _scenario(tmp_path)
    database = tmp_path / "world.db"
    assert main(["run", str(path), "--database", str(database)]) == 0
    before = RunCatalog(root).attempts()
    monkeypatch.setattr(cli, "_serve_inspection", lambda engine, port: None)
    assert main(["inspect", str(path), "--database", str(database)]) == 0
    assert RunCatalog(root).attempts() == before


@pytest.mark.parametrize("failure", ["step", "mirror"])
def test_cli_custom_engine_failures_keep_archive_authoritative(
    tmp_path: Path, failure: str
) -> None:
    from living_world.archives import AttemptLease, RunCatalog

    class Engine(SimulationEngine):
        def step(self) -> None:
            if failure == "step":
                self.state.tick += 1
                raise RuntimeError("private partial tick")
            super().step()

        def save_world(self) -> None:
            raise RuntimeError("private mirror failure")

    root = tmp_path / "archives"
    assert main(
        [
            "run",
            str(_scenario(tmp_path)),
            "--database",
            str(tmp_path / "world.db"),
            "--archive-root",
            str(root),
            "--max-ticks",
            "1",
        ],
        engine_factory=Engine,
    ) == (SIMULATION_FAILURE if failure == "step" else PERSISTENCE_FAILURE)
    catalog = RunCatalog(root)
    (summary,) = catalog.attempts()
    assert summary.lifecycle == "failed"
    assert summary.last_revision == (0 if failure == "step" else 1)
    assert not AttemptLease.is_owned(summary.ref)
    with catalog.open_attempt(summary.ref.attempt_id) as archive:
        assert [entry.kind for entry in archive.entries()] == (
            ["candidate_aborted", "attempt_finished"]
            if failure == "step"
            else ["attempt_finished"]
        )


def test_run_does_not_import_uvicorn_and_default_database_is_mirror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import builtins

    from living_world.archives import RunCatalog

    original_import = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        assert not name.startswith("uvicorn")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.chdir(tmp_path)
    assert main(["run", str(_scenario(tmp_path)), "--max-ticks", "1"]) == 0
    assert SQLiteRepository("world.sqlite3", read_only=True).load_world().tick == 1
    (summary,) = RunCatalog(RunCatalog.default_root()).attempts()
    assert summary.tick == 1


def test_invalid_scenario_is_metadata_only_attempt(tmp_path: Path) -> None:
    from living_world.archives import RunCatalog

    path = tmp_path / "bad.yaml"
    path.write_text("schema_version: invalid")
    root = tmp_path / "archives"
    assert (
        main(["run", str(path), "--archive-root", str(root)]) == INVALID_CONFIGURATION
    )
    (summary,) = RunCatalog(root).attempts()
    assert summary.scenario == "uninitialized"
    assert summary.last_revision is None
    assert not (summary.ref.directory / "inputs.json").exists()


@pytest.mark.parametrize(
    "declaration", ["./world.yaml", ".//./world.yaml", "sub/../world.yaml"]
)
def test_cli_loader_valid_relative_definition_declarations(
    tmp_path: Path, declaration: str
) -> None:
    from living_world.archives import RunCatalog, load_retained_inputs
    from living_world.scenarios.scenario import YAMLScenarioLoader

    scenario = _scenario(tmp_path)
    (tmp_path / "sub").mkdir()
    scenario.write_text(
        scenario.read_text().replace(
            "definitions: world.yaml", f"definitions: {declaration}"
        )
    )
    expected = YAMLScenarioLoader().load(scenario)
    original = scenario.read_bytes()
    root = tmp_path / "archives"
    assert (
        main(
            [
                "run",
                str(scenario),
                "--database",
                str(tmp_path / "world.db"),
                "--archive-root",
                str(root),
                "--max-ticks",
                "1",
            ]
        )
        == 0
    )
    (summary,) = RunCatalog(root).attempts()
    retained = load_retained_inputs(summary.ref)
    assert retained.scenario_path.read_bytes() == original
    assert (
        YAMLScenarioLoader().load(retained.scenario_path).configuration_fingerprint
        == expected.configuration_fingerprint
    )


def test_cli_invalid_definitions_remain_configuration_failure(tmp_path: Path) -> None:
    from living_world.archives import RunCatalog

    scenario = _scenario(tmp_path)
    (tmp_path / "world.yaml").write_text("definitions: invalid\n")
    root, database = tmp_path / "archives", tmp_path / "world.db"
    assert (
        main(
            [
                "run",
                str(scenario),
                "--database",
                str(database),
                "--archive-root",
                str(root),
            ]
        )
        == INVALID_CONFIGURATION
    )
    (summary,) = RunCatalog(root).attempts()
    assert summary.scenario == "runner-test"
    assert summary.lifecycle == "failed"
    assert summary.last_revision is None
    assert not database.exists()


@pytest.mark.parametrize("kind", ["io", "corruption"])
def test_archive_failures_remain_persistence_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    from living_world.archives import ArchiveError, RunCatalog
    from living_world.runtime.legacy import LegacyArchiveSession

    def unavailable(*args: object, **kwargs: object) -> None:
        raise (
            OSError("archive IO")
            if kind == "io"
            else ArchiveError("archive corruption")
        )

    monkeypatch.setattr(LegacyArchiveSession, "retain", unavailable)
    root = tmp_path / "archives"
    assert (
        main(["run", str(_scenario(tmp_path)), "--archive-root", str(root)])
        == PERSISTENCE_FAILURE
    )
    (summary,) = RunCatalog(root).attempts()
    assert summary.lifecycle == "failed"
    assert summary.last_revision is None


def test_legacy_cli_archives_actual_continuous_intent(tmp_path: Path) -> None:
    from living_world.archives import RunCatalog

    class Stop:
        def stop_requested(self) -> bool:
            return True

    root = tmp_path / "archives"
    assert (
        main(
            [
                "run",
                str(_scenario(tmp_path)),
                "--continuous",
                "--archive-root",
                str(root),
                "--database",
                str(tmp_path / "w.db"),
            ],
            stop_control=Stop(),
        )
        == 0
    )
    ref = RunCatalog(root).attempts()[0].ref
    with RunCatalog(root).open_attempt(ref.attempt_id) as archive:
        assert archive.config.settings["limits"]["continuous"] is True
        assert archive.config.settings["limits"]["max_ticks"] is None
