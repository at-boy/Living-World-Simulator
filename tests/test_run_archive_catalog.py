"""Attempt identity, retained evidence, discovery and exclusive ownership."""

import json
import multiprocessing
from collections.abc import Mapping
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest

from living_world.archives import (
    ArchiveError,
    AttemptArchive,
    AttemptConfig,
    AttemptRef,
    Checkpoint,
)
from living_world.archives.assets import load_retained_inputs, retain_inputs
from living_world.archives.catalog import ArchiveReservationError, RunCatalog
from living_world.archives.lease import AttemptLease
from living_world.repositories.world_snapshot import encode_world
from living_world.state.world_state import WorldState

Mode = Literal["recorded", "ollama", "journal_replay"]


def config(
    mode: Mode = "recorded",
    *,
    scenario_key: str = "test",
    seed: int = 7,
    settings: Mapping[str, object] | None = None,
) -> AttemptConfig:
    return AttemptConfig(
        mode, scenario_key, seed, "rev", {} if settings is None else settings
    )


def sources(tmp_path: Path) -> Path:
    source = tmp_path / "source ?#"
    source.mkdir(exist_ok=True)
    (source / "defs ?#.yaml").write_text("definitions: []\n")
    path = source / "scenario ?#.yaml"
    path.write_text(
        'schema_version: 1\nkey: test\nseed: 7\ndefinitions: "defs ?#.yaml"\n'
    )
    return path


def initialized(tmp_path: Path) -> tuple[RunCatalog, AttemptRef, Checkpoint]:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    retain_inputs(ref, sources(tmp_path), tape_path=None)
    with AttemptLease(ref):
        archive = catalog.open_attempt(ref.attempt_id, read_only=False)
        state = WorldState()
        checkpoint = archive.commit(
            encode_world(state),
            expected_revision=None,
            driver_cursor={"offset": 4},
            feedback_cursor={"pending": ["yes"]},
            entries=(),
        )
    return (catalog, ref, checkpoint)


def _owner(ref: AttemptRef, connection: Connection) -> None:
    with AttemptLease(ref):
        connection.send("owned")
        connection.recv()


def test_empty_reads_and_defaults_do_not_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "absent"
    catalog = RunCatalog(root)
    assert catalog.attempts() == ()
    with pytest.raises(ArchiveError):
        catalog.open_attempt(uuid4().hex)
    assert not root.exists()
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert RunCatalog.default_root() == tmp_path / "living-world/runs"
    monkeypatch.setenv("XDG_STATE_HOME", "relative")
    assert RunCatalog.default_root() == Path.home() / ".local/state/living-world/runs"


