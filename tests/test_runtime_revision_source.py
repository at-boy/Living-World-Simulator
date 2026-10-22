"""Exact detached checkpoint inspection and safe read-only failures."""

from pathlib import Path
from uuid import uuid4

import pytest

from living_world.api.revision_source import RevisionSource, RevisionSourceError
from living_world.archives import RunCatalog


def test_source_safe_errors(tmp_path: Path) -> None:
    source = RevisionSource(RunCatalog(tmp_path / "missing"))
    for identity, revision in (
        ("../private", 0),
        (uuid4().hex, True),
        (uuid4().hex, -1),
        (uuid4().hex, 1.5),
        (uuid4().hex, 0),
    ):
        with pytest.raises(RevisionSourceError) as caught:
            source.open(identity, revision)
        assert caught.value.code == str(caught.value) == "not_found"
        assert caught.value.__cause__ is None
    assert not (tmp_path / "missing").exists()
    with pytest.raises(TypeError):
        RevisionSource(object())
    with pytest.raises(TypeError):
        RevisionSource(RunCatalog(tmp_path), controller=object())


def archive_world(tmp_path: Path, *, revisions: int = 2):
    from test_runtime_service import reserved

    from living_world.archives import AttemptLease
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime.recorded import RecordedScenarioComposition

    catalog, _, ref, inputs = reserved(tmp_path)
    engine = RecordedScenarioComposition(inputs, max_ticks=20).initialize()
    snapshots = []
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        for revision in range(revisions):
            snapshots.append(encode_world(engine.state))
            archive.commit(
                snapshots[-1],
                expected_revision=revision - 1 if revision else None,
                driver_cursor={},
                feedback_cursor={},
                entries=(),
            )
            engine.step()
    return catalog, ref, snapshots


def inventory(root: Path):
    return {
        str(path.relative_to(root)): (
            (path.read_bytes(), path.stat().st_mtime_ns) if path.is_file() else None
        )
        for path in root.rglob("*")
    }


def test_source_pins_complete_revision(tmp_path, monkeypatch):
    from living_world.api import revision_source
    from living_world.api.inspection import EngineWorldInspector
    from living_world.repositories.world_snapshot import encode_world

    catalog, ref, snapshots = archive_world(tmp_path)
    loader = revision_source.load_archived_inspection
    engines = []

    def checked(*args):
        engine = loader(*args)
        assert encode_world(engine.state) == snapshots[args[2]]
        engines.append(engine)
        return engine

    monkeypatch.setattr(revision_source, "load_archived_inspection", checked)
    source = RevisionSource(catalog)
    first, second = source.open(ref.attempt_id, 0), source.open(ref.attempt_id, 1)
    assert first.tick() == 0 and second.tick() == 1
    assert first is source.open(ref.attempt_id, 0)
    assert engines[0] is not engines[1]
    for inspector, engine in zip((first, second), engines):
        expected = EngineWorldInspector(engine)
        for method in (
            "world_summary",
            "entities",
            "definitions",
            "resources",
            "relationships",
            "events",
            "goals",
            "needs",
            "work_orders",
            "consequences",
        ):
            assert getattr(inspector, method)() == getattr(expected, method)()
    payload = first.entities()[0]
    payload["name"] = "Changed externally"
    assert first.entities()[0]["name"] == "Ada"


