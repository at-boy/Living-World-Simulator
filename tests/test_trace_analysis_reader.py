"""Narrow read-only analysis over actual saved archive fixtures."""

import importlib
import os
import sqlite3
import tracemalloc
from dataclasses import FrozenInstanceError
from pathlib import Path
from uuid import uuid4

import pytest
from test_inference_trace_storage import request, request_trace, response_trace

from living_world.archives import (
    ArchiveFormatError,
    AttemptArchive,
    AttemptConfig,
    AttemptRef,
    InferenceBlob,
    JournalBoundary,
    JournalEntry,
)
from living_world.archives.model import canonical, loads
from living_world.repositories.world_snapshot import encode_world
from living_world.state.world_state import WorldState


def reader():
    return importlib.import_module("living_world.archives.trace_analysis")


def create(root: Path, *, checkpoint: bool = True) -> AttemptArchive:
    lineage, attempt = uuid4().hex, uuid4().hex
    directory = root / lineage / attempt
    directory.mkdir(parents=True)
    archive = AttemptArchive.create(
        AttemptRef(lineage, attempt, directory),
        AttemptConfig("recorded", "founders", 7, "revision", {}),
    )
    if checkpoint:
        archive.commit(
            encode_world(WorldState()),
            expected_revision=None,
            driver_cursor={},
            feedback_cursor={},
            entries=(),
        )
    return archive


def start(archive: AttemptArchive, name: str = "req") -> int:
    return archive.append(
        request(request_trace(), request_id=name),
        inference_blobs=(InferenceBlob(b"{}"),),
    )


def fail(archive: AttemptArchive, body: bytes | None, name: str = "req", **changes):
    return archive.append(
        JournalEntry(
            "response_failed",
            {
                "request_id": name,
                "code": "http_error",
                "response_trace": response_trace(body, http_status=503, **changes),
            },
        ),
        inference_blobs=() if body is None else (InferenceBlob(body),),
    )


def mutate(archive: AttemptArchive, sql: str, args: tuple = ()) -> None:
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(sql, args)


def snapshot(root: Path):
    return {
        p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }


def test_public_reader_empty_and_real_exact_metadata(tmp_path):
    api = reader()
    archive = create(tmp_path)
    empty = api.read_trace_page(archive.ref)
    assert empty.boundary == archive.journal_boundary()
    assert empty.calls == () and empty.next_after_sequence is None
    start(archive)
    fail(archive, b"\xff\x00")
    page = api.read_trace_page(archive.ref)
    (call,) = page.calls
    assert page.archive_format == 2
    assert page.integrity == "trace_metadata_checked"
    assert page.boundary == archive.journal_boundary()
    assert (
        call.sequence,
        call.request_id,
        call.base_revision,
        call.source_tick,
        call.actor_label,
        call.response_kind,
        call.error_code,
        call.outcome,
    ) == (1, "req", 0, 0, "Ada", "response_failed", "http_error", None)
    assert call.request_trace == request_trace()
    assert call.response_trace == response_trace(b"\xff\x00", http_status=503)
    assert call.content_digest is None and call.elapsed_seconds is None
    assert call.source is None
    with pytest.raises(FrozenInstanceError):
        call.actor_label = "changed"
    with pytest.raises(TypeError):
        call.request_trace["headers"]["Content-Type"] = "changed"
    with pytest.raises(FrozenInstanceError):
        page.calls = ()


