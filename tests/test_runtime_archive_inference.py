"""Archive transactions surround actual spawned inference and sealed copies."""

import hashlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from test_runtime_inference_capture import server as capture_server_fixture
from test_runtime_ollama_driver import initialized, live_archive

from living_world.archives import AttemptArchive
from living_world.runtime.broker import DecisionBroker


@pytest.fixture
def server():
    yield from capture_server_fixture.__wrapped__()


@pytest.mark.parametrize("kind", ["ollama", "llama_cpp"])
def test_spawned_body_is_committed_before_http_and_survives_reopen(
    tmp_path: Path, kind: str
) -> None:
    received = []
    checked = []
    raw = (
        b'{"response":"{\\"spoken_text\\":\\"I will watch.\\",\\"action_request\\":null}"}'
        if kind == "ollama"
        else b'{"choices":[{"message":{"content":"{\\"spoken_text\\":\\"I will watch.\\",\\"action_request\\":null}"}}]}'
    )

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append(body)
            with AttemptArchive.open(archive.ref, read_only=True) as reader:
                entry = [e for e in reader.entries() if e.kind == "request_started"][-1]
                trace = entry.payload.get("request_trace")
                checked.append(
                    trace is not None
                    and reader.inference_blobs((trace["body_digest"],))[0].body == body
                )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        provider = {
            "model": "local",
            "base_url": f"http://127.0.0.1:{server.server_port}",
            "timeout_seconds": 5,
        }
        if kind == "llama_cpp":
            provider.update(kind=kind, model_file="/missing/model.gguf")
        _catalog, lease, archive, live = live_archive(tmp_path, provider=provider)
        broker = DecisionBroker()
        try:
            driver, base = initialized(archive, live, broker)
            prep = driver.prepare(live.restore(base.snapshot), base, archive)
            deadline = time.monotonic() + 15
            status = "waiting"
            while status == "waiting" and time.monotonic() < deadline:
                status = prep.poll()
                time.sleep(0.01)
            assert status == "ready"
            assert checked == [True, True]
            prep.close()
            with AttemptArchive.open(archive.ref, read_only=True) as reader:
                responses = [
                    e for e in reader.entries() if e.kind == "response_validated"
                ]
                assert len(responses) == 2
                for response in responses:
                    trace = response.payload["response_trace"]
                    assert trace["http_status"] == 200
                    assert trace["durations"]["broker_seconds"] > 0
                    assert (
                        reader.inference_blobs((trace["body_digest"],))[0].body == raw
                    )
                requests = [e for e in reader.entries() if e.kind == "request_started"]
                assert [
                    e.payload["request_trace"]["body_digest"] for e in requests
                ] == [hashlib.sha256(b).hexdigest() for b in received]
            from test_runtime_ollama_driver import ImmediateBroker, ready

            from living_world.archives import AttemptLease
            from living_world.runtime.ollama_driver import OllamaTickDriver

            previous = archive
            owned = []
            held = []
            try:
                for _ in range(2):
                    child_ref = _catalog.fork(previous.ref.attempt_id, 0)
                    child_lease = AttemptLease(child_ref)
                    child_lease.acquire()
                    held.append(child_lease)
                    child = _catalog.open_attempt(child_ref.attempt_id, read_only=False)
                    owned.append(child)
                    cold_broker = ImmediateBroker()
                    cold = OllamaTickDriver(driver.config, driver.feedback, cold_broker)
                    reuse = cold.prepare(
                        live.restore(base.snapshot), child.checkpoint(), child
                    )
                    assert ready(reuse) == "ready" and cold_broker.calls == []
                    reuse.close()
                    copied = [e for e in child.entries() if e.kind == "response_reused"]
                    assert len(copied) == 2
                    for entry, response in zip(copied, responses):
                        assert (
                            entry.payload["response_trace"]
                            == response.payload["response_trace"]
                        )
                        assert (
                            entry.payload["elapsed_seconds"]
                            == response.payload["elapsed_seconds"]
                        )
                        assert (
                            entry.payload["source"]["attempt_id"]
                            == previous.ref.attempt_id
                        )
                        sha = entry.payload["response_trace"]["body_digest"]
                        assert child.inference_blobs((sha,))[0].body == raw
                    previous = child
                assert len(received) == 2
            finally:
                for child in reversed(owned):
                    child.close()
                for child_lease in reversed(held):
                    child_lease.release()
        finally:
            broker.close()
            archive.close()
            lease.release()
            server.shutdown()
            thread.join(2)


