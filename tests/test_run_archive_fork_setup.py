"""Deferred live forks pin immutable engine evidence before provider setup."""

import hashlib
import json
from collections.abc import Callable
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Literal, cast

import pytest

from living_world.archives import (
    ArchiveError,
    AttemptArchive,
    AttemptConfig,
    AttemptRef,
    Checkpoint,
)
from living_world.archives.assets import load_retained_inputs, retain_inputs
from living_world.archives.catalog import (
    ArchiveReservationError,
    AttemptSummary,
    RunCatalog,
)
from living_world.archives.lease import AttemptLease
from living_world.archives.model import ForkPoint, JournalEntry, canonical
from living_world.repositories.world_snapshot import encode_world
from living_world.state.world_state import WorldState


def config(model: str = "tiny:latest", **settings: object) -> AttemptConfig:
    return AttemptConfig(
        "ollama",
        "test",
        7,
        "rev",
        {"provider": {"model": model, "model_digest": "a" * 64}, **settings},
    )


def source(tmp_path: Path) -> tuple[RunCatalog, AttemptRef, Checkpoint]:
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(config())
    inputs = tmp_path / "source"
    inputs.mkdir()
    (inputs / "defs.yaml").write_text("definitions: []\n")
    (inputs / "scenario.yaml").write_text(
        "schema_version: 1\nkey: test\nseed: 7\ndefinitions: defs.yaml\n"
    )
    retain_inputs(ref, inputs / "scenario.yaml", tape_path=None)
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        checkpoint = archive.commit(
            encode_world(WorldState()),
            expected_revision=None,
            driver_cursor={"offset": 4},
            feedback_cursor={"pending": ["yes"]},
            entries=(),
        )
    return catalog, ref, checkpoint


def summary(catalog: RunCatalog, ref: AttemptRef) -> AttemptSummary:
    return next(s for s in catalog.attempts() if s.ref == ref)


