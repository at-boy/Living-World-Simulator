"""Shared llama runtime identity, transport and public configuration regressions."""

from dataclasses import asdict
from pathlib import Path

import pytest

from living_world.archives import AttemptConfig
from living_world.runtime.broker import ProviderConfig, client_for


def test_llama_provider_dispatch_and_archive_grammar(tmp_path: Path) -> None:
    config = ProviderConfig(
        model="tiny",
        kind="llama_cpp",
        model_file=str(tmp_path / "tiny.gguf"),
        base_url="http://127.0.0.1:8080",
        seed=7,
        model_digest="a" * 64,
    )
    assert client_for(config).provider_name == "llama.cpp"
    archived = AttemptConfig("ollama", "test", 7, "rev", {"provider": asdict(config)})
    assert archived.mode == "ollama"


def test_llama_payload_budgets() -> None:
    from living_world.cognition.llama_cpp_cognition_client import (
        LlamaCppCognitionClient,
    )
    from living_world.cognition.npc_context import NPCContext

    client = LlamaCppCognitionClient(
        model="tiny", max_output_tokens=19, temperature=0.2, seed=7
    )
    payload = client.build_payload(NPCContext("Erik", (), (), (), ()), ())
    assert payload["max_tokens"] == 19
    assert payload["temperature"] == 0.2
    assert payload["seed"] == 7
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}


import hashlib
import json
import multiprocessing
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from living_world.runtime.broker import provider_config, provider_document
from living_world.runtime.preflight import ProviderPreflightError, preflight_provider


@contextmanager
def llama_server(
    path,
    *,
    alias="tiny",
    advertised=None,
    magic=None,
    slow=False,
    mutate=False,
    response=None,
):
    calls = []
    bodies = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.path)
            if slow:
                time.sleep(2)
            if self.path == "/v1/models":
                body = {"data": [{"id": "tiny"}]}
            else:
                assert self.path == "/props"
                body = {"model_alias": alias, "model_path": str(advertised or path)}
                if mutate and calls.count("/props") == 2:
                    path.write_bytes(b"GGUFchanged")
            self.send_response(200)
            self.end_headers()
            try:
                self.wfile.write(json.dumps(body).encode())
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            calls.append(self.path)
            assert self.path == "/v1/chat/completions"
            bodies.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            if slow:
                time.sleep(2)
            self.send_response(200)
            self.end_headers()
            body = (
                response(bodies[-1])
                if callable(response)
                else (
                    response
                    if response is not None
                    else {
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {
                                            "spoken_text": "I will watch.",
                                            "action_request": None,
                                        }
                                    )
                                }
                            }
                        ]
                    }
                )
            )
            try:
                self.wfile.write(json.dumps(body).encode())
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", calls, bodies
        finally:
            server.shutdown()
            thread.join(2)


def llama_config(path, base, **options):
    return AttemptConfig(
        "ollama",
        "canonical_founders_v1",
        42,
        "test",
        {
            "driver_format": 1,
            "provider": {
                "kind": "llama_cpp",
                "model": "tiny",
                "model_file": str(path),
                "base_url": base,
                "timeout_seconds": 3,
                **options,
            },
            "limits": {"max_ticks": 3, "max_requests": 40},
        },
    )


@pytest.mark.parametrize(
    "options",
    [
        {"timeout_seconds": float("inf")},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": True},
        {"max_output_tokens": True},
        {"max_output_tokens": 0},
        {"temperature": float("nan")},
        {"temperature": -1},
        {"temperature": True},
        {"seed": True},
    ],
)
def test_llama_invalid_client_values(options):
    from living_world.cognition.llama_cpp_cognition_client import (
        LlamaCppCognitionClient,
    )

    with pytest.raises((ValueError, TypeError)):
        LlamaCppCognitionClient(model="tiny", **options)


@pytest.mark.parametrize(
    "options",
    [
        {"kind": "bad"},
        {"kind": "llama_cpp"},
        {"model_file": "/tmp/a.gguf"},
        {"kind": "llama_cpp", "model_file": "relative.gguf"},
        {"kind": "llama_cpp", "model_file": "/tmp/a\x00.gguf"},
        {"kind": "llama_cpp", "model_file": "/" + "x" * 4096},
    ],
)
def test_invalid_provider_metadata(options):
    with pytest.raises((ValueError, TypeError)):
        ProviderConfig("tiny", **options)