def test_stable_pages_prefix_gaps_and_tamper(tmp_path):
    api = reader()
    archive = create(tmp_path)
    first = start(archive)
    pending = api.read_trace_page(archive.ref)
    assert pending.calls[0].response_kind is None
    mutate(archive, "UPDATE sqlite_sequence SET seq=8 WHERE name='journal'")
    fail(archive, b"later")
    last = start(archive, "second")
    assert last == 10
    captured = api.read_trace_page(archive.ref, limit=1)
    assert captured.next_after_sequence == first
    tail = api.read_trace_page(
        archive.ref, boundary=captured.boundary, after_sequence=first, limit=1
    )
    assert [c.request_id for c in tail.calls] == ["second"]
    assert tail.next_after_sequence is None
    assert api.read_trace_page(archive.ref, boundary=pending.boundary) == pending
    assert captured.boundary == archive.journal_boundary()
    with pytest.raises(ArchiveFormatError):
        api.read_trace_body(
            archive.ref, InferenceBlob(b"later").sha256, boundary=pending.boundary
        )
    mutate(
        archive,
        "UPDATE journal SET payload=json_set(payload,'$.actor_label','Eve') WHERE sequence=1",
    )
    with pytest.raises(ArchiveFormatError):
        api.read_trace_page(archive.ref, boundary=pending.boundary)


@pytest.mark.parametrize(
    "body,state",
    [
        (b"", "complete"),
        (b"\xff\x00", "complete"),
        (b"{broken", "incomplete"),
        (None, "unavailable"),
    ],
)
def test_exact_body_evidence_and_read_only(tmp_path, body, state):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    fail(archive, body, body_state=state)
    (archive.ref.directory / "owner.lock").write_bytes(b"owned")
    (archive.ref.directory / "reservation.json").write_bytes(b"opaque")
    (archive.ref.directory / "retained-inputs").write_bytes(b"opaque")
    before = snapshot(tmp_path)
    page = api.read_trace_page(archive.ref)
    request_body = api.read_trace_body(
        archive.ref, InferenceBlob(b"{}").sha256, boundary=page.boundary
    )
    assert request_body.body == b"{}"
    if body is not None:
        result = api.read_trace_body(
            archive.ref, InferenceBlob(body).sha256, boundary=page.boundary
        )
        assert result.body == body and result.byte_length == len(body)
        assert result.sha256 == InferenceBlob(body).sha256
        assert result.integrity == "selected_body_verified"
        with pytest.raises(FrozenInstanceError):
            result.body = b"changed"
    with pytest.raises(ArchiveFormatError):
        api.read_trace_body(archive.ref, "a" * 64, boundary=page.boundary)
    assert snapshot(tmp_path) == before


def test_validated_action_and_reuse_metadata(tmp_path):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    decision = {"spoken_text": "Ready.", "action_request": None}
    archive.append(
        JournalEntry(
            "response_validated",
            {
                "request_id": "req",
                "decision": decision,
                "content_digest": "d" * 64,
                "elapsed_seconds": 0.25,
                "response_trace": response_trace(None),
            },
        )
    )
    before = api.read_trace_page(archive.ref)
    archive.commit(
        encode_world(WorldState(tick=1)),
        expected_revision=0,
        driver_cursor={},
        feedback_cursor={},
        entries=(
            JournalEntry(
                "action_resolved",
                {
                    "request_id": "req",
                    "base_revision": 0,
                    "source_tick": 0,
                    "actor_label": "Ada",
                    "outcome": "no_action",
                    "event_references": [],
                },
            ),
        ),
    )
    source = {
        "attempt_id": uuid4().hex,
        "request_id": "original",
        "boundary": {"sequence": 17, "digest": "c" * 64},
    }
    archive.append(
        JournalEntry(
            "response_reused",
            {
                **request(request_trace(), request_id="reused").payload,
                "decision": decision,
                "source": source,
                "response_trace": response_trace(None),
                "elapsed_seconds": 0.75,
                "content_digest": "e" * 64,
            },
        )
    )
    page = api.read_trace_page(archive.ref)
    assert page.calls[0].outcome == "no_action"
    assert page.calls[0].elapsed_seconds == 0.25
    assert page.calls[0].content_digest == "d" * 64
    assert page.calls[1].response_kind == "response_reused"
    assert page.calls[1].source == loads(canonical(source))
    assert page.calls[1].elapsed_seconds == 0.75
    assert api.read_trace_page(archive.ref, boundary=before.boundary) == before