def test_storage_failures_prevent_dispatch_and_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_runtime_ollama_driver import ImmediateBroker

    _, lease, archive, live = live_archive(tmp_path)
    broker = ImmediateBroker()
    try:
        driver, base = initialized(archive, live, broker)
        prep = driver.prepare(live.restore(base.snapshot), base, archive)
        record = archive.record

        def fail_request(*args: object, **kwargs: object) -> None:
            raise OSError("private storage failure")

        monkeypatch.setattr(archive, "record", fail_request)
        with pytest.raises(OSError):
            prep.poll()
        assert broker.calls == []
        assert not hasattr(broker, "_traces")
        assert prep.active is None
        monkeypatch.setattr(archive, "record", record)
        assert prep.poll() == "waiting"
        spool = archive.database_path.parent / "inference-spool"
        assert list(spool.iterdir())
        monkeypatch.setattr(archive, "record", fail_request)
        with pytest.raises(OSError):
            prep.poll()
        assert prep.active is not None and prep.staged == []
        assert archive.checkpoint() == base
        assert list(spool.iterdir())
        with pytest.raises(OSError):
            prep.close()
        assert prep.system is None and prep.staged == []
        assert list(spool.iterdir())
    finally:
        archive.close()
        lease.release()


@pytest.mark.parametrize("legacy_source", [False, True])
def test_reuse_and_captured_replay_copy_exact_trace_blobs(
    tmp_path: Path, legacy_source: bool
) -> None:
    from test_runtime_ollama_driver import ImmediateBroker, advance

    from living_world.archives import (
        AttemptConfig,
        AttemptLease,
        load_retained_inputs,
        retain_inputs,
    )
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime.journal_replay import (
        JournalReplayComposition,
        JournalReplayDriver,
    )
    from living_world.runtime.ollama_driver import (
        OllamaTickDriver,
        effective_config_fingerprint,
    )

    catalog, lease, source, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        driver, base = initialized(source, live, broker)
        final = advance(driver, live, source, base)
        if legacy_source:
            import json
            import sqlite3

            from test_inference_trace_storage import legacy

            with sqlite3.connect(source.database_path) as db:
                for seq, payload in db.execute(
                    "SELECT sequence,payload FROM journal"
                ).fetchall():
                    document = json.loads(payload)
                    document.pop("request_trace", None)
                    document.pop("response_trace", None)
                    db.execute(
                        "UPDATE journal SET payload=? WHERE sequence=?",
                        (json.dumps(document), seq),
                    )
            source = legacy(source)
        expected = [e for e in source.entries() if e.kind == "request_started"]
        child_ref = catalog.fork(source.ref.attempt_id, 0)
        with (
            AttemptLease(child_ref),
            catalog.open_attempt(child_ref.attempt_id, read_only=False) as child,
        ):
            cold = OllamaTickDriver(driver.config, driver.feedback, ImmediateBroker())
            advance(cold, live, child, child.checkpoint())
            reused = [e for e in child.entries() if e.kind == "response_reused"]
            for entry, original in zip(reused, expected):
                assert entry.payload.get("request_trace") == original.payload.get(
                    "request_trace"
                )
                if legacy_source:
                    assert (
                        "request_trace" not in entry.payload
                        and "response_trace" not in entry.payload
                    )
                else:
                    sha = entry.payload["request_trace"]["body_digest"]
                    assert child.inference_blobs((sha,)) == source.inference_blobs(
                        (sha,)
                    )
        config = AttemptConfig(
            "journal_replay",
            source.config.scenario_key,
            source.config.seed,
            "test",
            {"source_config_fingerprint": effective_config_fingerprint(source.config)},
        )
        ref = catalog.reserve(config)
        retain_inputs(
            ref, load_retained_inputs(source.ref).scenario_path, tape_path=None
        )
        from living_world.runtime.founders import FoundersLiveComposition

        replay = JournalReplayComposition(
            source, FoundersLiveComposition(load_retained_inputs(ref))
        )
        replay_driver = JournalReplayDriver(source, driver.feedback)
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as target,
        ):
            candidate = replay.initialize()
            commit = replay_driver.initialize(candidate, target)
            local = target.commit(
                encode_world(candidate.state),
                expected_revision=None,
                driver_cursor=commit.driver_cursor,
                feedback_cursor=commit.feedback_cursor,
                entries=(),
            )
            hidden = source.ref.directory.with_name(
                source.ref.directory.name + "-offline"
            )
            source.ref.directory.rename(hidden)
            try:
                result = advance(replay_driver, replay, target, local)
                assert result.snapshot == final.snapshot
                for entry in target.entries():
                    trace = entry.payload.get("request_trace")
                    if trace is not None:
                        body = target.inference_blobs((trace["body_digest"],))[0].body
                        assert hashlib.sha256(body).hexdigest() == trace["body_digest"]
            finally:
                hidden.rename(source.ref.directory)
            reused = [e for e in target.entries() if e.kind == "response_reused"]
            for entry, original in zip(reused, expected):
                assert entry.payload.get("request_trace") == original.payload.get(
                    "request_trace"
                )
                if legacy_source:
                    assert (
                        "request_trace" not in entry.payload
                        and "response_trace" not in entry.payload
                    )
                else:
                    sha = entry.payload["request_trace"]["body_digest"]
                    assert target.inference_blobs((sha,)) == source.inference_blobs(
                        (sha,)
                    )
    finally:
        source.close()
        lease.release()