def test_local_identity_preserves_path_spelling_and_legacy_document(tmp_path):
    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    (tmp_path / "sub").mkdir()
    spelling = tmp_path / "sub" / ".." / "tiny.gguf"
    with llama_server(model) as (base, calls, bodies):
        requested = llama_config(spelling, base)
        result = preflight_provider(requested)
    provider = provider_config(result)
    assert provider.model_file == str(spelling)
    assert provider.model == "tiny"
    assert provider.model_digest == hashlib.sha256(b"GGUFfixture").hexdigest()
    assert calls == ["/v1/models", "/props", "/props"] and not bodies
    old = ProviderConfig("tiny")
    assert provider_document(old) == {
        "model": "tiny",
        "base_url": "http://127.0.0.1:11434",
        "timeout_seconds": 30.0,
        "max_output_tokens": 512,
        "max_response_bytes": 1048576,
        "temperature": 0.0,
        "seed": None,
        "model_digest": None,
    }


@pytest.mark.parametrize(
    "failure,code",
    [
        ("alias", "invalid_preflight"),
        ("path", "invalid_preflight"),
        ("magic", "invalid_preflight"),
        ("pin", "model_digest_mismatch"),
        ("missing", "model_missing"),
        ("mutation", "invalid_preflight"),
        ("directory", "invalid_preflight"),
    ],
)
def test_preflight_identity_failures_reap(tmp_path, failure, code):
    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"bad!" if failure == "magic" else b"GGUFfixture")
    other = tmp_path / "other.gguf"
    other.write_bytes(b"GGUFother")
    if failure == "missing":
        model.unlink()
    if failure == "directory":
        model.unlink()
        model.mkdir()
    options = {"model_digest": "b" * 64} if failure == "pin" else {}
    before = {p.pid for p in multiprocessing.active_children()}
    with llama_server(
        model,
        alias="wrong" if failure == "alias" else "tiny",
        advertised=other if failure == "path" else None,
        mutate=failure == "mutation",
    ) as (base, _, _):
        with pytest.raises(ProviderPreflightError) as caught:
            preflight_provider(llama_config(model, base, **options))
        assert caught.value.code == code and str(caught.value) == code
    assert {p.pid for p in multiprocessing.active_children()} == before


@pytest.mark.parametrize("cancel", [False, True])
def test_llama_preflight_deadline_and_cancel(tmp_path, cancel):
    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    event = threading.Event()
    before = {p.pid for p in multiprocessing.active_children()}
    with llama_server(model, slow=True) as (base, _, _):
        timer = threading.Timer(0.2, event.set)
        if cancel:
            timer.start()
        started = time.monotonic()
        try:
            with pytest.raises(ProviderPreflightError) as caught:
                preflight_provider(
                    llama_config(model, base, timeout_seconds=10 if cancel else 0.3),
                    cancel_event=event,
                )
            assert caught.value.code == ("cancelled" if cancel else "timeout")
            assert time.monotonic() - started < 1
        finally:
            if cancel:
                timer.join()
    assert {p.pid for p in multiprocessing.active_children()} == before


@pytest.mark.parametrize(
    "frame",
    [
        {"model": "tiny:latest", "digest": "a" * 64},
        {"model": "tiny", "digest": "A" * 64},
        {"model": "tiny", "digest": "a" * 64, "model_file": "/private"},
        {"error": "private failure"},
    ],
)
def test_llama_parent_rejects_frames(tmp_path, frame):
    from living_world.runtime.preflight import _read_result

    result = tmp_path / "result.json"
    result.write_text(json.dumps(frame))
    with pytest.raises(ProviderPreflightError):
        _read_result(
            result,
            ProviderConfig(
                "tiny",
                kind="llama_cpp",
                model_file="/tmp/model.gguf",
                base_url="http://127.0.0.1:8080",
            ),
        )


def broker_input(text="Erik"):
    from living_world.cognition.npc_context import NPCContext
    from living_world.runtime.feedback import DecisionInput

    return DecisionInput(
        "entity_private", "founder", NPCContext(text, (), (), (), ()), (), (), "a" * 64
    )


def poll_broker(broker, job):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = broker.poll(job)
        if result is not None:
            return result
        time.sleep(0.01)
    raise AssertionError("broker never completed")


