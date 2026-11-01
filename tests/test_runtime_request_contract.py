"""Canonical configuration, public flags and sealed selected-provider replay."""

from dataclasses import replace

import pytest

from living_world.archives import ArchiveFormatError, AttemptConfig
from living_world.cli import build_parser
from living_world.runtime.broker import (
    ProviderConfig,
    client_for,
    provider_config,
    provider_document,
)
from living_world.runtime.ollama_driver import effective_config_fingerprint

NEW = "founders_empty_arguments_v1"


def config(selector=NEW, *, mode="ollama", scenario="canonical_founders_v1"):
    return AttemptConfig(
        mode,
        scenario,
        7,
        "test",
        {"provider": {"model": "tiny", "request_contract": selector}},
    )


def test_canonical_provider_and_factory_selection():
    legacy = ProviderConfig("tiny")
    assert legacy.request_contract == "legacy_v1"
    assert "request_contract" not in provider_document(legacy)
    selected = ProviderConfig("tiny", request_contract=NEW)
    assert provider_document(selected)["request_contract"] == NEW
    assert "<argument name>" not in client_for(selected).SYSTEM_INSTRUCTIONS
    assert provider_config(config()).request_contract == NEW
    assert effective_config_fingerprint(config()) != effective_config_fingerprint(
        AttemptConfig(
            "ollama",
            "canonical_founders_v1",
            7,
            "test",
            {"provider": {"model": "tiny"}},
        )
    )


@pytest.mark.parametrize("value", ["legacy_v1", "unknown", None, True, False, 1])
def test_raw_noncanonical_selector_rejected(value):
    with pytest.raises(ArchiveFormatError):
        config(value)


@pytest.mark.parametrize(
    "mode,scenario",
    [
        ("recorded", "canonical_founders_v1"),
        ("journal_replay", "canonical_founders_v1"),
        ("ollama", "other"),
    ],
)
def test_new_selector_requires_live_founders(mode, scenario):
    with pytest.raises(ArchiveFormatError):
        config(mode=mode, scenario=scenario)


@pytest.mark.parametrize("value", ["unknown", None, True, 1])
def test_direct_provider_rejects_invalid_selector(value):
    with pytest.raises((ValueError, TypeError)):
        ProviderConfig("tiny", request_contract=value)


@pytest.mark.parametrize("command", ["run", "serve"])
@pytest.mark.parametrize("selector", [None, "legacy_v1", NEW])
def test_fresh_cli_selector_normalization(tmp_path, monkeypatch, command, selector):
    from living_world.archives import RunCatalog
    from living_world.runtime import RuntimeService
    from living_world.runtime.entrypoints import (
        prepare_archived_launch,
        validate_archived_options,
    )

    parser = build_parser()
    flags = [] if selector is None else ["--request-contract", selector]
    a = parser.parse_args(
        [
            command,
            "--preset",
            "founders",
            "--driver",
            "ollama",
            "--model",
            "tiny",
            *flags,
        ]
    )
    validate_archived_options(a, parser)
    seen = []

    def capture(self, value, inputs, *, paused):
        seen.append(value)
        return "captured"

    monkeypatch.setattr(RuntimeService, "start", capture)
    launch = prepare_archived_launch(
        a, catalog=RunCatalog(tmp_path / "runs"), on_reserved=lambda ref: None
    )
    assert launch.launch(paused=True) == "captured"
    provider = seen[0].settings["provider"]
    assert provider.get("request_contract") == (NEW if selector == NEW else None)


@pytest.mark.parametrize(
    "flags",
    [
        ["run", "--founders", "success"],
        ["run", "--replay-attempt", "source"],
        ["inspect", "--attempt", "source"],
        ["analyze"],
    ],
)
@pytest.mark.parametrize("selector", ["legacy_v1", NEW])
def test_selector_is_never_ignored(tmp_path, flags, selector):
    from living_world.cli import main

    with pytest.raises(SystemExit) as caught:
        main(
            [
                *flags,
                "--request-contract",
                selector,
                "--archive-root",
                str(tmp_path / "runs"),
            ]
        )
    assert caught.value.code == 2
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("ollama", "f16d2e4140777e11e88a27d6ee5ba6cd224b6adfe4a072576a19d4a28fa22957"),
        (
            "llama_cpp",
            "f2237d6f0bbd2644c73e62462b52b1b792aaccff637f813cfca39ad40c4abf0d",
        ),
    ],
)
def test_baseline_effective_provider_fingerprints(kind, expected):
    p = ProviderConfig(
        model="tiny",
        seed=7,
        model_digest="b" * 64,
        **(
            {
                "kind": kind,
                "model_file": "/models/tiny.gguf",
                "base_url": "http://127.0.0.1:8080",
            }
            if kind == "llama_cpp"
            else {}
        ),
    )
    document = provider_document(p)
    assert "request_contract" not in document
    archived = AttemptConfig(
        "ollama", "canonical_founders_v1", 7, "test", {"provider": document}
    )
    assert effective_config_fingerprint(archived) == expected
    selected = replace(
        archived, settings={"provider": {**document, "request_contract": NEW}}
    )
    assert effective_config_fingerprint(selected) != expected