@pytest.mark.parametrize(
    "mutation,args",
    [
        ("DELETE FROM inference_blobs", ()),
        ("UPDATE inference_blobs SET body=?", ("{}",)),
        ("UPDATE inference_blobs SET body=?", (b"long",)),
        (
            "UPDATE journal SET payload=json_set(payload,'$.request_trace.body_length',3)",
            (),
        ),
        ("DROP TABLE inference_blobs", ()),
        ("UPDATE journal SET payload=?", ('{"request_id":"req","request_id":"req"}',)),
        ("UPDATE journal SET checkpoint_revision='bad'", ()),
        ("UPDATE journal SET kind=?", (b"request_started",)),
        ("UPDATE archive_meta SET payload=?", (b"{}",)),
        ("UPDATE archive_meta SET payload=json_set(payload,'$.format',3)", ()),
        ("UPDATE archive_meta SET payload=json_set(payload,'$.created_at','bad')", ()),
    ],
)
def test_malformed_storage_rejects_without_mutation(tmp_path, mutation, args):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    mutate(archive, mutation, args)
    before = snapshot(tmp_path)
    with pytest.raises(ArchiveFormatError):
        api.read_trace_page(archive.ref)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE journal SET payload=json_remove(payload,'$.request_trace') WHERE sequence=1",
        "UPDATE journal SET payload=json_set(payload,'$.request_id','unknown') WHERE sequence=2",
        "UPDATE journal SET payload=json_set(payload,'$.response_trace.body_length',10) WHERE sequence=2",
        "INSERT INTO journal(kind,payload) SELECT kind,payload FROM journal WHERE sequence=1",
        "INSERT INTO journal(kind,payload) SELECT kind,payload FROM journal WHERE sequence=2",
    ],
)
def test_local_trace_relationships_fail_closed(tmp_path, mutation):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    fail(archive, b"x")
    mutate(archive, mutation)
    with pytest.raises(ArchiveFormatError):
        api.read_trace_page(archive.ref)


def test_narrow_integrity_and_bounded_unselected_blob(tmp_path, monkeypatch):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    seal = archive.journal_boundary()
    mutate(archive, "UPDATE inference_blobs SET body=?", (b"!!",))
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(archive.ref, read_only=True)
    assert api.read_trace_page(archive.ref).boundary == seal
    with pytest.raises(ArchiveFormatError):
        api.read_trace_body(archive.ref, InferenceBlob(b"{}").sha256, boundary=seal)
    mutate(archive, "UPDATE inference_blobs SET body=?", (b"{}",))
    mutate(
        archive, "INSERT INTO inference_blobs VALUES(?,zeroblob(16777216))", ("f" * 64,)
    )
    mutate(archive, "UPDATE world_snapshots SET payload='corrupt'")
    mutate(archive, "INSERT INTO commands VALUES('broken','bad','bad','bad')")
    with pytest.raises(ArchiveFormatError):
        AttemptArchive.open(archive.ref, read_only=True)

    def forbidden(*args, **kwargs):
        raise AssertionError("full archive access")

    for name in (
        "open",
        "journal_records",
        "journal_boundary",
        "inference_blobs",
        "load_world",
    ):
        monkeypatch.setattr(AttemptArchive, name, forbidden)
    statements = []
    original_connect = sqlite3.connect

    def traced_connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", traced_connect)
    tracemalloc.start()
    try:
        page = api.read_trace_page(archive.ref)
        selected = api.read_trace_body(
            archive.ref, InferenceBlob(b"{}").sha256, boundary=page.boundary
        )
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert selected.body == b"{}" and peak < 8 * 1024 * 1024
    body_queries = [s for s in statements if "SELECT body " in s]
    assert len(body_queries) == 1 and "WHERE sha256=" in body_queries[0]