def test_source_lru_eviction_and_concurrent_readers(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from living_world.api import revision_source

    catalog, ref, _ = archive_world(tmp_path, revisions=10)
    loader = revision_source.load_archived_inspection
    loads = []

    def counted(*args):
        loads.append(args[2])
        return loader(*args)

    monkeypatch.setattr(revision_source, "load_archived_inspection", counted)
    source = RevisionSource(catalog)
    originals = [source.open(ref.attempt_id, n) for n in range(8)]
    assert source.open(ref.attempt_id, 0) is originals[0]
    with pytest.raises(RevisionSourceError):
        source.open(ref.attempt_id, 99)
    assert source.open(ref.attempt_id, 1) is originals[1]
    source.open(ref.attempt_id, 8)
    assert source.open(ref.attempt_id, 0) is originals[0]
    assert source.open(ref.attempt_id, 1) is originals[1]
    reloaded = source.open(ref.attempt_id, 2)
    assert reloaded is not originals[2]
    assert reloaded.world_summary() == originals[2].world_summary()
    with ThreadPoolExecutor(max_workers=8) as pool:
        views = list(pool.map(lambda _: source.open(ref.attempt_id, 9), range(24)))
    assert all(view is views[0] for view in views)
    assert loads.count(9) == 1 and loads.count(2) == 2


def test_source_is_read_only(tmp_path, monkeypatch):
    from living_world.archives import AttemptLease
    from living_world.cognition.ollama_cognition_client import OllamaCognitionClient
    from living_world.runtime import RunController, RuntimeService
    from living_world.runtime.broker import DecisionBroker
    from living_world.simulation.simulation_engine import SimulationEngine

    catalog, ref, _ = archive_world(tmp_path)
    before = inventory(catalog.root)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected mutation or provider access")

    for cls, name in (
        (SimulationEngine, "step"),
        (RunController, "__init__"),
        (RuntimeService, "__init__"),
        (DecisionBroker, "__init__"),
        (OllamaCognitionClient, "__init__"),
        (AttemptLease, "__enter__"),
    ):
        monkeypatch.setattr(cls, name, forbidden)
    source = RevisionSource(catalog)
    assert source.open(ref.attempt_id, 0).tick() == 0
    with pytest.raises(RevisionSourceError):
        source.open(ref.attempt_id, 99)
    assert inventory(catalog.root) == before
    # Missing lock files must remain absent: reads may probe, but never acquire leases.
    (ref.directory / "owner.lock").unlink()
    before = inventory(catalog.root)
    assert RevisionSource(catalog).open(ref.attempt_id, 1).tick() == 1
    assert inventory(catalog.root) == before


@pytest.mark.parametrize(
    "state,reason",
    [
        ("failed", "http_error"),
        ("stopped", "operator_stop"),
        ("interrupted", "interrupted"),
    ],
)
def test_source_keeps_unsuccessful_worlds_readable(tmp_path, state, reason):
    from living_world.archives import AttemptLease

    catalog, ref, _ = archive_world(tmp_path)
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        archive.record((), lifecycle=state, reason=reason)
    before = inventory(catalog.root)
    assert RevisionSource(catalog).open(ref.attempt_id, 1).tick() == 1
    assert inventory(catalog.root) == before


@pytest.mark.parametrize(
    "damage",
    ["input", "database", "missing_inputs", "missing_database", "duplicate", "schema"],
)
def test_source_corruption_is_safe_and_read_only(tmp_path, damage):
    import shutil
    import sqlite3

    catalog, ref, _ = archive_world(tmp_path)
    if damage == "input":
        from living_world.archives import load_retained_inputs

        load_retained_inputs(ref).scenario_path.write_text("private invalid contents")
    elif damage == "database":
        (ref.directory / "archive.sqlite3").write_bytes(b"private corrupt database")
    elif damage == "missing_inputs":
        (ref.directory / "inputs.json").unlink()
    elif damage == "missing_database":
        (ref.directory / "archive.sqlite3").unlink()
    elif damage == "duplicate":
        other = catalog.root / uuid4().hex / ref.attempt_id
        shutil.copytree(ref.directory, other)
    elif damage == "schema":
        # Tamper the stored schema: readers must reject it without repair.
        with sqlite3.connect(ref.directory / "archive.sqlite3") as connection:
            connection.execute("UPDATE world_snapshots SET schema_version=999")
            connection.execute("UPDATE checkpoints SET schema_version=999")
    before = inventory(catalog.root)
    with pytest.raises(RevisionSourceError) as caught:
        RevisionSource(catalog).open(ref.attempt_id, 0)
    assert caught.value.code == str(caught.value) == "archive_invalid"
    assert caught.value.__cause__ is None
    assert inventory(catalog.root) == before


def test_source_no_world_and_unrelated_corruption(tmp_path, monkeypatch):
    from living_world.archives import AttemptConfig, AttemptLease

    catalog, ref, _ = archive_world(tmp_path)
    empty = catalog.reserve(AttemptConfig("recorded", "empty", 0, "test", {}))
    setup = catalog.reserve_setup(
        AttemptConfig("ollama", "empty", 0, "test", {"provider": {"model": "test"}})
    )
    with AttemptLease(setup):
        catalog.fail_setup(setup, "model_missing")
    for identity in (empty.attempt_id, setup.attempt_id):
        with pytest.raises(RevisionSourceError) as caught:
            RevisionSource(catalog).open(identity, 0)
        assert caught.value.code == "not_found"
    (empty.directory / "archive.sqlite3").write_bytes(b"invalid")
    assert RevisionSource(catalog).open(ref.attempt_id, 0).tick() == 0

    def denied(self):
        raise PermissionError("private root path")

    monkeypatch.setattr(RunCatalog, "attempts", denied)
    with pytest.raises(RevisionSourceError) as caught:
        RevisionSource(catalog).open(ref.attempt_id, 0)
    assert caught.value.code == str(caught.value) == "archive_invalid"


def test_source_while_owner_advances(tmp_path):
    from test_runtime_service import reserved, wait_for

    from living_world.archives import CommandEnvelope
    from living_world.runtime import RuntimeService, RuntimeState

    catalog, config, ref, inputs = reserved(tmp_path)
    service = RuntimeService(catalog)
    owner = service.start(config, inputs, paused=True)
    try:
        source = RevisionSource(catalog, controller=owner)
        first = source.open(ref.attempt_id, 0)
        before = first.world_summary(), first.entities(), first.events()
        service.submit(
            CommandEnvelope("step", "step", owner.status().state_version)
        ).result(2)
        wait_for(
            owner, lambda state: state.tick == 1 and state.state is RuntimeState.PAUSED
        )
        assert source.open(ref.attempt_id, 1).tick() == 1
        assert (first.world_summary(), first.entities(), first.events()) == before
        assert source.open(ref.attempt_id, 0) is first
        assert catalog.attempts()[0].lifecycle == "paused"
    finally:
        service.shutdown()


@pytest.mark.parametrize("mode", ["generic_taped", "canonical", "live_replay"])
def test_source_complete_mode_payloads(tmp_path, monkeypatch, mode):
    from living_world.api import revision_source
    from living_world.api.inspection import EngineWorldInspector
    from living_world.repositories.world_snapshot import encode_world

    if mode == "canonical":
        from test_runtime_recorded import drive, reserve

        from living_world.archives import AttemptLease, load_retained_inputs
        from living_world.runtime import RunController
        from living_world.runtime.recorded import (
            RecordedFoundersComposition,
            RecordedTickDriver,
        )

        catalog, ref = reserve(tmp_path / "runs", "stall")
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
        ):
            controller = RunController(
                archive,
                RecordedFoundersComposition(load_retained_inputs(ref)),
                RecordedTickDriver(),
                max_ticks=1,
                start_paused=False,
            )
            drive(controller)
            controller.close()
    elif mode == "generic_taped":
        from test_runtime_service import reserved

        from living_world.archives import retain_inputs
        from living_world.runtime import RuntimeService
        from living_world.scenarios.scenario import YAMLScenarioLoader

        catalog, config, _, inputs = reserved(tmp_path)
        scenario = YAMLScenarioLoader().load(inputs.scenario_path)
        tape = tmp_path / "tape.yaml"
        tape.write_text(
            f"schema_version: 1\nscenario_key: generic\nscenario_fingerprint: {scenario.configuration_fingerprint}\nentries:\n- sequence: 1\n  actor_label: actor\n  action: null\n  rationale: Watch.\n  speech: Wait.\n"
        )
        ref = catalog.reserve(config)
        inputs = retain_inputs(ref, inputs.scenario_path, tape_path=tape)
        service = RuntimeService(catalog)
        service.start(config, inputs, paused=True)
        service.shutdown()
    else:
        from test_runtime_cli import live_args, provider

        from living_world.cli import main

        root = tmp_path / "runs"
        with provider() as (url, calls, _):
            assert main([*live_args(root, url), "--max-requests", "1"]) == 0
        call_count = len(calls)
        catalog = RunCatalog(root)
        live = catalog.attempts()[0].ref
        assert (
            main(
                [
                    "run",
                    "--replay-attempt",
                    live.attempt_id,
                    "--archive-root",
                    str(root),
                ]
            )
            == 0
        )
        assert len(calls) == call_count
        ref = live
    loader = revision_source.load_archived_inspection
    inspected = []

    def checked(catalog, identity, revision):
        engine = loader(catalog, identity, revision)
        with catalog.open_attempt(identity) as archive:
            assert encode_world(engine.state) == archive.checkpoint(revision).snapshot
        inspected.append(engine)
        return engine

    monkeypatch.setattr(revision_source, "load_archived_inspection", checked)
    before = inventory(catalog.root)
    source = RevisionSource(catalog)
    summaries = [s for s in catalog.attempts() if s.last_revision is not None]
    for summary in summaries:
        for revision in {0, summary.last_revision}:
            view = source.open(summary.ref.attempt_id, revision)
            expected = EngineWorldInspector(inspected[-1])
            for method in (
                "world_summary",
                "entities",
                "definitions",
                "resources",
                "events",
                "work_orders",
                "consequences",
                "replay",
            ):
                assert getattr(view, method)() == getattr(expected, method)()
    assert inventory(catalog.root) == before