@pytest.mark.parametrize("source_selector", [None, NEW])
def test_resume_inherits_and_fork_changes_selector_without_allocation(
    tmp_path, source_selector
):
    from test_runtime_llama_cpp import action_response, launch_llama, llama_server

    from living_world.runtime.entrypoints import RuntimeCLIError, _requested

    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    extra = () if source_selector is None else ("--request-contract", source_selector)
    with llama_server(model, response=action_response) as (base, _, _):
        catalog, refs, launch = launch_llama(tmp_path, base, model, extra=extra)
        try:
            launch.launch(paused=True)
        finally:
            launch.service.shutdown()
    source = refs[0].attempt_id
    parser = build_parser()

    def requested(mode, selector=None):
        extra = [] if selector is None else ["--request-contract", selector]
        return _requested(
            parser.parse_args(["run", "--" + mode + "-attempt", source, *extra]),
            catalog,
        )

    with catalog.open_attempt(source) as archive:
        original = archive.config
    same = source_selector or "legacy_v1"
    changed = "legacy_v1" if source_selector else NEW
    assert requested("resume") == original
    assert requested("resume", same) == original
    with pytest.raises(RuntimeCLIError) as caught:
        requested("resume", changed)
    assert caught.value.reason == "invalid_configuration"
    fork = requested("fork", changed)
    assert provider_config(fork).request_contract == changed
    assert effective_config_fingerprint(fork) != effective_config_fingerprint(original)
    assert len(catalog.attempts()) == 1


def test_selected_service_cold_restart_and_source_selected_offline_replay(
    tmp_path, monkeypatch
):
    import hashlib

    from test_runtime_llama_cpp import (
        action_response,
        launch_llama,
        llama_server,
        step_service,
    )
    from test_runtime_service import wait_for

    from living_world.perception.local_llm_http import UrllibJsonHttpTransport
    from living_world.runtime import RuntimeService, RuntimeState
    from living_world.runtime.broker import encoded_body

    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    with llama_server(model, response=action_response) as (base, calls, bodies):
        catalog, refs, launch = launch_llama(
            tmp_path, base, model, extra=("--request-contract", NEW)
        )
        try:
            c = launch.launch(paused=True)
            step_service(launch.service, c, "one")
        finally:
            launch.service.shutdown()
        with catalog.open_attempt(refs[0].attempt_id) as archive:
            point = archive.checkpoint()
            assert provider_config(archive.config).request_contract == NEW
            requests = [e for e in archive.entries() if e.kind == "request_started"]
            assert requests
            for entry, payload in zip(requests, bodies, strict=True):
                trace = entry.payload["request_trace"]
                blob = archive.inference_blobs((trace["body_digest"],))[0].body
                assert blob == encoded_body(payload).encode("ascii")
                assert hashlib.sha256(blob).hexdigest() == trace["body_digest"]
                assert payload["response_format"]["schema"]["properties"][
                    "action_request"
                ]["properties"]["arguments"] == {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                }
                for hidden in (
                    str(model),
                    "model_file",
                    "model_digest",
                    "entity_private",
                    "WorldState",
                ):
                    assert hidden not in blob.decode()
        resumed = RuntimeService(catalog)
        try:
            c = resumed.resume(refs[0].attempt_id, paused=True)
            child = c.status().attempt
            with catalog.open_attempt(child.attempt_id) as archive:
                assert archive.checkpoint(0).snapshot == point.snapshot
                assert provider_config(archive.config).request_contract == NEW
            step_service(resumed, c, "two")
        finally:
            resumed.shutdown()
        with catalog.open_attempt(child.attempt_id) as archive:
            final = archive.checkpoint()
        before = {
            p: (p.read_bytes(), p.stat().st_mtime_ns)
            for ref in (refs[0], child)
            for p in ref.directory.rglob("*")
            if p.is_file()
        }
        posts = len(calls)
    model.unlink()

    def forbidden(*args, **kwargs):
        raise AssertionError("offline replay touched unavailable provider")

    monkeypatch.setattr(UrllibJsonHttpTransport, "get_json", forbidden)
    monkeypatch.setattr(UrllibJsonHttpTransport, "post_json", forbidden)
    current_source = child.attempt_id
    for generation in range(2):
        replay = RuntimeService(catalog)
        try:
            c = (
                replay.replay(current_source, paused=False)
                if generation == 0
                else replay.resume(current_source, revision=0, paused=False)
            )
            wait_for(c, lambda s: s.state is RuntimeState.COMPLETED, timeout=8)
            current_source = c.status().attempt.attempt_id
            with catalog.open_attempt(current_source) as archive:
                actual = archive.checkpoint()
                assert actual.snapshot == final.snapshot
                assert actual.driver_cursor == final.driver_cursor
                assert actual.feedback_cursor == final.feedback_cursor
                assert not any(e.kind == "request_started" for e in archive.entries())
                assert any(e.kind == "response_reused" for e in archive.entries())
        finally:
            replay.shutdown()
    assert len(calls) == posts
    assert {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for ref in (refs[0], child)
        for p in ref.directory.rglob("*")
        if p.is_file()
    } == before


