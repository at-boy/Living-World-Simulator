"""Transactional, immutable run archive contracts."""

import sqlite3
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest

from living_world.archives import (
    ArchiveError,
    ArchiveFormatError,
    ArchiveRevisionConflict,
    AttemptArchive,
    AttemptConfig,
    AttemptRef,
    Checkpoint,
    JournalEntry,
)
from living_world.repositories.world_snapshot import WorldSnapshot, encode_world
from living_world.state.world_state import WorldState


def ref(tmp_path: Path) -> AttemptRef:
    return AttemptRef(uuid4().hex, uuid4().hex, tmp_path)


def config(
    mode: Literal["recorded", "ollama", "journal_replay"] = "recorded",
) -> AttemptConfig:
    return AttemptConfig(mode, "founders", 7, "revision", {})


def snapshot(tick: int = 0) -> WorldSnapshot:
    state = WorldState()
    state.tick = tick
    return encode_world(state)


def commit(
    archive: AttemptArchive,
    tick: int = 0,
    expected: int | None = None,
    entries: tuple[JournalEntry, ...] = (),
) -> Checkpoint:
    return archive.commit(
        snapshot(tick),
        expected_revision=expected,
        driver_cursor={"tick": tick},
        feedback_cursor={"pending": []},
        entries=entries,
    )


