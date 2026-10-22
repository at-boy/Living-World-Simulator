"""CLI archive routing and retained-world acceptance."""

import json
import os
import signal
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from living_world.archives import RunCatalog
from living_world.cli import main


def test_explicit_archive_resume_and_readonly_inspection(tmp_path, monkeypatch, capsys):
    from test_runner_cli import _scenario

    from living_world import cli

    root = tmp_path / "runs"
    assert (
        main(
            [
                "run",
                str(_scenario(tmp_path)),
                "--max-ticks",
                "1",
                "--archive-root",
                str(root),
                "--database",
                str(tmp_path / "world.db"),
            ]
        )
        == 0
    )
    source = RunCatalog(root).attempts()[0].ref
    capsys.readouterr()
    assert (
        main(
            ["run", "--resume-attempt", source.attempt_id, "--archive-root", str(root)]
        )
        == 0
    )
    assert "status=resumed start_tick=1 end_tick=2" in capsys.readouterr().out
    before = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }
    ticks = []
    monkeypatch.setattr(
        cli, "_serve_inspection", lambda engine, port: ticks.append(engine.state.tick)
    )
    assert (
        main(
            [
                "inspect",
                "--attempt",
                source.attempt_id,
                "--checkpoint",
                "0",
                "--archive-root",
                str(root),
            ]
        )
        == 0
    )
    assert ticks == [0]
    assert before == {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize(
    "flags",
    [
        [],
        ["--driver", "ollama"],
        ["--model", "test"],
        ["--driver", "ollama", "--model", "test", "--base-url", "https://example.com"],
        ["--driver", "ollama", "--model", "test", "--max-ticks", "0"],
    ],
)
def test_invalid_preset_never_reserves(tmp_path, flags):
    root = tmp_path / "runs"
    with pytest.raises(SystemExit) as error:
        main(["run", "--preset", "founders", "--archive-root", str(root), *flags])
    assert error.value.code == 2
    assert not root.exists()


def test_runtime_failure_fallback_and_known_setup_failure(tmp_path, capsys):
    from uuid import uuid4

    from test_runtime_preflight import tags_server

    root = tmp_path / "runs"
    assert (
        main(["run", "--resume-attempt", uuid4().hex, "--archive-root", str(root)]) == 4
    )
    summaries = RunCatalog(root).attempts()
    assert len(summaries) == 1 and summaries[0].lifecycle == "failed"
    assert summaries[0].last_revision is None
    with tags_server({"models": []}) as url:
        assert (
            main(
                [
                    "run",
                    "--preset",
                    "founders",
                    "--driver",
                    "ollama",
                    "--model",
                    "missing",
                    "--base-url",
                    url,
                    "--archive-root",
                    str(root),
                ]
            )
            == 6
        )
    summaries = RunCatalog(root).attempts()
    assert len(summaries) == 2
    assert any(item.failure_code == "model_missing" for item in summaries)
    assert "model_missing" in capsys.readouterr().err


def test_changed_resume_requires_explicit_fork_and_keeps_source(tmp_path, capsys):
    from test_runner_cli import _scenario

    root = tmp_path / "runs"
    assert (
        main(
            [
                "run",
                str(_scenario(tmp_path)),
                "--max-ticks",
                "1",
                "--database",
                str(tmp_path / "w.db"),
                "--archive-root",
                str(root),
            ]
        )
        == 0
    )
    source = RunCatalog(root).attempts()[0].ref
    before = {p: p.read_bytes() for p in source.directory.rglob("*") if p.is_file()}
    assert (
        main(
            [
                "run",
                "--resume-attempt",
                source.attempt_id,
                "--max-ticks",
                "2",
                "--archive-root",
                str(root),
            ]
        )
        == 2
    )
    assert (
        main(
            [
                "run",
                "--fork-attempt",
                source.attempt_id,
                "--max-ticks",
                "2",
                "--archive-root",
                str(root),
            ]
        )
        == 0
    )
    assert "status=resumed start_tick=1 end_tick=3" in capsys.readouterr().out
    assert before == {
        p: p.read_bytes() for p in source.directory.rglob("*") if p.is_file()
    }


@contextmanager
def provider(*, fail=False, block=None):
    entered, release = threading.Event(), threading.Event()
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def reply(self, method):
            calls.append(method)
            if method == block:
                entered.set()
                release.wait(8)
            if method == "POST":
                self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(500 if fail and method == "POST" else 200)
            self.end_headers()
            body = (
                {"models": [{"name": "tiny:latest", "digest": "a" * 64}]}
                if method == "GET"
                else {
                    "response": json.dumps(
                        {"spoken_text": "I will wait.", "action_request": None}
                    )
                }
            )
            try:
                self.wfile.write(json.dumps(body).encode())
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            self.reply("GET")

        def do_POST(self):
            self.reply("POST")

        def log_message(self, *_args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", calls, entered
        finally:
            release.set()
            server.shutdown()
            thread.join(2)


def live_args(root, url):
    return [
        "run",
        "--preset",
        "founders",
        "--driver",
        "ollama",
        "--model",
        "tiny",
        "--base-url",
        url,
        "--timeout-seconds",
        "10",
        "--archive-root",
        str(root),
    ]


def test_live_request_budget_and_full_offline_replay(tmp_path, capsys):
    root = tmp_path / "runs"
    with provider() as (url, calls, _):
        assert main([*live_args(root, url), "--max-requests", "1"]) == 0
        assert calls == ["GET", "POST"]
    assert "stop_reason=request_budget_exhausted" in capsys.readouterr().out
    source = RunCatalog(root).attempts()[0].ref
    assert (
        main(
            ["run", "--replay-attempt", source.attempt_id, "--archive-root", str(root)]
        )
        == 0
    )
    assert "proposals_finalized" not in capsys.readouterr().out
    assert len(RunCatalog(root).attempts()) == 2


def test_provider_runtime_error_stops_without_retry(tmp_path, capsys):
    root = tmp_path / "runs"
    with provider(fail=True) as (url, calls, _):
        assert main(live_args(root, url)) == 6
        assert calls == ["GET", "POST"]
    assert "http_error" in capsys.readouterr().err
    assert RunCatalog(root).attempts()[0].lifecycle == "failed"


@pytest.mark.parametrize("stage", ["GET", "POST"])
def test_real_sigint_during_provider_io_cleans_owner(tmp_path, stage):
    root = tmp_path / "runs"
    with provider(block=stage) as (url, _calls, entered):
        process = subprocess.Popen(
            [sys.executable, "-m", "living_world.cli", *live_args(root, url)],
            env={**os.environ, "PYTHONPATH": "src"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert entered.wait(5)
            process.send_signal(signal.SIGINT)
            out, err = process.communicate(timeout=7)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        assert process.returncode == 0, err
        assert "operator_stop" in out + err
        assert err.count("attempt=") == 1
        assert "Traceback" not in err
    from living_world.archives import AttemptLease

    summaries = RunCatalog(root).attempts()
    assert len(summaries) == 1
    with AttemptLease(summaries[0].ref):
        pass
    assert not any(
        thread.name in ("living-world-cli-stop", "living-world-runtime")
        for thread in threading.enumerate()
    )


@pytest.mark.parametrize(
    "flags",
    [
        ["--driver", "ollama"],
        ["--model", "tiny"],
        ["--max-requests", "2"],
        ["--base-url", "http://127.0.0.1:1234"],
    ],
)
def test_old_recorded_route_rejects_provider_options(tmp_path, flags):
    from test_runner_cli import _scenario

    root = tmp_path / "runs"
    with pytest.raises(SystemExit):
        main(["run", str(_scenario(tmp_path)), "--archive-root", str(root), *flags])
    assert not root.exists()


def test_inspection_uses_existing_http_app_and_never_allocates(tmp_path, monkeypatch):
    import socket
    import time
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    import uvicorn
    from test_runner_cli import _scenario

    from living_world import cli
    from living_world.api.server import create_app

    root = tmp_path / "runs"
    assert (
        main(
            [
                "run",
                str(_scenario(tmp_path)),
                "--archive-root",
                str(root),
                "--database",
                str(tmp_path / "w.db"),
            ]
        )
        == 0
    )
    ref = RunCatalog(root).attempts()[0].ref
    seen = []

    def serve(engine, port):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            server = uvicorn.Server(
                uvicorn.Config(create_app(engine), log_level="error")
            )
            thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]})
            thread.start()
            try:
                deadline = time.monotonic() + 3
                while not server.started and time.monotonic() < deadline:
                    time.sleep(0.01)
                assert server.started
                url = f"http://127.0.0.1:{sock.getsockname()[1]}/world"
                with urlopen(url, timeout=2) as response:
                    seen.append(response.status)
                with pytest.raises(HTTPError) as error:
                    urlopen(Request(url, method="POST"), timeout=2)
                assert error.value.code == 405
            finally:
                server.should_exit = True
                thread.join(3)
                assert not thread.is_alive()

    monkeypatch.setattr(cli, "_serve_inspection", serve)
    assert (
        main(["inspect", "--attempt", ref.attempt_id, "--archive-root", str(root)]) == 0
    )
    assert seen == [200]
    assert len(RunCatalog(root).attempts()) == 1


def test_preexisting_stop_and_control_exception_keep_attempt(tmp_path):
    class Stop:
        def stop_requested(self):
            return True

    class Broken:
        def stop_requested(self):
            raise RuntimeError("SECRET")

    root = tmp_path / "runs"
    with provider(block="GET") as (url, _, _):
        assert main(live_args(root, url), stop_control=Stop()) == 0
    with provider(block="GET") as (url, _, _):
        assert main(live_args(root, url), stop_control=Broken()) == 5
    assert len(RunCatalog(root).attempts()) == 2
    assert not any(t.name == "living-world-cli-stop" for t in threading.enumerate())


def test_equal_live_resume_and_changed_model_pin(tmp_path, capsys):
    root = tmp_path / "runs"
    with provider() as (url, _calls, _):
        assert main([*live_args(root, url), "--max-ticks", "1"]) == 0
        source = RunCatalog(root).attempts()[0].ref
        with RunCatalog(root).open_attempt(source.attempt_id) as archive:
            original = archive.config
        assert (
            main(
                [
                    "run",
                    "--resume-attempt",
                    source.attempt_id,
                    "--driver",
                    "ollama",
                    "--model",
                    "tiny",
                    "--base-url",
                    url + "/",
                    "--timeout-seconds",
                    "10.0",
                    "--max-ticks",
                    "1",
                    "--archive-root",
                    str(root),
                ]
            )
            == 0
        )
        child = next(
            item for item in RunCatalog(root).attempts() if item.parent is not None
        )
        with RunCatalog(root).open_attempt(child.ref.attempt_id) as archive:
            assert archive.config == original
    from test_runtime_preflight import tags_server

    with tags_server({"models": [{"name": "tiny:latest", "digest": "b" * 64}]}) as url:
        # Explicit fork can change endpoint, but preserves the original model pin.
        assert (
            main(
                [
                    "run",
                    "--fork-attempt",
                    source.attempt_id,
                    "--base-url",
                    url,
                    "--archive-root",
                    str(root),
                ]
            )
            == 6
        )
    assert "model_digest_mismatch" in capsys.readouterr().err


def test_missing_server_attempt_and_failed_fallback_are_safe(
    tmp_path, monkeypatch, capsys
):
    import socket
    from uuid import uuid4

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    root = tmp_path / "runs"
    assert main(live_args(root, url)) == 6
    assert RunCatalog(root).attempts()[0].failure_code == "transport"
    capsys.readouterr()

    def fail(*_args, **_kwargs):
        raise OSError("SECRET_PATH")

    monkeypatch.setattr(RunCatalog, "reserve", fail)
    assert (
        main(["run", "--resume-attempt", uuid4().hex, "--archive-root", str(root)]) == 4
    )
    assert "SECRET_PATH" not in capsys.readouterr().err
    assert len(RunCatalog(root).attempts()) == 1


@pytest.mark.parametrize("checkpoint", [[], ["--checkpoint", "999"]])
def test_missing_world_inspection_does_not_write(tmp_path, checkpoint):
    from uuid import uuid4

    root = tmp_path / "absent"
    assert (
        main(
            [
                "inspect",
                "--attempt",
                uuid4().hex,
                "--archive-root",
                str(root),
                *checkpoint,
            ]
        )
        == 4
    )
    assert not root.exists()


def test_archived_initial_tick_survives_publication_eviction(tmp_path, capsys):
    from test_runner_cli import _scenario

    root = tmp_path / "runs"
    assert (
        main(
            [
                "run",
                str(_scenario(tmp_path, max_ticks=30)),
                "--max-ticks",
                "1",
                "--database",
                str(tmp_path / "w.db"),
                "--archive-root",
                str(root),
            ]
        )
        == 0
    )
    source = RunCatalog(root).attempts()[0].ref
    capsys.readouterr()
    assert (
        main(
            [
                "run",
                "--fork-attempt",
                source.attempt_id,
                "--max-ticks",
                "12",
                "--archive-root",
                str(root),
            ]
        )
        == 0
    )
    assert "start_tick=1 end_tick=13" in capsys.readouterr().out


@pytest.mark.parametrize(
    "flags",
    [
        ["--proposal-tape", "tape.yaml"],
        ["--checkpoint-only"],
        ["--save-every", "1"],
        ["--continuous"],
        ["--model", "tiny"],
    ],
)
def test_replay_rejects_overrides_without_allocation(tmp_path, flags):
    from uuid import uuid4

    root = tmp_path / "runs"
    with pytest.raises(SystemExit):
        main(
            [
                "run",
                "--replay-attempt",
                uuid4().hex,
                "--archive-root",
                str(root),
                *flags,
            ]
        )
    assert not root.exists()


def test_replay_inherits_source_mirror_cadence(tmp_path, monkeypatch):
    from living_world.runtime import entrypoints

    root = tmp_path / "runs"
    with provider() as (url, _, _):
        assert (
            main([*live_args(root, url), "--max-requests", "1", "--save-every", "4"])
            == 0
        )
    source = RunCatalog(root).attempts()[0].ref
    observed = []
    original = entrypoints.RuntimeService

    class Service(original):
        def __init__(self, *args, **kwargs):
            observed.append(kwargs["save_every"])
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(entrypoints, "RuntimeService", Service)
    assert (
        main(
            [
                "run",
                "--replay-attempt",
                source.attempt_id,
                "--archive-root",
                str(root),
                "--database",
                str(tmp_path / "mirror.db"),
            ]
        )
        == 0
    )
    assert observed == [4]


@pytest.mark.parametrize("command", ["run", "inspect"])
def test_invalid_catalog_root_errors_are_closed_codes(tmp_path, command, capsys):
    from uuid import uuid4

    root = tmp_path / "PRIVATE_ROOT"
    root.symlink_to(tmp_path / "target", target_is_directory=True)
    args = (
        ["run", "--resume-attempt", uuid4().hex]
        if command == "run"
        else ["inspect", "--attempt", uuid4().hex]
    )
    assert main([*args, "--archive-root", str(root)]) == 4
    assert capsys.readouterr().err == "error: archive_failed\n"


@pytest.mark.parametrize("operator_stop", [False, True])
def test_final_mirror_failure_after_terminal_observation_is_not_success(
    tmp_path, monkeypatch, capsys, operator_stop
):
    from test_runner_cli import _scenario

    from living_world.repositories.world_snapshot import decode_world
    from living_world.runtime import entrypoints
    from living_world.runtime import service as service_module

    root = tmp_path / "runs"
    assert (
        main(
            [
                "run",
                str(_scenario(tmp_path)),
                "--max-ticks",
                "1",
                "--database",
                str(tmp_path / "source.db"),
                "--archive-root",
                str(root),
            ]
        )
        == 0
    )
    catalog = RunCatalog(root)
    source = catalog.attempts()[0].ref
    source_bytes = {
        p: p.read_bytes() for p in source.directory.rglob("*") if p.is_file()
    }
    capsys.readouterr()
    launched, main_join, final_mirror = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    original_service = entrypoints.RuntimeService
    original_mirror = service_module.write_checkpoint_mirror
    mirror_calls = 0

    class Service(original_service):
        def resume(self, *args, **kwargs):
            controller = super().resume(*args, **kwargs)
            launched.set()
            return controller

        def shutdown(self, **kwargs):
            if threading.current_thread() is threading.main_thread():
                main_join.set()
            super().shutdown(**kwargs)

    def mirror(checkpoint, *args, **kwargs):
        nonlocal mirror_calls
        mirror_calls += 1
        if mirror_calls == 1:
            return original_mirror(checkpoint, *args, **kwargs)
        final_mirror.set()
        assert main_join.wait(3), "CLI must join after observing terminal state"
        raise OSError("PRIVATE final mirror failure")

    if operator_stop:

        def wait_for_shutdown(_controller, stop_event, **_kwargs):
            assert stop_event.wait(3), "watcher must request owner shutdown"

        monkeypatch.setattr(service_module, "_loop", wait_for_shutdown)

    class Stop:
        def stop_requested(self):
            return operator_stop and launched.is_set()

    monkeypatch.setattr(entrypoints, "RuntimeService", Service)
    monkeypatch.setattr(service_module, "write_checkpoint_mirror", mirror)
    result = main(
        [
            "run",
            "--resume-attempt",
            source.attempt_id,
            "--checkpoint",
            "0",
            "--archive-root",
            str(root),
            "--database",
            str(tmp_path / "child.db"),
        ],
        stop_control=Stop(),
    )
    assert final_mirror.is_set()
    captured = capsys.readouterr()
    child = next(item for item in catalog.attempts() if item.parent is not None)
    assert child.lifecycle == "failed"
    with catalog.open_attempt(child.ref.attempt_id) as archive:
        checkpoint = archive.checkpoint()
        assert decode_world(checkpoint.snapshot).tick == (0 if operator_stop else 1)
        finished = [
            entry for entry in archive.entries() if entry.kind == "attempt_finished"
        ][-1]
        assert finished.payload["lifecycle"] == "failed"
        assert finished.payload["outcome"] == "mirror_failed"
        assert finished.payload["last_revision"] == checkpoint.revision
    assert source_bytes == {
        p: p.read_bytes() for p in source.directory.rglob("*") if p.is_file()
    }
    assert result == 4
    assert captured.out == ""
    assert "error: mirror_failed\n" in captured.err
    assert "PRIVATE" not in captured.err
    assert captured.err.count("attempt=") == 1
    assert child.ref.attempt_id in captured.err