def test_reservation_is_unique_closed_and_pre_world_failure_discoverable(
    tmp_path: Path,
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    first, second = (catalog.reserve(config()), catalog.reserve(config()))
    assert first.attempt_id != second.attempt_id
    assert first.directory == catalog.root / first.lineage_id / first.attempt_id
    with AttemptLease(first):
        catalog.open_attempt(first.attempt_id, read_only=False).record(
            (), lifecycle="failed", reason="scenario_invalid"
        )
    summary = next(x for x in catalog.attempts() if x.ref == first)
    assert summary.lifecycle == "failed" and summary.tick is None
    assert summary.failure_code == "scenario_invalid"
    assert summary.started_at is not None and summary.ended_at is not None
    assert set(json.loads((first.directory / "attempt.json").read_text())) == {
        "format",
        "lineage_id",
        "attempt_id",
        "config",
        "parent",
        "parent_journal",
        "reserved_at",
        "reservation_error",
    }


def test_creation_failure_keeps_reserved_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    def fail(*args: object, **kwargs: object) -> None:
        raise ArchiveError("failure")

    monkeypatch.setattr(AttemptArchive, "create", fail)
    catalog = RunCatalog(tmp_path / "runs")
    with pytest.raises(ArchiveReservationError) as error:
        catalog.reserve(config())
    (summary,) = catalog.attempts()
    assert summary.ref == error.value.ref
    assert summary.lifecycle == "failed" and summary.tick is None
    assert summary.failure_code == "archive_initialization_failed"


def test_incomplete_corrupt_future_attempts_do_not_hide_good(tmp_path: Path) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    good = catalog.reserve(config())
    incomplete = good.directory.parent / uuid4().hex
    incomplete.mkdir()
    future = catalog.reserve(config())
    manifest = future.directory / "attempt.json"
    data = json.loads(manifest.read_text())
    data["format"] = 99
    manifest.write_text(json.dumps(data))
    items = {item.ref.attempt_id: item for item in catalog.attempts()}
    assert items[incomplete.name].failure_code == "archive_incomplete"
    assert items[future.attempt_id].failure_code == "archive_invalid"
    assert items[good.attempt_id].mode == "recorded"
    with pytest.raises(ArchiveError):
        catalog.open_attempt(future.attempt_id)


def test_retained_inputs_are_exact_private_immutable_and_verified(
    tmp_path: Path,
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    original = scenario.read_bytes()
    retained = retain_inputs(ref, scenario, tape_path=None)
    assert retained.scenario_path.read_bytes() == original
    assert retained.definition_path.name == "defs ?#.yaml"
    assert retain_inputs(ref, scenario, tape_path=None) == retained
    scenario.unlink()
    assert load_retained_inputs(ref) == retained
    with pytest.raises(TypeError):
        retained.hashes["bad"] = "x"
    object_file = catalog.root / "objects" / next(iter(retained.hashes.values()))
    assert object_file.stat().st_ino != retained.scenario_path.stat().st_ino
    retained.definition_path.write_text("definitions: [changed]\n")
    with pytest.raises(ArchiveError):
        load_retained_inputs(ref)


@pytest.mark.parametrize("definition", ["../outside.yaml", "/tmp/outside.yaml"])
def test_retention_rejects_escaping_loader_paths(
    tmp_path: Path, definition: str
) -> None:
    ref = RunCatalog(tmp_path / "runs").reserve(config())
    scenario = sources(tmp_path)
    scenario.write_text(
        f"schema_version: 1\nkey: test\nseed: 7\ndefinitions: {definition}\n"
    )
    with pytest.raises(ArchiveError):
        retain_inputs(ref, scenario, tape_path=None)
    assert not (ref.directory / "inputs.json").exists()


def test_retention_rejects_symlink_and_config_mismatch(tmp_path: Path) -> None:
    ref = RunCatalog(tmp_path / "runs").reserve(config())
    scenario = sources(tmp_path)
    target = scenario.parent / "defs ?#.yaml"
    target.unlink()
    target.symlink_to(scenario)
    with pytest.raises(ArchiveError):
        retain_inputs(ref, scenario, tape_path=None)
    target.unlink()
    target.write_text("definitions: []\n")
    scenario.write_text(scenario.read_text().replace("seed: 7", "seed: 8"))
    with pytest.raises(ArchiveError):
        retain_inputs(ref, scenario, tape_path=None)


def test_divergent_retry_and_object_corruption_preserve_inputs(tmp_path: Path) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    retained = retain_inputs(ref, scenario, tape_path=None)
    original = retained.scenario_path.read_bytes()
    scenario.write_text(scenario.read_text() + "# changed\n")
    with pytest.raises(ArchiveError):
        retain_inputs(ref, scenario, tape_path=None)
    assert retained.scenario_path.read_bytes() == original
    (catalog.root / "objects" / next(iter(retained.hashes.values()))).write_bytes(
        b"bad"
    )
    other = catalog.reserve(config())
    scenario.write_bytes(original)
    with pytest.raises(ArchiveError):
        retain_inputs(other, scenario, tape_path=None)


def test_fork_exact_revision_cursors_inputs_and_parent_bytes(tmp_path: Path) -> None:
    catalog, ref, before = initialized(tmp_path)
    with AttemptLease(ref):
        archive = catalog.open_attempt(ref.attempt_id, read_only=False)
        state = WorldState()
        state.tick = 3
        archive.commit(
            encode_world(state),
            expected_revision=0,
            driver_cursor={},
            feedback_cursor={},
            entries=(),
        )
    old = (ref.directory / "archive.sqlite3").read_bytes()
    child = catalog.fork(ref.attempt_id, 0)
    assert child.lineage_id == ref.lineage_id and child.attempt_id != ref.attempt_id
    opened = catalog.open_attempt(child.attempt_id)
    assert opened.checkpoint() == before
    assert opened.parent == (ref.attempt_id, 0)
    assert opened.entries() == ()
    assert (ref.directory / "archive.sqlite3").read_bytes() == old
    assert (
        load_retained_inputs(child).scenario_path.read_bytes()
        == load_retained_inputs(ref).scenario_path.read_bytes()
    )
    with pytest.raises(ArchiveError):
        catalog.fork(ref.attempt_id, True)
    with pytest.raises(ArchiveError):
        catalog.fork(ref.attempt_id, 0, config=config("ollama"))


def test_active_process_owner_discovery_no_writes_and_exit_release(
    tmp_path: Path,
) -> None:
    catalog, ref, _ = initialized(tmp_path)
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_owner, args=(ref, child))
    process.start()
    try:
        assert parent.poll(10) and parent.recv() == "owned"
        old = {p: p.read_bytes() for p in ref.directory.rglob("*") if p.is_file()}
        assert AttemptLease.is_owned(ref)
        assert catalog.attempts()[0].lifecycle == "initializing"
        with pytest.raises(ArchiveError):
            AttemptLease(ref).acquire()
        assert {p: p.read_bytes() for p in old} == old
        process.terminate()
        process.join(10)
        assert not process.is_alive()
        assert not AttemptLease.is_owned(ref)
        assert catalog.attempts()[0].lifecycle == "interrupted"
    finally:
        if process.is_alive():
            process.terminate()
            process.join(10)
        parent.close()
        child.close()


def test_same_process_lease_release_and_unknown_identity(tmp_path: Path) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    lease = AttemptLease(ref)
    lease.acquire()
    try:
        with pytest.raises(ArchiveError):
            AttemptLease(ref).acquire()
        assert AttemptLease.is_owned(ref)
    finally:
        lease.release()
    lease.release()
    with AttemptLease(ref):
        assert AttemptLease.is_owned(ref)
    for bad in ("../bad", "A" * 32, "0" * 32):
        with pytest.raises(ArchiveError):
            catalog.open_attempt(bad)


def test_missing_inputs_checkpoint_and_duplicate_identity_fail_closed(
    tmp_path: Path,
) -> None:
    catalog, ref, _ = initialized(tmp_path)
    (ref.directory / "inputs.json").unlink()
    with pytest.raises(ArchiveError):
        catalog.open_attempt(ref.attempt_id)
    assert catalog.attempts()[0].failure_code == "archive_incomplete"
    duplicate = catalog.root / uuid4().hex / ref.attempt_id
    duplicate.mkdir(parents=True)
    with pytest.raises(ArchiveError):
        catalog.open_attempt(ref.attempt_id)


def test_probe_error_does_not_claim_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    catalog.reserve(config())

    def fail(ref: AttemptRef) -> None:
        raise OSError("denied")

    monkeypatch.setattr(AttemptLease, "is_owned", fail)
    (summary,) = catalog.attempts()
    assert summary.lifecycle == "initializing"
    assert summary.failure_code == "owner_probe_unavailable"


def test_one_symlink_attempt_does_not_hide_other_attempts(tmp_path: Path) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    good = catalog.reserve(config())
    link = good.directory.parent / uuid4().hex
    link.symlink_to(good.directory, target_is_directory=True)
    summaries = catalog.attempts()
    assert len(summaries) == 2
    assert (
        next(
            item for item in summaries if item.ref.attempt_id == link.name
        ).failure_code
        == "archive_invalid"
    )
    assert next(item for item in summaries if item.ref == good).mode == "recorded"


def test_discovery_uses_valid_archive_timestamp_when_reservation_missing(
    tmp_path: Path,
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    created = catalog.open_attempt(ref.attempt_id).created_at
    (ref.directory / "attempt.json").unlink()
    (summary,) = catalog.attempts()
    assert summary.started_at == created
    assert summary.failure_code == "archive_incomplete"


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_file",
        "duplicate_json",
        "future",
        "role_overlap",
        "traversal",
        "wrong_id",
        "hash_type",
    ],
)
def test_input_manifest_and_tree_fail_closed(tmp_path: Path, mutation: str) -> None:
    catalog, ref, _ = initialized(tmp_path)
    path = ref.directory / "inputs.json"
    raw = path.read_text()
    data = json.loads(raw)
    if mutation == "extra_file":
        (ref.directory / "inputs/unlisted").write_bytes(b"unretained")
    elif mutation == "duplicate_json":
        path.write_text(raw[:-1] + ',"format":1}')
    else:
        if mutation == "future":
            data["format"] = 2
        elif mutation == "role_overlap":
            data["definitions"] = data["scenario"]
        elif mutation == "traversal":
            data["scenario"] = "../escape"
        elif mutation == "wrong_id":
            data["attempt_id"] = uuid4().hex
        else:
            data["files"][data["scenario"]] = True
        path.write_text(json.dumps(data))
    with pytest.raises(ArchiveError):
        load_retained_inputs(ref)
    with pytest.raises(ArchiveError):
        catalog.open_attempt(ref.attempt_id)