def test_partial_attempt_no_checkpoint_and_legacy(tmp_path):
    api = reader()
    partial = create(tmp_path, checkpoint=False)
    partial.record((request(request_trace()),), inference_blobs=(InferenceBlob(b"{}"),))
    assert api.read_trace_page(partial.ref).calls[0].response_kind is None
    old = create(tmp_path)
    old.append(request())
    mutate(old, "UPDATE archive_meta SET payload=json_set(payload,'$.format',1)")
    mutate(old, "DROP TABLE inference_blobs")
    before = snapshot(tmp_path)
    page = api.read_trace_page(old.ref)
    assert page.archive_format == 1 and page.calls[0].request_trace is None
    with pytest.raises(ArchiveFormatError):
        api.read_trace_body(
            old.ref, InferenceBlob(b"{}").sha256, boundary=page.boundary
        )
    assert snapshot(tmp_path) == before
    mutate(
        old,
        "UPDATE journal SET payload=json_set(payload,'$.request_trace',json(?))",
        (canonical(request_trace()),),
    )
    with pytest.raises(ArchiveFormatError):
        api.read_trace_page(old.ref)


@pytest.mark.parametrize(
    "field",
    ["max_journal_rows", "max_journal_bytes", "max_row_bytes", "max_body_bytes"],
)
@pytest.mark.parametrize("invalid", [True, 0, -1, 1.5, None])
def test_limits_require_exact_positive_integers(field, invalid):
    with pytest.raises(ArchiveFormatError):
        reader().TraceReadLimits(**{field: invalid})


@pytest.mark.parametrize(
    "changes", [{"max_journal_rows": 1}, {"max_journal_bytes": 1}, {"max_row_bytes": 1}]
)
def test_metadata_budgets_reject(tmp_path, changes):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    fail(archive, b"")
    with pytest.raises(
        api.TraceAnalysisLimitError, match="^Trace analysis limit exceeded\\.$"
    ):
        api.read_trace_page(archive.ref, limits=api.TraceReadLimits(**changes))


def test_body_budget_checked_before_materialization(tmp_path):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    seal = api.read_trace_page(archive.ref).boundary
    with pytest.raises(api.TraceAnalysisLimitError):
        api.read_trace_body(
            archive.ref,
            InferenceBlob(b"{}").sha256,
            boundary=seal,
            limits=api.TraceReadLimits(max_body_bytes=1),
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": True},
        {"limit": 0},
        {"limit": 101},
        {"after_sequence": True},
        {"after_sequence": -1},
        {"after_sequence": 99},
        {"boundary": False},
        {"boundary": JournalBoundary(99, "a" * 64)},
        {"boundary": JournalBoundary(0, "a" * 64)},
        {"limits": None},
    ],
)
def test_invalid_page_parameters(tmp_path, kwargs):
    archive = create(tmp_path)
    with pytest.raises(ArchiveFormatError):
        reader().read_trace_page(archive.ref, **kwargs)


@pytest.mark.parametrize(
    "kind", ["missing", "file_symlink", "directory_symlink", "hardlink", "traversal"]
)
def test_unsafe_paths_create_nothing(tmp_path, kind):
    api = reader()
    archive = create(tmp_path)
    ref = archive.ref
    if kind == "missing":
        archive.database_path.unlink()
    elif kind == "file_symlink":
        original = archive.database_path.with_suffix(".saved")
        archive.database_path.rename(original)
        archive.database_path.symlink_to(original)
    elif kind == "directory_symlink":
        original = ref.directory.with_name("original")
        ref.directory.rename(original)
        ref.directory.symlink_to(original, target_is_directory=True)
    elif kind == "hardlink":
        os.link(archive.database_path, archive.database_path.with_suffix(".link"))
    else:
        ref = AttemptRef(
            ref.lineage_id, ref.attempt_id, ref.directory / ".." / ref.attempt_id
        )
    with pytest.raises(ArchiveFormatError):
        api.read_trace_page(ref)
    if kind == "missing":
        assert not archive.database_path.exists()