def tree(path: Path) -> dict[Path, tuple[bytes, int]]:
    return {
        p.relative_to(path): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in path.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("revision", [0, None])
@pytest.mark.parametrize("changed", [False, True])
def test_reservation_pins_once_before_io_and_publishes_exact_world(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    revision: int | None,
    changed: bool,
) -> None:
    catalog, parent, selected = source(tmp_path)
    before = tree(parent.directory)
    calls: list[int | None] = []
    original = AttemptArchive.fork_point

    def capture(self: AttemptArchive, revision: int | None = None) -> ForkPoint:
        calls.append(revision)
        return original(self, revision)

    monkeypatch.setattr(AttemptArchive, "fork_point", capture)
    requested = (
        AttemptConfig(
            "ollama",
            "test",
            7,
            "rev",
            {"provider": {"model": "other"}, "limits": {"max_ticks": 9}},
        )
        if changed
        else None
    )
    child = catalog.reserve_fork_setup(parent.attempt_id, revision, requested=requested)
    assert calls == [revision]
    assert child.lineage_id == parent.lineage_id
    intent = (child.directory / "setup.json").read_bytes()
    fork = json.loads(intent)["fork"]
    assert fork["parent"] == [parent.attempt_id, 0]
    assert dict(load_retained_inputs(child).hashes) == fork["input_hashes"]
    assert not any(
        (child.directory / name).exists()
        for name in ("attempt.json", "archive.sqlite3", "setup_complete.json")
    )
    assert tree(parent.directory) == before
    effective = (
        config()
        if requested is None
        else AttemptConfig(
            "ollama",
            "test",
            7,
            "rev",
            {
                "provider": {"model": "other:latest", "model_digest": "b" * 64},
                "limits": {"max_ticks": 9},
            },
        )
    )
    with AttemptLease(child):
        pending = summary(catalog, child)
        assert (
            pending.parent,
            pending.lifecycle,
            pending.last_revision,
            pending.tick,
        ) == ((parent.attempt_id, 0), "initializing", None, None)
        with (
            AttemptLease(parent),
            catalog.open_attempt(parent.attempt_id, read_only=False) as archive,
        ):
            archive.commit(
                encode_world(WorldState(tick=9)),
                expected_revision=0,
                driver_cursor={"offset": 99},
                feedback_cursor={},
                entries=(
                    JournalEntry(
                        "candidate_aborted", {"base_revision": 0, "reason": "cancelled"}
                    ),
                ),
            )
        catalog.complete_setup(child, effective)
        with pytest.raises(ArchiveError):
            catalog.complete_setup(child, effective)
        with pytest.raises(ArchiveError):
            catalog.fail_setup(child, "setup_failed")
    assert calls == [revision]
    assert (child.directory / "setup.json").read_bytes() == intent
    with catalog.open_attempt(child.attempt_id) as archive:
        assert archive.config == effective
        assert archive.parent == (parent.attempt_id, 0)
        assert archive.checkpoint().snapshot == selected.snapshot
        assert archive.checkpoint().driver_cursor == selected.driver_cursor
        assert archive.checkpoint().feedback_cursor == selected.feedback_cursor
        assert archive.journal_records() == ()
        assert (
            archive.parent_journal_boundary.sequence
            == fork["parent_journal"]["sequence"]
        )
    stable = tree(catalog.root)
    assert summary(catalog, child).last_revision == 0
    assert tree(catalog.root) == stable
    with (
        AttemptLease(child),
        catalog.open_attempt(child.attempt_id, read_only=False) as archive,
    ):
        archive.commit(
            encode_world(WorldState(tick=11)),
            expected_revision=0,
            driver_cursor={},
            feedback_cursor={},
            entries=(),
        )
    parent.directory.rename(parent.directory.with_name("unavailable"))
    with catalog.open_attempt(child.attempt_id) as archive:
        assert archive.latest_revision == 1
        assert archive.checkpoint(0).snapshot == selected.snapshot


@pytest.mark.parametrize(
    "field,value",
    [
        ("mode", "recorded"),
        ("mode", "journal_replay"),
        ("scenario_key", "other"),
        ("seed", 8),
        ("software_revision", "other"),
        ("settings", {"provider": {"model": "tiny"}, "launch_source": "cli"}),
    ],
)
def test_invalid_requested_transition_allocates_nothing(
    tmp_path: Path, field: str, value: object
) -> None:
    catalog, parent, _ = source(tmp_path)
    raw = {
        "mode": "ollama",
        "scenario_key": "test",
        "seed": 7,
        "software_revision": "rev",
        "settings": config().settings,
    }
    raw[field] = value
    before = tree(catalog.root)
    with pytest.raises(ArchiveError):
        catalog.reserve_fork_setup(parent.attempt_id, 0, requested=AttemptConfig(**raw))
    assert tree(catalog.root) == before


@pytest.mark.parametrize("revision", [True, -1, "0", 1])
def test_bad_revision_allocates_nothing(tmp_path: Path, revision: int | None) -> None:
    catalog, parent, _ = source(tmp_path)
    before = tree(catalog.root)
    with pytest.raises(ArchiveError):
        catalog.reserve_fork_setup(parent.attempt_id, revision)
    assert tree(catalog.root) == before


@pytest.mark.parametrize("mode", ["recorded", "journal_replay"])
def test_parent_mode_cannot_be_inferred_live(
    tmp_path: Path, mode: Literal["recorded", "journal_replay"]
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    parent = catalog.reserve(AttemptConfig(mode, "test", 7, "rev", {}))
    with pytest.raises(ArchiveError):
        catalog.reserve_fork_setup(parent.attempt_id, None)
    assert len(catalog.attempts()) == 1


@pytest.mark.parametrize("fault", ["retention", "intent_after_write"])
def test_post_allocation_failure_preserves_link_and_safe_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import living_world.archives.catalog as module

    catalog, parent, _ = source(tmp_path)
    before = tree(parent.directory)
    original = module.atomic_document

    def fail(*args: object, **kwargs: object) -> None:
        if fault == "intent_after_write":
            original(*args, **kwargs)
            if args[0].name != "setup.json":
                return
        raise OSError("private failure must not escape")

    monkeypatch.setattr(
        module, "retain_inputs" if fault == "retention" else "atomic_document", fail
    )
    with pytest.raises(ArchiveReservationError) as error:
        catalog.reserve_fork_setup(parent.attempt_id, 0)
    child = error.value.ref
    assert "private" not in str(error.value)
    assert child.lineage_id == parent.lineage_id
    assert catalog.setup_config(child) == config()
    found = summary(catalog, child)
    assert (found.parent, found.failure_code, found.last_revision, found.tick) == (
        (parent.attempt_id, 0),
        "setup_failed",
        None,
        None,
    )
    assert tree(parent.directory) == before


def change_json(path: Path, mutate: Callable[[dict[str, object]], None]) -> None:
    data = json.loads(path.read_text())
    mutate(data)
    path.write_text(json.dumps(data))


@pytest.mark.parametrize(
    "field,value",
    [
        ("parent", None),
        ("parent", ["../escape", 0]),
        ("parent", ["a" * 32, True]),
        ("parent_journal", None),
        ("parent_journal", {"sequence": True, "digest": "a" * 64}),
        ("parent_journal", {"sequence": 0, "digest": "a" * 64, "extra": 1}),
        ("checkpoint_sha256", "A" * 64),
        ("source_config_sha256", "short"),
        ("input_hashes", None),
        ("input_hashes", {"../secret": "a" * 64}),
        ("input_hashes", {"scenario/file": "bad"}),
        ("extra", 1),
    ],
)
def test_fork_metadata_closed_and_strict(
    tmp_path: Path, field: str, value: object
) -> None:
    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    change_json(
        child.directory / "setup.json", lambda d: d["fork"].__setitem__(field, value)
    )
    before = tree(catalog.root)
    with pytest.raises(ArchiveError):
        catalog.setup_config(child)
    assert summary(catalog, child).failure_code == "archive_invalid"
    with AttemptLease(child), pytest.raises(ArchiveError):
        catalog.complete_setup(child, config())
    assert tree(catalog.root) == before


@pytest.mark.parametrize("kind", ["null", "self", "missing"])
def test_fork_metadata_rejects_null_self_and_missing_fields(
    tmp_path: Path, kind: str
) -> None:
    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)

    def mutate(d: dict[str, object]) -> None:
        if kind == "null":
            d["fork"] = None
        elif kind == "self":
            d["fork"]["parent"][0] = child.attempt_id
        else:
            del d["fork"]["checkpoint_sha256"]

    change_json(child.directory / "setup.json", mutate)
    with pytest.raises(ArchiveError):
        catalog.setup_config(child)
    assert summary(catalog, child).failure_code == "archive_invalid"


def replace_inputs(ref: AttemptRef) -> None:
    """Replace valid bytes plus manifest consistently; intent must still detect it."""
    retained = load_retained_inputs(ref)
    retained.definition_path.write_text("definitions: []\n# replacement\n")
    name = retained.definition_path.relative_to(ref.directory / "inputs").as_posix()
    changed = hashlib.sha256(retained.definition_path.read_bytes()).hexdigest()
    change_json(
        ref.directory / "inputs.json", lambda d: d["files"].__setitem__(name, changed)
    )


def replace_checkpoint(ref: AttemptRef, field: str) -> None:
    """Change checkpoint with valid local digest/operation/fingerprint parity."""
    import sqlite3

    with sqlite3.connect(ref.directory / "archive.sqlite3") as connection:
        operation = json.loads(
            connection.execute(
                "SELECT operation FROM checkpoints WHERE revision=0"
            ).fetchone()[0]
        )
        if field == "snapshot":
            snapshot = encode_world(WorldState(tick=3))
            operation["payload"] = snapshot.payload
            connection.execute(
                "UPDATE checkpoints SET payload=?,digest=? WHERE revision=0",
                (snapshot.payload, snapshot.digest),
            )
            connection.execute(
                "UPDATE world_snapshots SET payload=?", (snapshot.payload,)
            )
        else:
            operation[field] = {"changed": True}
            connection.execute(
                f"UPDATE checkpoints SET {field}=? WHERE revision=0",
                (canonical(operation[field]),),
            )
        encoded = canonical(operation)
        connection.execute(
            "UPDATE checkpoints SET operation=?,fingerprint=? WHERE revision=0",
            (encoded, hashlib.sha256(encoded.encode()).hexdigest()),
        )


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "config",
        "inputs",
        "snapshot",
        "driver_cursor",
        "feedback_cursor",
        "prefix",
    ],
)
def test_changed_source_fails_before_final_publication(
    tmp_path: Path, damage: str
) -> None:
    import sqlite3

    catalog, parent, _ = source(tmp_path)
    with (
        AttemptLease(parent),
        catalog.open_attempt(parent.attempt_id, read_only=False) as archive,
    ):
        archive.record(
            (
                JournalEntry(
                    "candidate_aborted", {"base_revision": 0, "reason": "before"}
                ),
            )
        )
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    if damage == "missing":
        parent.directory.rename(parent.directory.with_name("unavailable"))
    elif damage == "inputs":
        replace_inputs(parent)
    elif damage in ("snapshot", "driver_cursor", "feedback_cursor"):
        replace_checkpoint(parent, damage)
    elif damage == "prefix":
        with sqlite3.connect(parent.directory / "archive.sqlite3") as connection:
            connection.execute(
                "UPDATE journal SET payload=?",
                (canonical({"base_revision": 0, "reason": "after"}),),
            )
    else:
        change_json(
            parent.directory / "attempt.json",
            lambda d: d["config"]["settings"]["provider"].__setitem__(
                "model_digest", "b" * 64
            ),
        )
        with sqlite3.connect(parent.directory / "archive.sqlite3") as connection:
            data = json.loads(
                connection.execute("SELECT payload FROM archive_meta").fetchone()[0]
            )
            data["config"]["settings"]["provider"]["model_digest"] = "b" * 64
            connection.execute("UPDATE archive_meta SET payload=?", (canonical(data),))
    before = tree(catalog.root)
    with AttemptLease(child):
        with pytest.raises(ArchiveError):
            catalog.complete_setup(child, config())
        assert not (child.directory / "attempt.json").exists()
        assert not (child.directory / "archive.sqlite3").exists()
        assert tree(catalog.root) == before
        catalog.fail_setup(child, "setup_failed")
    assert summary(catalog, child).parent == (parent.attempt_id, 0)