def test_tape_bytes_and_identity_are_validated_from_retained_tree(
    tmp_path: Path,
) -> None:
    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    fingerprint = YAMLScenarioLoader().load(scenario).configuration_fingerprint
    tape = tmp_path / "tape ?#.yaml"
    tape.write_text(
        f"schema_version: 1\nscenario_key: test\nscenario_fingerprint: {fingerprint}\nentries:\n  - sequence: 1\n    actor_label: Alice\n    action: null\n    rationale: Wait\n    speech: Waiting\n"
    )
    inputs = retain_inputs(ref, scenario, tape_path=tape)
    assert inputs.tape_path.read_bytes() == tape.read_bytes()
    tape.write_text(
        tape.read_text().replace("scenario_key: test", "scenario_key: wrong")
    )
    second = catalog.reserve(config())
    with pytest.raises(ArchiveError):
        retain_inputs(second, scenario, tape_path=tape)


@pytest.mark.parametrize(
    "mode,target,valid",
    [
        ("ollama", "ollama", True),
        ("ollama", "journal_replay", True),
        ("journal_replay", "ollama", False),
        ("recorded", "journal_replay", False),
    ],
)
def test_fork_configuration_mode_rules(
    tmp_path: Path, mode: Mode, target: Mode, valid: bool
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config(mode))
    retain_inputs(ref, sources(tmp_path), tape_path=None)
    with AttemptLease(ref):
        catalog.open_attempt(ref.attempt_id, read_only=False).commit(
            encode_world(WorldState()),
            expected_revision=None,
            driver_cursor={},
            feedback_cursor={},
            entries=(),
        )
    if valid:
        child = catalog.fork(
            ref.attempt_id,
            0,
            config=config(target, settings={"limits": {"max_requests": 3}}),
        )
        assert catalog.open_attempt(child.attempt_id).config.settings == {
            "limits": {"max_requests": 3}
        }
    else:
        with pytest.raises(ArchiveError):
            catalog.fork(ref.attempt_id, 0, config=config(target))