@pytest.mark.parametrize(
    "behavior,code",
    [
        ("normal", None),
        ("large", "oversized_response"),
        ("unsafe", "invalid_response"),
        ("bodylimit", "invalid_response"),
        ("cancel", "cancelled"),
        ("timeout", "timeout"),
    ],
)
def test_spawned_llama_broker(tmp_path, behavior, code):
    from living_world.runtime.broker import DecisionBroker

    response = None
    if behavior in ("large", "unsafe"):
        text = "x" * 2000 if behavior == "large" else "entity_123"
        response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"spoken_text": text, "action_request": None}
                        )
                    }
                }
            ]
        }
    before = {p.pid for p in multiprocessing.active_children()}
    with llama_server(
        tmp_path / "tiny.gguf", response=response, slow=behavior == "timeout"
    ) as (base, calls, bodies):
        broker = DecisionBroker()
        config = provider_config(
            llama_config(
                tmp_path / "tiny.gguf",
                base,
                max_response_bytes=1000 if behavior == "large" else 1048576,
                timeout_seconds=0.4 if behavior == "timeout" else 3,
            )
        )
        broker.start(
            "one",
            config,
            broker_input("E" * 16000 if behavior == "bodylimit" else "Erik"),
        )
        if behavior == "cancel":
            broker.close()
        result = poll_broker(broker, "one")
        broker.close()
        assert result.error_code == code
        if code is None:
            assert result.decision.spoken_text == "I will watch."
            assert result.response_digest
            raw = json.dumps(bodies)
            for private in (
                "entity_private",
                str(tmp_path),
                "model_file",
                "model_digest",
            ):
                assert private not in raw
        if behavior == "bodylimit":
            assert calls == []
    assert {p.pid for p in multiprocessing.active_children()} == before


def action_response(payload):
    request = json.loads(payload["messages"][1]["content"])
    options = request["actions"]
    choice = next(
        (a for a in options if a["key"] == "build_shelter"),
        options[0] if options else None,
    )
    decision = {"spoken_text": "I will watch.", "action_request": None}
    if choice:
        decision = {
            "spoken_text": None,
            "action_request": {
                "action_key": choice["key"],
                "target_label": (
                    choice["target_labels"][0] if choice["target_labels"] else None
                ),
                "rationale": "We need supplies.",
                "arguments": {},
            },
        }
    return {"choices": [{"message": {"content": json.dumps(decision)}}]}


def launch_llama(tmp_path, base, model, *, command="run", disturbance=None, extra=()):
    from living_world.archives import RunCatalog
    from living_world.cli import build_parser
    from living_world.runtime.entrypoints import (
        prepare_archived_launch,
        validate_archived_options,
    )

    parser = build_parser()
    a = parser.parse_args(
        [
            command,
            "--preset",
            "founders",
            "--driver",
            "llama.cpp",
            "--model",
            "tiny",
            "--model-file",
            str(model),
            "--base-url",
            base,
            "--archive-root",
            str(tmp_path / "runs"),
            "--max-ticks",
            "3",
            *extra,
        ]
    )
    validate_archived_options(a, parser)
    catalog = RunCatalog(tmp_path / "runs")
    refs = []
    prepared = prepare_archived_launch(
        a, catalog=catalog, on_reserved=refs.append, disturbance=disturbance
    )
    assert catalog.attempts() == ()
    return catalog, refs, prepared


def step_service(service, controller, name):
    from test_runtime_service import wait_for

    from living_world.archives import CommandEnvelope
    from living_world.runtime import RuntimeState

    tick = controller.status().tick
    envelope = CommandEnvelope(name, "step", controller.status().state_version)
    assert service.submit(envelope).result(2).status == "queued"
    wait_for(
        controller,
        lambda s: s.tick == tick + 1
        and s.state in (RuntimeState.PAUSED, RuntimeState.COMPLETED),
        timeout=8,
    )
    assert service.submit(envelope).result(2).status == "applied"


