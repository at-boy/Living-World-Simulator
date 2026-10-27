"""Transactional, immutable run archive contracts."""

import sqlite3
from dataclasses import asdict
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
    CommandReceipt,
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
            "UPDATE archive_meta SET payload=json_set(payload,'$.format',3)"
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
        JournalEntry(
            "response_validated",
            {
                "request_id": "request",
                "decision": {"spoken_text": "Waiting here", "action_request": None},
            },
        )
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


def test_control_actual_admission_version_survives_future_envelope(
    tmp_path: Path,
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    requested = JournalEntry(
        "control_requested",
        {
            "envelope": {
                "command_id": "future",
                "action": "step",
                "expected_state_version": 999,
            },
            "admitted_state_version": 3,
        },
    )
    archive.record((requested,))
    assert archive.command("future").state_version == 3
    rejected = CommandReceipt("future", "rejected", 3, 0, "stale_state_version")
    archive.record((JournalEntry("control_resolved", {"receipt": asdict(rejected)}),))
    with AttemptArchive.open(archive.ref, read_only=True) as reopened:
        assert reopened.command("future") == rejected


def test_recorded_zero_tick_configuration_and_other_modes() -> None:
    assert (
        AttemptConfig(
            "recorded", "test", 1, "test", {"limits": {"max_ticks": 0}}
        ).settings["limits"]["max_ticks"]
        == 0
    )
    for mode in ("ollama", "journal_replay"):
        with pytest.raises(ArchiveFormatError):
            AttemptConfig(mode, "test", 1, "test", {"limits": {"max_ticks": 0}})


def validated(request_id: str = "request", *, action: bool = False) -> JournalEntry:
    return JournalEntry(
        "response_validated",
        {
            "request_id": request_id,
            "decision": {
                "spoken_text": "Waiting here",
                "action_request": (
                    {
                        "action_key": "wait",
                        "target_label": None,
                        "rationale": "Wait",
                        "arguments": {},
                    }
                    if action
                    else None
                ),
            },
        },
    )


def resolution(**changes: object) -> JournalEntry:
    return JournalEntry(
        "action_resolved",
        {
            "request_id": "request",
            "base_revision": 0,
            "source_tick": 0,
            "actor_label": "Ada",
            "outcome": "no_action",
            "event_references": [],
            **changes,
        },
    )


def imported(**changes: object) -> JournalEntry:
    return JournalEntry(
        "response_reused",
        {
            **request_entry().payload,
            "decision": validated().payload["decision"],
            "source": {
                "attempt_id": "12345678123442348234123456789abc",
                "request_id": "old",
                "boundary": {"sequence": 3, "digest": "c" * 64},
            },
            **changes,
        },
    )


def test_journal_prefix_records_and_fork_point_are_immutable(tmp_path: Path) -> None:
    import hashlib
    from dataclasses import FrozenInstanceError

    from living_world.archives import JournalBoundary, JournalRecord
    from living_world.archives.model import canonical

    archive = AttemptArchive.create(ref(tmp_path), config())
    empty = JournalBoundary(0, hashlib.sha256(b"[]").hexdigest())
    assert archive.journal_boundary() == empty
    assert archive.journal_records(through_sequence=0) == ()
    with pytest.raises(ArchiveError):
        archive.fork_point()
    commit(archive)
    archive.append(request_entry())
    commit(archive, 1, 0, (validated(), resolution()))
    records = archive.journal_records()
    assert records == (
        JournalRecord(1, request_entry(), None, 0),
        JournalRecord(2, validated(), 1, 1),
        JournalRecord(3, resolution(), 1, 1),
    )
    expected = hashlib.sha256(
        canonical(
            [
                {
                    "sequence": r.sequence,
                    "kind": r.entry.kind,
                    "payload": r.entry.payload,
                    "checkpoint_revision": r.checkpoint_revision,
                    "revision_context": r.revision_context,
                }
                for r in records
            ]
        ).encode()
    ).hexdigest()
    assert archive.journal_boundary() == JournalBoundary(3, expected)
    assert archive.fork_point(0).checkpoint == archive.checkpoint(0)
    assert archive.fork_point(0).journal_boundary == archive.journal_boundary()
    assert archive.journal_records(through_sequence=1) == records[:1]
    assert archive.journal_boundary(through_sequence=0) == empty
    with pytest.raises(FrozenInstanceError):
        records[0].sequence = 99
    with pytest.raises(TypeError):
        records[0].entry.payload["request"]["identity"] = "Other"
    before = {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()
    }
    reader = AttemptArchive.open(archive.ref, read_only=True)
    reader.journal_records()
    reader.journal_boundary()
    reader.fork_point()
    assert {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()
    } == before


@pytest.mark.parametrize("bound", [True, -1, 1.0, "1", 9])
def test_journal_prefix_bounds_reject_invalid_or_missing(
    tmp_path: Path, bound: object
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    archive.append(request_entry())
    for accessor in (archive.journal_records, archive.journal_boundary):
        with pytest.raises(ArchiveError):
            accessor(through_sequence=bound)


@pytest.mark.parametrize("stage", ["pending", "failed", "validated"])
def test_action_resolution_requires_checkpoint_and_valid_response(
    tmp_path: Path, stage: str
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    archive.append(request_entry())
    if stage == "failed":
        archive.append(
            JournalEntry(
                "response_failed", {"request_id": "request", "code": "timeout"}
            )
        )
    elif stage == "validated":
        archive.append(validated())
    before = archive.entries()
    with pytest.raises(ArchiveError):
        archive.append(resolution())
    with pytest.raises(ArchiveError):
        archive.record((resolution(),))
    if stage != "validated":
        with pytest.raises(ArchiveError):
            commit(archive, 1, 0, (resolution(),))
        assert archive.checkpoint().revision == 0
        assert archive.entries() == before
    else:
        commit(archive, 1, 0, (resolution(),))
        with pytest.raises(ArchiveError):
            commit(archive, 2, 1, (resolution(),))
        assert archive.checkpoint().revision == 1


@pytest.mark.parametrize(
    "base_tick,request_tick,committed_tick,outcome,action",
    [
        (1, 0, 1, "no_action", False),
        (0, 0, 2, "no_action", False),
        (0, 1, 2, "no_action", False),
        (0, 0, 1, "accepted", False),
        (0, 0, 1, "no_action", True),
    ],
)
def test_invalid_action_tick_and_outcome_roll_back(
    tmp_path: Path,
    base_tick: int,
    request_tick: int,
    committed_tick: int,
    outcome: str,
    action: bool,
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    first = commit(archive, base_tick)
    archive.record((request_entry(tick=request_tick), validated(action=action)))
    before = archive.entries()
    with pytest.raises(ArchiveError):
        commit(
            archive,
            committed_tick,
            0,
            (resolution(source_tick=request_tick, outcome=outcome),),
        )
    assert archive.checkpoint() == first
    assert archive.entries() == before


def test_response_import_is_validated_local_identity_without_http_start(
    tmp_path: Path,
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    reuse = imported(content_digest="d" * 64, elapsed_seconds=0.5)
    assert archive.append(reuse) == archive.append(reuse)
    assert not any(e.kind == "request_started" for e in archive.entries())
    for divergent in (
        request_entry(),
        imported(input_fingerprint="e" * 64),
        validated(),
        JournalEntry("response_failed", {"request_id": "request", "code": "timeout"}),
    ):
        with pytest.raises(ArchiveError):
            archive.append(divergent)
    commit(archive, 1, 0, (resolution(),))
    assert archive.load_world().tick == 1
    with AttemptArchive.open(archive.ref, read_only=True) as reader:
        assert reader.entries() == (reuse, resolution())


@pytest.mark.parametrize("kind", ["response_validated", "response_reused"])
@pytest.mark.parametrize(
    "changes",
    [
        {"elapsed_seconds": True},
        {"elapsed_seconds": -1},
        {"elapsed_seconds": float("nan")},
        {"elapsed_seconds": float("inf")},
        {"content_digest": "X" * 64},
        {"unexpected": 3},
    ],
)
def test_response_provenance_rejects_invalid_values(
    kind: str, changes: dict[str, object]
) -> None:
    base = validated() if kind == "response_validated" else imported()
    with pytest.raises(ArchiveError):
        JournalEntry(kind, {**base.payload, **changes})


def test_response_provenance_legacy_and_optional_values(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    archive.append(request_entry())
    response = JournalEntry(
        "response_validated",
        {**validated().payload, "content_digest": "d" * 64, "elapsed_seconds": 0},
    )
    archive.append(response)
    assert archive.entries()[-1] == response


def test_response_import_checks_offered_vocabulary_and_identity(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    bad_decision = {
        "spoken_text": None,
        "action_request": {
            "action_key": "fly",
            "target_label": None,
            "rationale": "Fly",
            "arguments": {},
        },
    }
    with pytest.raises(ArchiveError):
        archive.append(imported(decision=bad_decision))
    archive.append(request_entry())
    with pytest.raises(ArchiveError):
        archive.append(imported())


def test_journal_gaps_are_preserved_and_missing_bounds_rejected(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    archive.append(
        JournalEntry("candidate_aborted", {"base_revision": 0, "reason": "one"})
    )
    archive.append(
        JournalEntry("candidate_aborted", {"base_revision": 0, "reason": "two"})
    )
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute("DELETE FROM journal WHERE sequence=1")
    assert tuple(r.sequence for r in archive.journal_records()) == (2,)
    assert archive.journal_boundary().sequence == 2
    with pytest.raises(ArchiveError):
        archive.journal_boundary(through_sequence=1)


@pytest.mark.parametrize(
    "mutation", ["standalone", "failed", "pending", "wrong_owner", "wrong_slot"]
)
def test_raw_action_journal_corruption_rejected_on_load(
    tmp_path: Path, mutation: str
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    archive.record((request_entry(), validated()))
    commit(archive, 1, 0, (resolution(),))
    archive.close()
    with sqlite3.connect(tmp_path / "archive.sqlite3") as connection:
        if mutation == "standalone":
            connection.execute(
                "UPDATE journal SET checkpoint_revision=NULL WHERE kind='action_resolved'"
            )
        elif mutation == "wrong_owner":
            connection.execute(
                "UPDATE journal SET checkpoint_revision=0,revision_context=0 WHERE kind='action_resolved'"
            )
        elif mutation == "failed":
            connection.execute(
                "UPDATE journal SET kind='response_failed',payload=? WHERE kind='response_validated'",
                ('{"request_id":"request","code":"timeout"}',),
            )
        elif mutation == "pending":
            connection.execute("DELETE FROM journal WHERE kind='response_validated'")
        else:
            connection.execute(
                "UPDATE journal SET payload=json_set(payload,'$.source_tick',1) WHERE kind='request_started'"
            )
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(archive.ref, read_only=True)


@pytest.mark.parametrize("outcome", ["accepted", "rejected"])
def test_action_outcomes_and_atomic_request_response_transaction(
    tmp_path: Path, outcome: str
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    result = commit(
        archive,
        1,
        0,
        (request_entry(), validated(action=True), resolution(outcome=outcome)),
    )
    assert (
        commit(
            archive,
            1,
            0,
            (request_entry(), validated(action=True), resolution(outcome=outcome)),
        )
        == result
    )
    assert all(r.checkpoint_revision == 1 for r in archive.journal_records())


@pytest.mark.parametrize(
    "record,arguments",
    [
        ("JournalBoundary", (True, "a" * 64)),
        ("JournalBoundary", (-1, "a" * 64)),
        ("JournalBoundary", (0, "A" * 64)),
        ("JournalRecord", (0, request_entry(), None, None)),
        ("JournalRecord", (1, request_entry(), True, None)),
        ("JournalRecord", (1, request_entry(), None, -1)),
        ("JournalRecord", (1, object(), None, None)),
        ("ForkPoint", (object(), object())),
    ],
)
def test_new_record_constructors_reject_bad_types(
    record: str, arguments: tuple[object, ...]
) -> None:
    from living_world import archives

    with pytest.raises(ArchiveError):
        getattr(archives, record)(*arguments)


@pytest.mark.parametrize(
    "source",
    [
        None,
        {},
        {
            "attempt_id": "bad",
            "request_id": "old",
            "boundary": {"sequence": 1, "digest": "a" * 64},
        },
        {
            "attempt_id": "12345678123442348234123456789abc",
            "request_id": "old",
            "boundary": {"sequence": True, "digest": "a" * 64},
        },
        {
            "attempt_id": "12345678123442348234123456789abc",
            "request_id": "old",
            "boundary": {"sequence": 1, "digest": "a" * 64},
            "extra": 3,
        },
    ],
)
def test_import_source_schema_is_closed(source: object) -> None:
    with pytest.raises(ArchiveError):
        imported(source=source)


def test_elapsed_seconds_rejects_unrepresentably_large_integer() -> None:
    with pytest.raises(ArchiveError):
        JournalEntry(
            "response_validated", {**validated().payload, "elapsed_seconds": 10**1000}
        )


def test_fork_point_uses_one_snapshot_during_source_append(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    archive.append(request_entry())
    expected = archive.journal_boundary()
    # WAL enables a real concurrent writer while the reader keeps its snapshot.
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    reader = AttemptArchive.open(archive.ref, read_only=True)
    original = reader._validate

    def validate_then_append(connection: sqlite3.Connection) -> tuple[Checkpoint, ...]:
        checkpoints = original(connection)

        def append() -> None:
            with AttemptArchive.open(archive.ref) as writer:
                commit(writer, 1, 0, (validated(), resolution()))

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(append).result(timeout=10)
        return checkpoints

    monkeypatch.setattr(reader, "_validate", validate_then_append)
    point = reader.fork_point()
    assert point.checkpoint.revision == 0
    assert point.journal_boundary == expected
    assert archive.checkpoint().revision == 1
    assert archive.journal_boundary() != expected


@pytest.mark.parametrize(
    "changes", [{"actor_label": "Other"}, {"base_revision": 1}, {"source_tick": 1}]
)
def test_mismatching_action_slot_rolls_back_commands_and_world(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    first = commit(archive)
    archive.record((request_entry(), validated(), control()))
    before = archive.entries()
    with pytest.raises(ArchiveError):
        commit(archive, 1, 0, (settlement(), resolution(**changes)))
    assert archive.entries() == before
    assert archive.checkpoint() == first
    assert archive.command("step").status == "queued"


def test_two_requests_cannot_resolve_same_actor_slot(tmp_path: Path) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    commit(archive)
    archive.record(
        (request_entry(), validated(), request_entry("second"), validated("second"))
    )
    with pytest.raises(ArchiveError):
        commit(archive, 1, 0, (resolution(), resolution(request_id="second")))
    assert archive.checkpoint().revision == 0
    assert not any(e.kind == "action_resolved" for e in archive.entries())


@pytest.mark.parametrize("first_elapsed,second_elapsed", [(0, 0.0), (0.0, 0)])
def test_import_identity_requires_identical_canonical_numeric_provenance(
    tmp_path: Path, first_elapsed: float, second_elapsed: float
) -> None:
    archive = AttemptArchive.create(ref(tmp_path), config())
    checkpoint = commit(archive)
    first = imported(elapsed_seconds=first_elapsed)
    sequence = archive.append(first)
    assert archive.append(imported(elapsed_seconds=first_elapsed)) == sequence
    boundary = archive.journal_boundary()
    records = archive.journal_records()
    candidate = JournalEntry(
        "candidate_aborted", {"base_revision": 0, "reason": "must roll back"}
    )
    with pytest.raises(ArchiveRevisionConflict):
        archive.record((candidate, imported(elapsed_seconds=second_elapsed)))
    assert archive.journal_records() == records
    assert archive.journal_boundary() == boundary
    assert archive.checkpoint() == checkpoint
    assert archive.load_world().tick == 0
    assert archive.append(first) == sequence
