"""Exact saved evidence and exclusive filesystem publication."""

import hashlib
import importlib
import json
import os
import zipfile
from dataclasses import fields

import pytest
from test_trace_analysis_reader import create, fail, mutate, snapshot, start

from living_world.archives import RunCatalog
from living_world.archives.model import plain
from living_world.archives.trace_analysis import read_trace_page


def api():
    module = importlib.import_module("living_world.archives")
    assert importlib.util.find_spec(
        module.__name__ + ".trace_export"
    ), "trace export missing"
    return importlib.import_module(module.__name__ + ".trace_export")


@pytest.mark.parametrize(
    "body,state",
    [
        (b"\xff\x00", "complete"),
        (b"", "complete"),
        (b"{bad", "incomplete"),
        (None, "unavailable"),
    ],
)
def test_binary_deterministic_metadata_and_source(tmp_path, body, state):
    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    start(archive)
    fail(archive, body, body_state=state)
    page = read_trace_page(archive.ref)
    before = snapshot(root)
    first, second = tmp_path / "one.zip", tmp_path / "two.zip"
    result = module.export_trace_bundle(RunCatalog(root), archive.ref.attempt_id, first)
    module.export_trace_bundle(RunCatalog(root), archive.ref.attempt_id, second)
    assert first.read_bytes() == second.read_bytes()
    assert result.byte_length == first.stat().st_size
    assert first.stat().st_mode & 0o777 == 0o600
    with zipfile.ZipFile(first) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        names = [
            "calls.jsonl",
            *sorted(n for n in bundle.namelist() if n.startswith("bodies/")),
            "manifest.json",
        ]
        assert bundle.namelist() == names
        assert manifest["boundary"] == {
            "sequence": page.boundary.sequence,
            "digest": page.boundary.digest,
        }
        assert manifest["integrity_scope"] == "local_trace_prefix_and_selected_bodies"
        assert manifest["format"] == "living-world-trace-evidence-v1"
        assert manifest["call_count"] == result.call_count == 1
        call = page.calls[0]
        assert json.loads(bundle.read("calls.jsonl")) == plain(
            {f.name: getattr(call, f.name) for f in fields(call)}
        )
        expected = {b"{}"} | (set() if body is None else {body})
        assert {bundle.read(n) for n in names if n.startswith("bodies/")} == expected
        assert result.body_count == len(expected)
        for entry in manifest["files"]:
            raw = bundle.read(entry["name"])
            assert len(raw) == entry["byte_length"]
            assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        for info in bundle.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.external_attr >> 16 & 0o777 == 0o600
            assert not info.extra and not info.comment
    assert snapshot(root) == before


@pytest.mark.parametrize(
    "location",
    [
        "existing",
        "symlink",
        "hardlink",
        "directory",
        "inside",
        "ancestor",
        "missing",
        "traversal",
    ],
)
def test_invalid_output_preserves_foreign(tmp_path, location):
    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    target = tmp_path / "out"
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"PRIVATE")
    if location == "existing":
        target.write_bytes(b"PRIVATE")
    elif location == "symlink":
        target.symlink_to(tmp_path / "absent")
    elif location == "hardlink":
        os.link(foreign, target)
    elif location == "directory":
        target.mkdir()
    elif location == "inside":
        target = root / "out"
    elif location == "ancestor":
        target = tmp_path
    elif location == "missing":
        target = tmp_path / "missing" / "out"
    else:
        target = tmp_path / "x" / ".." / "out"
    before = snapshot(tmp_path)
    with pytest.raises(module.TraceExportError) as error:
        module.export_trace_bundle(RunCatalog(root), archive.ref.attempt_id, target)
    assert (str(error.value), error.value.exit_code) == ("export_invalid", 2)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "values",
    [(True, 1024), (0, 1024), (10001, 1024), (1, False), (1, 1023), (1, 1073741825)],
)
def test_invalid_limits(values):
    module = api()
    with pytest.raises(module.TraceExportError, match="export_invalid"):
        module.TraceExportLimits(*values)