@pytest.mark.parametrize("disturbance", ["resource_loss", "work_blockage"])
def test_service_cold_restart_fork_and_offline_replay(
    tmp_path, disturbance, monkeypatch
):
    from test_runtime_service import wait_for

    from living_world.perception.local_llm_http import UrllibJsonHttpTransport
    from living_world.runtime import RuntimeService, RuntimeState
    from living_world.runtime.broker import encoded_body

    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    with llama_server(model, response=action_response) as (base, calls, bodies):
        catalog, refs, launch = launch_llama(
            tmp_path, base, model, disturbance=disturbance
        )
        c = launch.launch(paused=True)
        try:
            assert c.status().state is RuntimeState.PAUSED and c.status().tick == 0
            step_service(launch.service, c, "one")
        finally:
            launch.service.shutdown()
        with catalog.open_attempt(refs[0].attempt_id) as archive:
            point = archive.checkpoint()
            source_config = archive.config
            assert archive.command("one").status == "applied"
            assert any(e.kind == "response_validated" for e in archive.entries())
        resumed = RuntimeService(catalog)
        c = resumed.resume(refs[0].attempt_id, paused=True)
        child_ref = c.status().attempt
        try:
            with catalog.open_attempt(child_ref.attempt_id) as archive:
                assert archive.checkpoint(0).snapshot == point.snapshot
                assert archive.config == source_config
            step_service(resumed, c, "two")
        finally:
            resumed.shutdown()
        fork = RuntimeService(catalog)
        c = fork.fork(child_ref.attempt_id, config=source_config, paused=True)
        try:
            assert c.status().tick == 2
        finally:
            fork.shutdown()
        with catalog.open_attempt(child_ref.attempt_id) as archive:
            final = archive.checkpoint()
            requests = sum(e.kind == "request_started" for e in archive.entries())
            disturbances = [
                e for e in archive.entries() if e.kind == "boundary_disturbance"
            ]
            assert disturbances and disturbances[0].payload["kind"] == disturbance
        assert requests > 0
        for body in bodies:
            assert len(encoded_body(body)) <= 16000
            raw = json.dumps(body)
            assert str(model) not in raw and "model_digest" not in raw
        prior_calls = len(calls)
        model.unlink()

        def forbidden(*args, **kwargs):
            raise AssertionError("offline replay touched provider")

        monkeypatch.setattr(UrllibJsonHttpTransport, "get_json", forbidden)
        monkeypatch.setattr(UrllibJsonHttpTransport, "post_json", forbidden)
        replay = RuntimeService(catalog)
        c = replay.replay(child_ref.attempt_id, paused=False)
        try:
            wait_for(c, lambda s: s.state is RuntimeState.COMPLETED, timeout=8)
            with catalog.open_attempt(c.status().attempt.attempt_id) as archive:
                assert archive.checkpoint().snapshot == final.snapshot
                assert not any(e.kind == "request_started" for e in archive.entries())
                assert any(e.kind == "response_reused" for e in archive.entries())
        finally:
            replay.shutdown()
        assert len(calls) == prior_calls


@pytest.mark.parametrize(
    "failure,code",
    [
        ("missing", "model_missing"),
        ("alias", "invalid_preflight"),
        ("path", "invalid_preflight"),
        ("magic", "invalid_preflight"),
        ("mutation", "invalid_preflight"),
        ("directory", "invalid_preflight"),
        ("pin", "model_digest_mismatch"),
    ],
)
def test_allocated_setup_failure_is_retained(tmp_path, failure, code):
    from living_world.runtime import RuntimeStartupError

    model = tmp_path / "tiny.gguf"
    if failure != "missing":
        model.write_bytes(b"bad!" if failure == "magic" else b"GGUFfixture")
    other = tmp_path / "other.gguf"
    other.write_bytes(b"GGUFfixture")
    if failure == "directory":
        model.unlink()
        model.mkdir()
    with llama_server(
        model,
        alias="bad" if failure == "alias" else "tiny",
        advertised=other if failure == "path" else None,
        mutate=failure == "mutation",
    ) as (
        base,
        _,
        _,
    ):
        catalog, refs, launch = launch_llama(tmp_path, base, model)
        # A pin failure is tested through the direct normal service producer.
        if failure == "pin":
            from living_world.archives import AttemptLease, retain_inputs
            from living_world.founders import materialize_founders_assets
            from living_world.runtime import RuntimeService

            config = llama_config(model, base, model_digest="b" * 64)
            ref = catalog.reserve_setup(config)
            refs.append(ref)
            with materialize_founders_assets() as assets, AttemptLease(ref):
                inputs = retain_inputs(ref, assets.scenario, tape_path=None)
            service = RuntimeService(catalog)
            try:
                with pytest.raises(RuntimeStartupError) as caught:
                    service.start(config, inputs, paused=True)
            finally:
                service.shutdown()
        else:
            try:
                with pytest.raises(RuntimeStartupError) as caught:
                    launch.launch(paused=True)
            finally:
                launch.service.shutdown()
        assert caught.value.code == code
        assert len(catalog.attempts()) == 1
        assert catalog.attempts()[0].failure_code == code
        assert (refs[0].directory / "setup.json").is_file()


