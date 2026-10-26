"""Shared launch preparation without premature ownership or side effects."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from threading import Event

import pytest
from test_runtime_cli import live_args, provider
from test_runtime_service import wait_for

from living_world.archives import AttemptLease, RunCatalog
from living_world.cli import build_parser
from living_world.runtime import RuntimeStartupError, RuntimeState, entrypoints


def prepare(tmp_path, flags=(), *, callback=None):
    factory = getattr(entrypoints, "prepare_archived_launch", None)
    assert callable(factory), "shared prepared-launch factory is missing"
    args = build_parser().parse_args(["run", "--founders", "success", *flags])
    catalog = RunCatalog(tmp_path / "runs")
    announced = []
    launch = factory(args, catalog=catalog, on_reserved=callback or announced.append)
    return args, catalog, announced, launch


def test_prepare_has_no_archive_effect_and_copies_namespace(tmp_path):
    args, catalog, announced, launch = prepare(tmp_path)
    assert catalog.attempts() == ()
    assert launch.service.controller is None
    assert announced == []
    with pytest.raises(FrozenInstanceError):
        launch.service = None
    args.founders = "failure"
    args.max_ticks = 1
    args.save_every = 100
    controller = launch.launch(paused=True)
    try:
        assert controller.status().state is RuntimeState.PAUSED
        assert controller.status().tick == 0
        assert controller.published().revision == 0
        with catalog.open_attempt(announced[0].attempt_id) as archive:
            assert archive.config.settings["recorded_outcome"] == "success"
            assert archive.config.settings["limits"]["save_every"] == 1
            assert archive.config.settings["limits"]["max_ticks"] is None
        assert len(announced) == 1
    finally:
        launch.service.shutdown()


@pytest.mark.parametrize("invalid", [None, 0, 1, "true"])
def test_invalid_paused_does_not_consume_launch(tmp_path, invalid):
    _, catalog, _, launch = prepare(tmp_path)
    with pytest.raises(entrypoints.RuntimeCLIError) as failure:
        launch.launch(paused=invalid)
    assert (failure.value.exit_code, failure.value.reason) == (
        2,
        "invalid_configuration",
    )
    assert not catalog.attempts()
    controller = launch.launch(paused=True)
    try:
        assert controller.status().tick == 0
        with pytest.raises(entrypoints.RuntimeCLIError) as failure:
            launch.launch(paused=True)
        assert (failure.value.exit_code, failure.value.reason) == (
            2,
            "invalid_configuration",
        )
        assert len(catalog.attempts()) == 1
    finally:
        launch.service.shutdown()


def test_blocked_provider_exposes_service_and_rejects_concurrent_launch(tmp_path):
    with provider(block="GET") as (url, calls, entered):
        args = build_parser().parse_args(live_args(tmp_path / "runs", url))
        catalog = RunCatalog(tmp_path / "runs")
        factory = getattr(entrypoints, "prepare_archived_launch", None)
        assert callable(factory), "shared prepared-launch factory is missing"
        launch = factory(args, catalog=catalog, on_reserved=lambda ref: None)
        assert calls == [] and not catalog.attempts()
        with ThreadPoolExecutor() as pool:
            first = pool.submit(launch.launch, paused=True)
            assert entered.wait(3)
            try:
                second = pool.submit(launch.launch, paused=False)
                with pytest.raises(entrypoints.RuntimeCLIError) as failure:
                    second.result(1)
                assert failure.value.reason == "invalid_configuration"
                launch.service.shutdown()
                with pytest.raises(RuntimeStartupError) as failure:
                    first.result(3)
                assert failure.value.code == "cancelled"
                with pytest.raises(entrypoints.RuntimeCLIError):
                    launch.launch(paused=True)
                assert len(catalog.attempts()) == 1
                assert calls == ["GET"]
            finally:
                launch.service.shutdown()


@pytest.mark.parametrize(
    "outcome,tick,digest",
    [
        (
            "success",
            10,
            "08e45db464eeec34249d8e5349849f0a4cd03cea299e1f43836547960785bd09",
        ),
        (
            "stall",
            5,
            "1ac4b3d42faab2697464169bf184299e260309a033581bafd4d0eb17b953fee0",
        ),
        (
            "failure",
            13,
            "1bf0b8f37ff43a13b8c6ad0e63327844c0196d73b39e817eda2ed02d4b046dc6",
        ),
    ],
)
def test_recorded_launch_matches_canonical_worlds(tmp_path, outcome, tick, digest):
    _, catalog, announced, launch = prepare(tmp_path, ["--founders", outcome])
    controller = launch.launch(paused=False)
    try:
        status = wait_for(controller, lambda status: status.state.terminal, timeout=8)
        assert status.state is RuntimeState.COMPLETED and status.tick == tick
        assert controller.published().snapshot.digest == digest
        assert controller.published().driver_cursor["mode"] == "recorded"
    finally:
        launch.service.shutdown()
    with catalog.open_attempt(announced[0].attempt_id) as archive:
        assert archive.lifecycle()[-1]["state"] == "completed"
        assert archive.entries()[-1].kind == "attempt_finished"
        assert archive.entries()[-1].payload["outcome"] == (
            {
                "stall": None,
                "success": "settlement_success",
                "failure": "founding_failure",
            }[outcome]
        )


@pytest.mark.parametrize(
    "flags,maximum,continuous,cadence",
    [
        ([], 5, False, 1),
        (["--max-ticks", "2", "--save-every", "3"], 2, False, 3),
        (["--continuous"], None, True, 1),
    ],
)
def test_stall_limits(tmp_path, flags, maximum, continuous, cadence):
    _, catalog, announced, launch = prepare(tmp_path, ["--founders", "stall", *flags])
    launch.launch(paused=True)
    try:
        with catalog.open_attempt(announced[0].attempt_id) as archive:
            assert archive.config.settings["limits"] == {
                "max_ticks": maximum,
                "continuous": continuous,
                "save_every": cadence,
            }
    finally:
        launch.service.shutdown()


def test_recorded_handoff_is_unsettled_and_unleased(tmp_path, monkeypatch):
    original = entrypoints.RuntimeService.start
    seen = []

    def start(service, config, inputs, *, paused):
        ref = service.catalog.attempts()[0].ref
        with AttemptLease(ref), service.catalog.open_attempt(ref.attempt_id) as archive:
            assert archive.latest_revision is None
            assert not archive.entries() and not archive.lifecycle()
        seen.append(ref)
        return original(service, config, inputs, paused=paused)

    monkeypatch.setattr(entrypoints.RuntimeService, "start", start)
    _, _, announced, launch = prepare(tmp_path)
    launch.launch(paused=True)
    try:
        assert announced == seen
    finally:
        launch.service.shutdown()


def test_retention_failure_has_one_failed_identity_and_consumes_launch(
    tmp_path, monkeypatch
):
    def fail(*args, **kwargs):
        raise OSError("PRIVATE retention failure")

    monkeypatch.setattr(entrypoints.LegacyArchiveSession, "retain", fail)
    _, catalog, announced, launch = prepare(tmp_path)
    with pytest.raises(entrypoints.RuntimeCLIError) as failure:
        launch.launch(paused=True)
    assert failure.value.reason == "initialization_failed"
    assert failure.value.exit_code == 4
    assert announced == []
    assert len(catalog.attempts()) == 1
    ref = failure.value.ref
    assert ref == catalog.attempts()[0].ref
    with AttemptLease(ref), catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.lifecycle()[-1]["state"] == "failed"
        assert archive.latest_revision is None
    with pytest.raises(entrypoints.RuntimeCLIError):
        launch.launch(paused=True)
    assert len(catalog.attempts()) == 1


@pytest.mark.parametrize("mode", ["resume", "fork", "replay"])
def test_linked_launch_preserves_initial_checkpoint_and_source_bytes(
    tmp_path, monkeypatch, mode
):
    from living_world.runtime import service as service_module

    # A recorded source exercises resume/fork; journal replay requires a live source.
    catalog = RunCatalog(tmp_path / "runs")
    if mode == "replay":
        with provider() as (url, _, _):
            args = build_parser().parse_args(
                [
                    *live_args(catalog.root, url),
                    "--max-ticks",
                    "1",
                    "--save-every",
                    "3",
                ]
            )
            source_launch = entrypoints.prepare_archived_launch(
                args, catalog=catalog, on_reserved=lambda ref: None
            )
            controller = source_launch.launch(paused=False)
            wait_for(controller, lambda status: status.state.terminal)
            source_launch.service.shutdown()
    else:
        _, catalog, _, source_launch = prepare(
            tmp_path, ["--save-every", "3", "--max-ticks", "2"]
        )
        controller = source_launch.launch(paused=False)
        wait_for(controller, lambda status: status.state.terminal)
        source_launch.service.shutdown()
    source = controller.status().attempt
    with catalog.open_attempt(source.attempt_id) as archive:
        checkpoint = archive.checkpoint()
        expected = archive.checkpoint(0) if mode == "replay" else checkpoint
        config = archive.config
    before = {p: p.read_bytes() for p in source.directory.rglob("*") if p.is_file()}
    args = build_parser().parse_args(
        [
            "run",
            f"--{mode}-attempt",
            source.attempt_id,
            "--checkpoint",
            str(checkpoint.revision),
            "--database",
            str(tmp_path / "mirror.db"),
        ]
    )
    mirrors = []
    original = service_module.write_checkpoint_mirror

    def mirror(checkpoint, *args, **kwargs):
        mirrors.append(checkpoint.revision)
        return original(checkpoint, *args, **kwargs)

    monkeypatch.setattr(service_module, "write_checkpoint_mirror", mirror)
    cadences = []
    original_service = entrypoints.RuntimeService

    class ObservedService(original_service):
        def __init__(self, *args, **kwargs):
            cadences.append(kwargs["save_every"])
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(entrypoints, "RuntimeService", ObservedService)
    launch = entrypoints.prepare_archived_launch(
        args, catalog=catalog, on_reserved=lambda ref: None
    )
    # Defensive copying also applies to source selection and checkpoint.
    args.resume_attempt = args.fork_attempt = args.replay_attempt = "not-an-id"
    args.checkpoint = 99999
    child = launch.launch(paused=True)
    try:
        publication = child.published()
        assert publication.snapshot == expected.snapshot
        assert publication.driver_cursor == expected.driver_cursor
        assert publication.feedback_cursor == expected.feedback_cursor
        if mode != "replay":
            with catalog.open_attempt(child.status().attempt.attempt_id) as archive:
                assert archive.config == config
        assert mirrors == [publication.revision]
        assert cadences == [3]
    finally:
        launch.service.shutdown()
    assert before == {
        p: p.read_bytes() for p in source.directory.rglob("*") if p.is_file()
    }


def test_materialization_failure_consumes_launch_before_reservation(
    tmp_path, monkeypatch
):
    def fail():
        raise OSError("private asset path")

    _, catalog, _, launch = prepare(tmp_path)
    monkeypatch.setattr(entrypoints, "materialize_founders_assets", fail)
    with pytest.raises(OSError):
        launch.launch(paused=True)
    with pytest.raises(entrypoints.RuntimeCLIError):
        launch.launch(paused=True)
    assert not catalog.attempts()


def test_reservation_failure_preserves_allocated_identity(tmp_path, monkeypatch):
    from living_world.archives import ArchiveReservationError

    original = entrypoints.LegacyArchiveSession
    reserved = []

    def fail(catalog, config):
        session = original(catalog, config)
        reserved.append(session.ref)
        raise ArchiveReservationError(session.ref)

    monkeypatch.setattr(entrypoints, "LegacyArchiveSession", fail)
    _, catalog, announced, launch = prepare(tmp_path)
    with pytest.raises(ArchiveReservationError) as failure:
        launch.launch(paused=True)
    assert failure.value.ref == reserved[0]
    assert len(catalog.attempts()) == 1 and announced == []


def test_live_prepared_config_is_defensive_and_unpaused_runs(tmp_path):
    with provider() as (url, calls, _):
        args = build_parser().parse_args(
            [*live_args(tmp_path / "runs", url), "--max-requests", "1"]
        )
        catalog = RunCatalog(tmp_path / "runs")
        launch = entrypoints.prepare_archived_launch(
            args, catalog=catalog, on_reserved=lambda ref: None
        )
        args.model = "missing"
        args.base_url = "http://127.0.0.1:1"
        args.preset = None
        controller = launch.launch(paused=False)
        try:
            wait_for(controller, lambda status: status.state.terminal)
            assert calls == ["GET", "POST"]
            with catalog.open_attempt(
                controller.status().attempt.attempt_id
            ) as archive:
                assert archive.config.settings["provider"]["model"] == "tiny:latest"
        finally:
            launch.service.shutdown()


def test_recorded_enter_failure_settles_and_closes_usable_handle(tmp_path, monkeypatch):
    original = entrypoints.LegacyArchiveSession.__enter__

    def fail(session):
        original(session)
        raise OSError("private entering failure")

    monkeypatch.setattr(entrypoints.LegacyArchiveSession, "__enter__", fail)
    _, catalog, _, launch = prepare(tmp_path)
    with pytest.raises(entrypoints.RuntimeCLIError) as failure:
        launch.launch(paused=True)
    ref = failure.value.ref
    assert failure.value.reason == "initialization_failed"
    with AttemptLease(ref), catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.lifecycle()[-1]["reason"] == "initialization_failed"


def test_live_retention_failure_has_one_setup_identity(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("private retention failure")

    monkeypatch.setattr(entrypoints, "retain_inputs", fail)
    args = build_parser().parse_args(live_args(tmp_path / "runs", "http://127.0.0.1:1"))
    catalog = RunCatalog(tmp_path / "runs")
    launch = entrypoints.prepare_archived_launch(
        args, catalog=catalog, on_reserved=lambda ref: None
    )
    with pytest.raises(entrypoints.RuntimeCLIError) as failure:
        launch.launch(paused=False)
    assert failure.value.reason == "setup_failed"
    assert catalog.attempts()[0].ref == failure.value.ref
    with AttemptLease(failure.value.ref):
        pass
    with pytest.raises(entrypoints.RuntimeCLIError):
        launch.launch(paused=False)
    assert len(catalog.attempts()) == 1


def test_recorded_checkpoint_only_setting_and_no_provider_configuration(tmp_path):
    _, catalog, announced, launch = prepare(tmp_path, ["--checkpoint-only"])
    controller = launch.launch(paused=True)
    try:
        with catalog.open_attempt(announced[0].attempt_id) as archive:
            settings = archive.config.settings
            assert settings["launch_source"] == "cli"
            assert settings["driver_format"] == 1
            assert settings["finalize_proposals"] is False
            assert "provider" not in settings
        assert controller.status().tick == 0
    finally:
        launch.service.shutdown()


def test_continuous_stall_advances_beyond_default_limit(tmp_path):
    _, _, _, launch = prepare(tmp_path, ["--founders", "stall", "--continuous"])
    controller = launch.launch(paused=False)
    try:
        status = wait_for(controller, lambda status: status.tick >= 6)
        assert not status.state.terminal
    finally:
        launch.service.shutdown()


@pytest.mark.parametrize("mode", ["recorded", "live"])
@pytest.mark.parametrize("during_retention", [False, True])
def test_preowner_shutdown_settles_same_attempt(
    tmp_path, monkeypatch, mode, during_retention
):
    retained, release = Event(), Event()
    with provider() as (url, calls, _):
        flags = (
            ["run", "--founders", "success"]
            if mode == "recorded"
            else live_args(tmp_path / "runs", url)
        )
        args = build_parser().parse_args(flags)
        catalog = RunCatalog(tmp_path / "runs")
        announced = []
        launch = entrypoints.prepare_archived_launch(
            args, catalog=catalog, on_reserved=announced.append
        )
        if during_retention:
            original = (
                entrypoints.retain_inputs
                if mode == "live"
                else entrypoints.LegacyArchiveSession.retain
            )

            def retain(*args, **kwargs):
                inputs = original(*args, **kwargs)
                retained.set()
                assert release.wait(3)
                return inputs

            if mode == "live":
                monkeypatch.setattr(entrypoints, "retain_inputs", retain)
            else:
                monkeypatch.setattr(entrypoints.LegacyArchiveSession, "retain", retain)
            with ThreadPoolExecutor() as pool:
                started = pool.submit(launch.launch, paused=True)
                try:
                    assert retained.wait(3)
                    launch.service.shutdown()
                finally:
                    release.set()
                with pytest.raises(RuntimeStartupError) as failure:
                    started.result(3)
        else:
            launch.service.shutdown()
            with pytest.raises(RuntimeStartupError) as failure:
                launch.launch(paused=True)
        assert failure.value.code == "service_closed"
        ref = failure.value.ref
        assert ref is not None
        assert len(catalog.attempts()) == 1
        assert catalog.attempts()[0].ref == ref
        assert catalog.attempts()[0].lifecycle == "failed"
        assert catalog.attempts()[0].last_revision is None
        assert announced == [] and calls == []
        assert launch.service.controller is None
        with AttemptLease(ref):
            pass
        with pytest.raises(entrypoints.RuntimeCLIError):
            launch.launch(paused=True)
        assert len(catalog.attempts()) == 1


@pytest.mark.parametrize("phase", ["live_settle", "recorded_settle", "recorded_close"])
def test_preowner_cleanup_failure_preserves_identity(tmp_path, monkeypatch, phase):
    def fail(*args, **kwargs):
        raise OSError("private cleanup failure")

    catalog = RunCatalog(tmp_path / "runs")
    flags = (
        ["run", "--founders", "success"]
        if phase.startswith("recorded")
        else live_args(catalog.root, "http://127.0.0.1:1")
    )
    if phase == "live_settle":
        monkeypatch.setattr(catalog, "fail_setup", fail)
    elif phase == "recorded_settle":
        monkeypatch.setattr(entrypoints.LegacyArchiveSession, "fail", fail)
    else:
        original = entrypoints.LegacyArchiveSession.close
        closes = []

        def close(session):
            original(session)
            closes.append(session.ref)
            if len(closes) == 2:
                fail()

        monkeypatch.setattr(entrypoints.LegacyArchiveSession, "close", close)
    launch = entrypoints.prepare_archived_launch(
        build_parser().parse_args(flags),
        catalog=catalog,
        on_reserved=lambda ref: pytest.fail("premature announcement"),
    )
    launch.service.shutdown()
    with pytest.raises(entrypoints.RuntimeCLIError) as failure:
        launch.launch(paused=True)
    assert (failure.value.exit_code, failure.value.reason) == (4, "archive_failed")
    assert failure.value.ref == catalog.attempts()[0].ref
    assert len(catalog.attempts()) == 1
    with AttemptLease(failure.value.ref):
        pass
    with pytest.raises(entrypoints.RuntimeCLIError):
        launch.launch(paused=True)


@pytest.mark.parametrize("retention_failed", [False, True])
def test_initial_recorded_close_failure_keeps_identity(
    tmp_path, monkeypatch, retention_failed
):
    original = entrypoints.LegacyArchiveSession.close

    def close(session):
        original(session)
        raise OSError("private initial close failure")

    if retention_failed:

        def retain(*args, **kwargs):
            raise OSError("private retention failure")

        monkeypatch.setattr(entrypoints.LegacyArchiveSession, "retain", retain)
    monkeypatch.setattr(entrypoints.LegacyArchiveSession, "close", close)
    _, catalog, announced, launch = prepare(tmp_path)
    with pytest.raises(entrypoints.RuntimeCLIError) as failure:
        launch.launch(paused=True)
    assert (failure.value.exit_code, failure.value.reason) == (4, "archive_failed")
    assert len(catalog.attempts()) == 1
    assert failure.value.ref == catalog.attempts()[0].ref
    assert launch.service.controller is None and announced == []
    with pytest.raises(entrypoints.RuntimeCLIError):
        launch.launch(paused=True)
    assert len(catalog.attempts()) == 1