def test_checkpoint_cursor_and_outcomes_commit_together(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    entry = JournalEntry(
        "candidate_aborted", {"base_revision": 0, "reason": "cancelled"}
    )
    checkpoint = commit(archive, entries=(entry,))
    assert checkpoint.revision == 0
    assert checkpoint.driver_cursor == {"tick": 0}
    assert archive.entries() == (entry,)
    assert archive.load_world().tick == 0
    with pytest.raises(TypeError):
        checkpoint.feedback_cursor["pending"] = ()


def test_failed_commit_keeps_previous_world_and_revision(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    first = commit(archive)
    with pytest.raises(ArchiveRevisionConflict):
        commit(archive, 1, 999)
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(
            "CREATE TRIGGER fail_checkpoint BEFORE INSERT ON checkpoints WHEN NEW.revision = 1 BEGIN SELECT RAISE(ABORT, 'injected'); END"
        )
    with pytest.raises(ArchiveError):
        commit(archive, 1, 0)
    assert archive.checkpoint() == first
    assert archive.load_world().tick == 0


def test_duplicate_commit_is_idempotent(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    first = commit(archive)
    assert commit(archive) == first
    second = commit(archive, 1, 0)
    assert commit(archive) == first
    assert archive.checkpoint() == second
    with pytest.raises(ArchiveRevisionConflict):
        commit(archive, 2, None)


def test_archive_metadata_does_not_change_recorded_payload(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    checkpoint = commit(archive)
    with sqlite3.connect(archive.database_path) as connection:
        assert connection.execute(
            "SELECT schema_version,payload FROM world_snapshots WHERE id=1"
        ).fetchone() == (
            checkpoint.snapshot.schema_version,
            checkpoint.snapshot.payload,
        )
    archive.save_world(archive.load_world())
    assert archive.checkpoint().snapshot == checkpoint.snapshot


def test_readonly_never_writes(tmp_path: Path) -> None:
    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    commit(archive)
    archive.close()
    database = tmp_path / "archive.sqlite3"
    before = (database.read_bytes(), database.stat().st_mtime_ns)
    database.chmod(0o444)
    with AttemptArchive.open(identity, read_only=True) as reader:
        assert reader.load_world().tick == 0
        with pytest.raises(ArchiveError):
            commit(reader, 1, 0)
    assert (database.read_bytes(), database.stat().st_mtime_ns) == before
    database.chmod(0o644)


def test_open_missing_does_not_create(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError):
        AttemptArchive.open(ref(tmp_path))
    assert list(tmp_path.iterdir()) == []


def request_entry(request_id: str = "request", tick: int = 0) -> JournalEntry:
    return JournalEntry(
        "request_started",
        {
            "request_id": request_id,
            "base_revision": 0,
            "source_tick": tick,
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


def control(command_id: str = "step", action: str = "step") -> JournalEntry:
    return JournalEntry(
        "control_requested",
        {
            "envelope": {
                "command_id": command_id,
                "action": action,
                "expected_state_version": 0,
            }
        },
    )


def settlement(
    command_id: str = "step", revision: int = 1, status: str = "applied"
) -> JournalEntry:
    return JournalEntry(
        "control_resolved",
        {
            "receipt": {
                "command_id": command_id,
                "status": status,
                "state_version": 1,
                "revision": revision,
                "reason": None,
            }
        },
    )


def test_commands_and_step_settlement_are_atomic(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    seq = archive.append(control())
    assert archive.append(control()) == seq
    assert archive.command("step").status == "queued"
    with pytest.raises(ArchiveError):
        archive.append(settlement())
    assert archive.command("step").status == "queued"
    commit(archive, 1, 0, (settlement(),))
    assert archive.command("step").revision == 1
    assert archive.command("step").status == "applied"
    assert archive.append(settlement()) == 2
    with pytest.raises(ArchiveRevisionConflict):
        archive.append(settlement(status="rejected"))
    with pytest.raises(ArchiveRevisionConflict):
        archive.append(control(action="pause"))


def test_audit_reference_and_offered_vocabulary_validation(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    started = request_entry()
    assert archive.append(started) == archive.append(started)
    bad = JournalEntry(
        "response_validated",
        {
            "request_id": "request",
            "decision": {
                "spoken_text": None,
                "action_request": {
                    "action_key": "fly",
                    "target_label": None,
                    "rationale": "Go",
                    "arguments": {},
                },
            },
        },
    )
    with pytest.raises(ArchiveError):
        archive.append(bad)
    response = JournalEntry(
        "response_failed", {"request_id": "request", "code": "timeout"}
    )
    assert archive.append(response) == archive.append(response)
    with pytest.raises(ArchiveRevisionConflict):
        archive.append(
            JournalEntry(
                "response_failed", {"request_id": "request", "code": "transport"}
            )
        )
    resolved = JournalEntry(
        "action_resolved",
        {
            "request_id": "request",
            "base_revision": 0,
            "source_tick": 1,
            "actor_label": "Ada",
            "outcome": "no_action",
            "event_references": [],
        },
    )
    with pytest.raises(ArchiveError):
        archive.append(resolved)
    with pytest.raises(ArchiveError):
        archive.append(
            JournalEntry(
                "response_failed", {"request_id": "unknown", "code": "timeout"}
            )
        )


@pytest.mark.parametrize(
    "settings",
    [
        {"token": "secret"},
        {"provider": {"password": "secret"}},
        {"provider": {"base_url": "https://example.com"}},
        {"provider": {"base_url": "http://user:secret@localhost"}},
        {"provider": {"base_url": "http://localhost/?token=secret"}},
        {"limits": {"max_ticks": True}},
        {"limits": {"max_requests": 0}},
        {"provider": {"temperature": float("nan")}},
        {"driver_format": True},
        {"provider": {"seed": False}},
        {"limits": {"unknown": 1}},
    ],
)
def test_config_rejects_nonsecret_allowlist_violations(
    settings: dict[str, object],
) -> None:
    with pytest.raises(ArchiveError):
        AttemptConfig("recorded", "founders", 0, "revision", settings)


@pytest.mark.parametrize(
    "kind,payload",
    [
        ("response_failed", {"request_id": "x", "code": "timeout", "body": "secret"}),
        ("candidate_aborted", {"base_revision": True, "reason": "bad"}),
        (
            "attempt_finished",
            {"lifecycle": "running", "outcome": None, "last_revision": None},
        ),
        (
            "control_requested",
            {
                "envelope": {
                    "command_id": "x",
                    "action": "step",
                    "expected_state_version": False,
                }
            },
        ),
    ],
)
def test_closed_journal_schemas(kind: str, payload: dict[str, object]) -> None:
    with pytest.raises(ArchiveError):
        JournalEntry(kind, payload)


def test_reading_corruption_and_future_format_never_repairs(tmp_path: Path) -> None:
    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    commit(archive)
    archive.close()
    with sqlite3.connect(tmp_path / "archive.sqlite3") as connection:
        connection.execute(
            "UPDATE archive_meta SET payload=json_set(payload,'$.format',2)"
        )
    before = (tmp_path / "archive.sqlite3").read_bytes()
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(identity, read_only=True)
    assert (tmp_path / "archive.sqlite3").read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE checkpoints SET digest='bad'",
        'UPDATE checkpoints SET driver_cursor=\'{"x":1,"x":2}\'',
        "UPDATE checkpoints SET feedback_cursor='{\"x\":NaN}'",
        "UPDATE world_snapshots SET payload='{}'",
        "UPDATE checkpoints SET fingerprint='bad'",
        'UPDATE journal SET payload=\'{"request_id":"missing","code":"timeout"}\'',
        "UPDATE commands SET envelope_hash='bad'",
    ],
)
def test_corrupt_rows_fail_closed(tmp_path: Path, mutation: str) -> None:
    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    commit(archive)
    archive.append(control())
    archive.close()
    with sqlite3.connect(tmp_path / "archive.sqlite3") as connection:
        connection.execute(mutation)
    with pytest.raises(ArchiveError):
        AttemptArchive.open(identity, read_only=True)


def test_no_initial_world_and_live_compatibility_rejected(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config("ollama"))
    assert archive.latest_revision is None
    with pytest.raises(ArchiveError):
        archive.load_world()
    with pytest.raises(ArchiveError):
        archive.save_world(WorldState())


def test_lifecycle_and_audit_roll_back_together(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    with pytest.raises(ArchiveError):
        archive.record((control(), settlement()), lifecycle="paused")
    assert archive.entries() == ()
    assert archive.lifecycle() == ()
    archive.record((), lifecycle="paused", reason="operator")
    archive.append(
        JournalEntry(
            "attempt_finished",
            {"lifecycle": "stopped", "outcome": None, "last_revision": None},
        )
    )
    assert tuple(item["state"] for item in archive.lifecycle()) == ("paused", "stopped")


def test_writer_thread_and_symlink_escape_rejected(tmp_path: Path) -> None:
    import concurrent.futures

    archive = AttemptArchive.create(ref(tmp_path), config())
    with concurrent.futures.ThreadPoolExecutor() as pool, pytest.raises(ArchiveError):
        pool.submit(archive.record, ()).result()
    linked = tmp_path / "linked"
    linked.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ArchiveError):
        AttemptArchive.open(
            AttemptRef(archive.ref.lineage_id, archive.ref.attempt_id, linked)
        )


@pytest.mark.parametrize("after_commit", [False, True])
def test_process_termination_keeps_complete_transaction(
    tmp_path: Path, after_commit: bool
) -> None:
    import subprocess
    import sys

    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    commit(archive)
    archive.append(control())
    archive.append(request_entry())
    archive.append(
        JournalEntry("response_failed", {"request_id": "request", "code": "timeout"})
    )
    archive.close()
    # Child reaches a real SQLite boundary, reports it through a pipe, then
    # blocks reading stdin. Parent kills it deterministically without sleeps.
    program = """
import sys, sqlite3
from pathlib import Path
from typing import Literal
from living_world.archives import AttemptArchive, AttemptRef, JournalEntry
from living_world.repositories.world_snapshot import WorldSnapshot, encode_world
from living_world.state.world_state import WorldState
identity = AttemptRef(sys.argv[1],sys.argv[2],Path(sys.argv[3]))
after = sys.argv[4] == 'True'
original = sqlite3.connect
class BoundaryConnection(sqlite3.Connection):
    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> sqlite3.Cursor:
        result = super().execute(sql,parameters)
        if not after and sql.startswith('INSERT INTO checkpoints'):
            print('boundary',flush=True)
            sys.stdin.read()
        return result
    def commit(self) -> None:
        super().commit()
        if after:
            print('boundary',flush=True)
            sys.stdin.read()
sqlite3.connect = lambda *args, **kwargs: original(*args, factory=BoundaryConnection, **kwargs)
archive = AttemptArchive.open(identity)
state=WorldState(); state.tick=1
entry=JournalEntry('control_resolved', {'receipt': {'command_id':'step','status':'applied','state_version':1,'revision':1,'reason':None}})
action=JournalEntry('action_resolved', {'base_revision':0,'source_tick':0,'actor_label':'Ada','request_id':'request','outcome':'no_action','event_references':[]})
archive.commit(encode_world(state),expected_revision=0,driver_cursor={'tick':1},feedback_cursor={'pending':['step']},entries=(entry,action))
"""
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            program,
            identity.lineage_id,
            identity.attempt_id,
            str(tmp_path),
            str(after_commit),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout.readline().strip() == "boundary"
        process.kill()
        process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
    with AttemptArchive.open(identity) as recovered:
        checkpoint = recovered.checkpoint()
        assert checkpoint.revision == (1 if after_commit else 0)
        assert recovered.load_world().tick == checkpoint.revision
        assert checkpoint.driver_cursor["tick"] == checkpoint.revision
        assert recovered.command("step").status == (
            "applied" if after_commit else "queued"
        )
        assert len(recovered.entries()) == (5 if after_commit else 3)
        assert checkpoint.feedback_cursor["pending"] == (
            ("step",) if after_commit else ()
        )
        assert (
            any(entry.kind == "action_resolved" for entry in recovered.entries())
            == after_commit
        )


def test_deleted_checkpoint_audit_is_corrupt(tmp_path: Path) -> None:
    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    entry = JournalEntry(
        "candidate_aborted", {"base_revision": 0, "reason": "cancelled"}
    )
    commit(archive, entries=(entry,))
    archive.close()
    with sqlite3.connect(tmp_path / "archive.sqlite3") as connection:
        connection.execute("DELETE FROM journal")
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(identity, read_only=True)


def test_live_metadata_corruption_is_rejected(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(
            "UPDATE archive_meta SET payload=json_set(payload,'$.format',json('true'))"
        )
    with pytest.raises(ArchiveFormatError):
        archive.checkpoint()


def test_commit_errors_wrap_non_snapshot_and_missing_schema(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    with pytest.raises(ArchiveFormatError):
        archive.commit(
            None,
            expected_revision=None,
            driver_cursor={},
            feedback_cursor={},
            entries=(),
        )
    with pytest.raises(ArchiveError):
        archive.record((), lifecycle=[])


def test_queued_receipt_uses_admission_revision_after_reopen(tmp_path: Path) -> None:
    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    commit(archive)
    commit(archive, 1, 0)
    archive.append(control("pause", "pause"))
    assert archive.command("pause").revision == 1
    archive.close()
    with AttemptArchive.open(identity) as reopened:
        assert reopened.command("pause").revision == 1
    with sqlite3.connect(tmp_path / "archive.sqlite3") as connection:
        connection.execute("UPDATE journal SET revision_context=999")
    with pytest.raises(ArchiveError):
        AttemptArchive.open(identity, read_only=True)


def test_compatibility_save_wraps_validation_errors(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    with pytest.raises(ArchiveError):
        archive.save_world(object())


def test_readonly_rejects_all_writer_paths_and_never_creates_schema(
    tmp_path: Path,
) -> None:
    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    commit(archive)
    archive.close()
    before = archive.database_path.read_bytes()
    with AttemptArchive.open(identity, read_only=True) as reader:
        for write in (
            lambda: reader.record(()),
            lambda: reader.append(control()),
            lambda: reader.save_world(WorldState()),
        ):
            with pytest.raises(ArchiveError):
                write()
    assert archive.database_path.read_bytes() == before
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute("DROP TABLE lifecycle")
    before = archive.database_path.read_bytes()
    with pytest.raises(ArchiveError):
        AttemptArchive.open(identity, read_only=True)
    assert archive.database_path.read_bytes() == before


def test_frozen_input_records_and_legacy_snapshot_bytes(tmp_path: Path) -> None:
    from living_world.repositories.world_snapshot import WorldSnapshot

    values = {"limits": {"max_ticks": None}}
    configuration = AttemptConfig("recorded", "founders", -1, "revision", values)
    values["limits"]["max_ticks"] = 1
    assert configuration.settings["limits"]["max_ticks"] is None
    archive = AttemptArchive.create(ref(tmp_path), configuration)
    # A supported minimal schema-one payload retains its exact original bytes.
    legacy = WorldSnapshot(1, " " + snapshot(3).payload + " ")
    saved = archive.commit(
        legacy, expected_revision=None, driver_cursor={}, feedback_cursor={}, entries=()
    )
    assert saved.snapshot == legacy
    assert archive.load_world().tick == 3


def test_settled_receipt_cannot_authorize_a_new_checkpoint(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    archive.append(control())
    original = commit(archive, 1, 0, (settlement(),))
    before = (archive.entries(), archive.command("step"))
    with pytest.raises(ArchiveRevisionConflict):
        commit(archive, 2, 1, (settlement(),))
    assert archive.checkpoint() == original
    assert archive.load_world().tick == 1
    assert (archive.entries(), archive.command("step")) == before
    assert commit(archive, 1, 0, (settlement(),)) == original


def test_persisted_operation_cannot_reuse_prior_settlement(tmp_path: Path) -> None:
    import hashlib
    import json

    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    commit(archive)
    archive.append(control())
    commit(archive, 1, 0, (settlement(),))
    commit(archive, 2, 1)
    archive.close()
    with sqlite3.connect(archive.database_path) as connection:
        operation = json.loads(
            connection.execute(
                "SELECT operation FROM checkpoints WHERE revision=2"
            ).fetchone()[0]
        )
        entry = settlement()
        operation["entries"] = [{"kind": entry.kind, "payload": dict(entry.payload)}]
        # The forged document is otherwise canonical and correctly hashed.
        operation["entries"][0]["payload"]["receipt"] = dict(entry.payload["receipt"])
        encoded = json.dumps(operation, sort_keys=True, separators=(",", ":"))
        connection.execute(
            "UPDATE checkpoints SET operation=?,fingerprint=? WHERE revision=2",
            (encoded, hashlib.sha256(encoded.encode()).hexdigest()),
        )
    before = archive.database_path.read_bytes()
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(identity, read_only=True)
    assert archive.database_path.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM lifecycle",
        "UPDATE lifecycle SET state='failed'",
        "UPDATE lifecycle SET reason='changed'",
        "UPDATE lifecycle SET journal_sequence=NULL",
        "UPDATE lifecycle SET journal_sequence=999",
    ],
)
def test_terminal_journal_requires_matching_lifecycle_effect(
    tmp_path: Path, mutation: str
) -> None:
    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    archive.append(
        JournalEntry(
            "attempt_finished",
            {"lifecycle": "stopped", "outcome": None, "last_revision": None},
        )
    )
    archive.close()
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(mutation)
    before = archive.database_path.read_bytes()
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(identity, read_only=True)
    assert archive.database_path.read_bytes() == before


def test_each_terminal_audit_has_its_own_private_lifecycle_link(tmp_path: Path) -> None:
    identity = ref(tmp_path)
    archive = AttemptArchive.create(identity, config())
    archive.record((), lifecycle="paused", reason="operator")
    entry = JournalEntry(
        "attempt_finished",
        {"lifecycle": "stopped", "outcome": None, "last_revision": None},
    )
    assert archive.append(entry) != archive.append(entry)
    assert len(archive.lifecycle()) == 3
    assert all(
        set(row) == {"sequence", "state", "reason", "timestamp"}
        for row in archive.lifecycle()
    )
    with sqlite3.connect(archive.database_path) as connection:
        assert connection.execute(
            "SELECT journal_sequence FROM lifecycle ORDER BY sequence"
        ).fetchall() == [(None,), (1,), (2,)]
    archive.close()
    with AttemptArchive.open(identity, read_only=True) as reader:
        assert len(reader.lifecycle()) == 3