def test_cleanup_failure_is_fixed_warning_and_no_duplicate_response(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from test_runtime_ollama_driver import ImmediateBroker

    class BrokenAck(ImmediateBroker):
        def acknowledge_trace(self, job_id: str, *, result: object = None) -> None:
            raise OSError("SECRET /private/path raw model body")

    _, lease, archive, live = live_archive(tmp_path)
    try:
        driver, base = initialized(archive, live, BrokenAck())
        prep = driver.prepare(live.restore(base.snapshot), base, archive)
        # A failed cleanup intentionally leaves the broker's previous trace bound,
        # preventing another dispatch. Settle just the first result and pause.
        prep.poll()
        prep.request_pause()
        assert prep.poll() == "paused"
        before = [e for e in archive.entries() if e.kind == "response_validated"]
        assert len(before) == 1
        prep.close()
        prep.close()
        assert [
            e for e in archive.entries() if e.kind == "response_validated"
        ] == before
        assert caplog.messages == ["Inference trace cleanup pending."]
        assert list((archive.database_path.parent / "inference-spool").iterdir())
    finally:
        archive.close()
        lease.release()


def test_legacy_direct_guard_precedes_feedback_and_child_traces(tmp_path: Path) -> None:
    from test_inference_trace_storage import legacy
    from test_runtime_ollama_driver import ImmediateBroker, ready

    from living_world.archives import ArchiveFormatError, AttemptLease
    from living_world.runtime.ollama_driver import OllamaTickDriver

    catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        driver, base = initialized(archive, live, broker)
        old = legacy(archive)
        candidate = live.restore(base.snapshot)
        driver.validate_checkpoint(candidate, base, old)
        with pytest.raises(
            ArchiveFormatError,
            match="Exact inference traces require archive format two; resume into a new attempt.",
        ):
            driver.prepare(candidate, base, old)
        assert broker.calls == []
        assert old.entries() == archive.entries()
        ref = catalog.fork(old.ref.attempt_id, 0)
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as child,
        ):
            cold = OllamaTickDriver(driver.config, driver.feedback, ImmediateBroker())
            prep = cold.prepare(live.restore(base.snapshot), child.checkpoint(), child)
            assert ready(prep) == "ready"
            prep.close()
            assert all(
                "request_trace" in e.payload
                for e in child.entries()
                if e.kind == "request_started"
            )
        old.close()
    finally:
        archive.close()
        lease.release()