@pytest.mark.parametrize("complete", [False, True])
def test_child_manifest_and_bytes_replacement_rejected_against_intent(
    tmp_path: Path, complete: bool
) -> None:
    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    if complete:
        with AttemptLease(child):
            catalog.complete_setup(child, config())
    replace_inputs(child)
    before = tree(catalog.root)
    with pytest.raises(ArchiveError):
        load_retained_inputs(child)
    with pytest.raises(ArchiveError):
        catalog.open_attempt(child.attempt_id)
    assert summary(catalog, child).failure_code == "archive_invalid"
    assert tree(catalog.root) == before


@pytest.mark.parametrize("damage", ["snapshot", "driver_cursor", "feedback_cursor"])
def test_marked_child_cp0_hash_rejects_self_consistent_changes(
    tmp_path: Path, damage: str
) -> None:
    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    with AttemptLease(child):
        catalog.complete_setup(child, config())
    replace_checkpoint(child, damage)
    # The ordinary store accepts these internally consistent bytes.
    with AttemptArchive.open(child, read_only=True) as archive:
        archive.checkpoint(0)
    before = tree(catalog.root)
    with pytest.raises(ArchiveError):
        catalog.open_attempt(child.attempt_id)
    assert summary(catalog, child).failure_code == "archive_invalid"
    assert tree(catalog.root) == before


