"""Runtime service ownership, admission and cleanup at real archive boundaries."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from living_world.archives import (
    AttemptConfig,
    AttemptLease,
    CommandEnvelope,
    RunCatalog,
    retain_inputs,
)
from living_world.runtime import RuntimeState


def reserved(tmp_path: Path, *, limits=None):
    (tmp_path / "world.yaml").write_text("definitions:\n  - key: person\n")
    path = tmp_path / "scenario.yaml"
    path.write_text("""schema_version: 1
key: generic
seed: 7
definitions: world.yaml
run:
  max_ticks: 3
  terminal_conditions: [tick_limit]
entities:
  - label: actor
    definition: person
    name: Ada
relationships: []
""")
    catalog = RunCatalog(tmp_path / "runs")
    config = AttemptConfig("recorded", "generic", 7, "test", {"limits": limits or {}})
    ref = catalog.reserve(config)
    return catalog, config, ref, retain_inputs(ref, path, tape_path=None)


def wait_for(controller, predicate, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        status = controller.status()
        if predicate(status):
            return status
        time.sleep(0.005)
    raise AssertionError(controller.status())


def test_service_same_attempt_owner_and_durable_step(tmp_path: Path) -> None:
    from living_world.runtime import RuntimeService, RuntimeStartupError

    catalog, config, ref, inputs = reserved(tmp_path)
    owner = []
    service = RuntimeService(
        catalog, on_reserved=lambda value: owner.append((value, threading.get_ident()))
    )
    controller = service.start(config, inputs, paused=True)
    try:
        assert service.catalog is catalog
        assert controller.status().attempt == ref
        assert owner == [(ref, controller._owner)]
        assert owner[0][1] != threading.get_ident()
        with pytest.raises(RuntimeError):
            controller.poll()
        with pytest.raises(RuntimeStartupError) as failure:
            service.start(config, inputs, paused=True)
        assert failure.value.code == "service_closed"
        envelope = CommandEnvelope("one", "step", controller.status().state_version)
        admission = service.submit(envelope).result(timeout=2)
        assert admission.status == "queued"
        wait_for(
            controller,
            lambda state: state.tick == 1 and state.state is RuntimeState.PAUSED,
        )
        with catalog.open_attempt(ref.attempt_id) as archive:
            assert archive.command("one").status == "applied"
        assert service.submit(envelope).result(timeout=2).status == "applied"
    finally:
        service.shutdown()
    assert len(catalog.attempts()) == 1
    with AttemptLease(ref):
        pass
    assert not service._thread.is_alive()


def test_submit_before_launch_and_shutdown_first(tmp_path: Path) -> None:
    from living_world.runtime import RuntimeService, RuntimeStartupError

    catalog, config, _ref, inputs = reserved(tmp_path)
    service = RuntimeService(catalog)
    with pytest.raises(RuntimeStartupError) as failure:
        service.submit(CommandEnvelope("early", "stop", 0)).result()
    assert failure.value.code == "service_not_ready"
    service.shutdown()
    with pytest.raises(RuntimeStartupError) as failure:
        service.start(config, inputs, paused=False)
    assert failure.value.code == "service_closed"
    assert len(catalog.attempts()) == 1


def test_shutdown_cancels_blocked_start_without_lock_or_callback_leak(
    tmp_path: Path,
) -> None:
    from living_world.runtime import RuntimeService, RuntimeStartupError

    catalog, config, ref, inputs = reserved(tmp_path)
    entered, release = threading.Event(), threading.Event()

    def callback(value):
        entered.set()
        assert release.wait(2)

    service = RuntimeService(catalog, on_reserved=callback)
    with ThreadPoolExecutor() as pool:
        started = pool.submit(service.start, config, inputs, paused=True)
        assert entered.wait(2)
        stopped = pool.submit(service.shutdown)
        release.set()
        stopped.result(timeout=3)
        with pytest.raises(RuntimeStartupError) as failure:
            started.result(timeout=3)
        assert failure.value.ref == ref
        assert failure.value.code == "cancelled"
    with AttemptLease(ref):
        pass


def test_callback_failure_safe_and_config_mismatch_untouched(tmp_path: Path) -> None:
    from living_world.runtime import RuntimeService, RuntimeStartupError

    catalog, config, ref, inputs = reserved(tmp_path)
    original = {
        p.relative_to(ref.directory): p.read_bytes()
        for p in ref.directory.rglob("*")
        if p.is_file()
    }
    wrong = AttemptConfig("recorded", "generic", 7, "different", {})
    service = RuntimeService(catalog)
    with pytest.raises(RuntimeStartupError) as failure:
        service.start(wrong, inputs, paused=True)
    service.shutdown()
    assert failure.value.ref == ref
    assert failure.value.code == "invalid_configuration"
    assert original == {
        p.relative_to(ref.directory): p.read_bytes()
        for p in ref.directory.rglob("*")
        if p.is_file()
    }

    def callback(value):
        raise RuntimeError("PRIVATE TEXT")

    service = RuntimeService(catalog, on_reserved=callback)
    with pytest.raises(RuntimeStartupError) as failure:
        service.start(config, inputs, paused=True)
    service.shutdown()
    assert failure.value.code == "setup_failed"
    assert "PRIVATE" not in str(failure.value)
    assert catalog.attempts()[0].lifecycle == "failed"


def test_standalone_loop_preserves_concurrent_stop_intent(tmp_path: Path) -> None:
    from test_runtime_controller import Composition, Driver

    from living_world.runtime import RunController, run_owner_loop

    class RacingStop(threading.Event):
        def __init__(self):
            super().__init__()
            self.first = True

        def is_set(self):
            result = super().is_set()
            if self.first:
                self.first = False
                self.set()
            return result

    stop = RacingStop()
    catalog, _config, ref, _inputs = reserved(tmp_path)
    done = threading.Event()

    def owner():
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
        ):
            controller = RunController(
                archive, Composition(), Driver(), max_ticks=None, start_paused=True
            )
            run_owner_loop(controller, stop_event=stop)
        done.set()

    thread = threading.Thread(target=owner, daemon=True)
    thread.start()
    thread.join(0.3)
    completed = done.is_set()
    stop.set()
    thread.join(1)
    assert completed


@pytest.mark.parametrize("mirror_failure", [False, True])
def test_service_shutdown_before_first_poll_stops_without_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mirror_failure: bool
) -> None:
    from living_world.repositories.sqlite_repository import SQLiteRepository
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime import RuntimeService, RuntimeStartupError
    from living_world.runtime import service as module

    catalog, config, ref, inputs = reserved(tmp_path, limits={"max_ticks": 0})
    created, released = threading.Event(), threading.Event()
    original = module.RunController

    class Controlled(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created.set()
            assert released.wait(3)

    monkeypatch.setattr(module, "RunController", Controlled)
    mirror = (
        tmp_path / "missing" / "world.sqlite3"
        if mirror_failure
        else tmp_path / "world.sqlite3"
    )
    service = RuntimeService(catalog, mirror_path=mirror)
    with ThreadPoolExecutor() as pool:
        started = pool.submit(service.start, config, inputs, paused=False)
        try:
            assert created.wait(2)
            stopped = pool.submit(service.shutdown)
            assert service._stop.wait(2)
        finally:
            released.set()
        stopped.result(3)
        with pytest.raises(RuntimeStartupError) as failure:
            started.result(3)
    assert failure.value.ref == ref
    assert failure.value.code == ("mirror_failed" if mirror_failure else "cancelled")
    with catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.lifecycle()[-1]["state"] == (
            "failed" if mirror_failure else "stopped"
        )
        assert archive.latest_revision == 0
        checkpoint = archive.checkpoint()
        assert checkpoint.driver_cursor["next_tick"] == 0
        if mirror_failure:
            assert archive.lifecycle()[-1]["reason"] == "mirror_failed"
            assert archive.entries()[-1].payload["last_revision"] == 0
            assert not mirror.exists()
        else:
            assert (
                encode_world(SQLiteRepository(str(mirror), read_only=True).load_world())
                == checkpoint.snapshot
            )
    service.shutdown()
    assert not service._thread.is_alive()
    with AttemptLease(ref):
        pass


def live_reserved(tmp_path: Path, base_url: str, *, limits=None, model="tiny"):
    from living_world.founders.assets import materialize_founders_assets
    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog = RunCatalog(tmp_path)
    with materialize_founders_assets() as assets:
        scenario = YAMLScenarioLoader().load(assets.scenario)
        config = AttemptConfig(
            "ollama",
            scenario.key,
            scenario.seed,
            "test",
            {
                "provider": {
                    "model": model,
                    "base_url": base_url,
                    "timeout_seconds": 0.5,
                },
                "limits": limits or {},
            },
        )
        ref = catalog.reserve_setup(config)
        inputs = retain_inputs(ref, assets.scenario, tape_path=None)
    return catalog, config, ref, inputs


@pytest.mark.parametrize(
    "behavior,code",
    [("normal", "model_missing"), ("hung", "timeout"), ("body", "timeout")],
)
def test_failed_preflight_has_one_retained_attempt_no_world_or_lease(
    tmp_path: Path, behavior: str, code: str
) -> None:
    from test_runtime_preflight import tags_server

    from living_world.runtime import RuntimeService, RuntimeStartupError

    with tags_server({"models": []}, behavior=behavior) as base:
        catalog, config, ref, inputs = live_reserved(tmp_path, base)
        service = RuntimeService(catalog)
        with pytest.raises(RuntimeStartupError) as failure:
            service.start(config, inputs, paused=True)
        service.shutdown()
    assert failure.value.ref == ref and failure.value.code == code
    assert len(catalog.attempts()) == 1
    assert catalog.attempts()[0].failure_code == code
    assert not (ref.directory / "archive.sqlite3").exists()
    with AttemptLease(ref):
        pass


def test_real_preflight_callback_before_get_and_setup_cancellation(
    tmp_path: Path,
) -> None:
    from test_runtime_preflight import tags_server

    from living_world.runtime import RuntimeService, RuntimeStartupError

    callback = threading.Event()
    requested = threading.Event()

    def get():
        assert callback.is_set()
        requested.set()

    with tags_server(
        {"models": [{"name": "tiny:latest", "digest": "a" * 64}]},
        behavior="hung",
        on_get=get,
    ) as base:
        catalog, config, ref, inputs = live_reserved(tmp_path, base)
        service = RuntimeService(catalog, on_reserved=lambda value: callback.set())
        with ThreadPoolExecutor() as pool:
            startup = pool.submit(service.start, config, inputs, paused=True)
            assert requested.wait(2)
            service.shutdown()
            with pytest.raises(RuntimeStartupError) as failure:
                startup.result(2)
            assert failure.value.code == "cancelled"
    assert catalog.attempts()[0].failure_code == "cancelled"
    with AttemptLease(ref):
        pass


def test_mirror_failure_is_at_committed_archive_boundary(tmp_path: Path) -> None:
    from living_world.runtime import RuntimeService, RuntimeStartupError

    catalog, config, ref, inputs = reserved(tmp_path)
    service = RuntimeService(
        catalog, mirror_path=tmp_path / "missing" / "world.sqlite3"
    )
    with pytest.raises(RuntimeStartupError) as failure:
        service.start(config, inputs, paused=True)
    service.shutdown()
    assert failure.value.code == "mirror_failed"
    with catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.latest_revision == 0
        assert archive.lifecycle()[-1]["state"] == "failed"
        assert archive.lifecycle()[-1]["reason"] == "mirror_failed"


def test_budget_stops_without_retry_while_provider_error_stays_paused(
    tmp_path: Path, monkeypatch
) -> None:
    from test_runtime_ollama_driver import ImmediateBroker
    from test_runtime_preflight import tags_server

    from living_world.runtime import RuntimeService, launch

    for name, budget, failure in [("budget", 1, None), ("failure", 40, "timeout")]:
        with tags_server(
            {"models": [{"name": "tiny:latest", "digest": "a" * 64}]}
        ) as base:
            catalog, config, ref, inputs = live_reserved(
                tmp_path / name, base, limits={"max_requests": budget}
            )
            monkeypatch.setattr(
                launch,
                "DecisionBroker",
                lambda failure=failure: ImmediateBroker(failure=failure),
            )
            service = RuntimeService(catalog)
            c = service.start(config, inputs, paused=False)
            try:
                status = wait_for(
                    c,
                    lambda status, name=name: (
                        status.state.terminal
                        if name == "budget"
                        else status.state is RuntimeState.PROVIDER_ERROR_PAUSED
                    ),
                )
                assert status.tick == 0
                assert status.state is (
                    RuntimeState.STOPPED
                    if name == "budget"
                    else RuntimeState.PROVIDER_ERROR_PAUSED
                )
                if name == "failure":
                    receipt = service.submit(
                        CommandEnvelope("resume", "resume", status.state_version)
                    ).result(2)
                    assert receipt.reason == "provider_retry_required"
                    service.submit(
                        CommandEnvelope("retry", "retry", c.status().state_version)
                    ).result(2)
                    wait_for(
                        c,
                        lambda status: status.state
                        is RuntimeState.PROVIDER_ERROR_PAUSED
                        and status.state_version > 3,
                    )
            finally:
                service.shutdown()
            with catalog.open_attempt(ref.attempt_id) as archive:
                if name == "budget":
                    assert (
                        archive.lifecycle()[-1]["reason"] == "request_budget_exhausted"
                    )
                    assert (
                        archive.entries()[-1].payload["outcome"]
                        == "request_budget_exhausted"
                    )


@pytest.mark.parametrize("completed", [False, True])
def test_final_mirror_failure_is_durable_and_archive_ahead(
    tmp_path: Path, monkeypatch, completed: bool
) -> None:
    from living_world.runtime import RuntimeService
    from living_world.runtime import service as module

    original = module.write_checkpoint_mirror

    def mirror(checkpoint, destination, *, attempt):
        if checkpoint.revision > 0:
            raise OSError("private mirror problem")
        original(checkpoint, destination, attempt=attempt)

    monkeypatch.setattr(module, "write_checkpoint_mirror", mirror)
    catalog, config, ref, inputs = reserved(
        tmp_path, limits={"max_ticks": 1} if completed else None
    )
    service = RuntimeService(catalog, mirror_path=tmp_path / "mirror.sqlite3")
    c = service.start(config, inputs, paused=not completed)
    if completed:
        wait_for(c, lambda status: status.state is RuntimeState.FAILED)
    service.shutdown()
    assert c.status().state is RuntimeState.FAILED
    assert c.status().error_code == "mirror_failed"
    with catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.latest_revision == 1
        assert archive.lifecycle()[-1]["reason"] == "mirror_failed"


def test_queue_fifo_conflict_cancel_and_shutdown_drain(
    tmp_path: Path, monkeypatch
) -> None:
    from living_world.runtime import CommandConflictError, RuntimeService
    from living_world.runtime import service as module

    original = module.RunController.submit
    entered, release = threading.Event(), threading.Event()
    order = []

    def submit(controller, envelope):
        if envelope.command_id == "one":
            entered.set()
            assert release.wait(2)
        order.append(envelope.command_id)
        return original(controller, envelope)

    monkeypatch.setattr(module.RunController, "submit", submit)
    catalog, config, ref, inputs = reserved(tmp_path)
    service = RuntimeService(catalog)
    c = service.start(config, inputs, paused=True)
    one = CommandEnvelope("one", "step", c.status().state_version)
    first = service.submit(one)
    assert entered.wait(2)
    second = service.submit(CommandEnvelope("two", "stop", c.status().state_version))
    cancelled = service.submit(
        CommandEnvelope("cancelled", "stop", c.status().state_version)
    )
    assert cancelled.cancel()
    with ThreadPoolExecutor() as pool:
        stopped = pool.submit(service.shutdown)
        assert service._stop.wait(2)
        release.set()
        stopped.result(3)
    assert first.result(1).status == "queued"
    assert second.result(1).status == "queued"
    assert order == ["one", "two"]
    with catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.command("one").status == "rejected"
        assert archive.command("two").status == "rejected"
        assert archive.command("cancelled") is None
    # A conflicting envelope stays on its Future and the owner remains usable.
    child = RuntimeService(catalog)
    c = child.resume(ref.attempt_id, paused=True)
    try:
        child.submit(CommandEnvelope("same", "step", c.status().state_version)).result(
            2
        )
        wait_for(
            c, lambda status: status.tick == 1 and status.state is RuntimeState.PAUSED
        )
        with pytest.raises(CommandConflictError):
            child.submit(
                CommandEnvelope("same", "stop", c.status().state_version)
            ).result(2)
        assert (
            child.submit(CommandEnvelope("stop", "stop", c.status().state_version))
            .result(2)
            .status
            == "queued"
        )
        wait_for(c, lambda status: status.state is RuntimeState.STOPPED)
        assert (
            child.submit(CommandEnvelope("terminal", "step", c.status().state_version))
            .result(2)
            .reason
            == "terminal_attempt"
        )
    finally:
        child.shutdown()


def test_shutdown_timeout_retains_owner_and_later_join_succeeds(tmp_path: Path) -> None:
    from living_world.runtime import RuntimeService, RuntimeStartupError

    catalog, config, ref, inputs = reserved(tmp_path)
    entered, release = threading.Event(), threading.Event()

    def callback(value):
        entered.set()
        release.wait(10)

    service = RuntimeService(catalog, on_reserved=callback)
    with ThreadPoolExecutor() as pool:
        started = pool.submit(service.start, config, inputs, paused=True)
        assert entered.wait(2)
        try:
            with pytest.raises(RuntimeStartupError) as failure:
                service.shutdown()
            assert failure.value.code == "service_failed" and failure.value.ref == ref
            assert service._thread.is_alive()
        finally:
            release.set()
            service.shutdown()
        with pytest.raises(RuntimeStartupError) as failure:
            started.result(2)
        assert failure.value.code == "cancelled"
    with AttemptLease(ref):
        pass


@pytest.mark.parametrize(
    "outcome,maximum,tick,digest",
    [
        (
            "success",
            None,
            10,
            "08e45db464eeec34249d8e5349849f0a4cd03cea299e1f43836547960785bd09",
        ),
        (
            "stall",
            5,
            5,
            "1ac4b3d42faab2697464169bf184299e260309a033581bafd4d0eb17b953fee0",
        ),
        (
            "failure",
            None,
            13,
            "1bf0b8f37ff43a13b8c6ad0e63327844c0196d73b39e817eda2ed02d4b046dc6",
        ),
    ],
)
def test_canonical_service_worlds_match_existing_pins(
    tmp_path: Path, outcome: str, maximum: int | None, tick: int, digest: str
) -> None:
    from living_world.founders.assets import materialize_founders_assets
    from living_world.runtime import RuntimeService
    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog = RunCatalog(tmp_path)
    with materialize_founders_assets() as assets:
        scenario = YAMLScenarioLoader().load(assets.scenario)
        config = AttemptConfig(
            "recorded",
            scenario.key,
            scenario.seed,
            "test",
            {"limits": {"max_ticks": maximum}},
        )
        ref = catalog.reserve(config)
        inputs = retain_inputs(ref, assets.scenario, tape_path=getattr(assets, outcome))
    service = RuntimeService(catalog)
    c = service.start(config, inputs, paused=False)
    try:
        status = wait_for(c, lambda status: status.state.terminal, timeout=8)
        assert status.state is RuntimeState.COMPLETED
        assert status.tick == tick
        assert c.published().snapshot.digest == digest
        assert c.published().driver_cursor["mode"] == "recorded"
    finally:
        service.shutdown()


def test_generic_tape_service_resume_and_continuous_fork(tmp_path: Path) -> None:
    from living_world.runtime import RuntimeService
    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog, config, _unused, inputs = reserved(tmp_path)
    # A distinct reserved attempt captures the generic scenario with a tape.
    scenario = YAMLScenarioLoader().load(inputs.scenario_path)
    tape = tmp_path / "tape.yaml"
    tape.write_text(f"""schema_version: 1
