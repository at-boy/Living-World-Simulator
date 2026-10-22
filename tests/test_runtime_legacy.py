from pathlib import Path

import pytest
from test_runner_cli import RecordingRepository, _scenario

from living_world.archives import ArchiveFormatError, AttemptConfig, RunCatalog
from living_world.repositories.world_snapshot import encode_world
from living_world.running import RunConfiguration, RunResult, ScenarioRunner
from living_world.runtime.legacy import LegacyArchiveSession, legacy_cursor
from living_world.scenarios.scenario import LoadedScenario
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState


def config(**settings: object) -> AttemptConfig:
    return AttemptConfig("recorded", "runner-test", 7, "test", settings)


def test_finalize_flag_closed_boolean() -> None:
    assert config(finalize_proposals=False).settings["finalize_proposals"] is False
    for value in (0, "true", None):
        with pytest.raises(ArchiveFormatError):
            config(finalize_proposals=value)
    with pytest.raises(ArchiveFormatError):
        AttemptConfig("ollama", "runner-test", 7, "test", {"finalize_proposals": True})


def test_session_complete_ticks_and_exact_payload(tmp_path: Path) -> None:
    catalog = RunCatalog(tmp_path / "archives")
    engine = SimulationEngine(RecordingRepository())
    path = _scenario(tmp_path)
    with LegacyArchiveSession(catalog, config()) as session:
        retained = session.retain(path, tape_path=None)
        result = ScenarioRunner(engine).run(
            retained.scenario_path, RunConfiguration(save_every=3), observer=session
        )
        assert session.last_revision == 4
        assert session.archive.checkpoint().snapshot == encode_world(engine.state)
        assert dict(session.archive.checkpoint().driver_cursor) == dict(
            legacy_cursor(engine)
        )
        session.succeed(result)
    (summary,) = catalog.attempts()
    assert summary.lifecycle == "completed"
    assert summary.last_revision == 4


def test_observer_validation_before_scenario_mutation(tmp_path: Path) -> None:
    engine = SimulationEngine(RecordingRepository())
    with pytest.raises(TypeError):
        ScenarioRunner(engine).run(
            _scenario(tmp_path), RunConfiguration(), observer=object()
        )
    assert engine.state.run_metadata is None


@pytest.mark.parametrize(
    "boundary", ["partial_step", "terminal", "finalizer", "mirror"]
)
def test_failures_keep_only_complete_boundaries(tmp_path: Path, boundary: str) -> None:
    from living_world.archives import AttemptLease
    from living_world.repositories.world_snapshot import decode_world
    from living_world.running import RunPersistenceError, RunSimulationError

    class Engine(SimulationEngine):
        def step(self) -> None:
            if boundary == "partial_step":
                self.state.tick += 1
                raise RuntimeError("private failure")
            super().step()

    class Repository(RecordingRepository):
        def save_world(self, state: WorldState) -> None:
            if boundary == "mirror":
                raise RuntimeError("private mirror")
            super().save_world(state)

    class Preparation:
        def prepare(self, engine: SimulationEngine, scenario: LoadedScenario) -> None:
            pass

        def finish(
            self,
            engine: SimulationEngine,
            result: RunResult,
            *,
            finalize_proposals: bool,
        ) -> None:
            if boundary == "finalizer":
                engine.events.record(kind="uncommitted_finalization")
                raise ValueError("private finalizer")

    def terminal(engine: SimulationEngine) -> bool:
        if boundary == "terminal" and engine.state.tick == 1:
            raise ValueError("private predicate")
        return False

    catalog = RunCatalog(tmp_path / "archives")
    session = LegacyArchiveSession(catalog, config())
    engine = Engine(Repository())
    with pytest.raises((RunPersistenceError, RunSimulationError, ValueError)), session:
        retained = session.retain(
            _scenario(tmp_path, conditions="[custom]"), tape_path=None
        )
        ScenarioRunner(
            engine, Preparation(), terminal_conditions={"custom": terminal}
        ).run(retained.scenario_path, RunConfiguration(max_ticks=1), observer=session)
    (summary,) = catalog.attempts()
    assert summary.lifecycle == "failed"
    assert summary.last_revision == (0 if boundary == "partial_step" else 1)
    assert not AttemptLease.is_owned(session.ref)
    with catalog.open_attempt(session.ref.attempt_id) as archive:
        snapshot = decode_world(archive.checkpoint().snapshot)
        assert not any(
            event.kind == "uncommitted_finalization"
            for event in snapshot.events.values()
        )
        assert [entry.kind for entry in archive.entries()] == (
            ["attempt_finished"]
            if boundary == "mirror"
            else ["candidate_aborted", "attempt_finished"]
        )
        assert "private" not in str(archive.entries())


def test_unsettled_exit_and_setup_failure_release_lease(tmp_path: Path) -> None:
    from living_world.archives import AttemptLease

    catalog = RunCatalog(tmp_path / "archives")
    with LegacyArchiveSession(catalog, config()) as interrupted:
        pass
    assert not AttemptLease.is_owned(interrupted.ref)
    (summary,) = catalog.attempts()
    assert summary.lifecycle == "interrupted"
    assert summary.last_revision is None
    with (
        pytest.raises(RuntimeError, match="original"),
        LegacyArchiveSession(catalog, config()) as failed,
    ):
        raise RuntimeError("original")
    assert not AttemptLease.is_owned(failed.ref)
    with catalog.open_attempt(failed.ref.attempt_id) as archive:
        (entry,) = archive.entries()
        assert entry.payload["last_revision"] is None


