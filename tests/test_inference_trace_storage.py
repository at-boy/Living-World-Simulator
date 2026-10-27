"""Privileged exact-byte storage, immutable metadata and sealed-prefix access."""

import hashlib
import importlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path
from uuid import uuid4

import pytest

from living_world import archives
from living_world.archives import (
    ArchiveError,
    ArchiveFormatError,
    ArchiveRevisionConflict,
    AttemptArchive,
    AttemptConfig,
    AttemptRef,
    JournalEntry,
)
from living_world.archives.model import canonical, loads, plain
from living_world.repositories.world_snapshot import encode_world
from living_world.state.world_state import WorldState

TIMESTAMPS = (
    "dispatch_started_at",
    "worker_started_at",
    "http_started_at",
    "headers_received_at",
    "first_body_byte_at",
    "read_finished_at",
    "settled_at",
)
DURATIONS = (
    "broker_seconds",
    "worker_seconds",
    "http_seconds",
    "headers_seconds",
    "first_byte_seconds",
    "body_read_seconds",
)


def blob(body: bytes) -> archives.InferenceBlob:
    assert hasattr(archives, "InferenceBlob"), "exact-byte blob value is missing"
    return archives.InferenceBlob(body)


def request_trace(body: bytes = b"{}", **changes: object) -> dict[str, object]:
    return {
        "format": 1,
        "provider_kind": "ollama",
        "model": "local",
        "model_digest": None,
        "method": "POST",
        "url": "http://127.0.0.1:11434/api/generate",
        "headers": {"Content-Type": "application/json"},
        "body_digest": hashlib.sha256(body).hexdigest(),
        "body_length": len(body),
        "prepared_at": "2026-10-27T12:00:00+00:00",
        "timeout_seconds": 10,
        "max_response_bytes": 8,
        **changes,
    }


def response_trace(
    body: bytes | None = b"\xff\x00", **changes: object
) -> dict[str, object]:
    return {
        "format": 1,
        "body_state": "unavailable" if body is None else "complete",
        "body_digest": None if body is None else hashlib.sha256(body).hexdigest(),
        "body_length": None if body is None else len(body),
        "http_status": 200,
        "timestamps": dict.fromkeys(TIMESTAMPS),
        "durations": dict.fromkeys(DURATIONS),
        **changes,
    }


def request(trace: object = None, *, request_id: str = "req") -> JournalEntry:
    payload = {
        "request_id": request_id,
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
            "actions": [],
        },
    }
    if trace is not None:
        payload["request_trace"] = trace
    return JournalEntry("request_started", payload)


def response(trace: object) -> JournalEntry:
    return JournalEntry(
        "response_failed",
        {"request_id": "req", "code": "invalid_response", "response_trace": trace},
    )


def create(path: Path) -> AttemptArchive:
    path.mkdir(exist_ok=True)
    result = AttemptArchive.create(
        AttemptRef(uuid4().hex, uuid4().hex, path),
        AttemptConfig("recorded", "founders", 7, "revision", {}),
    )
    result.commit(
        encode_world(WorldState()),
        expected_revision=None,
        driver_cursor={},
        feedback_cursor={},
        entries=(),
    )
    return result


def legacy(archive: AttemptArchive) -> AttemptArchive:
    with sqlite3.connect(archive.database_path) as connection:
        meta = plain(
            loads(connection.execute("SELECT payload FROM archive_meta").fetchone()[0])
        )
        meta["format"] = 1
        connection.execute("UPDATE archive_meta SET payload=?", (canonical(meta),))
        connection.execute("DROP TABLE IF EXISTS inference_blobs")
    return AttemptArchive.open(archive.ref)