@pytest.mark.parametrize(
    "flags",
    [
        ["--preset", "founders", "--driver", "llama.cpp", "--model", "tiny"],
        [
            "--preset",
            "founders",
            "--driver",
            "ollama",
            "--model",
            "tiny",
            "--model-file",
            "/tmp/tiny.gguf",
        ],
        ["--founders", "success", "--model-file", "/tmp/tiny.gguf"],
    ],
)
def test_public_rejects_bad_options_before_allocation(tmp_path, flags):
    from living_world.cli import main

    root = tmp_path / "runs"
    with pytest.raises(SystemExit) as caught:
        main(["run", *flags, "--archive-root", str(root)])
    assert caught.value.code == 2
    assert not root.exists()


def test_cli_resume_fork_provider_and_file_bindings(tmp_path):
    from living_world.cli import build_parser
    from living_world.runtime.entrypoints import RuntimeCLIError, _requested
    from living_world.runtime.ollama_driver import effective_config_fingerprint

    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    with llama_server(model) as (base, _, _):
        catalog, refs, launch = launch_llama(tmp_path, base, model)
        launch.launch(paused=True)
        launch.service.shutdown()
    parser = build_parser()
    source = refs[0].attempt_id
    with catalog.open_attempt(source) as archive:
        original = archive.config

    def requested(mode, *flags):
        return _requested(
            parser.parse_args(["run", "--" + mode + "-attempt", source, *flags]),
            catalog,
        )

    assert requested("resume") == original
    assert (
        requested(
            "resume",
            "--driver",
            "llama.cpp",
            "--model",
            "tiny",
            "--model-file",
            str(model),
        )
        == original
    )
    for flags in (
        ("--driver", "ollama", "--model", "tiny"),
        ("--model", "tiny:latest"),
        ("--model-file", str(tmp_path / "other.gguf")),
        ("--base-url", "http://127.0.0.1:8081"),
        ("--max-output-tokens", "8"),
    ):
        with pytest.raises(RuntimeCLIError):
            requested("resume", *flags)
    for flags in (
        ("--driver", "ollama"),
        (
            "--driver",
            "llama.cpp",
            "--model-file",
            str(model),
            "--model",
            "tiny",
            "--base-url",
            "https://remote.invalid",
        ),
    ):
        with pytest.raises(RuntimeCLIError):
            requested("fork", *flags)
    switched = requested("fork", "--driver", "ollama", "--model", "other")
    p = provider_config(switched)
    assert p.kind == "ollama" and p.model_file is None and p.model_digest is None
    assert p.base_url == "http://127.0.0.1:11434"
    assert (
        "kind" not in switched.settings["provider"]
        and "model_file" not in switched.settings["provider"]
    )
    changed = requested("fork", "--model-file", str(tmp_path / "other.gguf"))
    assert provider_config(changed).model_digest is None
    assert effective_config_fingerprint(changed) != effective_config_fingerprint(
        original
    )
    assert effective_config_fingerprint(switched) != effective_config_fingerprint(
        original
    )
    assert len(catalog.attempts()) == 1


@pytest.mark.parametrize("command", ["run", "serve"])
def test_fresh_cli_default_llama_url_without_allocation(tmp_path, command, monkeypatch):
    from living_world.archives import RunCatalog
    from living_world.cli import build_parser
    from living_world.runtime import RuntimeService
    from living_world.runtime.entrypoints import (
        prepare_archived_launch,
        validate_archived_options,
    )

    parser = build_parser()
    a = parser.parse_args(
        [
            command,
            "--preset",
            "founders",
            "--driver",
            "llama.cpp",
            "--model",
            "tiny",
            "--model-file",
            str(tmp_path / "tiny.gguf"),
        ]
    )
    validate_archived_options(a, parser)
    catalog = RunCatalog(tmp_path / "runs")
    configs = []

    def capture(self, config, inputs, *, paused):
        configs.append(config)
        assert paused
        return "captured"

    monkeypatch.setattr(RuntimeService, "start", capture)
    prepared = prepare_archived_launch(a, catalog=catalog, on_reserved=lambda ref: None)
    assert catalog.attempts() == ()
    assert prepared.launch(paused=True) == "captured"
    p = provider_config(configs[0])
    assert p.base_url == "http://127.0.0.1:8080" and p.kind == "llama_cpp"