@pytest.mark.parametrize("source_selector", [None, NEW])
@pytest.mark.parametrize("change", [False, True])
def test_validated_cold_reuse_respects_selector_and_prepares_correct_payload(
    tmp_path, source_selector, change
):
    from test_runtime_llama_cpp import (
        action_response,
        llama_config,
        llama_server,
        wait_preparation,
    )
    from test_runtime_ollama_driver import initialized, live_archive

    from living_world.archives import AttemptLease
    from living_world.runtime.broker import DecisionBroker
    from living_world.runtime.ollama_driver import OllamaTickDriver

    model = tmp_path / "tiny.gguf"
    model.write_bytes(b"GGUFfixture")
    with llama_server(model, response=action_response) as (base, _, bodies):
        kwargs = (
            {} if source_selector is None else {"request_contract": source_selector}
        )
        provider = dict(llama_config(model, base, **kwargs).settings["provider"])
        catalog, lease, source, live = live_archive(
            tmp_path / "runs", provider=provider
        )
        staged = None
        try:
            driver, point = initialized(source, live, DecisionBroker())
            staged = driver.prepare(live.restore(point.snapshot), point, source)
            assert wait_preparation(staged) == "ready"
            staged.close()
            posts = len(bodies)
            assert posts == 2
            values = dict(provider)
            if change:
                if source_selector:
                    values.pop("request_contract")
                else:
                    values["request_contract"] = NEW
            requested = replace(
                source.config, settings={**source.config.settings, "provider": values}
            )
            child_ref = catalog.fork(source.ref.attempt_id, 0, config=requested)
            with (
                AttemptLease(child_ref),
                catalog.open_attempt(child_ref.attempt_id, read_only=False) as child,
            ):
                cold = OllamaTickDriver(
                    provider_config(requested), driver.feedback, DecisionBroker()
                )
                staged = cold.prepare(
                    live.restore(point.snapshot), child.checkpoint(), child
                )
                assert wait_preparation(staged) == "ready"
                entries = child.entries()
                assert sum(e.kind == "response_reused" for e in entries) == (
                    0 if change else 2
                )
                assert len(bodies) == posts + (2 if change else 0)
                if change:
                    new_contract = values.get("request_contract") == NEW
                    for body in bodies[posts:]:
                        arguments = body["response_format"]["schema"]["properties"][
                            "action_request"
                        ]["properties"]["arguments"]
                        assert (
                            arguments["additionalProperties"] is False
                        ) == new_contract
                    old_requests = [
                        e for e in source.entries() if e.kind == "request_started"
                    ]
                    new_requests = [e for e in entries if e.kind == "request_started"]
                    assert (
                        old_requests[0].payload["input_fingerprint"]
                        != new_requests[0].payload["input_fingerprint"]
                    )
                    assert (
                        old_requests[0].payload["config_fingerprint"]
                        != new_requests[0].payload["config_fingerprint"]
                    )
                staged.close()
        finally:
            if staged is not None:
                staged.close()
            source.close()
            lease.release()


