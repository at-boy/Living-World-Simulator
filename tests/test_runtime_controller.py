"""Durable owner boundary tests; fake IO never replaces the archive or engine."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest

from living_world.archives import (
    AttemptArchive,
    AttemptConfig,
    AttemptRef,
    Checkpoint,
    CommandEnvelope,
    CommandReceipt,
    JournalEntry,
)
from living_world.repositories.world_snapshot import WorldSnapshot, decode_world
from living_world.runtime import (
    CommandConflictError,
    DriverCommit,
    RunController,
    RuntimeState,
    RuntimeStatus,
)
from living_world.runtime.recorded import SnapshotRepository
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState


class Composition:
    def __init__(self, *, terminal: bool = False, fail: bool = False) -> None:
        self.initialized = 0
        self.terminal = terminal
        self.fail = fail

    def initialize(self) -> SimulationEngine:
        self.initialized += 1
        return SimulationEngine()

    def restore(self, snapshot: WorldSnapshot) -> SimulationEngine:
        engine = SimulationEngine(SnapshotRepository(snapshot))
        if self.fail:

            class Failure:
                def step(self, state: WorldState) -> None:
                    state.tick = 999
                    raise RuntimeError("private error")

            engine.register_system(Failure(), key="failure")
        return engine

    def terminal_condition(self, engine: SimulationEngine) -> str | None:
        return "done" if self.terminal else None

    def finalize(self, engine: SimulationEngine, *, stopped: bool) -> None:
        pass


class Preparation:
    activity = "waiting"
    error_code = "timeout"

    def __init__(self, engine: SimulationEngine, driver: Driver) -> None:
        self.engine, self.driver = engine, driver
        self.paused = False

    def poll(self) -> Literal["waiting", "ready", "provider_error", "paused"]:
        return (
            "paused"
            if self.paused and self.driver.result != "provider_error"
            else self.driver.result
        )

    def request_pause(self) -> None:
        self.paused = True

    def install(self) -> None:
        pass

    def finish_tick(self) -> DriverCommit:
        return DriverCommit({"tick": self.engine.state.tick}, {}, ())

    def close(self) -> None:
        pass


class Driver:
    def __init__(
        self, result: Literal["waiting", "ready", "provider_error"] = "ready"
    ) -> None:
        self.result = result

    def initialize(
        self, candidate: SimulationEngine, archive: AttemptArchive
    ) -> DriverCommit:
        return DriverCommit({"tick": candidate.state.tick}, {}, ())

    def prepare(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> Preparation:
        return Preparation(candidate, self)


def setup(
    tmp_path: Path,
    *,
    driver: Driver = None,
    composition: Composition | None = None,
    max_ticks: int | None = None,
    paused: bool = True,
) -> tuple[RunController, AttemptArchive]:
    archive = AttemptArchive.create(
        AttemptRef(uuid4().hex, uuid4().hex, tmp_path),
        AttemptConfig("recorded", "test", 1, "test", {}),
    )
    controller = RunController(
        archive,
        composition or Composition(),
        driver or Driver(),
        max_ticks=max_ticks,
        start_paused=paused,
    )
    return controller, archive


def drive(controller: RunController, count: int = 8) -> RuntimeStatus:
    for _ in range(count):
        controller.poll()
    return controller.status()


def command(
    controller: RunController,
    action: Literal["pause", "resume", "step", "stop", "retry"],
    name: str | None = None,
) -> CommandReceipt:
    return controller.submit(
        CommandEnvelope(name or action, action, controller.status().state_version)
    )


def test_deferred_initialization_and_latched_pause(tmp_path: Path) -> None:
    composition = Composition()
    controller, archive = setup(tmp_path, composition=composition, paused=False)
    assert composition.initialized == 0
    assert controller.status().revision is None
    receipt = command(controller, "pause")
    assert receipt.status == "queued"
    assert drive(controller).state is RuntimeState.PAUSED
    assert controller.status().tick == 0
    assert archive.command("pause").status == "applied"
    assert archive.checkpoint().driver_cursor == {"tick": 0}


def test_step_duplicate_conflict_and_queued_stale_step(tmp_path: Path) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    version = controller.status().state_version
    first = CommandEnvelope("first", "step", version)
    second = CommandEnvelope("second", "step", version)
    assert controller.submit(first).status == "queued"
    controller.submit(second)
    assert drive(controller).tick == 1
    receipt = controller.submit(first)
    assert receipt.status == "applied" and receipt.revision == 1
    assert archive.command("second").reason == "stale_state_version"
    with pytest.raises(CommandConflictError):
        controller.submit(CommandEnvelope("first", "resume", version))
    assert controller.status().tick == 1


def test_future_command_uses_actual_admission_version(tmp_path: Path) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    version = controller.status().state_version
    receipt = controller.submit(CommandEnvelope("future", "step", version + 999))
    assert receipt.status == "rejected" and receipt.state_version == version
    assert archive.command("future") == receipt
    assert controller.status().state_version == version


def test_waiting_keeps_publication_and_pause_cancels_unapplied_step(
    tmp_path: Path,
) -> None:
    driver = Driver("waiting")
    controller, archive = setup(tmp_path, driver=driver)
    drive(controller)
    old = controller.published()
    command(controller, "step")
    controller.poll()
    assert controller.published() == old
    command(controller, "pause")
    assert drive(controller).state is RuntimeState.PAUSED
    assert controller.status().tick == 0
    assert archive.command("step").reason == "operator_paused"
    assert archive.command("pause").status == "applied"


def test_provider_error_retry_retains_one_step(tmp_path: Path) -> None:
    driver = Driver("provider_error")
    controller, archive = setup(tmp_path, driver=driver)
    drive(controller)
    command(controller, "step")
    assert drive(controller).state is RuntimeState.PROVIDER_ERROR_PAUSED
    assert archive.command("step").status == "queued"
    assert command(controller, "resume").reason == "provider_retry_required"
    driver.result = "ready"
    command(controller, "retry")
    assert drive(controller).state is RuntimeState.PAUSED
    assert controller.status().tick == 1
    assert archive.command("step").status == "applied"
    assert archive.command("retry").status == "applied"


def test_pause_provider_error_then_retry_does_not_tick(tmp_path: Path) -> None:
    driver = Driver("waiting")
    controller, archive = setup(tmp_path, driver=driver)
    drive(controller)
    command(controller, "step")
    controller.poll()
    command(controller, "pause")
    driver.result = "provider_error"
    assert drive(controller).state is RuntimeState.PROVIDER_ERROR_PAUSED
    driver.result = "ready"
    command(controller, "retry")
    assert drive(controller).state is RuntimeState.PAUSED
    assert controller.status().tick == 0
    assert archive.command("step").reason == "operator_paused"


@pytest.mark.parametrize("terminal,limit", [(True, None), (False, 0)])
def test_zero_step_terminal_boundary(
    tmp_path: Path, terminal: bool, limit: int | None
) -> None:
    controller, _archive = setup(
        tmp_path, composition=Composition(terminal=terminal), max_ticks=limit
    )
    assert drive(controller).state is RuntimeState.COMPLETED
    assert controller.status().tick == 0
    assert command(controller, "stop").reason == "terminal_attempt"


def test_failed_mutating_tick_is_quarantined(tmp_path: Path) -> None:
    controller, archive = setup(tmp_path, composition=Composition(fail=True))
    drive(controller)
    old = controller.published()
    command(controller, "step")
    assert drive(controller).state is RuntimeState.FAILED
    assert controller.published() == old
    assert decode_world(archive.checkpoint().snapshot).tick == 0
    assert controller.status().error_code == "tick_failed"


def test_commit_failure_retains_prior_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    old = controller.published()

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("private storage")

    monkeypatch.setattr(archive, "commit", fail)
    command(controller, "step")
    assert drive(controller).state is RuntimeState.FAILED
    assert controller.published() == old
    assert archive.latest_revision == 0


def test_audit_failure_after_commit_publishes_real_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    command(controller, "step")
    original = archive.record

    def fail(entries: tuple[JournalEntry, ...], **kwargs: object) -> tuple[int, ...]:
        if archive.latest_revision == 1:
            raise RuntimeError("audit failed")
        return original(entries, **kwargs)

    monkeypatch.setattr(archive, "record", fail)
    assert drive(controller).state is RuntimeState.FAILED
    assert controller.status().error_code == "audit_failed"
    assert controller.published().revision == archive.latest_revision == 1
    assert archive.command("step").status == "applied"


def test_stop_and_read_thread_safety(tmp_path: Path) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    with ThreadPoolExecutor() as executor:
        assert executor.submit(controller.status).result().tick == 0
        assert executor.submit(controller.published).result().revision == 0
        with pytest.raises(RuntimeError):
            executor.submit(controller.poll).result()
    command(controller, "stop")
    assert drive(controller).state is RuntimeState.STOPPED
    assert archive.command("stop").status == "applied"
    ref = archive.ref
    controller.close()
    controller.close()
    with AttemptArchive.open(ref, read_only=True) as reopened:
        assert reopened.lifecycle()[-1]["state"] == "stopped"
        assert decode_world(reopened.checkpoint().snapshot).tick == 0


def test_publication_cache_evicts_only_complete_old_revisions(tmp_path: Path) -> None:
    controller, _archive = setup(tmp_path)
    drive(controller)
    for index in range(10):
        command(controller, "step", str(index))
        drive(controller)
    assert controller.status().tick == 10
    with pytest.raises(LookupError):
        controller.published(0)
    assert controller.published(3).revision == 3


def test_close_settles_queued_step_before_stopping(tmp_path: Path) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    command(controller, "step")
    ref = archive.ref
    controller.close()
    with AttemptArchive.open(ref, read_only=True) as reader:
        assert reader.command("step").reason == "operator_stopped"
        assert reader.lifecycle()[-1]["state"] == "stopped"
        assert decode_world(reader.checkpoint().snapshot).tick == 0


def test_initialization_failure_settles_latched_control(tmp_path: Path) -> None:
    class Broken(Composition):
        def initialize(self) -> SimulationEngine:
            raise RuntimeError("private setup text")

    controller, archive = setup(tmp_path, composition=Broken())
    command(controller, "pause")
    assert controller.poll().state is RuntimeState.FAILED
    assert archive.command("pause").reason == "initialization_failed"
    assert controller.status().revision is None


def test_restoration_mutation_fails_without_hiding_durable_boundary(
    tmp_path: Path,
) -> None:
    class Changed(Composition):
        def restore(self, snapshot: WorldSnapshot) -> SimulationEngine:
            engine = super().restore(snapshot)
            engine.state.tick += 1
            return engine

    controller, archive = setup(tmp_path, composition=Changed())
    drive(controller)
    old = controller.published()
    command(controller, "step")
    assert drive(controller).state is RuntimeState.FAILED
    assert controller.published() == old
    assert archive.latest_revision == 0


def test_stop_waiting_step_cancels_without_publishing_candidate(tmp_path: Path) -> None:
    driver = Driver("waiting")
    controller, archive = setup(tmp_path, driver=driver)
    drive(controller)
    command(controller, "step")
    controller.poll()
    assert controller.status().state is RuntimeState.AWAITING_MODEL
    command(controller, "stop")
    assert drive(controller).state is RuntimeState.STOPPED
    assert controller.status().tick == 0
    assert archive.command("step").reason == "operator_stopped"


def test_child_limit_counts_only_child_ticks(tmp_path: Path) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    command(controller, "step")
    drive(controller)
    parent = controller.published()
    # This unit fixture directly seeds an archive; recorded integration uses catalog.fork.
    child_ref = AttemptRef(uuid4().hex, uuid4().hex, tmp_path / "child")
    child_ref.directory.mkdir()
    child = AttemptArchive.create(child_ref, archive.config)
    child.commit(
        parent.snapshot,
        expected_revision=None,
        driver_cursor=parent.driver_cursor,
        feedback_cursor=parent.feedback_cursor,
        entries=(),
    )
    resumed = RunController(
        child, Composition(), Driver(), max_ticks=1, start_paused=False
    )
    assert drive(resumed).state is RuntimeState.COMPLETED
    assert resumed.status().tick == 2


@pytest.mark.parametrize("maximum", [True, -1, 1.5])
def test_controller_rejects_invalid_tick_bound(tmp_path: Path, maximum: object) -> None:
    archive = AttemptArchive.create(
        AttemptRef(uuid4().hex, uuid4().hex, tmp_path),
        AttemptConfig("recorded", "test", 1, "test", {}),
    )
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        RunController(
            archive, Composition(), Driver(), max_ticks=maximum, start_paused=True
        )


def test_reopened_stopped_attempt_remains_terminal(tmp_path: Path) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    command(controller, "stop")
    drive(controller)
    ref = archive.ref
    controller.close()
    reopened = AttemptArchive.open(ref)
    fresh = RunController(
        reopened, Composition(), Driver(), max_ticks=None, start_paused=False
    )
    assert fresh.poll().state is RuntimeState.STOPPED
    assert command(fresh, "resume").reason == "terminal_attempt"
    assert fresh.status().tick == 0


def test_failed_stop_resolves_its_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("private commit failure")

    monkeypatch.setattr(archive, "commit", fail)
    command(controller, "stop")
    assert drive(controller).state is RuntimeState.FAILED
    assert archive.command("stop").status == "rejected"


def test_owner_poll_dispatch_work_is_bounded(tmp_path: Path) -> None:
    controller, archive = setup(tmp_path)
    drive(controller)
    version = controller.status().state_version
    for index in range(100):
        controller.submit(CommandEnvelope(str(index), "step", version))
    controller.poll()
    assert archive.command("99").status == "queued"
    assert controller.status().tick == 0


def test_reopened_setup_failure_cannot_initialize_again(tmp_path: Path) -> None:
    class Broken(Composition):
        def initialize(self) -> SimulationEngine:
            raise RuntimeError("setup failed")

    controller, archive = setup(tmp_path, composition=Broken())
    assert controller.poll().state is RuntimeState.FAILED
    ref = archive.ref
    controller.close()
    reopened = AttemptArchive.open(ref)
    composition = Composition()
    fresh = RunController(
        reopened, composition, Driver(), max_ticks=None, start_paused=True
    )
    assert fresh.poll().state is RuntimeState.FAILED
    assert composition.initialized == 0
    assert fresh.status().revision is None


@pytest.mark.parametrize("broken", [False, True])
def test_close_before_initialization_settles_multiple_controls(
    tmp_path: Path, broken: bool
) -> None:
    class Broken(Composition):
        def initialize(self) -> SimulationEngine:
            raise RuntimeError("private setup failure")

    class NoPreparation(Driver):
        def prepare(
            self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
        ) -> Preparation:
            raise AssertionError("Shutdown must not start provider preparation.")

    controller, archive = setup(
        tmp_path,
        composition=Broken() if broken else Composition(),
        driver=NoPreparation(),
    )
    pause = command(controller, "pause")
    stop = command(controller, "stop")
    assert pause.status == stop.status == "queued"
    ref = archive.ref
    controller.close()
    with AttemptArchive.open(ref, read_only=True) as reopened:
        assert reopened.command("stop").reason == "stale_state_version"
        if broken:
            assert controller.status().state is RuntimeState.FAILED
            assert controller.status().error_code == "initialization_failed"
            assert reopened.latest_revision is None
            assert reopened.command("pause").reason == "initialization_failed"
        else:
            assert controller.status().state is RuntimeState.STOPPED
            assert controller.status().tick == 0
            assert reopened.command("pause").status == "applied"
            assert decode_world(reopened.checkpoint().snapshot).tick == 0
            assert reopened.lifecycle()[-1]["state"] == "stopped"
        assert reopened.command("pause").status != "queued"
        assert reopened.command("stop").status != "queued"


def test_initial_stop_precedes_terminal_when_requested(tmp_path: Path) -> None:
    controller, archive = setup(
        tmp_path, composition=Composition(terminal=True), max_ticks=0
    )
    controller = RunController(
        archive,
        Composition(terminal=True),
        Driver(),
        max_ticks=0,
        start_paused=False,
        initial_stop_precedes_terminal=True,
    )
    command(controller, "stop")
    assert controller.poll().state is RuntimeState.STOPPED
    assert controller.status().tick == 0
    controller.close()


def test_request_budget_stops_committed_world_with_reason(tmp_path: Path) -> None:
    class BudgetDriver(Driver):
        def prepare(self, candidate, base, archive):
            result = super().prepare(candidate, base, archive)
            result.error_code = "request_budget_exhausted"
            return result

    controller, archive = setup(
        tmp_path, driver=BudgetDriver("provider_error"), paused=False
    )
    controller.poll()
    controller.poll()
    assert hasattr(controller, "stop_for_budget")
    controller.stop_for_budget()
    assert controller.status().state is RuntimeState.STOPPED
    assert controller.status().tick == 0
    assert archive.lifecycle()[-1]["reason"] == "request_budget_exhausted"
    assert archive.entries()[-1].payload["outcome"] == "request_budget_exhausted"
    controller.close()