def test_retention_borrows_current_thread_lease_and_writer_requires_it(
    tmp_path: Path,
) -> None:
    from living_world.archives.lease import AttemptLease

    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    with pytest.raises(ArchiveError):
        catalog.open_attempt(ref.attempt_id, read_only=False)
    with AttemptLease(ref):
        assert AttemptLease.owned_by_current_thread(ref)
        inputs = retain_inputs(ref, sources(tmp_path), tape_path=None)
        assert inputs.scenario_path.exists()
        assert AttemptLease.owned_by_current_thread(ref)
        with catalog.open_attempt(ref.attempt_id, read_only=False) as archive:
            archive.record((), lifecycle="paused")
        with pytest.raises(ArchiveError):
            AttemptLease(ref).acquire()
    assert not AttemptLease.owned_by_current_thread(ref)
    assert not AttemptLease.is_owned(ref)


def test_foreign_thread_cannot_borrow_or_open_writer(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)

    def foreign() -> None:
        assert not AttemptLease.owned_by_current_thread(ref)
        with pytest.raises(ArchiveError):
            catalog.open_attempt(ref.attempt_id, read_only=False)
        with pytest.raises(ArchiveError):
            retain_inputs(ref, scenario, tape_path=None)

    with AttemptLease(ref), ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(foreign).result(timeout=10)
        assert AttemptLease.owned_by_current_thread(ref)