@pytest.mark.parametrize(
    "target,ddl",
    [
        (
            "archive_meta",
            "CREATE TABLE archive_meta(id INTEGER, payload TEXT NOT NULL)",
        ),
        (
            "journal",
            "CREATE TABLE journal(sequence INTEGER, kind TEXT NOT NULL,payload TEXT NOT NULL,checkpoint_revision INTEGER,revision_context INTEGER)",
        ),
        (
            "inference_blobs",
            "CREATE TABLE inference_blobs(sha256 TEXT, body BLOB NOT NULL)",
        ),
        (
            "inference_blobs",
            "CREATE VIEW inference_blobs AS SELECT 'x' AS sha256, x'00' AS body",
        ),
        ("archive_meta", "CREATE VIEW archive_meta AS SELECT 1 AS id,'{}' AS payload"),
    ],
)
def test_malformed_or_view_schema_rejected(tmp_path, target, ddl):
    archive = create(tmp_path)
    mutate(archive, f"DROP TABLE {target}")
    mutate(archive, ddl)
    with pytest.raises(ArchiveFormatError):
        reader().read_trace_page(archive.ref)


@pytest.mark.parametrize(
    "change",
    [
        {"actor_label": "Eve"},
        {"base_revision": 1},
        {"source_tick": 1},
        {"outcome": "accepted"},
        {"request_id": "unknown"},
    ],
)
def test_action_identity_and_no_action_validation(tmp_path, change):
    archive = create(tmp_path)
    start(archive)
    archive.append(
        JournalEntry(
            "response_validated",
            {
                "request_id": "req",
                "decision": {"spoken_text": "Ready.", "action_request": None},
            },
        )
    )
    payload = {
        "request_id": "req",
        "actor_label": "Ada",
        "base_revision": 0,
        "source_tick": 0,
        "outcome": "no_action",
        "event_references": [],
        **change,
    }
    mutate(
        archive,
        "INSERT INTO journal(kind,payload) VALUES('action_resolved',?)",
        (canonical(payload),),
    )
    with pytest.raises(ArchiveFormatError):
        reader().read_trace_page(archive.ref)


def test_duplicate_action_and_offered_decision_reject(tmp_path):
    archive = create(tmp_path)
    start(archive)
    entry = JournalEntry(
        "response_validated",
        {
            "request_id": "req",
            "decision": {"spoken_text": "Ready.", "action_request": None},
        },
    )
    archive.append(entry)
    payload = {
        "request_id": "req",
        "actor_label": "Ada",
        "base_revision": 0,
        "source_tick": 0,
        "outcome": "no_action",
        "event_references": [],
    }
    for _ in range(2):
        mutate(
            archive,
            "INSERT INTO journal(kind,payload) VALUES('action_resolved',?)",
            (canonical(payload),),
        )
    with pytest.raises(ArchiveFormatError):
        reader().read_trace_page(archive.ref)
    mutate(archive, "DELETE FROM journal WHERE kind='action_resolved'")
    decision = {
        "spoken_text": "Ready.",
        "action_request": {
            "action_key": "invented",
            "target_label": None,
            "rationale": "Try.",
            "arguments": {},
        },
    }
    mutate(
        archive,
        "UPDATE journal SET payload=? WHERE kind='response_validated'",
        (canonical({"request_id": "req", "decision": decision}),),
    )
    with pytest.raises(ArchiveFormatError):
        reader().read_trace_page(archive.ref)


def test_reference_length_conflicts_reject(tmp_path):
    archive = create(tmp_path)
    start(archive)
    fail(archive, b"{}")
    mutate(
        archive,
        "UPDATE journal SET payload=json_set(payload,'$.response_trace.body_length',1) WHERE sequence=2",
    )
    with pytest.raises(ArchiveFormatError):
        reader().read_trace_page(archive.ref)


def test_gap_boundary_and_invalid_body_parameters(tmp_path):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    mutate(archive, "UPDATE sqlite_sequence SET seq=8 WHERE name='journal'")
    fail(archive, None)
    seal = api.read_trace_page(archive.ref).boundary
    assert seal == archive.journal_boundary()
    with pytest.raises(ArchiveFormatError):
        api.read_trace_page(archive.ref, boundary=JournalBoundary(5, "a" * 64))
    for sha, boundary in [
        (True, seal),
        ("bad", seal),
        ("a" * 64, None),
        ("a" * 64, True),
    ]:
        with pytest.raises(ArchiveFormatError):
            api.read_trace_body(archive.ref, sha, boundary=boundary)