@pytest.mark.parametrize(
    "exit_code,reason", [(3, "incompatible_save"), (4, "archive_failed")]
)
def test_source_shared_loader_failure_does_not_evict(
    tmp_path, monkeypatch, exit_code, reason
):
    from living_world.api import revision_source
    from living_world.runtime.entrypoints import RuntimeCLIError

    catalog, ref, _ = archive_world(tmp_path, revisions=9)
    source = RevisionSource(catalog)
    views = [source.open(ref.attempt_id, revision) for revision in range(8)]

    def failed(*args):
        raise RuntimeCLIError(exit_code, reason)

    monkeypatch.setattr(revision_source, "load_archived_inspection", failed)
    before = inventory(catalog.root)
    with pytest.raises(RevisionSourceError) as caught:
        source.open(ref.attempt_id, 8)
    assert caught.value.code == str(caught.value) == "archive_invalid"
    assert caught.value.__cause__ is None
    assert all(
        source.open(ref.attempt_id, revision) is view
        for revision, view in enumerate(views)
    )
    assert inventory(catalog.root) == before


def test_source_cached_validation_and_owner_probe_diagnostic(tmp_path, monkeypatch):
    from living_world.archives import ArchiveError, AttemptLease

    catalog, ref, _ = archive_world(tmp_path)

    def unavailable(ref):
        raise ArchiveError("private owner diagnostic")

    monkeypatch.setattr(AttemptLease, "is_owned", unavailable)
    source = RevisionSource(catalog)
    first = source.open(ref.attempt_id, 0)
    assert first.tick() == 0
    (ref.directory / "inputs.json").write_text("tampered")
    before = inventory(catalog.root)
    assert source.open(ref.attempt_id, 0) is first
    with pytest.raises(RevisionSourceError) as caught:
        source.open(ref.attempt_id, 1)
    assert caught.value.code == "archive_invalid"
    assert inventory(catalog.root) == before


