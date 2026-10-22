"""Installed-model identity and bounded owned preflight processes."""

import json
import multiprocessing
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

import pytest

from living_world.archives import AttemptConfig


@contextmanager
def tags_server(
    body: object, *, behavior: str = "normal", on_get: Callable[[], None] | None = None
) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            assert self.path == "/api/tags"
            if on_get is not None:
                on_get()
            try:
                if behavior == "headers":
                    for (
                        byte
                    ) in b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n":
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(0.04)
                    return
                self.send_response(500 if behavior == "error" else 200)
                self.end_headers()
                raw = json.dumps(body).encode()
                if behavior == "body":
                    for byte in raw:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(0.04)
                elif behavior == "hung":
                    time.sleep(2)
                else:
                    self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(2)


def requested(base: str, model: str = "tiny", **options: object) -> AttemptConfig:
    return AttemptConfig(
        "ollama",
        "test",
        7,
        "rev",
        {
            "provider": {
                "model": model,
                "base_url": base,
                "timeout_seconds": 2,
                **options,
            },
            "limits": {"max_requests": 4},
        },
    )


def test_preflight_resolves_defaults_and_changes_fingerprint() -> None:
    from living_world.runtime import effective_config_fingerprint, provider_config
    from living_world.runtime.preflight import preflight_provider

    results = []
    for digest in ("a", "b"):
        with tags_server(
            {
                "models": [
                    {
                        "name": "tiny:latest",
                        "model": "tiny:latest",
                        "digest": "sha256:" + digest.upper() * 64,
                        "details": {"private": "ignored"},
                    }
                ]
            }
        ) as base:
            config = requested(base)
            effective = preflight_provider(config)
            provider = provider_config(effective)
            assert provider.model == "tiny:latest"
            assert provider.model_digest == digest * 64
            assert provider.seed == 7 and provider.max_output_tokens == 512
            assert effective.scenario_key == "test" and effective.settings[
                "limits"
            ] == {"max_requests": 4}
            assert "model_digest" not in cast(
                dict[str, object], config.settings["provider"]
            )
            results.append(effective_config_fingerprint(effective))
    assert results[0] != results[1]


@pytest.mark.parametrize(
    ("model", "models", "code"),
    [
        ("tiny", [], "model_missing"),
        ("tiny:v1", [{"name": "tiny:latest", "digest": "a" * 64}], "model_missing"),
        (
            "tiny",
            [
                {"name": "tiny", "digest": "a" * 64},
                {"name": "tiny:latest", "digest": "a" * 64},
            ],
            "invalid_preflight",
        ),
        (
            "tiny",
            [
                {"name": "tiny", "digest": "a" * 64},
                {"name": "tiny", "digest": "a" * 64},
            ],
            "invalid_preflight",
        ),
        ("tiny", [{"name": "tiny", "digest": "bad"}], "invalid_preflight"),
        (
            "tiny",
            [{"name": "tiny", "model": "other", "digest": "a" * 64}],
            "invalid_preflight",
        ),
        (
            "tiny",
            [
                {"name": "tiny", "digest": "a" * 64},
                {"name": "bad name", "digest": "a" * 64},
            ],
            "invalid_preflight",
        ),
        ("tiny", [{"name": "bad\x80", "digest": "a" * 64}], "invalid_preflight"),
        ("tiny", None, "invalid_preflight"),
        ("tiny", {}, "invalid_preflight"),
    ],
)
def test_preflight_rejects_missing_ambiguous_or_malformed_models(
    model: str, models: object, code: str
) -> None:
    from living_world.runtime.preflight import (
        ProviderPreflightError,
        preflight_provider,
    )

    with tags_server({"models": models}) as base:
        with pytest.raises(ProviderPreflightError) as caught:
            preflight_provider(requested(base, model))
        assert caught.value.code == code


@pytest.mark.parametrize(
    "model", ["tiny", "tiny:v1", "namespace/tiny", "host:5000/namespace/tiny"]
)
def test_preflight_exact_namespace_and_pinned_digest(model: str) -> None:
    from living_world.runtime.preflight import (
        ProviderPreflightError,
        preflight_provider,
    )

    chosen = model if ":" in model.rsplit("/", 1)[-1] else model + ":latest"
    with tags_server({"models": [{"name": chosen, "digest": "a" * 64}]}) as base:
        effective = preflight_provider(
            requested(base, model, model_digest="sha256:" + "A" * 64)
        )
        assert (
            cast(dict[str, object], effective.settings["provider"])["model"] == chosen
        )
        with pytest.raises(ProviderPreflightError) as caught:
            preflight_provider(requested(base, model, model_digest="b" * 64))
        assert caught.value.code == "model_digest_mismatch"


