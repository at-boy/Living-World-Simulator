"""Exact-byte capture, durable spool and real spawned HTTP regressions."""

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import pytest

from living_world.cognition.npc_context import NPCContext
from living_world.perception.local_llm_http import (
    LocalLLMHttpError,
    UrllibJsonHttpTransport,
)
from living_world.runtime.broker import DecisionBroker, ProviderConfig
from living_world.runtime.feedback import DecisionInput


def prepared(config=None):
    from living_world.runtime.inference_trace import prepare_inference

    return prepare_inference(
        config or ProviderConfig(model="local"), NPCContext("Erik", (), (), (), ()), ()
    )


def test_prepared_exact_and_frozen_both_providers():
    from living_world.runtime.broker import client_for, encoded_body

    for kind in ("ollama", "llama_cpp"):
        config = ProviderConfig(
            model="local",
            kind=kind,
            model_file="/tmp/m.gguf" if kind == "llama_cpp" else None,
        )
        p = prepared(config)
        assert (
            p.body
            == encoded_body(
                client_for(config).build_payload(NPCContext("Erik", (), (), (), ()), ())
            ).encode()
        )
        assert p.request_trace["body_digest"] == hashlib.sha256(p.body).hexdigest()
        assert p.request_trace["body_length"] == len(p.body)
        with pytest.raises(TypeError):
            p.request_trace["headers"]["Content-Type"] = "bad"