def _inherited_lease(lease: AttemptLease, connection: Connection) -> None:
    owned = AttemptLease.owned_by_current_thread(lease.ref)
    try:
        lease.release()
    except ArchiveError:
        rejected = True
    else:
        rejected = False
    connection.send((owned, rejected))


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="POSIX fork inheritance",
)
def test_inherited_process_cannot_borrow_or_release_parent_lease(
    tmp_path: Path,
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    ctx = multiprocessing.get_context("fork")
    parent, child = ctx.Pipe()
    with AttemptLease(ref) as lease:
        process = ctx.Process(target=_inherited_lease, args=(lease, child))
        process.start()
        try:
            assert parent.poll(10) and parent.recv() == (False, True)
            process.join(10)
            assert not process.is_alive() and process.exitcode == 0
            assert AttemptLease.is_owned(ref)
        finally:
            if process.is_alive():
                process.terminate()
                process.join(10)
            parent.close()
            child.close()


def test_nested_loader_paths_preserve_exact_original_scenario_bytes(
    tmp_path: Path,
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    nested = scenario.parent / "nested ?#"
    nested.mkdir()
    (nested / "vocabulary.yaml").write_bytes(
        (scenario.parent / "defs ?#.yaml").read_bytes()
    )
    scenario.write_text(
        scenario.read_text().replace("defs ?#.yaml", "nested ?#/vocabulary.yaml")
    )
    original = scenario.read_bytes()
    retained = retain_inputs(ref, scenario, tape_path=None)
    assert retained.scenario_path.read_bytes() == original
    assert (
        retained.definition_path.relative_to(retained.scenario_path.parent).as_posix()
        == "nested ?#/vocabulary.yaml"
    )


def test_failed_fork_keeps_reserved_child_and_parent_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import living_world.archives.catalog as module

    catalog, ref, _ = initialized(tmp_path)
    old = (ref.directory / "archive.sqlite3").read_bytes()

    def fail(*args: object, **kwargs: object) -> None:
        raise ArchiveError("injected retention failure")

    monkeypatch.setattr(module, "retain_inputs", fail)
    with pytest.raises(ArchiveError):
        catalog.fork(ref.attempt_id, 0)
    summaries = catalog.attempts()
    (child,) = [item for item in summaries if item.ref != ref]
    assert child.parent == (ref.attempt_id, 0) and child.tick is None
    assert (ref.directory / "archive.sqlite3").read_bytes() == old


def test_lock_probe_never_changes_mtime_and_closed_handle_is_not_owned(
    tmp_path: Path,
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    lock = ref.directory / "owner.lock"
    before = lock.stat().st_mtime_ns
    lease = AttemptLease(ref)
    lease.acquire()
    assert AttemptLease.is_owned(ref)
    assert lock.stat().st_mtime_ns == before
    assert lease._handle is not None
    lease._handle.close()
    assert not AttemptLease.owned_by_current_thread(ref)
    assert not AttemptLease.is_owned(ref)
    lease.release()


def test_archive_hardlink_and_future_database_are_rejected_without_changes(
    tmp_path: Path,
) -> None:
    import os
    import sqlite3

    catalog, ref, _ = initialized(tmp_path)
    database = ref.directory / "archive.sqlite3"
    link = tmp_path / "alias.sqlite3"
    os.link(database, link)
    with pytest.raises(ArchiveError):
        catalog.open_attempt(ref.attempt_id)
    link.unlink()
    with sqlite3.connect(database) as connection:
        (raw,) = connection.execute("SELECT payload FROM archive_meta").fetchone()
        metadata = json.loads(raw)
        metadata["format"] = 99
        connection.execute("UPDATE archive_meta SET payload=?", (json.dumps(metadata),))
    old = database.read_bytes()
    (summary,) = catalog.attempts()
    assert summary.failure_code == "archive_invalid"
    assert database.read_bytes() == old


def test_invalid_lineage_nodes_do_not_hide_real_attempts(tmp_path: Path) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    good = catalog.reserve(config())
    (catalog.root / uuid4().hex).write_bytes(b"not a lineage")
    (catalog.root / uuid4().hex).symlink_to(
        good.directory.parent, target_is_directory=True
    )
    summaries = catalog.attempts()
    assert len(summaries) == 1 and summaries[0].ref == good


def test_inaccessible_attempt_does_not_hide_good_attempt_or_repair_history(
    tmp_path: Path,
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    damaged = catalog.reserve(config())
    good = catalog.reserve(config())
    files = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for ref in (damaged, good)
        for path in ref.directory.iterdir()
        if path.is_file()
    }
    original_mode = damaged.directory.stat().st_mode & 0o777
    damaged.directory.chmod(0)
    try:
        summaries = {item.ref.attempt_id: item for item in catalog.attempts()}
        assert summaries[good.attempt_id].ref == good
        assert summaries[good.attempt_id].mode == "recorded"
        failed = summaries[damaged.attempt_id]
        assert failed.ref == damaged and failed.lifecycle == "failed"
        assert failed.failure_code == "archive_invalid"
        assert failed.mode is None and failed.tick is None
    finally:
        damaged.directory.chmod(original_mode)
    assert {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in files
    } == files


def test_fork_seals_visible_journal_prefix_and_detects_metadata_disagreement(
    tmp_path: Path,
) -> None:
    from living_world.archives import JournalEntry

    catalog, ref, before = initialized(tmp_path)
    with AttemptLease(ref):
        writer = catalog.open_attempt(ref.attempt_id, read_only=False)
        writer.append(
            JournalEntry("candidate_aborted", {"base_revision": 0, "reason": "before"})
        )
    source = catalog.open_attempt(ref.attempt_id)
    sealed = source.journal_boundary()
    child = catalog.fork(ref.attempt_id, 0)
    opened = catalog.open_attempt(child.attempt_id)
    assert opened.parent_journal_boundary == sealed
    assert opened.checkpoint() == before
    with AttemptLease(ref):
        writer.append(
            JournalEntry("candidate_aborted", {"base_revision": 0, "reason": "after"})
        )
    assert source.journal_boundary() != sealed
    assert source.journal_boundary(through_sequence=sealed.sequence) == sealed
    path = child.directory / "attempt.json"
    data = json.loads(path.read_text())
    assert data["parent_journal"] == {
        "sequence": sealed.sequence,
        "digest": sealed.digest,
    }
    data["parent_journal"]["digest"] = "f" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ArchiveError):
        catalog.open_attempt(child.attempt_id)


def test_legacy_absent_parent_journal_metadata_is_readable_without_writes(
    tmp_path: Path,
) -> None:
    import sqlite3

    catalog, ref, _ = initialized(tmp_path)
    manifest = ref.directory / "attempt.json"
    data = json.loads(manifest.read_text())
    data.pop("parent_journal", None)
    manifest.write_text(json.dumps(data))
    database = ref.directory / "archive.sqlite3"
    with sqlite3.connect(database) as connection:
        raw = json.loads(
            connection.execute("SELECT payload FROM archive_meta").fetchone()[0]
        )
        raw.pop("parent_journal", None)
        connection.execute("UPDATE archive_meta SET payload=?", (json.dumps(raw),))
    before = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in ref.directory.iterdir()
        if p.is_file()
    }
    assert catalog.open_attempt(ref.attempt_id).parent_journal_boundary is None
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before


@pytest.mark.parametrize(
    "metadata",
    [
        True,
        {},
        {"sequence": -1, "digest": "a" * 64},
        {"sequence": 0, "digest": "A" * 64},
        {"sequence": 0, "digest": "a" * 64, "extra": 1},
    ],
)
def test_malformed_parent_journal_metadata_rejected(
    tmp_path: Path, metadata: object
) -> None:
    catalog, ref, _ = initialized(tmp_path)
    child = catalog.fork(ref.attempt_id, 0)
    manifest = child.directory / "attempt.json"
    data = json.loads(manifest.read_text())
    data["parent_journal"] = metadata
    manifest.write_text(json.dumps(data))
    with pytest.raises(ArchiveError):
        catalog.open_attempt(child.attempt_id)


def test_parent_boundary_requires_parent_and_reservation_contract_stays_four_values(
    tmp_path: Path,
) -> None:
    from living_world.archives import JournalBoundary
    from living_world.archives.catalog import read_reservation

    catalog = RunCatalog(tmp_path / "runs")
    boundary = JournalBoundary(0, "a" * 64)
    with pytest.raises(ArchiveError):
        catalog.reserve(config(), parent_journal_boundary=boundary)
    ref = catalog.reserve(config())
    assert len(read_reservation(ref)) == 4
    with pytest.raises(ArchiveError):
        AttemptArchive.create(ref, config(), parent_journal_boundary=boundary)


def test_sealed_prefix_tampering_changes_recomputed_digest(tmp_path: Path) -> None:
    import sqlite3

    from living_world.archives import JournalEntry

    catalog, ref, _ = initialized(tmp_path)
    with AttemptLease(ref):
        writer = catalog.open_attempt(ref.attempt_id, read_only=False)
        writer.append(
            JournalEntry(
                "candidate_aborted", {"base_revision": 0, "reason": "original"}
            )
        )
    child = catalog.fork(ref.attempt_id, 0)
    sealed = catalog.open_attempt(child.attempt_id).parent_journal_boundary
    assert sealed is not None
    with sqlite3.connect(ref.directory / "archive.sqlite3") as connection:
        connection.execute(
            "UPDATE journal SET payload=json_set(payload,'$.reason','tampered')"
        )
    source = catalog.open_attempt(ref.attempt_id)
    assert source.journal_boundary(through_sequence=sealed.sequence) != sealed
    with sqlite3.connect(ref.directory / "archive.sqlite3") as connection:
        connection.execute("DELETE FROM journal")
    with pytest.raises(ArchiveError):
        source.journal_boundary(through_sequence=sealed.sequence)


@pytest.mark.parametrize(
    "field,value",
    [
        ("parent_journal", {"sequence": True, "digest": "a" * 64}),
        ("parent_journal", {"sequence": 0, "digest": "a" * 64, "extra": 1}),
        ("parent", None),
    ],
)
def test_archive_parent_metadata_malformed_or_disagrees_rejected(
    tmp_path: Path, field: str, value: object
) -> None:
    import sqlite3

    catalog, ref, _ = initialized(tmp_path)
    child = catalog.fork(ref.attempt_id, 0)
    database = child.directory / "archive.sqlite3"
    with sqlite3.connect(database) as connection:
        data = json.loads(
            connection.execute("SELECT payload FROM archive_meta").fetchone()[0]
        )
        data[field] = value
        connection.execute("UPDATE archive_meta SET payload=?", (json.dumps(data),))
    before = database.read_bytes()
    with pytest.raises(ArchiveError):
        catalog.open_attempt(child.attempt_id)
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "declaration", ["./defs ?#.yaml", ".//./defs ?#.yaml", "sub/../defs ?#.yaml"]
)
def test_safe_source_declarations_keep_exact_bytes_and_fingerprint(
    tmp_path: Path, declaration: str
) -> None:
    import hashlib

    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    (scenario.parent / "sub").mkdir()
    scenario.write_text(scenario.read_text().replace("defs ?#.yaml", declaration))
    original_scenario = scenario.read_bytes()
    original_definitions = (scenario.parent / "defs ?#.yaml").read_bytes()
    fingerprint = YAMLScenarioLoader().load(scenario).configuration_fingerprint
    retained = retain_inputs(ref, scenario, tape_path=None)
    assert retained.scenario_path.read_bytes() == original_scenario
    assert retained.definition_path.read_bytes() == original_definitions
    assert retained.definition_path.name == "defs ?#.yaml"
    assert (
        YAMLScenarioLoader().load(retained.scenario_path).configuration_fingerprint
        == fingerprint
    )
    assert (
        retained.hashes["scenario/" + scenario.name]
        == hashlib.sha256(original_scenario).hexdigest()
    )
    assert (
        retained.hashes["scenario/defs ?#.yaml"]
        == hashlib.sha256(original_definitions).hexdigest()
    )
    assert load_retained_inputs(ref) == retained