@pytest.mark.parametrize("behavior", ["headers", "body", "hung"])
def test_preflight_hard_deadline_reaps_trickled_or_hung_worker(behavior: str) -> None:
    from living_world.runtime.preflight import (
        ProviderPreflightError,
        preflight_provider,
    )

    before = {p.pid for p in multiprocessing.active_children()}
    with tags_server(
        {"models": [{"name": "tiny", "digest": "a" * 64}]}, behavior=behavior
    ) as base:
        started = time.monotonic()
        with pytest.raises(ProviderPreflightError) as caught:
            preflight_provider(requested(base, timeout_seconds=0.3))
        assert caught.value.code == "timeout"
        assert time.monotonic() - started < 1.0
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_preflight_cancel_is_parent_only_and_prompt() -> None:
    from living_world.runtime.preflight import (
        ProviderPreflightError,
        preflight_provider,
    )

    before = {p.pid for p in multiprocessing.active_children()}
    event = threading.Event()
    event.set()
    with pytest.raises(ProviderPreflightError) as caught:
        preflight_provider(
            requested("http://127.0.0.1:1", timeout_seconds=60), cancel_event=event
        )
    assert caught.value.code == "cancelled"
    event.clear()
    with tags_server({}, behavior="hung") as base:
        timer = threading.Timer(0.2, event.set)
        timer.start()
        started = time.monotonic()
        try:
            with pytest.raises(ProviderPreflightError) as caught:
                preflight_provider(
                    requested(base, timeout_seconds=60), cancel_event=event
                )
            assert caught.value.code == "cancelled"
            assert time.monotonic() - started < 1
        finally:
            timer.join()
    assert {p.pid for p in multiprocessing.active_children()} == before


@pytest.mark.parametrize(
    ("body", "options", "behavior", "code"),
    [
        ({}, {}, "normal", "invalid_preflight"),
        ({"models": []}, {"max_response_bytes": 3}, "normal", "oversized_response"),
        ({"private": "never exposed"}, {}, "error", "http_error"),
    ],
)
def test_preflight_safe_transport_and_shape_errors(
    body: object, options: dict[str, object], behavior: str, code: str
) -> None:
    from living_world.runtime.preflight import (
        ProviderPreflightError,
        preflight_provider,
    )

    before = {p.pid for p in multiprocessing.active_children()}
    with tags_server(body, behavior=behavior) as base:
        with pytest.raises(ProviderPreflightError) as caught:
            preflight_provider(requested(base, **options))
        assert caught.value.code == code and str(caught.value) == code
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_preflight_keyboard_interrupt_reaps_owned_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from living_world.runtime import preflight

    before = {p.pid for p in multiprocessing.active_children()}
    from types import SimpleNamespace

    calls = 0

    def interrupted_clock() -> float:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return time.monotonic()

    monkeypatch.setattr(preflight, "time", SimpleNamespace(monotonic=interrupted_clock))
    with tags_server({}, behavior="hung") as base, pytest.raises(KeyboardInterrupt):
        preflight.preflight_provider(requested(base))
    assert {p.pid for p in multiprocessing.active_children()} == before


@pytest.mark.parametrize(
    "frame",
    [
        b"x" * 8193,
        b"[]",
        b'{"model":"tiny","digest":"bad"}',
        b'{"error":"raw private"}',
        b'{"model":"tiny","digest":"' + b"A" * 64 + b'"}',
    ],
)
def test_parent_rejects_invalid_bounded_result_frame(
    tmp_path: Path, frame: bytes
) -> None:
    from living_world.runtime.broker import ProviderConfig
    from living_world.runtime.preflight import ProviderPreflightError, _read_result

    path = tmp_path / "result.json"
    path.write_bytes(frame)
    with pytest.raises(ProviderPreflightError) as caught:
        _read_result(path, ProviderConfig("tiny"))
    assert caught.value.code == "worker_failed"


def test_setup_inputs_exist_before_first_provider_get(tmp_path: Path) -> None:
    from living_world.archives.assets import load_retained_inputs, retain_inputs
    from living_world.archives.catalog import RunCatalog
    from living_world.archives.lease import AttemptLease
    from living_world.runtime.preflight import preflight_provider

    catalog = RunCatalog(tmp_path / "runs")
    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(
        "schema_version: 1\nkey: test\nseed: 7\ndefinitions: defs.yaml\n"
    )
    (tmp_path / "defs.yaml").write_text("definitions: []\n")
    observed = threading.Event()

    def inspect_before_get() -> None:
        assert (ref.directory / "setup.json").is_file()
        assert not (ref.directory / "attempt.json").exists()
        assert not (ref.directory / "archive.sqlite3").exists()
        assert (
            load_retained_inputs(ref).scenario_path.read_bytes()
            == scenario.read_bytes()
        )
        observed.set()

    with tags_server(
        {"models": [{"name": "tiny:latest", "digest": "a" * 64}]},
        on_get=inspect_before_get,
    ) as base:
        ref = catalog.reserve_setup(requested(base))
        intent = (ref.directory / "setup.json").read_bytes()
        with AttemptLease(ref):
            retain_inputs(ref, scenario, tape_path=None)
            effective = preflight_provider(catalog.setup_config(ref))
            assert observed.is_set()
            catalog.complete_setup(ref, effective)
        with catalog.open_attempt(ref.attempt_id) as archive:
            assert archive.config == effective and archive.latest_revision is None
        assert (ref.directory / "setup.json").read_bytes() == intent


def test_preflight_local_worker_setup_failure_is_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from living_world.runtime import preflight

    def unavailable(**kwargs: object) -> None:
        raise OSError("private path")

    monkeypatch.setattr(preflight, "TemporaryDirectory", unavailable)
    with pytest.raises(preflight.ProviderPreflightError) as caught:
        preflight.preflight_provider(requested("http://127.0.0.1:1"))
    assert caught.value.code == "worker_failed"