def test_blob_is_exact_bytes_frozen_and_content_addressed() -> None:
    value = blob(b"\xff\x00")
    assert value.body == b"\xff\x00"
    assert value.sha256 == hashlib.sha256(value.body).hexdigest()
    assert value.byte_length == 2
    with pytest.raises(FrozenInstanceError):
        value.body = b"x"
    for invalid in ("text", bytearray(), memoryview(b""), None):
        with pytest.raises(ArchiveFormatError):
            blob(invalid)
    assert blob(b"").byte_length == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"extra": 1},
        {"format": True},
        {"format": 2},
        {"provider_kind": "remote"},
        {"model": " "},
        {"model_digest": ""},
        {"method": "GET"},
        {"url": "https://localhost/api/generate"},
        {"url": "http://evil.test/api/generate"},
        {"url": "http://user@localhost/api/generate"},
        {"url": "http://localhost/api/generate?q=1"},
        {"url": "http://localhost/api/generate#x"},
        {"url": "http://localhost/api/generate;x"},
        {"url": "http://localhost/v1/chat/completions"},
        {"headers": {"Content-Type": "application/json", "Authorization": "secret"}},
        {"body_digest": "A" * 64},
        {"body_length": True},
        {"body_length": 0},
        {"body_length": 16001},
        {"prepared_at": "2026-10-27T12:00:00"},
        {"prepared_at": "2026-10-27T12:00:00+01:00"},
        {"prepared_at": "bad"},
        {"timeout_seconds": True},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("inf")},
        {"max_response_bytes": True},
        {"max_response_bytes": 0},
    ],
)
def test_request_metadata_rejects_invalid_closed_values(
    changes: dict[str, object],
) -> None:
    module = importlib.import_module("living_world.archives.inference")
    with pytest.raises(ArchiveFormatError):
        module.validate_request_trace(request_trace(**changes))


def test_metadata_is_deeply_frozen_and_supports_both_providers() -> None:
    module = importlib.import_module("living_world.archives.inference")
    original = request_trace(
        provider_kind="llama_cpp",
        url="http://[::1]:8080/v1/chat/completions",
        model_digest="actual-pin",
    )
    value = module.validate_request_trace(original)
    original["headers"]["Content-Type"] = "changed"
    assert value["headers"]["Content-Type"] == "application/json"
    with pytest.raises(TypeError):
        value["headers"]["Content-Type"] = "changed"
    with pytest.raises(ArchiveFormatError):
        module.validate_request_trace(
            {k: v for k, v in request_trace().items() if k != "model"}
        )
    assert module.validate_response_trace(response_trace(b""))["body_length"] == 0
    assert module.validate_response_trace(response_trace(None))["body_length"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"extra": 0},
        {"format": True},
        {"body_state": "unknown"},
        {"body_state": "unavailable"},
        {"body_digest": None},
        {"body_length": None},
        {"body_digest": "bad"},
        {"body_length": -1},
        {"body_length": True},
        {"http_status": True},
        {"http_status": 99},
        {"http_status": 600},
        {"timestamps": {}},
        {"durations": {}},
        {"timestamps": dict.fromkeys(TIMESTAMPS, "2026-10-27")},
        {"durations": dict.fromkeys(DURATIONS, True)},
        {"durations": dict.fromkeys(DURATIONS, -1)},
        {"durations": dict.fromkeys(DURATIONS, float("nan"))},
    ],
)
def test_response_metadata_rejects_invalid_closed_values(
    changes: dict[str, object],
) -> None:
    module = importlib.import_module("living_world.archives.inference")
    with pytest.raises(ArchiveFormatError):
        module.validate_response_trace(response_trace(**changes))