@pytest.mark.parametrize(
    "fault", ["before_sqlite", "empty", "schema", "before_cp0", "after_cp0"]
)
def test_partial_publication_retains_linkage_and_never_repairs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import sqlite3

    import living_world.archives.catalog as module

    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    original_create = AttemptArchive.create
    original_document = module.atomic_document

    def create(*args: object, **kwargs: object) -> None:
        database = child.directory / "archive.sqlite3"
        if fault == "empty":
            database.touch()
        elif fault == "schema":
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE archive_meta(payload TEXT)")
        elif fault == "before_cp0":
            original_create(*args, **kwargs).close()
        else:
            raise OSError("before sqlite")
        raise OSError("interrupted create")

    def document(path: Path, value: object) -> None:
        if path.name == "setup_complete.json":
            raise OSError("interrupted marker")
        original_document(path, value)

    if fault == "after_cp0":
        monkeypatch.setattr(module, "atomic_document", document)
    else:
        monkeypatch.setattr(AttemptArchive, "create", create)
    with AttemptLease(child):
        with pytest.raises(ArchiveReservationError) as error:
            catalog.complete_setup(child, config())
        assert error.value.ref == child
        before = tree(catalog.root)
        pending = summary(catalog, child)
        assert (
            pending.lifecycle,
            pending.parent,
            pending.last_revision,
            pending.tick,
        ) == ("initializing", (parent.attempt_id, 0), None, None)
        load_retained_inputs(child)
        for operation in (
            lambda: catalog.open_attempt(child.attempt_id),
            lambda: catalog.complete_setup(child, config()),
            lambda: catalog.fail_setup(child, "setup_failed"),
        ):
            with pytest.raises(ArchiveError):
                operation()
        assert tree(catalog.root) == before
    failed = summary(catalog, child)
    assert (failed.failure_code, failed.parent, failed.last_revision, failed.tick) == (
        "archive_incomplete",
        (parent.attempt_id, 0),
        None,
        None,
    )
    assert tree(catalog.root) == before