def test_public_llama_http_step_resume_shutdown_and_inspection(tmp_path):
    import signal

    from test_runtime_serve import child, request, wait_until

    from living_world.archives import RunCatalog
    from living_world.runtime.entrypoints import load_archived_inspection

    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    with llama_server(model, response=action_response) as (url, _calls, bodies):
        with child(
            tmp_path,
            "--preset",
            "founders",
            "--driver",
            "llama.cpp",
            "--model",
            "tiny",
            "--model-file",
            str(model),
            "--base-url",
            url,
        ) as (process, base):
            token = (tmp_path / "token").read_text().strip()
            state = wait_until(
                lambda: request(base, token, "/runtime/status")[0]["live"]
            )
            _, nonce = request(base, token, "/runtime/status")
            assert state["tick"] == 0 and state["state"] == "paused"
            receipt, _ = request(
                base,
                token,
                "/runtime/commands",
                {
                    "command_id": "one",
                    "action": "step",
                    "expected_state_version": state["state_version"],
                },
                nonce,
            )
            assert receipt["status"] == "queued"
            wait_until(
                lambda: request(base, token, "/runtime/status")[0]["live"]["tick"] == 1
            )
            process.send_signal(signal.SIGTERM)
            out, err = process.communicate(timeout=8)
            assert process.returncode == 0 and "Traceback" not in err
            assert token not in out + err
        catalog = RunCatalog(tmp_path / "runs")
        source = catalog.attempts()[0].ref
        assert load_archived_inspection(catalog, source.attempt_id, 0).state.tick == 0
        before_posts = len(bodies)
        with child(tmp_path, "--resume-attempt", source.attempt_id) as (_, base):
            token = (tmp_path / "token").read_text().strip()
            state = wait_until(
                lambda: request(base, token, "/runtime/status")[0]["live"]
            )
            assert state["tick"] == 1 and state["state"] == "paused"
            assert len(bodies) == before_posts
        assert len(catalog.attempts()) == 2


def wait_preparation(preparation):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        status = preparation.poll()
        if status != "waiting":
            return status
        time.sleep(0.01)
    raise AssertionError("preparation never settled")


@pytest.mark.parametrize("change", [None, "file", "provider"])
def test_cold_validated_response_reuse_binds_provider_and_file(tmp_path, change):
    from dataclasses import replace

    from test_runtime_ollama_driver import initialized, live_archive

    from living_world.archives import AttemptLease
    from living_world.runtime.broker import DecisionBroker
    from living_world.runtime.ollama_driver import OllamaTickDriver

    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    with llama_server(model, response=action_response) as (base, _, bodies):
        provider = dict(llama_config(model, base).settings["provider"])
        catalog, lease, source, live = live_archive(
            tmp_path / "runs", provider=provider
        )
        try:
            driver, point = initialized(source, live, DecisionBroker())
            staged = driver.prepare(live.restore(point.snapshot), point, source)
            assert wait_preparation(staged) == "ready"
            staged.close()  # validated decisions remain durable, world uncommitted
            posts = len(bodies)
            assert posts == 2
            config = source.config
            if change:
                values = dict(provider)
                if change == "file":
                    values["model_file"] = str(tmp_path / "other.gguf")
                else:
                    values.pop("kind")
                    values.pop("model_file")
                config = replace(
                    config, settings={**config.settings, "provider": values}
                )
            child_ref = catalog.fork(source.ref.attempt_id, 0, config=config)
            with (
                AttemptLease(child_ref),
                catalog.open_attempt(child_ref.attempt_id, read_only=False) as child,
            ):
                cold = OllamaTickDriver(
                    provider_config(config), driver.feedback, DecisionBroker()
                )
                staged = cold.prepare(
                    live.restore(point.snapshot), child.checkpoint(), child
                )
                if change == "provider":
                    # Inspect normal matching before dispatch: different provider must not
                    # consume retained llama responses; cancelling preserves no new call.
                    assert staged.poll() == "waiting"
                    assert not any(e.kind == "response_reused" for e in child.entries())
                    assert any(e.kind == "request_started" for e in child.entries())
                else:
                    assert wait_preparation(staged) == "ready"
                    if change is None:
                        assert len(bodies) == posts
                        assert (
                            sum(e.kind == "response_reused" for e in child.entries())
                            == 2
                        )
                        assert not any(
                            e.kind == "request_started" for e in child.entries()
                        )
                    else:
                        assert len(bodies) == posts + 2
                        assert not any(
                            e.kind == "response_reused" for e in child.entries()
                        )
                staged.close()
        finally:
            source.close()
            lease.release()