scenario_key: generic
scenario_fingerprint: {scenario.configuration_fingerprint}
entries:
- sequence: 1
  actor_label: actor
  action: null
  rationale: I will watch.
  speech: I can help.
- sequence: 2
  actor_label: actor
  action: null
  rationale: I will watch.
  speech: I can help.
- sequence: 3
  actor_label: actor
  action: null
  rationale: I will watch.
  speech: I can help.
""")
    ref = catalog.reserve(config)
    inputs = retain_inputs(ref, inputs.scenario_path, tape_path=tape)
    service = RuntimeService(catalog)
    c = service.start(config, inputs, paused=True)
    service.submit(CommandEnvelope("one", "step", c.status().state_version)).result(2)
    wait_for(c, lambda state: state.tick == 1 and state.state is RuntimeState.PAUSED)
    saved = c.published()
    service.shutdown()
    service = RuntimeService(catalog)
    c = service.resume(ref.attempt_id, saved.revision, paused=True)
    try:
        assert c.published().snapshot == saved.snapshot
        assert c.published().driver_cursor == saved.driver_cursor
        service.submit(
            CommandEnvelope("run", "resume", c.status().state_version)
        ).result(2)
        assert (
            wait_for(c, lambda state: state.state.terminal).state
            is RuntimeState.COMPLETED
        )
        assert c.status().tick == 4  # renewed default 3 ticks from saved tick 1
    finally:
        service.shutdown()
    config = AttemptConfig(
        "recorded", "generic", 7, "test", {"limits": {"continuous": True}}
    )
    service = RuntimeService(catalog)
    c = service.fork(ref.attempt_id, saved.revision, config=config, paused=False)
    try:
        wait_for(c, lambda state: state.tick >= 5)
        assert not c.status().state.terminal
    finally:
        service.shutdown()


@pytest.mark.parametrize("phase", ["controller", "published_setup"])
def test_failure_after_archive_creation_is_durably_settled(
    tmp_path: Path, monkeypatch, phase: str
) -> None:
    from living_world.runtime import RuntimeService, RuntimeStartupError
    from living_world.runtime import service as module

    if phase == "controller":
        catalog, config, ref, inputs = reserved(tmp_path)

        def constructor(*args, **kwargs):
            raise RuntimeError("PRIVATE")

        monkeypatch.setattr(module, "RunController", constructor)
        service = RuntimeService(catalog)
        with pytest.raises(RuntimeStartupError) as failure:
            service.start(config, inputs, paused=True)
        service.shutdown()
    else:
        from test_runtime_preflight import tags_server

        with tags_server(
            {"models": [{"name": "tiny:latest", "digest": "a" * 64}]}
        ) as url:
            catalog, config, ref, inputs = live_reserved(tmp_path, url)
            original = catalog.complete_setup

            def complete(*args, **kwargs):
                original(*args, **kwargs)
                raise OSError("PRIVATE")

            monkeypatch.setattr(catalog, "complete_setup", complete)
            service = RuntimeService(catalog)
            with pytest.raises(RuntimeStartupError) as failure:
                service.start(config, inputs, paused=True)
            service.shutdown()
    assert failure.value.code in ("service_failed", "archive_failed")
    with catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.lifecycle()[-1]["state"] == "failed"
        assert archive.latest_revision is None
    with AttemptLease(ref):
        pass


def test_unexpected_admission_failure_is_safe_and_stops_owner(
    tmp_path: Path, monkeypatch
) -> None:
    from living_world.runtime import RuntimeService, RuntimeStartupError
    from living_world.runtime import service as module

    catalog, config, _ref, inputs = reserved(tmp_path)
    service = RuntimeService(catalog)
    c = service.start(config, inputs, paused=True)

    def fail(*args, **kwargs):
        raise OSError("PRIVATE ADMISSION FAILURE")

    monkeypatch.setattr(module.RunController, "submit", fail)
    try:
        with pytest.raises(RuntimeStartupError) as failure:
            service.submit(
                CommandEnvelope("one", "step", c.status().state_version)
            ).result(2)
        assert failure.value.code == "service_failed"
        wait_for(c, lambda state: state.state is RuntimeState.FAILED)
    finally:
        service.shutdown()


def test_mirror_cadence_is_relative_to_committed_ticks(
    tmp_path: Path, monkeypatch
) -> None:
    from living_world.repositories.sqlite_repository import SQLiteRepository
    from living_world.repositories.world_snapshot import decode_world, encode_world
    from living_world.runtime import RuntimeService
    from living_world.runtime import service as module

    ticks = []
    original = module.write_checkpoint_mirror

    def mirror(checkpoint, *args, **kwargs):
        ticks.append(decode_world(checkpoint.snapshot).tick)
        return original(checkpoint, *args, **kwargs)

    monkeypatch.setattr(module, "write_checkpoint_mirror", mirror)
    catalog, config, _ref, inputs = reserved(tmp_path)
    path = tmp_path / "world.sqlite3"
    service = RuntimeService(catalog, mirror_path=path, save_every=2)
    c = service.start(config, inputs, paused=False)
    wait_for(c, lambda status: status.state.terminal)
    service.shutdown()
    assert ticks == [0, 2, 3]
    assert (
        encode_world(SQLiteRepository(str(path), read_only=True).load_world())
        == c.published().snapshot
    )


def test_admission_write_then_error_rejects_durable_queued_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    from living_world.archives import AttemptArchive
    from living_world.runtime import RuntimeService, RuntimeStartupError

    catalog, config, ref, inputs = reserved(tmp_path)
    service = RuntimeService(catalog)
    controller = service.start(config, inputs, paused=True)
    original = AttemptArchive.record

    def record(archive, entries, **kwargs):
        result = original(archive, entries, **kwargs)
        if any(entry.kind == "control_requested" for entry in entries):
            raise OSError("private post-commit failure")
        return result

    monkeypatch.setattr(AttemptArchive, "record", record)
    try:
        with pytest.raises(RuntimeStartupError):
            service.submit(
                CommandEnvelope("accepted", "step", controller.status().state_version)
            ).result(2)
        wait_for(controller, lambda status: status.state is RuntimeState.FAILED)
    finally:
        service.shutdown()
    with catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.command("accepted").status == "rejected"