def test_sealed_prefix_does_not_capture_later_response_and_rejects_tamper(
    tmp_path: Path,
) -> None:
    import sqlite3

    from test_runtime_ollama_driver import ImmediateBroker

    from living_world.archives import ArchiveFormatError
    from living_world.runtime.archive_inference import capture_trace_blobs, trace_fields

    _, lease, archive, live = live_archive(tmp_path)
    try:
        driver, base = initialized(archive, live, ImmediateBroker())
        prep = driver.prepare(live.restore(base.snapshot), base, archive)
        prep.poll()
        seal = archive.journal_boundary()
        started = archive.entries()[-1]
        prep.request_pause()
        prep.poll()
        response = archive.entries()[-1]
        assert len(capture_trace_blobs(archive, seal, (started,))) == 1
        with pytest.raises(ArchiveFormatError, match="outside selected prefix"):
            capture_trace_blobs(archive, seal, (started, response))
        with pytest.raises(ArchiveFormatError, match="identity mismatch"):
            trace_fields(
                started,
                type(response)(
                    response.kind, {**response.payload, "request_id": "other"}
                ),
            )
        prep.close()
        with sqlite3.connect(archive.database_path) as db:
            db.execute(
                "UPDATE journal SET payload=replace(payload, 'local', 'other') WHERE kind='request_started'"
            )
        with pytest.raises(ArchiveFormatError):
            capture_trace_blobs(archive, seal, (started,))
    finally:
        archive.close()
        lease.release()


@pytest.mark.parametrize(
    "body,status,cap,code",
    [
        (b"bad", 200, 100, "invalid_response"),
        (b"\xff", 200, 100, "invalid_response"),
        (b"", 200, 100, "invalid_response"),
        (b"{}", 200, 100, "invalid_response"),
        (b"private error", 503, 100, "http_error"),
        (b"123456789", 200, 4, "oversized_response"),
        (
            b'{"response":"{\\"spoken_text\\":\\"next_index is hidden\\",\\"action_request\\":null}"}',
            200,
            1000,
            "unsafe_response",
        ),
    ],
)
def test_archived_raw_failures_survive_without_staging(
    tmp_path: Path, server, body: bytes, status: int, cap: int, code: str
) -> None:
    url, handler = server
    handler.response_body, handler.status = body, status
    _, lease, archive, live = live_archive(
        tmp_path,
        provider={
            "model": "local",
            "base_url": url,
            "timeout_seconds": 3,
            "max_response_bytes": cap,
        },
    )
    broker = DecisionBroker()
    try:
        driver, base = initialized(archive, live, broker)
        prep = driver.prepare(live.restore(base.snapshot), base, archive)
        deadline = time.monotonic() + 10
        outcome = "waiting"
        while outcome == "waiting" and time.monotonic() < deadline:
            outcome = prep.poll()
            time.sleep(0.01)
        assert outcome == "provider_error" and prep.error_code == code
        assert prep.staged == [] and archive.checkpoint() == base
        response = [e for e in archive.entries() if e.kind == "response_failed"][-1]
        trace = response.payload["response_trace"]
        expected = body[: cap + 1] if code == "oversized_response" else body
        assert archive.inference_blobs((trace["body_digest"],))[0].body == expected
        assert trace["body_state"] == (
            "incomplete" if code == "oversized_response" else "complete"
        )
        assert "decision" not in response.payload
        prep.close()
    finally:
        broker.close()
        archive.close()
        lease.release()


@pytest.mark.parametrize("cancel", [False, True])
def test_timeout_and_close_preserve_partial_capture(
    tmp_path: Path, server, cancel: bool
) -> None:
    url, handler = server
    handler.response_body = b"private incomplete response"
    handler.delay = 1
    _, lease, archive, live = live_archive(
        tmp_path, provider={"model": "local", "base_url": url, "timeout_seconds": 0.4}
    )
    broker = DecisionBroker()
    try:
        driver, base = initialized(archive, live, broker)
        prep = driver.prepare(live.restore(base.snapshot), base, archive)
        prep.poll()
        if cancel:
            deadline = time.monotonic() + 3
            while not handler.received and time.monotonic() < deadline:
                time.sleep(0.01)
            time.sleep(0.1)
            prep.close()
        else:
            deadline = time.monotonic() + 5
            status = "waiting"
            while status == "waiting" and time.monotonic() < deadline:
                status = prep.poll()
                time.sleep(0.01)
            assert status == "provider_error" and prep.error_code == "timeout"
        response = [e for e in archive.entries() if e.kind == "response_failed"][-1]
        trace = response.payload["response_trace"]
        assert response.payload["code"] == ("cancelled" if cancel else "timeout")
        assert trace["durations"]["broker_seconds"] > 0
        assert archive.checkpoint() == base and prep.staged == []
        if trace["body_state"] != "unavailable":
            assert archive.inference_blobs((trace["body_digest"],))[0].body == b"p"
        prep.close()
    finally:
        broker.close()
        archive.close()
        lease.release()