@pytest.mark.parametrize(
    "kind,expected",
    [
        (None, "9c3a9e2bf4db4312cf0f71816ff6bb27b33a98a86a66613d794145c5b2ac210a"),
        (
            "resource_loss",
            "66cf3b6faa29a183a583d0327464137b8101881a0aecbb40ed6b534b038dcd55",
        ),
        (
            "work_blockage",
            "5664438f6e37ea3f87b306b51f4721e62a86cdf10b0e21bc5b51043f3b5591ab",
        ),
    ],
)
def test_exact_legacy_effective_hashes(kind, expected):
    from living_world.archives.model import BoundaryDisturbance
    from living_world.runtime.ollama_driver import effective_config_fingerprint

    settings = {"provider": {"model": "local"}}
    if kind is not None:
        settings["disturbance"] = kind
        settings["boundary_disturbance"] = BoundaryDisturbance(
            kind=kind, format=2 if kind == "work_blockage" else 1
        ).as_document()
    config = AttemptConfig("ollama", "canonical_founders_v1", 7, "test", settings)
    assert effective_config_fingerprint(config) == expected


def test_explicit_ollama_kind_normalizes_without_new_archive_fields(tmp_path):
    from test_runtime_preflight import requested, tags_server

    with tags_server({"models": [{"name": "tiny:latest", "digest": "a" * 64}]}) as base:
        effective = preflight_provider(requested(base, kind="ollama", model_file=None))
    assert "kind" not in effective.settings["provider"]
    assert "model_file" not in effective.settings["provider"]


def test_public_headless_llama_run(tmp_path, capsys):
    from living_world.archives import RunCatalog
    from living_world.cli import main

    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    with llama_server(model, response=action_response) as (base, _, bodies):
        assert (
            main(
                [
                    "run",
                    "--preset",
                    "founders",
                    "--driver",
                    "llama.cpp",
                    "--model",
                    "tiny",
                    "--model-file",
                    str(model),
                    "--base-url",
                    base,
                    "--max-ticks",
                    "1",
                    "--archive-root",
                    str(tmp_path / "runs"),
                ]
            )
            == 0
        )
    out, err = capsys.readouterr()
    assert "end_tick=1" in out and "attempt=" in err
    assert bodies
    catalog = RunCatalog(tmp_path / "runs")
    with catalog.open_attempt(catalog.attempts()[0].ref.attempt_id) as archive:
        assert archive.config.mode == "ollama"
        assert provider_config(archive.config).kind == "llama_cpp"
        from living_world.repositories.world_snapshot import decode_world

        assert decode_world(archive.checkpoint().snapshot).tick == 1


def test_setup_cannot_change_provider_kind_or_path(tmp_path):
    from dataclasses import replace

    from living_world.archives import ArchiveFormatError
    from living_world.archives.catalog import validate_setup_config

    model = tmp_path / "tiny.gguf"
    source = llama_config(model, "http://127.0.0.1:8080")
    effective_provider = provider_document(provider_config(source))
    effective_provider["model_digest"] = "a" * 64
    effective = replace(
        source, settings={**source.settings, "provider": effective_provider}
    )
    old_provider = dict(source.settings["provider"])
    old_provider.pop("kind")
    old_provider.pop("model_file")
    old = replace(source, settings={**source.settings, "provider": old_provider})
    with pytest.raises(ArchiveFormatError):
        validate_setup_config(old, effective)
    with pytest.raises(ArchiveFormatError):
        validate_setup_config(effective, old)
    changed = {**effective_provider, "model_file": str(tmp_path / "other.gguf")}
    with pytest.raises(ArchiveFormatError):
        validate_setup_config(
            source,
            replace(effective, settings={**effective.settings, "provider": changed}),
        )