def test_revision_none_pins_latest_once_and_explicit_old_revision_stays_old(
    tmp_path: Path,
) -> None:
    catalog, parent, cp0 = source(tmp_path)
    entry = JournalEntry(
        "candidate_aborted", {"base_revision": 0, "reason": "captured"}
    )
    with (
        AttemptLease(parent),
        catalog.open_attempt(parent.attempt_id, read_only=False) as archive,
    ):
        cp1 = archive.commit(
            encode_world(WorldState(tick=2)),
            expected_revision=0,
            driver_cursor={"offset": 8},
            feedback_cursor={"later": True},
            entries=(entry,),
        )
    latest = catalog.reserve_fork_setup(parent.attempt_id, None)
    older = catalog.reserve_fork_setup(parent.attempt_id, 0)
    expected = ((latest, cp1), (older, cp0))
    before = tree(parent.directory)
    for child, checkpoint in expected:
        intent = json.loads((child.directory / "setup.json").read_text())["fork"]
        assert intent["parent"] == [parent.attempt_id, checkpoint.revision]
        assert intent["parent_journal"]["sequence"] == 1
        assert (
            intent["checkpoint_sha256"]
            == hashlib.sha256(
                canonical(
                    {
                        "snapshot": {
                            "schema_version": checkpoint.snapshot.schema_version,
                            "payload": checkpoint.snapshot.payload,
                        },
                        "driver_cursor": checkpoint.driver_cursor,
                        "feedback_cursor": checkpoint.feedback_cursor,
                    }
                ).encode()
            ).hexdigest()
        )
        with AttemptLease(child):
            catalog.complete_setup(child, config())
        with catalog.open_attempt(child.attempt_id) as archive:
            assert archive.checkpoint(0).snapshot == checkpoint.snapshot
            assert archive.checkpoint(0).driver_cursor == checkpoint.driver_cursor
            assert archive.checkpoint(0).feedback_cursor == checkpoint.feedback_cursor
    assert tree(parent.directory) == before