@pytest.mark.parametrize("kind", ["limit", "cancel", "corrupt", "missing", "interrupt"])
def test_safe_failures_no_output(tmp_path, kind):
    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    start(archive)
    fail(archive, b"private")
    output = tmp_path / "out.zip"
    kwargs = {}
    expected = "trace_unavailable"
    if kind == "limit":
        kwargs["limits"] = module.TraceExportLimits(max_output_bytes=1024)
        expected = "export_limit_exceeded"
    elif kind in {"cancel", "interrupt"}:

        def stop():
            if kind == "interrupt":
                raise KeyboardInterrupt
            return True

        kwargs["stop_requested"] = stop
        expected = "export_cancelled"
    elif kind == "corrupt":
        mutate(archive, "UPDATE inference_blobs SET body=x'00'")
    else:
        archive.database_path.unlink()
    before = snapshot(root)
    with pytest.raises(module.TraceExportError, match=expected):
        module.export_trace_bundle(
            RunCatalog(root), archive.ref.attempt_id, output, **kwargs
        )
    assert not output.exists()
    assert snapshot(root) == before
    assert not list(tmp_path.glob(".trace-export-*"))


@pytest.mark.parametrize(
    "failure", ["write", "close", "fsync", "link", "race", "directory_fsync", "cleanup"]
)
def test_io_failure_and_publication_custody(tmp_path, monkeypatch, failure):
    module = api()
    archive = create(tmp_path / "runs")
    start(archive)
    output = tmp_path / "out.zip"

    def broken(*a, **kw):
        raise OSError("PRIVATE")

    if failure == "write":
        monkeypatch.setattr(module.zipfile._ZipWriteFile, "write", broken)
    elif failure == "close":
        original_close = module.zipfile.ZipFile.close

        def close(self):
            original_close(self)
            if self.mode == "w":
                broken()

        monkeypatch.setattr(module.zipfile.ZipFile, "close", close)
    elif failure in {"fsync", "directory_fsync"}:
        original = os.fsync
        count = 0

        def sync(fd):
            nonlocal count
            count += 1
            if failure == "fsync" or count == 2:
                broken()
            original(fd)

        monkeypatch.setattr(module.os, "fsync", sync)
    elif failure in {"link", "race"}:

        def link(*a):
            if failure == "race":
                output.write_bytes(b"foreign")
            broken()

        monkeypatch.setattr(module.os, "link", link)
    else:
        from pathlib import Path

        original_unlink = Path.unlink

        def unlink(self, *a, **kw):
            if self.name.startswith(".trace-export-"):
                broken()
            return original_unlink(self, *a, **kw)

        monkeypatch.setattr(Path, "unlink", unlink)
    expected = (
        "export_published_uncertain"
        if failure in {"directory_fsync", "cleanup"}
        else "export_failed"
    )
    with pytest.raises(module.TraceExportError, match=expected):
        module.export_trace_bundle(
            RunCatalog(tmp_path / "runs"), archive.ref.attempt_id, output
        )
    if failure in {"directory_fsync", "cleanup"}:
        with zipfile.ZipFile(output) as bundle:
            assert bundle.testzip() is None
    elif failure == "race":
        assert output.read_bytes() == b"foreign"
    else:
        assert not output.exists()
    if failure != "cleanup":
        assert not list(tmp_path.glob(".trace-export-*"))