@pytest.mark.parametrize(
    "declaration",
    [
        "../source ?#/defs ?#.yaml",
        "sub/../../source ?#/defs ?#.yaml",
        "sub\\..\\defs ?#.yaml",
    ],
)
def test_source_normalization_rejects_escape_prefixes_and_backslashes(
    tmp_path: Path, declaration: str
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    (scenario.parent / "sub").mkdir()
    scenario.write_text(
        scenario.read_text().replace('"defs ?#.yaml"', json.dumps(declaration))
    )
    with pytest.raises(ArchiveError):
        retain_inputs(ref, scenario, tape_path=None)
    assert not (ref.directory / "inputs.json").exists()


def test_source_normalization_rejects_cancelled_symlink(tmp_path: Path) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (scenario.parent / "sub").symlink_to(outside, target_is_directory=True)
    scenario.write_text(
        scenario.read_text().replace("defs ?#.yaml", "sub/../defs ?#.yaml")
    )
    with pytest.raises(ArchiveError):
        retain_inputs(ref, scenario, tape_path=None)
    assert not (ref.directory / "inputs.json").exists()


def test_normalized_definition_rejects_hardlinks_and_retained_tamper(
    tmp_path: Path,
) -> None:
    import os

    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    definition = scenario.parent / "defs ?#.yaml"
    link = tmp_path / "hardlink.yaml"
    os.link(definition, link)
    scenario.write_text(scenario.read_text().replace("defs ?#.yaml", "./defs ?#.yaml"))
    with pytest.raises(ArchiveError):
        retain_inputs(ref, scenario, tape_path=None)
    link.unlink()
    retained = retain_inputs(ref, scenario, tape_path=None)
    retained.definition_path.write_bytes(b"definitions: [tampered]\n")
    with pytest.raises(ArchiveError):
        load_retained_inputs(ref)


@pytest.mark.parametrize(
    "declaration",
    [
        "scenario/./defs ?#.yaml",
        "scenario//defs ?#.yaml",
        "scenario/sub/../defs ?#.yaml",
    ],
)
def test_manifest_roles_stay_strict_after_source_normalization(
    tmp_path: Path, declaration: str
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    scenario = sources(tmp_path)
    scenario.write_text(scenario.read_text().replace("defs ?#.yaml", "./defs ?#.yaml"))
    retain_inputs(ref, scenario, tape_path=None)
    manifest = ref.directory / "inputs.json"
    data = json.loads(manifest.read_text())
    data["definitions"] = declaration
    manifest.write_text(json.dumps(data))
    with pytest.raises(ArchiveError):
        load_retained_inputs(ref)