@pytest.mark.parametrize(
    "identity,revision",
    [
        ("00000000000000000000000000000000", 0),
        ("bc75e0b0-9987-489e-92c7-ad38940cba5b", 0),
        ("../secret", 0),
        ("", 0),
        (None, 0),
        (uuid4().hex, False),
        (uuid4().hex, "0"),
        (uuid4().hex, None),
    ],
)
def test_invalid_selection_never_touches_catalog(
    tmp_path, monkeypatch, identity, revision
):
    def forbidden(self):
        raise AssertionError("Invalid selection reached storage")

    monkeypatch.setattr(RunCatalog, "attempts", forbidden)
    with pytest.raises(RevisionSourceError) as caught:
        RevisionSource(RunCatalog(tmp_path / "absent")).open(identity, revision)
    assert caught.value.code == "not_found"
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("create_empty_database", [False, True])
def test_failed_reservation_without_world_is_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, create_empty_database: bool
) -> None:
    from living_world.api import revision_source
    from living_world.archives import (
        ArchiveError,
        ArchiveReservationError,
        AttemptArchive,
        AttemptConfig,
        AttemptLease,
    )
    from living_world.cognition.ollama_cognition_client import OllamaCognitionClient
    from living_world.runtime import RunController, RuntimeService
    from living_world.runtime.broker import DecisionBroker
    from living_world.simulation.simulation_engine import SimulationEngine

    catalog, good, _ = archive_world(tmp_path, revisions=8)
    source = RevisionSource(catalog)
    cached = [source.open(good.attempt_id, revision) for revision in range(8)]
    create = AttemptArchive.create

    def publication_failure(*args: object, **kwargs: object) -> None:
        if create_empty_database:
            create(*args, **kwargs).close()
        raise ArchiveError("private publication failure")

    monkeypatch.setattr(AttemptArchive, "create", publication_failure)
    with pytest.raises(ArchiveReservationError) as reserved:
        catalog.reserve(AttemptConfig("recorded", "uninitialized", 0, "test", {}))
    ref = reserved.value.ref
    summary = next(item for item in catalog.attempts() if item.ref == ref)
    assert summary.lifecycle == "failed"
    assert summary.last_revision is None and summary.tick is None
    assert summary.mode == "recorded"
    assert summary.failure_code == "archive_initialization_failed"
    assert (ref.directory / "archive.sqlite3").exists() is create_empty_database
    forbidden_calls: list[str] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        forbidden_calls.append("unexpected reconstruction, ownership or execution")
        raise AssertionError(forbidden_calls[-1])

    monkeypatch.setattr(revision_source, "load_archived_inspection", forbidden)
    for cls, name in (
        (SimulationEngine, "step"),
        (RunController, "__init__"),
        (RuntimeService, "__init__"),
        (DecisionBroker, "__init__"),
        (OllamaCognitionClient, "__init__"),
        (AttemptLease, "__enter__"),
    ):
        monkeypatch.setattr(cls, name, forbidden)
    before = inventory(catalog.root)
    with pytest.raises(RevisionSourceError) as caught:
        source.open(ref.attempt_id, 0)
    assert caught.value.code == str(caught.value) == "not_found"
    assert caught.value.__cause__ is None
    assert all(
        source.open(good.attempt_id, revision) is view
        for revision, view in enumerate(cached)
    )
    assert forbidden_calls == []
    assert inventory(catalog.root) == before