def test_pending_legacy_empty_and_sealed_append(tmp_path, monkeypatch):
    from test_inference_trace_storage import request

    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    archive.append(request(None))
    mutate(archive, "UPDATE archive_meta SET payload=json_set(payload,'$.format',1)")
    original = module.read_trace_page
    captured = None

    def page(ref, **kw):
        nonlocal captured
        result = original(ref, **kw)
        if captured is None:
            captured = result.boundary
            archive.append(request(None, request_id="later"))
        else:
            assert kw["boundary"] == captured
        return result

    monkeypatch.setattr(module, "read_trace_page", page)
    output = tmp_path / "out.zip"
    result = module.export_trace_bundle(
        RunCatalog(root), archive.ref.attempt_id, output
    )
    assert result.call_count == 1 and result.body_count == 0
    with zipfile.ZipFile(output) as bundle:
        call = json.loads(bundle.read("calls.jsonl"))
        assert call["request_trace"] is None and call["response_trace"] is None
        assert call["response_kind"] is None
        assert json.loads(bundle.read("manifest.json"))["archive_format"] == 1
    monkeypatch.setattr(module, "read_trace_page", original)
    empty = create(root)
    assert (
        module.export_trace_bundle(
            RunCatalog(root), empty.ref.attempt_id, tmp_path / "empty.zip"
        ).call_count
        == 0
    )


def test_reuse_exact_backend_timing_and_deduplication(tmp_path):
    from uuid import uuid4

    from test_inference_trace_storage import request, request_trace, response_trace

    from living_world.archives import InferenceBlob, JournalEntry

    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    source = {
        "attempt_id": uuid4().hex,
        "request_id": "original",
        "boundary": {"sequence": 17, "digest": "c" * 64},
    }
    trace = request_trace(model="actual-archived-model", model_digest="sha256:actual")
    response = response_trace(
        b"",
        durations={
            "broker_seconds": 0,
            "worker_seconds": None,
            "http_seconds": 0.25,
            "headers_seconds": None,
            "first_byte_seconds": None,
            "body_read_seconds": None,
        },
    )
    archive.append(
        JournalEntry(
            "response_reused",
            {
                **request(trace, request_id="reused").payload,
                "decision": {"spoken_text": "Ready.", "action_request": None},
                "source": source,
                "response_trace": response,
                "elapsed_seconds": 0,
                "content_digest": "e" * 64,
            },
        ),
        inference_blobs=(InferenceBlob(b"{}"), InferenceBlob(b"")),
    )
    output = tmp_path / "out.zip"
    module.export_trace_bundle(RunCatalog(root), archive.ref.attempt_id, output)
    with zipfile.ZipFile(output) as bundle:
        call = json.loads(bundle.read("calls.jsonl"))
        assert call["source"] == source
        assert call["request_trace"] == trace and call["response_trace"] == response
        assert call["elapsed_seconds"] == 0
        assert call["content_digest"] == "e" * 64
        assert call["response_kind"] == "response_reused"
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["omitted"] == [
            "world_validation",
            "ancestor_closure",
            "uncommitted_spool",
            "model_weights",
            "session_credentials",
        ]


def test_pages_limit_and_prefetch_budget(tmp_path, monkeypatch):
    from test_inference_trace_storage import request, request_trace

    from living_world.archives import InferenceBlob

    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    for i in range(101):
        archive.append(request(None, request_id=str(i)))
    with pytest.raises(module.TraceExportError, match="export_limit_exceeded"):
        module.export_trace_bundle(
            RunCatalog(root),
            archive.ref.attempt_id,
            tmp_path / "limit.zip",
            limits=module.TraceExportLimits(max_calls=100),
        )
    result = module.export_trace_bundle(
        RunCatalog(root), archive.ref.attempt_id, tmp_path / "pages.zip"
    )
    assert result.call_count == 101
    second = create(root)
    body = b"a" * 4096
    second.append(request(request_trace(body)), inference_blobs=(InferenceBlob(body),))

    def forbidden(*a, **kw):
        raise AssertionError("impossible payload loaded")

    monkeypatch.setattr(module, "read_trace_body", forbidden)
    with pytest.raises(module.TraceExportError, match="export_limit_exceeded"):
        module.export_trace_bundle(
            RunCatalog(root),
            second.ref.attempt_id,
            tmp_path / "body.zip",
            limits=module.TraceExportLimits(max_output_bytes=3072),
        )
    assert not list(tmp_path.glob(".trace-export-*"))