def test_spool_atomic_bounded_and_explicit_unavailable(tmp_path):
    from living_world.runtime.inference_spool import (
        create_trace_spool,
        publish_trace_snapshot,
        read_trace_snapshot,
    )
    from living_world.runtime.inference_trace import settle_observation

    p = prepared()
    directory = create_trace_spool(tmp_path / "spools", "a" * 32)
    assert directory.stat().st_mode & 0o777 == 0o700
    assert read_trace_snapshot(directory, p) is None
    (directory / "observation.partial").write_text("partial crash")
    assert read_trace_snapshot(directory, p) is None
    (directory / "observation.partial").unlink()
    o = settle_observation(
        None,
        dispatch_started_at="2026-10-27T10:00:00+00:00",
        settled_at="2026-10-26T10:00:00+00:00",
        broker_seconds=1,
    )
    publish_trace_snapshot(directory, p, o)
    assert (directory / "observation.json").stat().st_mode & 0o777 == 0o600
    assert read_trace_snapshot(directory, p) == o
    (directory / "observation.json").write_text('{"format":1,"format":1}')
    with pytest.raises(ValueError):
        read_trace_snapshot(directory, p)


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        response_body = b"{}"
        status = 200
        delay = 0.0
        before_body = 0.0
        drip = 0.0
        received: ClassVar[list[bytes]] = []

        def do_POST(self):
            self.received.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(self.status)
            self.end_headers()
            try:
                time.sleep(self.before_body)
                if self.drip:
                    for byte in self.response_body:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(self.drip)
                elif self.delay:
                    self.wfile.write(self.response_body[:1])
                    self.wfile.flush()
                    time.sleep(self.delay)
                    self.wfile.write(self.response_body[1:])
                else:
                    self.wfile.write(self.response_body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as srv:
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{srv.server_port}", Handler
        srv.shutdown()
        thread.join(2)


@pytest.mark.parametrize(
    "body,status,cap,code",
    [
        (b"\xff", 200, 100, "invalid_response"),
        (b"bad", 200, 100, "invalid_response"),
        (b"", 200, 100, "invalid_response"),
        (b"error", 503, 100, "http_error"),
        (b"123456789", 200, 4, "oversized_response"),
    ],
)
def test_http_observes_raw_failures(server, body, status, cap, code):
    base, handler = server
    handler.response_body, handler.status = body, status
    observations = []
    with pytest.raises(LocalLLMHttpError) as exc:
        UrllibJsonHttpTransport(cap).post_bytes(
            url=base + "/api/generate",
            body=b"{}",
            timeout_seconds=2,
            observer=observations.append,
        )
    assert exc.value.code == code
    assert observations[0].body is None
    assert observations[-1].body == body[: cap + 1]
    assert observations[-1].status_code == status
    assert observations[-1].complete == (len(body) <= cap)
    assert observations[-1].durations["http_seconds"] is not None
    assert (observations[-1].timestamps["first_body_byte_at"] is None) == (not body)


def wait_result(broker, job):
    end = time.monotonic() + 8
    while time.monotonic() < end:
        result = broker.poll(job)
        if result is not None:
            return result
        time.sleep(0.01)
    pytest.fail("broker did not settle")


@pytest.mark.parametrize("kind", ["ollama", "llama_cpp"])
def test_bound_spawn_exact_bytes_and_ack(server, tmp_path, kind):
    base, handler = server
    answer = {"spoken_text": "I watch.", "action_request": None}
    handler.response_body = json.dumps(
        {"response": json.dumps(answer)}
        if kind == "ollama"
        else {"choices": [{"message": {"content": json.dumps(answer)}}]}
    ).encode()
    config = ProviderConfig(
        model="local",
        base_url=base,
        timeout_seconds=5,
        kind=kind,
        model_file="/tmp/m.gguf" if kind == "llama_cpp" else None,
    )
    p = prepared(config)
    broker = DecisionBroker()
    job = "a" * 32
    broker.bind_trace(job, p, spool_root=tmp_path / "spools")
    with pytest.raises(ValueError):
        broker.acknowledge_trace(job)
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    result = wait_result(broker, job)
    assert result.decision is not None
    assert handler.received == [p.body]
    assert result.response_body == handler.response_body
    assert result.response_trace["body_state"] == "complete"
    assert result.response_trace["durations"]["worker_seconds"] is not None
    assert broker.poll(job) is result
    directory = tmp_path / "spools" / job
    assert directory.exists()
    broker.acknowledge_trace(job)
    assert not directory.exists()
    broker.close()


def test_observer_failure_fails_closed(server):
    base, _ = server

    def fail(_):
        raise OSError("private error")

    with pytest.raises(LocalLLMHttpError) as exc:
        UrllibJsonHttpTransport().post_bytes(
            url=base, body=b"{}", timeout_seconds=1, observer=fail
        )
    assert exc.value.code == "worker_failed"


def test_partial_eof_is_not_complete(server):
    # A bounded client must distinguish truncated Content-Length from EOF.
    import io
    from http.client import HTTPResponse

    class Socket:
        def makefile(self, *args):
            return io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 8\r\n\r\n{}")

    response = HTTPResponse(Socket())
    response.begin()
    from unittest.mock import patch

    observations = []

    class Opener:
        def open(self, *args, **kwargs):
            return response

    with (
        patch(
            "living_world.perception.local_llm_http.build_opener", return_value=Opener()
        ),
        pytest.raises(LocalLLMHttpError),
    ):
        UrllibJsonHttpTransport().post_bytes(
            url=server[0],
            body=b"{}",
            timeout_seconds=1,
            observer=observations.append,
        )
    assert observations[-1].body == b"{}"
    assert not observations[-1].complete


def test_no_super_broker_explicit_ack(tmp_path):
    from living_world.runtime.broker import BrokerResult

    class Injected(DecisionBroker):
        def __init__(self):
            pass

        def start(self, job_id, config, decision_input):
            pass

    broker = Injected()
    job = "a" * 32
    broker.bind_trace(job, prepared(), spool_root=tmp_path / "spools")
    with pytest.raises(ValueError):
        broker.acknowledge_trace(job)
    broker.acknowledge_trace(
        job, result=BrokerResult(job, None, "worker_failed", None, 0)
    )
    assert not (tmp_path / "spools" / job).exists()


def test_cancel_reaps_before_harvest_and_preserves_prefix(server, tmp_path):
    from living_world.runtime.inference_spool import read_trace_snapshot

    base, handler = server
    handler.delay, handler.response_body = 2, b"{}"
    config = ProviderConfig(model="local", base_url=base, timeout_seconds=5)
    broker, job, p = DecisionBroker(), "a" * 32, prepared(config)
    broker.bind_trace(job, p, spool_root=tmp_path / "spools")
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    directory = tmp_path / "spools" / job
    end = time.monotonic() + 4
    while time.monotonic() < end:
        o = read_trace_snapshot(directory, p)
        if o is not None and o.body == b"{":
            break
        time.sleep(0.01)
    else:
        pytest.fail("prefix was not published")
    process = broker._process
    broker.close()
    assert broker._process is None
    with pytest.raises(ValueError):
        process.is_alive()  # closed only after reaping
    result = broker.poll(job)
    assert result.error_code == "cancelled"
    assert result.response_body == b"{"
    assert result.response_trace["body_state"] == "incomplete"
    assert result.response_trace["durations"]["worker_seconds"] is None
    assert result.response_trace["timestamps"]["first_body_byte_at"] is not None
    assert result.response_trace["timestamps"]["read_finished_at"] is None
    assert directory.exists()
    broker.acknowledge_trace(job, result=result)


@pytest.mark.parametrize(
    "variant",
    [
        "digest",
        "duplicate",
        "oversized",
        "symlink",
        "directory",
        "base64",
        "null",
        "nonfinite",
    ],
)
def test_corrupt_spool_rejected_and_retained(tmp_path, variant):
    from living_world.runtime.inference_spool import (
        create_trace_spool,
        publish_trace_snapshot,
        read_trace_snapshot,
    )
    from living_world.runtime.inference_trace import settle_observation

    directory = create_trace_spool(tmp_path / "spools", "a" * 32)
    p = prepared(ProviderConfig(model="local", max_response_bytes=10))
    o = settle_observation(
        None,
        dispatch_started_at="2026-01-01T00:00:00+00:00",
        settled_at="2026-01-01T00:00:00+00:00",
        broker_seconds=0,
    )
    publish_trace_snapshot(directory, p, o)
    path = directory / "observation.json"
    frame = json.loads(path.read_bytes())
    if variant == "digest":
        frame["request_body_digest"] = "b" * 64
    elif variant == "base64":
        frame["body_base64"] = "@@"
    elif variant == "null":
        frame["body_base64"] = ""
    elif variant == "nonfinite":
        frame["response_trace"]["durations"]["http_seconds"] = float("inf")
    if variant == "duplicate":
        path.write_text('{"format":1,"format":1}')
    elif variant == "oversized":
        path.write_bytes(b" " * 70000)
    elif variant == "symlink":
        path.unlink()
        path.symlink_to(tmp_path / "elsewhere")
    elif variant == "directory":
        path.unlink()
        path.mkdir()
    else:
        path.write_text(json.dumps(frame))
    with pytest.raises(ValueError):
        read_trace_snapshot(directory, p)
    assert directory.exists()


def test_request_mismatch_rejected_before_network(tmp_path):
    broker, job = DecisionBroker(), "a" * 32
    broker.bind_trace(job, prepared(), spool_root=tmp_path / "spools")
    with pytest.raises(ValueError):
        broker.start(
            job,
            ProviderConfig(model="different"),
            DecisionInput(
                "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
            ),
        )
    assert broker._process is None


def test_http_total_deadline_and_prefix(server):
    base, handler = server
    handler.delay, handler.response_body = 0.3, b"{}"
    observations = []
    with pytest.raises(LocalLLMHttpError) as exc:
        UrllibJsonHttpTransport().post_bytes(
            url=base, body=b"{}", timeout_seconds=0.1, observer=observations.append
        )
    assert exc.value.code == "timeout"
    assert observations[-1].body == b"{"
    assert not observations[-1].complete
    assert observations[-1].timestamps["read_finished_at"] is not None


def test_fsync_failure_and_symlink_root_are_safe(tmp_path, monkeypatch):
    from living_world.runtime.inference_spool import (
        create_trace_spool,
        publish_trace_snapshot,
    )
    from living_world.runtime.inference_trace import settle_observation

    root = tmp_path / "link"
    root.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        create_trace_spool(root, "a" * 32)
    directory = create_trace_spool(tmp_path / "spools", "a" * 32)

    def fail(_):
        raise OSError("private")

    monkeypatch.setattr("living_world.runtime.inference_spool.os.fsync", fail)
    o = settle_observation(
        None,
        dispatch_started_at="2026-01-01T00:00:00+00:00",
        settled_at="2026-01-01T00:00:00+00:00",
        broker_seconds=0,
    )
    with pytest.raises(ValueError, match="^Inference capture failed.$"):
        publish_trace_snapshot(directory, prepared(), o)
    assert not (directory / "observation.json").exists()
    assert (directory / "observation.partial").exists()


@pytest.mark.parametrize(
    "corruption", ["invalid", "missing", "incomplete", "status", "digest"]
)
def test_capture_corruption_never_accepts_real_decision(server, tmp_path, corruption):
    base, handler = server
    handler.response_body = (
        b'{"response":"{\\"spoken_text\\":\\"I watch.\\",\\"action_request\\":null}"}'
    )
    config = ProviderConfig(model="local", base_url=base, timeout_seconds=5)
    broker, job = DecisionBroker(), "a" * 32
    broker.bind_trace(job, prepared(config), spool_root=tmp_path / "spools")
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    end = time.monotonic() + 4
    while broker._process.is_alive() and time.monotonic() < end:
        time.sleep(0.01)
    path = tmp_path / "spools" / job / "observation.json"
    if corruption == "invalid":
        path.write_text("corrupt")
    elif corruption == "missing":
        path.unlink()
    else:
        frame = json.loads(path.read_bytes())
        if corruption == "incomplete":
            frame["response_trace"]["body_state"] = "incomplete"
        elif corruption == "status":
            frame["response_trace"]["http_status"] = 503
        else:
            frame["response_trace"]["body_digest"] = "a" * 64
        path.write_text(json.dumps(frame))
    result = wait_result(broker, job)
    assert result.error_code == "worker_failed"
    assert result.decision is None
    assert result.response_trace["body_state"] == "unavailable"
    with pytest.raises(ValueError):
        broker.acknowledge_trace(job, result=result)
    assert path.parent.exists()


@pytest.mark.parametrize("settlement", ["deadline", "close"])
def test_complete_body_does_not_override_timeout_or_cancel(
    server, tmp_path, settlement
):
    base, handler = server
    handler.response_body = (
        b'{"response":"{\\"spoken_text\\":\\"I watch.\\",\\"action_request\\":null}"}'
    )
    config = ProviderConfig(model="local", base_url=base, timeout_seconds=5)
    broker, job = DecisionBroker(), "a" * 32
    broker.bind_trace(job, prepared(config), spool_root=tmp_path / "spools")
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    end = time.monotonic() + 4
    while broker._process.is_alive() and time.monotonic() < end:
        time.sleep(0.01)
    if settlement == "deadline":
        broker._deadline = 0
    else:
        broker.close()
    result = wait_result(broker, job)
    assert result.error_code == ("timeout" if settlement == "deadline" else "cancelled")
    assert result.decision is None
    assert result.response_trace["body_state"] == "complete"
    assert result.response_body == handler.response_body
    assert broker._process is None


def test_publication_failure_never_returns_accepted_result(server, tmp_path):
    base, handler = server
    handler.response_body = (
        b'{"response":"{\\"spoken_text\\":\\"I watch.\\",\\"action_request\\":null}"}'
    )
    config = ProviderConfig(model="local", base_url=base, timeout_seconds=5)
    broker, job = DecisionBroker(), "a" * 32
    broker.bind_trace(job, prepared(config), spool_root=tmp_path / "spools")
    directory = tmp_path / "spools" / job
    (directory / "observation.partial").write_text("crash")
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    result = wait_result(broker, job)
    assert result.error_code == "worker_failed" and result.decision is None
    assert result.response_trace["body_state"] == "unavailable"
    assert directory.exists()
    assert handler.received == []  # callback before HTTP open failed


def test_start_failure_settles_unavailable(tmp_path, monkeypatch):
    import multiprocessing

    broker, job = DecisionBroker(), "a" * 32
    broker.bind_trace(job, prepared(), spool_root=tmp_path / "spools")

    def fail(_):
        raise OSError("private")

    monkeypatch.setattr(multiprocessing.get_context("spawn").Process, "start", fail)
    with pytest.raises(OSError):
        broker.start(
            job,
            ProviderConfig(model="local"),
            DecisionInput(
                "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
            ),
        )
    result = broker.poll(job)
    assert result.error_code == "worker_failed"
    assert result.response_trace["body_state"] == "unavailable"
    assert broker._process is None
    broker.acknowledge_trace(job, result=result)


def test_http_observation_rejects_unknown_or_nonfinite_fields():
    from living_world.perception.local_llm_http import HttpObservation

    timestamps = dict.fromkeys(
        (
            "http_started_at",
            "headers_received_at",
            "first_body_byte_at",
            "read_finished_at",
        )
    )
    durations = dict.fromkeys(
        ("http_seconds", "headers_seconds", "first_byte_seconds", "body_read_seconds")
    )
    for bad in (float("nan"), float("inf"), -1, True):
        with pytest.raises(ValueError):
            HttpObservation(
                None, False, None, timestamps, {**durations, "http_seconds": bad}
            )
    with pytest.raises(ValueError):
        HttpObservation(None, False, None, {**timestamps, "private": None}, durations)
    observation = HttpObservation(b"", True, 200, timestamps, durations)
    with pytest.raises(TypeError):
        observation.durations["http_seconds"] = 0


def test_job_binding_cannot_be_reused_after_fake_ack(tmp_path):
    from living_world.runtime.broker import BrokerResult

    class Injected(DecisionBroker):
        def __init__(self):
            pass

        def start(self, job_id, config, decision_input):
            pass

    broker, job = Injected(), "a" * 32
    broker.bind_trace(job, prepared(), spool_root=tmp_path / "spools")
    broker.acknowledge_trace(
        job, result=BrokerResult(job, None, "worker_failed", None, 0)
    )
    with pytest.raises(ValueError):
        broker.bind_trace(job, prepared(), spool_root=tmp_path / "spools")


def test_invalid_bound_result_is_retained(server, tmp_path):
    base, handler = server
    handler.response_body = (
        b'{"response":"{\\"spoken_text\\":\\"I watch.\\",\\"action_request\\":null}"}'
    )
    config = ProviderConfig(model="local", base_url=base, timeout_seconds=5)
    broker, job = DecisionBroker(), "a" * 32
    broker.bind_trace(job, prepared(config), spool_root=tmp_path / "spools")
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    end = time.monotonic() + 4
    while broker._process.is_alive() and time.monotonic() < end:
        time.sleep(0.01)
    path = tmp_path / "spools" / job / "result.json"
    path.write_text("corrupt")
    result = wait_result(broker, job)
    assert result.error_code == "worker_failed"
    with pytest.raises(ValueError):
        broker.acknowledge_trace(job, result=result)
    assert path.exists()


@pytest.mark.parametrize("headers_only", [True, False])
def test_headers_only_and_slow_drip_remain_bounded(server, headers_only):
    base, handler = server
    handler.response_body = b"12345678901234567890"
    handler.before_body = 0.4 if headers_only else 0
    handler.drip = 0 if headers_only else 0.025
    observations = []
    started = time.monotonic()
    with pytest.raises(LocalLLMHttpError) as exc:
        UrllibJsonHttpTransport().post_bytes(
            url=base, body=b"{}", timeout_seconds=0.12, observer=observations.append
        )
    assert exc.value.code == "timeout"
    assert time.monotonic() - started < 0.5
    last = observations[-1]
    assert not last.complete
    assert last.body == b"" if headers_only else 0 < len(last.body) < 20
    assert (last.timestamps["first_body_byte_at"] is None) == headers_only
    assert last.durations["headers_seconds"] is not None
    assert last.durations["body_read_seconds"] is not None


@pytest.mark.parametrize(
    "body,status,code",
    [
        (b"{}", 200, "invalid_response"),
        (b"\xff", 200, "invalid_response"),
        (b"", 200, "invalid_response"),
        (b"private error", 503, "http_error"),
    ],
)
def test_bound_spawn_retains_failed_raw_envelopes(server, tmp_path, body, status, code):
    base, handler = server
    handler.response_body, handler.status = body, status
    config = ProviderConfig(model="local", base_url=base, timeout_seconds=5)
    broker, job = DecisionBroker(), "a" * 32
    broker.bind_trace(job, prepared(config), spool_root=tmp_path / "spools")
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    result = wait_result(broker, job)
    assert result.error_code == code
    assert result.response_body == body
    assert result.response_trace["http_status"] == status
    assert result.response_trace["body_state"] == "complete"
    assert result.response_trace["durations"]["worker_seconds"] is not None
    broker.acknowledge_trace(job, result=result)


@pytest.mark.parametrize("at", [1, 2, 3, 4])
def test_observer_failures_at_later_stages_are_fatal(server, at):
    base, _ = server
    calls = 0

    def observer(_):
        nonlocal calls
        calls += 1
        if calls == at:
            raise RuntimeError("private")

    with pytest.raises(LocalLLMHttpError) as exc:
        UrllibJsonHttpTransport().post_bytes(
            url=base, body=b"{}", timeout_seconds=1, observer=observer
        )
    assert exc.value.code == "worker_failed"


def test_atomic_replace_keeps_previous_snapshot_on_failed_write(tmp_path, monkeypatch):
    from living_world.runtime.inference_spool import (
        create_trace_spool,
        publish_trace_snapshot,
        read_trace_snapshot,
    )
    from living_world.runtime.inference_trace import settle_observation

    directory = create_trace_spool(tmp_path / "spools", "a" * 32)
    p = prepared()
    o = settle_observation(
        None,
        dispatch_started_at="2026-01-01T00:00:00+00:00",
        settled_at="2026-01-01T00:00:00+00:00",
        broker_seconds=0,
    )
    publish_trace_snapshot(directory, p, o)

    def fail(_):
        raise OSError()

    monkeypatch.setattr("living_world.runtime.inference_spool.os.fsync", fail)
    with pytest.raises(ValueError):
        publish_trace_snapshot(directory, p, o)
    assert read_trace_snapshot(directory, p) == o


def test_crashed_worker_prefix_can_be_imported_and_acknowledged(server, tmp_path):
    from living_world.runtime.inference_spool import read_trace_snapshot

    base, handler = server
    handler.delay, handler.response_body = 2, b"{}"
    config = ProviderConfig(model="local", base_url=base, timeout_seconds=5)
    broker, job, p = DecisionBroker(), "a" * 32, prepared(config)
    broker.bind_trace(job, p, spool_root=tmp_path / "spools")
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    directory = tmp_path / "spools" / job
    end = time.monotonic() + 4
    while time.monotonic() < end:
        observation = read_trace_snapshot(directory, p)
        if observation is not None and observation.body == b"{":
            break
        time.sleep(0.01)
    else:
        pytest.fail("prefix was not published")
    broker._process.kill()
    broker._process.join(1)
    result = wait_result(broker, job)
    assert result.error_code == "worker_failed"
    assert result.response_body == b"{"
    assert result.response_trace["durations"]["worker_seconds"] is None
    broker.acknowledge_trace(job, result=result)
    assert not directory.exists()


def test_ack_does_not_delete_changed_valid_snapshot(server, tmp_path):
    from living_world.archives.model import plain
    from living_world.runtime.inference_spool import publish_trace_snapshot
    from living_world.runtime.inference_trace import InferenceObservation

    base, handler = server
    handler.response_body = (
        b'{"response":"{\\"spoken_text\\":\\"I watch.\\",\\"action_request\\":null}"}'
    )
    config = ProviderConfig(model="local", base_url=base, timeout_seconds=5)
    broker, job, p = DecisionBroker(), "a" * 32, prepared(config)
    broker.bind_trace(job, p, spool_root=tmp_path / "spools")
    broker.start(
        job,
        config,
        DecisionInput(
            "private", "Erik", NPCContext("Erik", (), (), (), ()), (), (), "a" * 64
        ),
    )
    result = wait_result(broker, job)
    assert result.decision is not None
    directory = tmp_path / "spools" / job
    trace = plain(result.response_trace)
    trace["timestamps"]["dispatch_started_at"] = None
    trace["timestamps"]["settled_at"] = None
    trace["durations"]["broker_seconds"] = None
    trace["http_status"] = 201
    publish_trace_snapshot(
        directory, p, InferenceObservation(trace, result.response_body)
    )
    with pytest.raises(ValueError):
        broker.acknowledge_trace(job, result=result)
    assert directory.exists()


@pytest.mark.parametrize("inherited_subclass", [False, True])
def test_plain_broker_cannot_ack_before_start_with_supplied_result(
    tmp_path, inherited_subclass
):
    from living_world.runtime.broker import BrokerResult

    class Inherited(DecisionBroker):
        pass

    broker = Inherited() if inherited_subclass else DecisionBroker()
    job = "a" * 32
    broker.bind_trace(job, prepared(), spool_root=tmp_path / "spools")
    with pytest.raises(ValueError, match="Trace is not validated and settled"):
        broker.acknowledge_trace(
            job, result=BrokerResult(job, None, "worker_failed", None, 0)
        )
    assert (tmp_path / "spools" / job).exists()


@pytest.mark.parametrize("root_kind", ["existing", "new_root", "new_ancestors"])
def test_create_spool_syncs_all_new_directory_parent_entries(
    tmp_path, monkeypatch, root_kind
):
    import os

    from living_world.runtime.inference_spool import create_trace_spool

    root = (
        tmp_path / "outer" / "spools"
        if root_kind == "new_ancestors"
        else tmp_path / "spools"
    )
    if root_kind == "existing":
        root.mkdir()
        expected_parents = [root]
        expected_children = [root / ("a" * 32)]
    elif root_kind == "new_root":
        expected_parents = [tmp_path, root]
        expected_children = [root, root / ("a" * 32)]
    else:
        expected_parents = [tmp_path, tmp_path / "outer", root]
        expected_children = [tmp_path / "outer", root, root / ("a" * 32)]
    synced = []
    original_fsync = os.fsync

    def recording_fsync(fd):
        info = os.fstat(fd)
        matching = [
            path
            for path in expected_parents
            if path.exists()
            and (path.stat().st_dev, path.stat().st_ino) == (info.st_dev, info.st_ino)
        ]
        assert len(matching) == 1
        index = len(synced)
        assert matching[0] == expected_parents[index]
        assert expected_children[index].is_dir()  # mkdir before its parent's sync
        if index + 1 < len(expected_children):
            assert not expected_children[index + 1].exists()  # sync before next mkdir
        synced.append(matching[0])
        original_fsync(fd)

    monkeypatch.setattr(
        "living_world.runtime.inference_spool.os.fsync", recording_fsync
    )
    directory = create_trace_spool(root, "a" * 32)
    assert synced == expected_parents
    assert directory.is_dir()


@pytest.mark.parametrize("failure_at", [0, 1, 2])
def test_spool_creation_fsync_failure_is_fatal_and_preserves_owned_paths(
    tmp_path, monkeypatch, failure_at
):
    import os

    broker, job = DecisionBroker(), "a" * 32
    root = tmp_path / "outer" / "spools"
    original_fsync = os.fsync
    calls = 0

    def fail_fsync(fd):
        nonlocal calls
        if calls == failure_at:
            raise OSError("private filesystem failure")
        calls += 1
        original_fsync(fd)

    monkeypatch.setattr("living_world.runtime.inference_spool.os.fsync", fail_fsync)
    with pytest.raises(ValueError, match="^Inference capture failed.$"):
        broker.bind_trace(job, prepared(), spool_root=root)
    created = [tmp_path / "outer", root, root / job]
    assert all(path.is_dir() for path in created[: failure_at + 1])
    assert all(not path.exists() for path in created[failure_at + 1 :])
    assert job not in broker._traces
    assert broker._process is None