def test_large_text_budget_before_fetch_and_selected_budget_before_body(
    tmp_path, monkeypatch
):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    seal = api.read_trace_page(archive.ref).boundary
    statements = []
    original = sqlite3.connect

    def traced(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", traced)
    with pytest.raises(api.TraceAnalysisLimitError):
        api.read_trace_body(
            archive.ref,
            InferenceBlob(b"{}").sha256,
            boundary=seal,
            limits=api.TraceReadLimits(max_body_bytes=1),
        )
    assert not any("SELECT body " in statement for statement in statements)
    with original(archive.database_path) as connection:
        connection.execute("UPDATE journal SET payload=?", ("x" * 16777216,))
    statements.clear()
    tracemalloc.start()
    try:
        with pytest.raises(api.TraceAnalysisLimitError):
            api.read_trace_page(
                archive.ref, limits=api.TraceReadLimits(max_row_bytes=4096)
            )
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 8 * 1024 * 1024
    assert not any(
        "SELECT sequence,kind,payload" in statement for statement in statements
    )


def test_real_concurrent_append_keeps_one_snapshot(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, get_ident

    api = reader()
    archive = create(tmp_path)
    start(archive)
    seal = archive.journal_boundary()
    scan_started, writer_prepared, writer_finished = Event(), Event(), Event()
    reader_observed_waiting_commit = Event()
    original = sqlite3.connect
    main_thread = get_ident()

    def callback(statement):
        if statement.startswith("SELECT sequence,kind,payload"):
            scan_started.set()
            if writer_prepared.wait(3) and not writer_finished.is_set():
                reader_observed_waiting_commit.set()

    def connected(*args, **kwargs):
        connection = original(*args, **kwargs)
        if get_ident() == main_thread:
            connection.set_trace_callback(callback)
        else:

            def writer_callback(statement):
                if statement == "COMMIT":
                    writer_prepared.set()

            connection.set_trace_callback(writer_callback)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connected)

    def append_response():
        assert scan_started.wait(3)
        writer = AttemptArchive.open(archive.ref)
        fail(writer, b"new")
        writer_finished.set()

    with ThreadPoolExecutor(max_workers=1) as executor:
        writing = executor.submit(append_response)
        page = api.read_trace_page(archive.ref)
        writing.result(timeout=3)
    assert reader_observed_waiting_commit.is_set()
    assert page.boundary == seal and page.calls[0].response_kind is None
    assert api.read_trace_page(archive.ref).calls[0].response_kind == "response_failed"


def test_page_dto_rejects_mutable_call_container(tmp_path):
    api = reader()
    archive = create(tmp_path)
    page = api.read_trace_page(archive.ref)
    with pytest.raises(ArchiveFormatError):
        api.TracePage(2, page.boundary, [], None)


def test_deep_malformed_json_reports_safe_archive_error(tmp_path):
    archive = create(tmp_path)
    start(archive)
    mutate(archive, "UPDATE journal SET payload=?", ("[" * 2000 + "0" + "]" * 2000,))
    with pytest.raises(ArchiveFormatError):
        reader().read_trace_page(archive.ref)


def test_body_dto_rejects_mutable_bytes(tmp_path):
    api = reader()
    archive = create(tmp_path)
    boundary = api.read_trace_page(archive.ref).boundary
    with pytest.raises(ArchiveFormatError):
        api.TraceBody(boundary, bytearray(b"x"), InferenceBlob(b"x").sha256, 1)


def test_backend_and_timing_metadata_remain_exact(tmp_path):
    api = reader()
    archive = create(tmp_path)
    trace = request_trace(
        provider_kind="llama_cpp",
        model="specific-model",
        model_digest="pin",
        url="http://[::1]:8080/v1/chat/completions",
    )
    archive.append(request(trace), inference_blobs=(InferenceBlob(b"{}"),))
    timestamps = dict(response_trace(None)["timestamps"])
    timestamps["dispatch_started_at"] = "2026-10-27T12:00:01Z"
    timestamps["settled_at"] = "2026-10-27T12:00:00+00:00"
    durations = dict(response_trace(None)["durations"])
    durations["broker_seconds"] = 0.125
    response = response_trace(None, timestamps=timestamps, durations=durations)
    archive.append(
        JournalEntry(
            "response_failed",
            {
                "request_id": "req",
                "code": "timeout",
                "response_trace": response,
            },
        )
    )
    (call,) = api.read_trace_page(archive.ref).calls
    assert call.request_trace == trace
    assert call.response_trace == response
    assert call.error_code == "timeout" and call.elapsed_seconds is None


@pytest.mark.parametrize(
    "mode",
    [
        "wal_absent",
        "wal_existing",
        "rollback_wal",
        "rollback_shm",
        "header_read",
        "header_write",
        "magic",
    ],
)
def test_unsupported_journal_modes_reject_before_sqlite_open(
    tmp_path, monkeypatch, mode
):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    seal = api.read_trace_page(archive.ref).boundary
    if mode.startswith("wal_"):
        connection = sqlite3.connect(archive.database_path)
        try:
            assert connection.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        finally:
            connection.close()
        assert not archive.database_path.with_name("archive.sqlite3-wal").exists()
        assert not archive.database_path.with_name("archive.sqlite3-shm").exists()
    if mode in ("wal_existing", "rollback_wal"):
        archive.database_path.with_name("archive.sqlite3-wal").write_bytes(
            b"opaque-wal"
        )
    if mode in ("wal_existing", "rollback_shm"):
        archive.database_path.with_name("archive.sqlite3-shm").write_bytes(
            b"opaque-shm"
        )
    if mode in ("header_read", "header_write", "magic"):
        with archive.database_path.open("r+b") as handle:
            handle.seek({"header_read": 19, "header_write": 18, "magic": 0}[mode])
            handle.write(b"\x03")
    before = snapshot(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("unsupported database must reject before sqlite connect")

    monkeypatch.setattr(sqlite3, "connect", forbidden)
    for operation in (
        lambda: api.read_trace_page(archive.ref),
        lambda: api.read_trace_body(
            archive.ref, InferenceBlob(b"{}").sha256, boundary=seal
        ),
    ):
        with pytest.raises(
            ArchiveFormatError,
            match=r"^Trace analysis requires rollback-journal archives\.$",
        ):
            operation()
        assert snapshot(tmp_path) == before


@pytest.mark.parametrize("table", ["archive_meta", "journal"])
@pytest.mark.parametrize("row_limit", [64, 2097152])
def test_descending_pk_oversized_identity_never_materialized(
    tmp_path, monkeypatch, table, row_limit
):
    api = reader()
    archive = create(tmp_path)
    start(archive)
    with sqlite3.connect(archive.database_path) as connection:
        connection.execute(f"DROP TABLE {table}")
        if table == "archive_meta":
            connection.execute(
                "CREATE TABLE archive_meta(id INTEGER PRIMARY KEY DESC, payload TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO archive_meta VALUES(zeroblob(16777216),'{}')"
            )
        else:
            connection.execute(
                "CREATE TABLE journal(sequence INTEGER PRIMARY KEY DESC,kind TEXT NOT NULL,payload TEXT NOT NULL,checkpoint_revision INTEGER,revision_context INTEGER)"
            )
            connection.execute(
                "INSERT INTO journal VALUES(zeroblob(16777216),'request_started','{}',NULL,NULL)"
            )
    statements = []
    original = sqlite3.connect

    def traced(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", traced)
    before = snapshot(tmp_path)
    tracemalloc.start()
    try:
        with pytest.raises(ArchiveFormatError, match="schema"):
            api.read_trace_page(
                archive.ref, limits=api.TraceReadLimits(max_row_bytes=row_limit)
            )
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 8 * 1024 * 1024
    assert not any(
        statement.startswith("SELECT id,") or "max(sequence)" in statement.lower()
        for statement in statements
    )
    assert snapshot(tmp_path) == before