def test_final_seal_recheck_and_self_validation_fail_closed(tmp_path, monkeypatch):
    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    start(archive)
    original = module._validate

    def validate(*a):
        original(*a)
        mutate(
            archive,
            "UPDATE journal SET payload=json_set(payload,'$.actor_label','Changed') WHERE kind='request_started'",
        )

    monkeypatch.setattr(module, "_validate", validate)
    with pytest.raises(module.TraceExportError, match="trace_unavailable"):
        module.export_trace_bundle(
            RunCatalog(root), archive.ref.attempt_id, tmp_path / "out.zip"
        )
    assert not (tmp_path / "out.zip").exists()
    assert not list(tmp_path.glob(".trace-export-*"))


def test_replaced_temporary_is_preserved(tmp_path, monkeypatch):
    module = api()
    archive = create(tmp_path / "runs")
    original = module.read_trace_page

    def page(*a, **kw):
        if "boundary" in kw:
            temporary = next(tmp_path.glob(".trace-export-*"))
            temporary.unlink()
            temporary.write_bytes(b"foreign replacement")
        return original(*a, **kw)

    monkeypatch.setattr(module, "read_trace_page", page)
    with pytest.raises(module.TraceExportError, match="export_failed"):
        module.export_trace_bundle(
            RunCatalog(tmp_path / "runs"), archive.ref.attempt_id, tmp_path / "out.zip"
        )
    assert not (tmp_path / "out.zip").exists()
    assert next(tmp_path.glob(".trace-export-*")).read_bytes() == b"foreign replacement"


def test_mid_body_cancellation_and_reader_budget(tmp_path, monkeypatch):
    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    from test_inference_trace_storage import request, request_trace

    from living_world.archives import InferenceBlob

    archive.append(
        request(request_trace(max_response_bytes=131072)),
        inference_blobs=(InferenceBlob(b"{}"),),
    )
    fail(archive, b"x" * 131072)
    original = module.read_trace_body
    stopped = False

    def body(*a, **kw):
        nonlocal stopped
        result = original(*a, **kw)
        stopped = True
        return result

    monkeypatch.setattr(module, "read_trace_body", body)
    with pytest.raises(module.TraceExportError, match="export_cancelled"):
        module.export_trace_bundle(
            RunCatalog(root),
            archive.ref.attempt_id,
            tmp_path / "out.zip",
            stop_requested=lambda: stopped,
        )
    assert not (tmp_path / "out.zip").exists()
    assert not list(tmp_path.glob(".trace-export-*"))

    def over(*a, **kw):
        raise module.TraceAnalysisLimitError()

    monkeypatch.setattr(module, "read_trace_page", over)
    with pytest.raises(module.TraceExportError, match="export_limit_exceeded"):
        module.export_trace_bundle(
            RunCatalog(root), archive.ref.attempt_id, tmp_path / "budget.zip"
        )


def test_staged_crc_verification_failure(tmp_path, monkeypatch):
    module = api()
    root = tmp_path / "runs"
    archive = create(root)
    start(archive)
    original = module._validate

    def corrupt(handle, *args):
        handle.seek(0)
        header = handle.read(30)
        name_length = int.from_bytes(header[26:28], "little")
        handle.seek(30 + name_length)
        handle.write(b"!")
        handle.flush()
        original(handle, *args)

    monkeypatch.setattr(module, "_validate", corrupt)
    with pytest.raises(module.TraceExportError, match="export_failed"):
        module.export_trace_bundle(
            RunCatalog(root), archive.ref.attempt_id, tmp_path / "out.zip"
        )
    assert not (tmp_path / "out.zip").exists()
    assert not list(tmp_path.glob(".trace-export-*"))