@pytest.mark.parametrize(
    "body,state",
    [
        (b"\xff\x00", "complete"),
        (b"", "complete"),
        (b"x" * 9, "incomplete"),
        (None, "unavailable"),
    ],
)
def test_binary_response_roundtrip_and_prefix_seal(
    tmp_path: Path, body: bytes | None, state: str
) -> None:
    archive = create(tmp_path)
    assert archive.format_version == 2
    first = archive.append(request(request_trace()), inference_blobs=(blob(b"{}"),))
    seal = archive.journal_boundary()
    archive.append(
        response(response_trace(body, body_state=state)),
        inference_blobs=() if body is None else (blob(body),),
    )
    assert archive.journal_boundary(through_sequence=first) == seal
    assert archive.inference_blobs((blob(b"{}").sha256,), through_sequence=first) == (
        blob(b"{}"),
    )
    if body is not None:
        assert archive.inference_blobs((blob(body).sha256,)) == (blob(body),)
        with pytest.raises(ArchiveFormatError):
            archive.inference_blobs((blob(body).sha256,), through_sequence=first)
    before = archive.database_path.read_bytes()
    reader = AttemptArchive.open(archive.ref, read_only=True)
    assert reader.inference_blobs((blob(b"{}").sha256,)) == (blob(b"{}"),)
    assert archive.database_path.read_bytes() == before


def test_atomic_rollback_and_idempotence(tmp_path: Path) -> None:
    archive = create(tmp_path)
    entry = request(request_trace())
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(
            "CREATE TRIGGER fail_journal BEFORE INSERT ON journal BEGIN SELECT RAISE(ABORT, 'injected'); END"
        )
    with pytest.raises(ArchiveError):
        archive.append(entry, inference_blobs=(blob(b"{}"),))
    assert archive.entries() == ()
    with sqlite3.connect(archive.database_path) as connection:
        assert (
            connection.execute("SELECT count(*) FROM inference_blobs").fetchone()[0]
            == 0
        )
        connection.execute("DROP TRIGGER fail_journal")
    sequence = archive.append(entry, inference_blobs=(blob(b"{}"),))
    assert archive.append(entry, inference_blobs=(blob(b"{}"),)) == sequence
    with pytest.raises(ArchiveRevisionConflict):
        archive.append(
            request(request_trace(timeout_seconds=11)), inference_blobs=(blob(b"{}"),)
        )
    with pytest.raises(ArchiveFormatError):
        archive.append(
            response(response_trace(b"x" * 10)), inference_blobs=(blob(b"x" * 10),)
        )
    assert archive.entries() == (entry,)
    with pytest.raises(ArchiveFormatError):
        archive.record((), inference_blobs=(blob(b"orphan"),))
    with pytest.raises(ArchiveFormatError):
        archive.append(response(response_trace()))


def test_response_requires_traced_request_and_observed_length(tmp_path: Path) -> None:
    archive = create(tmp_path)
    archive.append(request())
    with pytest.raises(ArchiveFormatError):
        archive.append(response(response_trace(None)))
    other = create(tmp_path / "other")
    with pytest.raises(ArchiveFormatError):
        other.append(
            request(request_trace(body_length=3)), inference_blobs=(blob(b"{}"),)
        )


def test_response_insert_failure_rolls_back_blob(tmp_path: Path) -> None:
    archive = create(tmp_path)
    archive.append(request(request_trace()), inference_blobs=(blob(b"{}"),))
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(
            "CREATE TRIGGER fail_response BEFORE INSERT ON journal WHEN NEW.kind='response_failed' BEGIN SELECT RAISE(ABORT, 'injected'); END"
        )
    with pytest.raises(ArchiveError):
        archive.append(response(response_trace()), inference_blobs=(blob(b"\xff\x00"),))
    with sqlite3.connect(archive.database_path) as connection:
        assert (
            connection.execute("SELECT count(*) FROM inference_blobs").fetchone()[0]
            == 1
        )
    assert len(archive.entries()) == 1


@pytest.mark.parametrize(
    "sql,args",
    [
        ("UPDATE inference_blobs SET body=?", (b"changed",)),
        ("UPDATE inference_blobs SET body=?", ("{}",)),
        ("UPDATE inference_blobs SET sha256=?", ("a" * 64,)),
        ("DELETE FROM inference_blobs", ()),
        (
            "INSERT INTO inference_blobs VALUES(?,?)",
            (hashlib.sha256(b"orphan").hexdigest(), b"orphan"),
        ),
        ("DROP TABLE inference_blobs", ()),
    ],
)
def test_corruption_fails_closed(
    tmp_path: Path, sql: str, args: tuple[object, ...]
) -> None:
    archive = create(tmp_path)
    archive.append(request(request_trace()), inference_blobs=(blob(b"{}"),))
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(sql, args)
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(archive.ref)