def test_same_tick_finalization_revision_and_deduplication(tmp_path: Path) -> None:
    class Preparation:
        def prepare(self, engine: SimulationEngine, scenario: LoadedScenario) -> None:
            pass

        def finish(
            self,
            engine: SimulationEngine,
            result: RunResult,
            *,
            finalize_proposals: bool,
        ) -> None:
            engine.events.record(kind="finalized")

    with LegacyArchiveSession(RunCatalog(tmp_path / "archives"), config()) as session:
        retained = session.retain(_scenario(tmp_path), tape_path=None)
        engine = SimulationEngine(RecordingRepository())
        result = ScenarioRunner(engine, Preparation()).run(
            retained.scenario_path, RunConfiguration(max_ticks=0), observer=session
        )
        assert engine.state.tick == 0
        assert session.last_revision == 1
        session.finished(engine, result)
        assert session.last_revision == 1
        session.succeed(result)
        session.fail("legacy_run_failed")
        assert len(session.archive.entries()) == 1


def test_observer_exception_is_chained_persistence_error(tmp_path: Path) -> None:
    from living_world.running import RunPersistenceError

    failure = RuntimeError("private observer")

    class Observer:
        def initialized(
            self, engine: SimulationEngine, scenario: LoadedScenario
        ) -> None:
            raise failure

        def tick_completed(self, engine: SimulationEngine) -> None:
            raise AssertionError

        def finished(self, engine: SimulationEngine, result: RunResult) -> None:
            raise AssertionError

    repository = RecordingRepository()
    with pytest.raises(RunPersistenceError) as caught:
        ScenarioRunner(SimulationEngine(repository)).run(
            _scenario(tmp_path), RunConfiguration(), observer=Observer()
        )
    assert caught.value.__cause__ is failure
    assert repository.saved_ticks == []


def test_enter_failure_releases_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from living_world.archives import ArchiveError, AttemptLease

    catalog = RunCatalog(tmp_path / "archives")
    session = LegacyArchiveSession(catalog, config())

    def unavailable(*args: object, **kwargs: object) -> None:
        raise ArchiveError("writer unavailable")

    monkeypatch.setattr(catalog, "open_attempt", unavailable)
    with pytest.raises(ArchiveError, match="writer unavailable"):
        session.__enter__()
    assert not AttemptLease.is_owned(session.ref)
    with pytest.raises(ArchiveError, match="not entered"):
        _ = session.archive


def test_cleanup_audit_error_preserves_original_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from living_world.archives import ArchiveError, AttemptLease

    session = LegacyArchiveSession(RunCatalog(tmp_path / "archives"), config())
    with pytest.raises(ValueError, match="original"), session:

        def audit_failure(*args: object, **kwargs: object) -> None:
            raise ArchiveError("audit unavailable")

        monkeypatch.setattr(session.archive, "record", audit_failure)
        raise ValueError("original")
    assert not AttemptLease.is_owned(session.ref)


def test_generic_tape_archive_and_checkpoint_metadata(tmp_path: Path) -> None:
    from test_recorded_proposal_tapes import scenario_path

    from living_world.cli import main
    from living_world.repositories.sqlite_repository import SQLiteRepository

    path = scenario_path(tmp_path)
    scenario = SimulationEngine().load_scenario(path)
    tape = tmp_path / "tape.yaml"
    tape.write_text(
        "schema_version: 1\nscenario_key: camp\nscenario_fingerprint: "
        + scenario.configuration_fingerprint
        + "\nentries:\n  - sequence: 1\n    actor_label: founder\n    action: null\n    speech: Hello\n    rationale: Talk first\n"
    )
    root, database = tmp_path / "archives", tmp_path / "world.sqlite3"
    args = [
        "run",
        str(path),
        "--proposal-tape",
        str(tape),
        "--archive-root",
        str(root),
        "--database",
        str(database),
    ]
    assert main([*args, "--max-ticks", "0", "--checkpoint-only"]) == 0
    catalog = RunCatalog(root)
    (first,) = catalog.attempts()
    with catalog.open_attempt(first.ref.attempt_id) as archive:
        assert archive.config.settings["finalize_proposals"] is False
        cursor = archive.checkpoint().driver_cursor
        assert cursor["next_index"] == 0
        assert cursor["tape_fingerprint"] is not None
    assert main([*args, "--max-ticks", "1"]) == 0
    second = next(summary for summary in catalog.attempts() if summary.ref != first.ref)
    with catalog.open_attempt(second.ref.attempt_id) as archive:
        assert archive.config.settings["finalize_proposals"] is True
        assert archive.checkpoint().driver_cursor["next_index"] == 1
        assert archive.checkpoint().snapshot == encode_world(
            SQLiteRepository(str(database), read_only=True).load_world()
        )
        assert [entry.kind for entry in archive.entries()] == ["attempt_finished"]