@pytest.mark.parametrize(
    "arguments,accepted", [({}, True), ({"target": "Plant the first crop"}, False)]
)
def test_untrusted_arguments_reach_ordinary_work_gateway_intact(arguments, accepted):
    import json

    from test_work_action_gateway import _creation, _engine, _handler

    from living_world.cognition import NPCActionResolver
    from living_world.cognition.local_llm_cognition_format import (
        parse_decision_response,
    )

    engine, settlement, actor = _engine()
    handler = _handler(
        engine, settlement, actor, creation_offers=(_creation(settlement),)
    )
    decision = parse_decision_response(
        json.dumps(
            {
                "spoken_text": None,
                "action_request": {
                    "action_key": "produce_food",
                    "target_label": "Plant the first crop",
                    "rationale": "We need food.",
                    "arguments": arguments,
                },
            }
        ),
        handler.action_options,
    )
    assert dict(decision.action_request.arguments) == arguments
    result = NPCActionResolver(handler.action_options, (handler,)).resolve(
        actor_id=actor, request=decision.action_request
    )
    assert result.accepted is accepted
    assert bool(engine.state.work_states) is accepted


@pytest.mark.parametrize("kind", ["ollama", "llama_cpp"])
@pytest.mark.parametrize("arguments", [{}, {"target": "Plant the first crop"}])
def test_spawned_selected_broker_keeps_exact_prepared_body_and_untrusted_arguments(
    tmp_path, kind, arguments
):
    import json
    import multiprocessing
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from test_runtime_llama_cpp import poll_broker
    from test_work_action_gateway import _creation, _engine, _handler

    from living_world.cognition import NPCActionResolver
    from living_world.cognition.npc_context import NPCContext
    from living_world.runtime.broker import DecisionBroker
    from living_world.runtime.feedback import DecisionInput
    from living_world.runtime.inference_trace import prepare_inference

    bodies = []
    response = json.dumps(
        {
            "spoken_text": None,
            "action_request": {
                "action_key": "produce_food",
                "target_label": "Plant the first crop",
                "rationale": "We need food.",
                "arguments": arguments,
            },
        }
    )

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            bodies.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.end_headers()
            payload = (
                {"response": response}
                if kind == "ollama"
                else {"choices": [{"message": {"content": response}}]}
            )
            self.wfile.write(json.dumps(payload).encode())

        def log_message(self, *args):
            pass

    before = {p.pid for p in multiprocessing.active_children()}
    engine, settlement, actor = _engine()
    handler = _handler(
        engine, settlement, actor, creation_offers=(_creation(settlement),)
    )
    context = NPCContext("Mara", (), (), (), ())
    item = DecisionInput(
        actor, "founder", context, handler.action_options, (handler,), "a" * 64
    )
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        provider = ProviderConfig(
            "tiny",
            kind=kind,
            model_file=str(tmp_path / "tiny.gguf") if kind == "llama_cpp" else None,
            base_url=f"http://127.0.0.1:{server.server_port}",
            timeout_seconds=3,
            request_contract=NEW,
        )
        prepared = prepare_inference(provider, context, handler.action_options)
        broker = DecisionBroker()
        try:
            broker.bind_trace("1" * 32, prepared, spool_root=tmp_path / "spool")
            broker.start("1" * 32, provider, item)
            result = poll_broker(broker, "1" * 32)
            assert result.error_code is None
            assert bodies == [prepared.body]
            assert json.loads(result.response_body) == (
                {"response": response}
                if kind == "ollama"
                else {"choices": [{"message": {"content": response}}]}
            )
            assert dict(result.decision.action_request.arguments) == arguments
            resolved = NPCActionResolver(handler.action_options, (handler,)).resolve(
                actor_id=actor, request=result.decision.action_request
            )
            assert resolved.accepted is (not arguments)
            assert bool(engine.state.work_states) is (not arguments)
            for private in (
                actor,
                settlement,
                str(tmp_path),
                "model_file",
                "model_digest",
            ):
                assert private not in prepared.body.decode()
        finally:
            broker.close()
            server.shutdown()
            thread.join(2)
    assert {p.pid for p in multiprocessing.active_children()} == before


@pytest.mark.parametrize("command", ["run", "serve"])
def test_public_help_exposes_contract_choices(command, capsys):
    from living_world.cli import main

    with pytest.raises(SystemExit) as caught:
        main([command, "--help"])
    assert caught.value.code == 0
    help_text = capsys.readouterr().out
    assert "--request-contract" in help_text
    assert "legacy_v1" in help_text and NEW in help_text