def test_legacy_reader_writer_no_migration_or_hash_change(tmp_path: Path) -> None:
    archive = legacy(create(tmp_path))
    assert archive.format_version == 1
    entry = request()
    archive.append(entry)
    seal = archive.journal_boundary()
    before = archive.database_path.read_bytes()
    reader = AttemptArchive.open(archive.ref, read_only=True)
    assert reader.journal_boundary() == seal
    assert reader.entries() == (entry,)
    assert reader.inference_blobs(()) == ()
    assert archive.database_path.read_bytes() == before
    with pytest.raises(ArchiveFormatError):
        archive.append(
            request(request_trace(), request_id="traced"),
            inference_blobs=(blob(b"{}"),),
        )
    with pytest.raises(ArchiveFormatError):
        archive.record((), inference_blobs=(blob(b"{}"),))
    archive.save_world(archive.load_world())
    with sqlite3.connect(archive.database_path) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='inference_blobs'"
            ).fetchall()
            == []
        )


def test_empty_format_two_requires_blob_table(tmp_path: Path) -> None:
    archive = create(tmp_path)
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute("DROP TABLE inference_blobs")
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(archive.ref)


def test_digest_arguments_prefix_gaps_copy_and_writer_guards(tmp_path: Path) -> None:
    archive = create(tmp_path)
    first = archive.append(request(request_trace()), inference_blobs=(blob(b"{}"),))
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute("UPDATE sqlite_sequence SET seq=9 WHERE name='journal'")
    last = archive.append(
        response(response_trace()), inference_blobs=(blob(b"\xff\x00"),)
    )
    assert last == 10
    for digests, horizon in [
        ((blob(b"{}").sha256,), 0),
        ((), 2),
        (("bad",), None),
        ((blob(b"{}").sha256,) * 2, None),
        ([blob(b"{}").sha256], None),
    ]:
        with pytest.raises(ArchiveFormatError):
            archive.inference_blobs(digests, through_sequence=horizon)
    ordered = (blob(b"\xff\x00").sha256, blob(b"{}").sha256)
    assert archive.inference_blobs(ordered) == (blob(b"\xff\x00"), blob(b"{}"))
    copy = create(tmp_path / "copy")
    copy.record(
        tuple(
            record.entry for record in archive.journal_records(through_sequence=first)
        ),
        inference_blobs=archive.inference_blobs(
            (blob(b"{}").sha256,), through_sequence=first
        ),
    )
    assert copy.inference_blobs((blob(b"{}").sha256,)) == (blob(b"{}"),)
    reader = AttemptArchive.open(archive.ref, read_only=True)
    with pytest.raises(ArchiveError):
        reader.record((), inference_blobs=(blob(b"{}"),))
    with ThreadPoolExecutor(max_workers=1) as executor, pytest.raises(ArchiveError):
        executor.submit(archive.record, (), inference_blobs=(blob(b"{}"),)).result()


def test_reused_trace_has_source_request_and_optional_response(tmp_path: Path) -> None:
    archive = create(tmp_path)
    base = dict(request().payload)
    base.update(
        decision={"spoken_text": "Ready.", "action_request": None},
        source={
            "attempt_id": uuid4().hex,
            "request_id": "original",
            "boundary": {"sequence": 1, "digest": "c" * 64},
        },
    )
    with pytest.raises(ArchiveFormatError):
        JournalEntry(
            "response_reused", {**base, "response_trace": response_trace(None)}
        )
    entry = JournalEntry("response_reused", {**base, "request_trace": request_trace()})
    archive.append(entry, inference_blobs=(blob(b"{}"),))
    both = JournalEntry(
        "response_reused",
        {
            **base,
            "request_id": "req2",
            "request_trace": request_trace(),
            "response_trace": response_trace(),
        },
    )
    archive.append(both, inference_blobs=(blob(b"\xff\x00"),))
    assert archive.entries() == (entry, both)