@pytest.mark.parametrize("fail_import", [False, True])
def test_captured_complete_stop_and_failed_import_keep_evidence(
    tmp_path: Path, server, monkeypatch: pytest.MonkeyPatch, fail_import: bool
) -> None:
    url, handler = server
    raw = b'{"response":"{\\"spoken_text\\":\\"I will watch.\\",\\"action_request\\":null}"}'
    handler.response_body = raw
    _, lease, archive, live = live_archive(
        tmp_path, provider={"model": "local", "base_url": url, "timeout_seconds": 3}
    )
    broker = DecisionBroker()
    try:
        driver, base = initialized(archive, live, broker)
        prep = driver.prepare(live.restore(base.snapshot), base, archive)
        prep.poll()
        job = prep.active[1]
        deadline = time.monotonic() + 10
        result = None
        while result is None and time.monotonic() < deadline:
            result = broker.poll(job)
            time.sleep(0.01)
        assert result is not None and result.response_body == raw
        if fail_import:

            def fail(*args: object, **kwargs: object) -> None:
                raise OSError("storage unavailable")

            monkeypatch.setattr(archive, "record", fail)
            with pytest.raises(OSError):
                prep.poll()
            assert prep.active is not None and prep.staged == []
            with pytest.raises(OSError):
                prep.close()
            assert list((archive.database_path.parent / "inference-spool").iterdir())
            assert not any(
                e.kind in ("response_validated", "response_failed", "action_resolved")
                for e in archive.entries()
            )
        else:
            prep.close()
            responses = [e for e in archive.entries() if e.kind == "response_failed"]
            assert len(responses) == 1 and responses[0].payload["code"] == "cancelled"
            assert responses[0].payload["response_trace"] == result.response_trace
            sha = responses[0].payload["response_trace"]["body_digest"]
            assert archive.inference_blobs((sha,))[0].body == raw
            assert not list(
                (archive.database_path.parent / "inference-spool").iterdir()
            )
        assert (
            prep.system is None and prep.staged == [] and archive.checkpoint() == base
        )
    finally:
        broker.close()
        archive.close()
        lease.release()


def _crash_with_unimported_capture(root: str, attempt_id: str) -> None:
    import os

    from living_world.archives import AttemptLease, RunCatalog, load_retained_inputs
    from living_world.runtime.founders import FoundersLiveComposition

    catalog = RunCatalog(Path(root))
    ref = next(
        item.ref for item in catalog.attempts() if item.ref.attempt_id == attempt_id
    )
    with (
        AttemptLease(ref),
        catalog.open_attempt(attempt_id, read_only=False) as archive,
    ):
        live = FoundersLiveComposition(load_retained_inputs(archive.ref))
        from living_world.runtime.broker import (
            client_for,
            encoded_body,
            provider_config,
        )
        from living_world.runtime.feedback import FoundersFeedback
        from living_world.runtime.ollama_driver import OllamaTickDriver

        config = provider_config(archive.config)
        client = client_for(config)
        feedback = FoundersFeedback(
            lambda context, options: len(
                encoded_body(client.build_payload(context, options))
            )
        )
        broker = DecisionBroker()
        driver = OllamaTickDriver(config, feedback, broker)
        base = archive.checkpoint()
        prep = driver.prepare(live.restore(base.snapshot), base, archive)
        prep.poll()
        job = prep.active[1]
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if broker.poll(job) is not None:
                os._exit(73)
            time.sleep(0.01)
        os._exit(74)