def test_completion_requires_same_catalog_and_current_thread_lease(
    tmp_path: Path,
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    with pytest.raises(ArchiveError):
        catalog.complete_setup(child, config())
    with AttemptLease(child):
        with pytest.raises(ArchiveError):
            RunCatalog(tmp_path / "foreign").complete_setup(child, config())
        with ThreadPoolExecutor(max_workers=1) as pool, pytest.raises(ArchiveError):
            pool.submit(catalog.complete_setup, child, config()).result()
        assert not (child.directory / "attempt.json").exists()
        catalog.fail_setup(child, "cancelled")
        before = tree(catalog.root)
        catalog.fail_setup(child, "cancelled")
        for operation in (
            lambda: catalog.complete_setup(child, config()),
            lambda: catalog.fail_setup(child, "setup_failed"),
        ):
            with pytest.raises(ArchiveError):
                operation()
        assert tree(catalog.root) == before
    assert summary(catalog, child).parent == (parent.attempt_id, 0)
    assert summary(catalog, child).failure_code == "cancelled"


@pytest.mark.parametrize(
    "field", ["parent", "parent_journal", "reserved_at", "reservation_error"]
)
def test_partial_reservation_must_match_fork_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("before SQLite")

    monkeypatch.setattr(AttemptArchive, "create", fail)
    with AttemptLease(child):
        with pytest.raises(ArchiveReservationError):
            catalog.complete_setup(child, config())
        value = {
            "parent": None,
            "parent_journal": None,
            "reserved_at": "2026-01-01T00:00:00+00:00",
            "reservation_error": "archive_initialization_failed",
        }[field]
        change_json(
            child.directory / "attempt.json", lambda d: d.__setitem__(field, value)
        )
        before = tree(catalog.root)
        assert summary(catalog, child).failure_code == "archive_invalid"
        with pytest.raises(ArchiveError):
            load_retained_inputs(child)
        assert tree(catalog.root) == before


def _hold_setup_lease(ref: AttemptRef, connection: Connection) -> None:
    with AttemptLease(ref):
        connection.send("owned")
        connection.recv()


def test_real_killed_owner_leaves_linked_pending_inputs_read_only(
    tmp_path: Path,
) -> None:
    import multiprocessing

    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    context = multiprocessing.get_context("spawn")
    receiving, sending = context.Pipe()
    owner = context.Process(target=_hold_setup_lease, args=(child, sending))
    owner.start()
    try:
        assert receiving.poll(10)
        assert receiving.recv() == "owned"
        assert summary(catalog, child).lifecycle == "initializing"
        owner.kill()
        owner.join(10)
        assert not owner.is_alive()
        before = tree(catalog.root)
        result = summary(catalog, child)
        assert (result.parent, result.lifecycle, result.last_revision, result.tick) == (
            (parent.attempt_id, 0),
            "interrupted",
            None,
            None,
        )
        load_retained_inputs(child)
        with pytest.raises(ArchiveError):
            catalog.open_attempt(child.attempt_id)
        assert tree(catalog.root) == before
    finally:
        if owner.is_alive():
            owner.kill()
            owner.join(10)
        owner.close()
        receiving.close()
        sending.close()


@pytest.mark.parametrize(
    "damage", ["marker", "reservation", "missing_cp0", "failure_conflict"]
)
def test_marked_fork_corruption_stays_invalid(tmp_path: Path, damage: str) -> None:
    import sqlite3

    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    with AttemptLease(child):
        catalog.complete_setup(child, config())
    if damage == "marker":
        change_json(
            child.directory / "setup_complete.json",
            lambda d: d.__setitem__("config_sha256", "b" * 64),
        )
    elif damage == "reservation":
        change_json(
            child.directory / "attempt.json", lambda d: d.__setitem__("parent", None)
        )
    elif damage == "failure_conflict":
        (child.directory / "setup_failure.json").write_text(
            json.dumps(
                {
                    "format": 1,
                    "lineage_id": child.lineage_id,
                    "attempt_id": child.attempt_id,
                    "code": "setup_failed",
                    "ended_at": "2026-01-01T00:00:00+00:00",
                }
            )
        )
    else:
        with sqlite3.connect(child.directory / "archive.sqlite3") as connection:
            connection.execute("DELETE FROM checkpoints")
            connection.execute("DELETE FROM world_snapshots")
    before = tree(catalog.root)
    with pytest.raises(ArchiveError):
        catalog.open_attempt(child.attempt_id)
    assert summary(catalog, child).failure_code == "archive_invalid"
    assert tree(catalog.root) == before


def test_exact_snapshot_tape_and_source_request_evidence_preserved(
    tmp_path: Path,
) -> None:
    from living_world.repositories.world_snapshot import WorldSnapshot
    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog = RunCatalog(tmp_path / "runs")
    parent = catalog.reserve(config())
    (tmp_path / "defs.yaml").write_text("definitions: []\n")
    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(
        "schema_version: 1\nkey: test\nseed: 7\ndefinitions: defs.yaml\n"
    )
    tape = tmp_path / "tape.yaml"
    fingerprint = YAMLScenarioLoader().load(scenario).configuration_fingerprint
    tape.write_text(
        f"schema_version: 1\nscenario_key: test\nscenario_fingerprint: {fingerprint}\nentries:\n  - sequence: 1\n    actor_label: Ada\n    action: null\n    speech: Waiting.\n    rationale: Waiting.\n"
    )
    retain_inputs(parent, scenario, tape_path=tape)
    payload = (
        json.dumps(json.loads(encode_world(WorldState()).payload), indent=3) + "\n"
    )
    selected = WorldSnapshot(encode_world(WorldState()).schema_version, payload)
    request = JournalEntry(
        "request_started",
        {
            "request_id": "source-request",
            "base_revision": 0,
            "source_tick": 0,
            "actor_label": "Ada",
            "input_fingerprint": "a" * 64,
            "config_fingerprint": "b" * 64,
            "request": {
                "identity": "Ada",
                "self_knowledge": [],
                "current_perceptions": [],
                "core_cognition": [],
                "retrieved_information": [],
                "conversation_history": [],
                "actions": [
                    {"key": "wait", "description": "Wait here", "target_labels": []}
                ],
            },
        },
    )
    with (
        AttemptLease(parent),
        catalog.open_attempt(parent.attempt_id, read_only=False) as archive,
    ):
        archive.commit(
            selected,
            expected_revision=None,
            driver_cursor={"request_offset": 7},
            feedback_cursor={"history": ["retained"]},
            entries=(),
        )
        archive.record(
            (
                request,
                JournalEntry(
                    "response_failed",
                    {"request_id": "source-request", "code": "timeout"},
                ),
            )
        )
    before = tree(parent.directory)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    with AttemptLease(child):
        catalog.complete_setup(child, config())
    with catalog.open_attempt(child.attempt_id) as archive:
        assert archive.checkpoint().snapshot.payload == payload
        assert archive.checkpoint().driver_cursor == {"request_offset": 7}
        assert archive.checkpoint().feedback_cursor == {"history": ("retained",)}
        assert archive.journal_records() == ()
        assert archive.lifecycle() == ()
    assert tree(parent.directory) == before
    child_inputs = load_retained_inputs(child)
    parent_inputs = load_retained_inputs(parent)
    assert child_inputs.hashes == parent_inputs.hashes
    assert child_inputs.tape_path is not None
    assert child_inputs.tape_path.read_bytes() == tape.read_bytes()


def test_no_checkpoint_and_foreign_parent_reject_before_allocation(
    tmp_path: Path,
) -> None:
    catalog = RunCatalog(tmp_path / "runs")
    empty = catalog.reserve(config())
    before = tree(catalog.root)
    with pytest.raises(ArchiveError):
        catalog.reserve_fork_setup(empty.attempt_id, None)
    assert tree(catalog.root) == before
    # A different catalog cannot resolve the parent's identity.
    with pytest.raises(ArchiveError):
        RunCatalog(tmp_path / "foreign").reserve_fork_setup(empty.attempt_id, None)
    assert not (tmp_path / "foreign").exists()


@pytest.mark.parametrize("damage", ["non_provider", "digest", "model", "limits"])
def test_effective_configuration_cannot_diverge_from_captured_request(
    tmp_path: Path, damage: str
) -> None:
    catalog, parent, _ = source(tmp_path)
    child = catalog.reserve_fork_setup(parent.attempt_id, 0)
    effective = {
        "non_provider": config(launch_source="cli"),
        "digest": AttemptConfig(
            "ollama",
            "test",
            7,
            "rev",
            {"provider": {"model": "tiny:latest", "model_digest": "b" * 64}},
        ),
        "model": config("other:latest"),
        "limits": config(limits={"max_ticks": 3}),
    }[damage]
    before = tree(catalog.root)
    with AttemptLease(child), pytest.raises(ArchiveError):
        catalog.complete_setup(child, effective)
    assert tree(catalog.root) == before


@pytest.mark.parametrize("requested", [False, "config", {}])
def test_non_config_request_rejected_before_allocation(
    tmp_path: Path, requested: object
) -> None:
    catalog, parent, _ = source(tmp_path)
    before = tree(catalog.root)
    with pytest.raises(ArchiveError):
        catalog.reserve_fork_setup(
            parent.attempt_id, 0, requested=cast(AttemptConfig, requested)
        )
    assert tree(catalog.root) == before


@pytest.mark.parametrize("fault", ["lock", "prewrite", "postwrite", "lock_sync"])
def test_early_allocated_fault_preserves_captured_intent_without_lock_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import living_world.archives.catalog as module

    catalog, parent, _ = source(tmp_path)
    source_before = tree(parent.directory)
    original_document = module.atomic_document
    original_lock = catalog._create_lock
    intents: list[str] = []

    def write(path: Path, value: object) -> None:
        if path.name == "setup.json":
            intents.append(canonical(value))
            if len(intents) == 1 and fault == "prewrite":
                raise OSError("before intent write")
            original_document(path, value)
            if len(intents) == 1 and fault == "postwrite":
                raise OSError("after intent replace before sync")
        else:
            original_document(path, value)

    def lock(ref: AttemptRef) -> None:
        # The complete immutable linkage must precede every lock attempt.
        assert (ref.directory / "setup.json").exists()
        if fault == "lock":
            raise OSError("lock create failed")
        original_lock(ref)
        if fault == "lock_sync":
            raise OSError("lock sync failed")

    monkeypatch.setattr(module, "atomic_document", write)
    monkeypatch.setattr(catalog, "_create_lock", lock)
    with pytest.raises(ArchiveReservationError) as error:
        catalog.reserve_fork_setup(parent.attempt_id, 0)
    child = error.value.ref
    assert child.lineage_id == parent.lineage_id
    assert catalog.setup_config(child) == config()
    fork = json.loads((child.directory / "setup.json").read_text())["fork"]
    assert fork["parent"] == [parent.attempt_id, 0]
    assert fork["input_hashes"] == dict(load_retained_inputs(parent).hashes)
    assert len(intents) == (2 if fault == "prewrite" else 1)
    assert all(intent == intents[0] for intent in intents)
    result = summary(catalog, child)
    assert (result.parent, result.failure_code, result.last_revision, result.tick) == (
        (parent.attempt_id, 0),
        "setup_failed",
        None,
        None,
    )
    if fault != "lock_sync":
        assert not (child.directory / "owner.lock").exists()
        with pytest.raises(ArchiveError), AttemptLease(child):
            pass
        assert not (child.directory / "owner.lock").exists()
    assert tree(parent.directory) == source_before
    before = tree(catalog.root)
    assert summary(catalog, child).failure_code == "setup_failed"
    assert tree(catalog.root) == before


@pytest.mark.parametrize("damage", ["malformed", "divergent", "unsafe_lock", "final"])
def test_allocated_failure_handler_never_repairs_existing_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    import living_world.archives.catalog as module

    catalog, parent, _ = source(tmp_path)
    original_document = module.atomic_document
    evidence: dict[Path, tuple[bytes, int]] = {}
    allocated: list[AttemptRef] = []

    def write(path: Path, value: object) -> None:
        original_document(path, value)
        if path.name == "setup.json" and damage in {"malformed", "divergent"}:
            if damage == "malformed":
                path.write_text("{malformed")
            else:
                change_json(
                    path,
                    lambda data: data.__setitem__(
                        "reserved_at", "2026-01-01T00:00:00+00:00"
                    ),
                )
            evidence[path] = (path.read_bytes(), path.stat().st_mtime_ns)
            raise OSError("intent write interrupted with unsafe existing metadata")

    def lock(ref: AttemptRef) -> None:
        allocated.append(ref)
        if damage == "unsafe_lock":
            (ref.directory / "owner.lock").symlink_to(parent.directory / "owner.lock")
        elif damage == "final":
            path = ref.directory / "attempt.json"
            path.write_text("do not repair")
            evidence[path] = (path.read_bytes(), path.stat().st_mtime_ns)
        raise OSError("stop allocated creation")

    monkeypatch.setattr(module, "atomic_document", write)
    monkeypatch.setattr(catalog, "_create_lock", lock)
    with pytest.raises(ArchiveReservationError) as error:
        catalog.reserve_fork_setup(parent.attempt_id, 0)
    child = error.value.ref
    assert not (child.directory / "setup_failure.json").exists()
    assert not (child.directory / "archive.sqlite3").exists()
    for path, before in evidence.items():
        assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    if damage == "unsafe_lock":
        assert (child.directory / "owner.lock").is_symlink()


def test_allocated_failure_handler_does_not_bypass_owned_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    catalog, parent, _ = source(tmp_path)
    original_lock = catalog._create_lock
    acquired, release = threading.Event(), threading.Event()
    owners: list[threading.Thread] = []

    def lock(ref: AttemptRef) -> None:
        original_lock(ref)

        def own() -> None:
            with AttemptLease(ref):
                acquired.set()
                release.wait(10)

        owner = threading.Thread(target=own)
        owners.append(owner)
        owner.start()
        assert acquired.wait(10)
        raise OSError("fault while another thread owns lock")

    monkeypatch.setattr(catalog, "_create_lock", lock)
    try:
        with pytest.raises(ArchiveReservationError) as error:
            catalog.reserve_fork_setup(parent.attempt_id, 0)
        child = error.value.ref
        assert not (child.directory / "setup_failure.json").exists()
        assert catalog.setup_config(child) == config()
        assert summary(catalog, child).parent == (parent.attempt_id, 0)
        assert summary(catalog, child).lifecycle == "initializing"
    finally:
        release.set()
        for owner in owners:
            owner.join(10)
    assert not any(owner.is_alive() for owner in owners)
    assert summary(catalog, child).lifecycle == "interrupted"


def test_persistent_allocated_io_failure_preserves_safe_ref_without_claiming_linkage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import living_world.archives.catalog as module

    catalog, parent, _ = source(tmp_path)
    before = tree(parent.directory)
    writes: list[str] = []

    def fail(path: Path, value: object) -> None:
        writes.append(path.name)
        raise OSError("all metadata writes unavailable")

    monkeypatch.setattr(module, "atomic_document", fail)
    with pytest.raises(ArchiveReservationError) as error:
        catalog.reserve_fork_setup(parent.attempt_id, 0)
    child = error.value.ref
    assert child.directory.is_dir()
    assert child.lineage_id == parent.lineage_id
    assert writes == ["setup.json", "setup.json"]
    assert not (child.directory / "setup.json").exists()
    assert not (child.directory / "setup_failure.json").exists()
    assert not (child.directory / "owner.lock").exists()
    assert summary(catalog, child).parent is None
    assert "unavailable" not in str(error.value)
    assert tree(parent.directory) == before