def test_blob_insert_failure_leaves_no_request(tmp_path: Path) -> None:
    archive = create(tmp_path)
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(
            "CREATE TRIGGER fail_blob BEFORE INSERT ON inference_blobs BEGIN SELECT RAISE(ABORT, 'injected'); END"
        )
    with pytest.raises(ArchiveError):
        archive.append(request(request_trace()), inference_blobs=(blob(b"{}"),))
    assert archive.entries() == ()


def test_legacy_trace_commit_rejected_without_publication(tmp_path: Path) -> None:
    archive = legacy(create(tmp_path))
    before = archive.database_path.read_bytes()
    with pytest.raises(ArchiveFormatError):
        archive.commit(
            encode_world(WorldState()),
            expected_revision=0,
            driver_cursor={},
            feedback_cursor={},
            entries=(request(request_trace()),),
        )
    assert archive.database_path.read_bytes() == before
    assert archive.latest_revision == 0


def test_untraced_hashes_world_and_cursors_match_legacy(tmp_path: Path) -> None:
    current = create(tmp_path)
    old = legacy(create(tmp_path / "old"))
    historical_request = canonical(request().payload)
    for archive in (current, old):
        archive.append(request())
    assert canonical(current.entries()[0].payload) == historical_request
    assert current.journal_boundary() == old.journal_boundary()
    assert current.checkpoint() == old.checkpoint()
    # Trace storage cannot enter the world/cursor publication path.
    checkpoint = current.checkpoint()
    current.append(
        request(request_trace(), request_id="traced"), inference_blobs=(blob(b"{}"),)
    )
    assert current.checkpoint() == checkpoint


def test_validated_response_trace_does_not_replace_transport_digest(
    tmp_path: Path,
) -> None:
    archive = create(tmp_path)
    request_entry = request(request_trace())
    response_entry = JournalEntry(
        "response_validated",
        {
            "request_id": "req",
            "decision": {"spoken_text": "Ready.", "action_request": None},
            "content_digest": "d" * 64,
            "elapsed_seconds": 0.25,
            "response_trace": response_trace(b"\x00\xff"),
        },
    )
    archive.record(
        (request_entry, response_entry),
        inference_blobs=(blob(b"{}"), blob(b"\x00\xff")),
    )
    retained = archive.entries()[1].payload
    assert retained["content_digest"] == "d" * 64
    assert retained["elapsed_seconds"] == 0.25
    assert retained["response_trace"]["body_digest"] == blob(b"\x00\xff").sha256


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE journal SET payload=json_set(payload,'$.request_trace.body_length',3)",
        "UPDATE journal SET payload=json_set(payload,'$.request_trace.body_digest','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')",
        "UPDATE journal SET payload=json_remove(payload,'$.request_trace')",
        "UPDATE inference_blobs SET sha256=NULL",
    ],
)
def test_metadata_reference_and_sqlite_type_corruption(
    tmp_path: Path, mutation: str
) -> None:
    archive = create(tmp_path)
    archive.append(request(request_trace()), inference_blobs=(blob(b"{}"),))
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(mutation)
    with pytest.raises(ArchiveFormatError):
        archive.inference_blobs(())


def test_reused_response_uses_copied_request_limit(tmp_path: Path) -> None:
    archive = create(tmp_path)
    base = dict(request(request_trace(max_response_bytes=1)).payload)
    base.update(
        decision={"spoken_text": "Ready.", "action_request": None},
        source={
            "attempt_id": uuid4().hex,
            "request_id": "original",
            "boundary": {"sequence": 1, "digest": "c" * 64},
        },
        response_trace=response_trace(b"123"),
    )
    with pytest.raises(ArchiveFormatError):
        archive.append(
            JournalEntry("response_reused", base),
            inference_blobs=(blob(b"{}"), blob(b"123")),
        )
    assert archive.entries() == ()