def test_hard_crash_spool_remains_uncommitted_and_child_does_not_recover(
    tmp_path: Path, server
) -> None:
    import os
    import subprocess
    import sys

    from test_runtime_ollama_driver import ImmediateBroker, ready

    from living_world.archives import AttemptLease
    from living_world.runtime.ollama_driver import OllamaTickDriver

    url, handler = server
    handler.response_body = b'{"response":"{\\"spoken_text\\":\\"private unpublished\\",\\"action_request\\":null}"}'
    catalog, lease, archive, live = live_archive(
        tmp_path, provider={"model": "local", "base_url": url, "timeout_seconds": 3}
    )
    try:
        driver, base = initialized(archive, live, ImmediateBroker())
        lease.release()
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from test_runtime_archive_inference import _crash_with_unimported_capture; import sys; _crash_with_unimported_capture(*sys.argv[1:])",
                str(tmp_path),
                archive.ref.attempt_id,
            ],
            env={**os.environ, "PYTHONPATH": "src:tests"},
            capture_output=True,
            check=False,
            timeout=15,
        )
        assert result.returncode == 73, result.stderr.decode()
        before = archive.entries()
        spool = archive.database_path.parent / "inference-spool"
        files = {p: p.read_bytes() for p in spool.rglob("*") if p.is_file()}
        assert files and not any(e.kind.startswith("response_") for e in before)
        ref = catalog.fork(archive.ref.attempt_id, 0)
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as child,
        ):
            broker = ImmediateBroker()
            cold = OllamaTickDriver(driver.config, driver.feedback, broker)
            prep = cold.prepare(live.restore(base.snapshot), child.checkpoint(), child)
            assert ready(prep) == "provider_error" and prep.error_code == "uncertain"
            assert broker.calls == []
            assert not any(e.kind == "response_reused" for e in child.entries())
            prep.close()
        assert archive.entries() == before
        assert {p: p.read_bytes() for p in spool.rglob("*") if p.is_file()} == files
    finally:
        archive.close()
        lease.release()