def test_clock_metadata_keeps_unknowns_and_does_not_order_wall_clock() -> None:
    module = importlib.import_module("living_world.archives.inference")
    stamps = dict.fromkeys(TIMESTAMPS)
    stamps.update(
        dispatch_started_at="2026-10-27T12:00:01Z",
        settled_at="2026-10-27T12:00:00+00:00",
    )
    durations = dict.fromkeys(DURATIONS)
    durations.update(broker_seconds=0, worker_seconds=1.5)
    result = module.validate_response_trace(
        response_trace(None, timestamps=stamps, durations=durations)
    )
    assert result["timestamps"] == stamps
    assert result["durations"] == durations
    with pytest.raises(TypeError):
        result["durations"]["worker_seconds"] = 2


@pytest.mark.parametrize(
    "changes",
    [
        {"url": "http://localhost/api/generate?"},
        {"url": "http://localhost/api/generate#"},
        {"url": "http://local\thost/api/generate"},
        {"url": "http://localhost:70000/api/generate"},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": 10**1000},
        {"headers": {}},
        {"headers": {"Content-Type": "text/plain"}},
        {"provider_kind": ["ollama"]},
        {"body_length": 1.5},
    ],
)
def test_additional_request_representation_guards(changes: dict[str, object]) -> None:
    module = importlib.import_module("living_world.archives.inference")
    with pytest.raises(ArchiveFormatError):
        module.validate_request_trace(request_trace(**changes))


@pytest.mark.parametrize("value", [None, [], "", True])
def test_metadata_validators_require_objects(value: object) -> None:
    module = importlib.import_module("living_world.archives.inference")
    for validate in (module.validate_request_trace, module.validate_response_trace):
        with pytest.raises(ArchiveFormatError):
            validate(value)


def test_format_one_command_ledger_and_ordinary_duplicate_write(tmp_path: Path) -> None:
    archive = legacy(create(tmp_path))
    command = JournalEntry(
        "control_requested",
        {
            "envelope": {
                "command_id": "pause",
                "action": "pause",
                "expected_state_version": 0,
            }
        },
    )
    settled = JournalEntry(
        "control_resolved",
        {
            "receipt": {
                "command_id": "pause",
                "status": "rejected",
                "state_version": 0,
                "revision": 0,
                "reason": "Already paused.",
            }
        },
    )
    sequences = archive.record((command, settled))
    assert archive.record((command, settled)) == sequences
    assert archive.command("pause").status == "rejected"
    assert AttemptArchive.open(archive.ref).command("pause") == archive.command("pause")


@pytest.mark.parametrize("version", [True, 1.0, "2", 0, 3])
def test_metadata_requires_exact_supported_integer_version(
    tmp_path: Path, version: object
) -> None:
    archive = create(tmp_path)
    with sqlite3.connect(archive.database_path) as connection:
        meta = plain(
            loads(connection.execute("SELECT payload FROM archive_meta").fetchone()[0])
        )
        meta["format"] = version
        connection.execute("UPDATE archive_meta SET payload=?", (canonical(meta),))
    before = archive.database_path.read_bytes()
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(archive.ref, read_only=True)
    assert archive.database_path.read_bytes() == before


def test_format_two_rejects_wrong_blob_schema(tmp_path: Path) -> None:
    archive = create(tmp_path)
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute("DROP TABLE inference_blobs")
        connection.execute(
            "CREATE TABLE inference_blobs(sha256 TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(archive.ref)


def test_present_null_trace_is_not_an_omitted_optional_field() -> None:
    with pytest.raises(ArchiveFormatError):
        JournalEntry("request_started", {**request().payload, "request_trace": None})
    with pytest.raises(ArchiveFormatError):
        JournalEntry(
            "response_failed",
            {"request_id": "req", "code": "timeout", "response_trace": None},
        )