def test_offline_replay_preserves_captured_response_evidence_and_local_identity(
    tmp_path: Path,
) -> None:
    """Real response bytes and original clocks survive source-independent replay."""
    import json
    import sqlite3

    from living_world.archives import (
        ArchiveFormatError,
        AttemptConfig,
        AttemptLease,
        load_retained_inputs,
        retain_inputs,
    )
    from living_world.archives.model import canonical
    from living_world.repositories.world_snapshot import decode_world, encode_world
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.runtime.journal_replay import (
        JournalReplayComposition,
        JournalReplayDriver,
    )
    from living_world.runtime.ollama_driver import effective_config_fingerprint

    bodies = tuple(
        json.dumps(
            {"response": json.dumps({"spoken_text": text, "action_request": None})}
        ).encode()
        for text in ("I will watch.", "I will rest.")
    )

    class Handler(BaseHTTPRequestHandler):
        calls = 0

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            slot = Handler.calls
            Handler.calls += 1
            self.send_response(200)
            self.end_headers()
            time.sleep((0.03, 0.15)[slot])
            self.wfile.write(bodies[slot])

        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as http:
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        catalog, lease, source, live = live_archive(
            tmp_path,
            provider={
                "model": "local",
                "base_url": f"http://127.0.0.1:{http.server_port}",
                "timeout_seconds": 5,
            },
        )
        broker = DecisionBroker()
        try:
            driver, base = initialized(source, live, broker)
            original = live.restore(base.snapshot)
            preparation = driver.prepare(original, base, source)
            deadline = time.monotonic() + 15
            status = "waiting"
            while status == "waiting" and time.monotonic() < deadline:
                status = preparation.poll()
                time.sleep(0.01)
            assert status == "ready" and Handler.calls == 2
            preparation.install()
            original.step()
            commit = preparation.finish_tick()
            final = source.commit(
                encode_world(original.state),
                expected_revision=base.revision,
                driver_cursor=commit.driver_cursor,
                feedback_cursor=commit.feedback_cursor,
                entries=commit.journal_entries,
            )
            preparation.close()
            expected_requests = [
                e.payload for e in source.entries() if e.kind == "request_started"
            ]
            expected_responses = [
                e.payload for e in source.entries() if e.kind == "response_validated"
            ]
            assert len(expected_requests) == len(expected_responses) == 2
            expected_request_bodies = tuple(
                source.inference_blobs((payload["request_trace"]["body_digest"],))[
                    0
                ].body
                for payload in expected_requests
            )
            original_durations = [
                p["response_trace"]["durations"]["broker_seconds"]
                for p in expected_responses
            ]
            assert all(value > 0 for value in original_durations)
            assert original_durations[0] != original_durations[1]
            assert (
                expected_responses[0]["response_trace"]["timestamps"]
                != expected_responses[1]["response_trace"]["timestamps"]
            )
            for payload, body in zip(expected_responses, bodies):
                assert payload["response_trace"]["body_state"] == "complete"
                assert payload["content_digest"] == hashlib.sha256(body).hexdigest()
                assert payload["elapsed_seconds"] > 0

            config = AttemptConfig(
                "journal_replay",
                source.config.scenario_key,
                source.config.seed,
                "test",
                {
                    "source_config_fingerprint": effective_config_fingerprint(
                        source.config
                    )
                },
            )
            ref = catalog.reserve(config)
            inputs = retain_inputs(
                ref, load_retained_inputs(source.ref).scenario_path, tape_path=None
            )
            replay = JournalReplayComposition(source, FoundersLiveComposition(inputs))
            replay_driver = JournalReplayDriver(source, driver.feedback)
            # Capture completes while source exists. Replay cannot call the provider
            # or consult the source directory from this point onward.
            http.shutdown()
            thread.join(2)
            source.close()
            hidden = source.ref.directory.with_name(
                source.ref.directory.name + "-offline"
            )
            source.ref.directory.rename(hidden)
            try:
                with (
                    AttemptLease(ref),
                    catalog.open_attempt(ref.attempt_id, read_only=False) as target,
                ):
                    candidate = replay.initialize()
                    initial = replay_driver.initialize(candidate, target)
                    local = target.commit(
                        encode_world(candidate.state),
                        expected_revision=None,
                        driver_cursor=initial.driver_cursor,
                        feedback_cursor=initial.feedback_cursor,
                        entries=(),
                    )
                    prepared = replay_driver.prepare(candidate, local, target)
                    assert prepared.poll() == "ready"
                    imported = target.journal_records()
                    copied = [
                        r.entry.payload
                        for r in imported
                        if r.entry.kind == "response_reused"
                    ]
                    assert len(copied) == 2
                    for actual, request, response, body, original_request_body in zip(
                        copied,
                        expected_requests,
                        expected_responses,
                        bodies,
                        expected_request_bodies,
                    ):
                        assert actual["request_trace"] == request["request_trace"]
                        for key in (
                            "response_trace",
                            "content_digest",
                            "elapsed_seconds",
                        ):
                            assert actual[key] == response[key]
                        assert actual["response_trace"]["body_length"] == len(body)
                        response_sha = actual["response_trace"]["body_digest"]
                        assert target.inference_blobs((response_sha,))[0].body == body
                        request_sha = actual["request_trace"]["body_digest"]
                        request_body = target.inference_blobs((request_sha,))[0].body
                        assert request_body == original_request_body
                        assert hashlib.sha256(request_body).hexdigest() == request_sha
                    digests = tuple(
                        sorted(
                            {
                                payload[key]["body_digest"]
                                for payload in copied
                                for key in ("request_trace", "response_trace")
                            }
                        )
                    )
                    imported_bodies = target.inference_blobs(digests)

                    repeated = replay_driver.prepare(
                        replay.restore(local.snapshot), local, target
                    )
                    assert repeated.poll() == "ready"
                    assert target.journal_records() == imported
                    assert target.inference_blobs(digests) == imported_bodies
                    repeated.close()
                    prepared.install()
                    candidate.step()
                    replayed = prepared.finish_tick()
                    actual = target.commit(
                        encode_world(candidate.state),
                        expected_revision=local.revision,
                        driver_cursor=replayed.driver_cursor,
                        feedback_cursor=replayed.feedback_cursor,
                        entries=replayed.journal_entries,
                    )
                    prepared.close()
                    assert actual.snapshot == final.snapshot
                    assert decode_world(actual.snapshot).events == original.state.events
                    assert actual.driver_cursor == final.driver_cursor
                    assert actual.feedback_cursor == final.feedback_cursor
                    assert Handler.calls == 2

                    # Valid-but-different local timing passes storage validation;
                    # the replay's evidence identity guard must reject it itself.
                    with sqlite3.connect(target.database_path) as db:
                        sequence, payload = db.execute(
                            "SELECT sequence,payload FROM journal WHERE kind='response_reused' ORDER BY sequence LIMIT 1"
                        ).fetchone()
                        changed = json.loads(payload)
                        changed["response_trace"]["durations"]["broker_seconds"] += 1
                        db.execute(
                            "UPDATE journal SET payload=? WHERE sequence=?",
                            (canonical(changed), sequence),
                        )
                    valid_but_changed = target.journal_records()
                    with pytest.raises(
                        ArchiveFormatError,
                        match="Replay local inference trace mismatch",
                    ):
                        replay_driver.prepare(
                            replay.restore(local.snapshot), local, target
                        )
                    assert target.journal_records() == valid_but_changed
                    assert target.checkpoint() == actual
            finally:
                hidden.rename(source.ref.directory)
        finally:
            broker.close()
            source.close()
            lease.release()
            http.shutdown()
            thread.join(2)
