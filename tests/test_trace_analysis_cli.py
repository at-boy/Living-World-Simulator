"""Supported offline command, custody reuse, and owned HTTP lifetime."""

import importlib
import json
import os
import select
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from living_world.cli import build_parser, main


def args(tmp_path, *extra):
    return [
        "analyze",
        "--archive-root",
        str(tmp_path / "runs"),
        "--admin-token-file",
        str(tmp_path / "token"),
        "--port",
        "0",
        *extra,
    ]


class Stop:
    def stop_requested(self):
        return True


def test_parser_supported_inert_command():
    parsed = build_parser().parse_args(["analyze"])
    assert parsed.port == 8000 and parsed.archive_root is None
    assert not hasattr(parsed, "scenario")


def test_shared_custody_is_legacy_identity(tmp_path):
    shared = importlib.import_module("living_world.api.local_admin")
    from living_world.runtime import serving

    assert shared.AdminTokenFile is serving._Credential
    assert shared.ServeCLIError is serving.ServeCLIError
    credential = shared.AdminTokenFile.open(tmp_path / "token", [tmp_path / "runs"])
    try:
        credential.publish("secret")
        assert (tmp_path / "token").stat().st_mode & 0o777 == 0o600
    finally:
        credential.close()
    assert not (tmp_path / "token").exists()


@pytest.mark.parametrize(
    "extra",
    [
        ["--port", "-1"],
        ["--port", "65536"],
        ["--model", "x"],
        ["--resume-attempt", "x"],
        ["scenario.yaml"],
        ["--host", "0.0.0.0"],
    ],
)
def test_unsupported_arguments_rejected(tmp_path, extra):
    with pytest.raises(SystemExit) as error:
        main(args(tmp_path, *extra))
    assert error.value.code == 2
    assert not (tmp_path / "runs").exists()


def test_non_tty_precedes_catalog_or_bind(tmp_path, monkeypatch, capsys):
    module = importlib.import_module("living_world.api.analysis_serving")

    def forbidden(*a, **kw):
        raise AssertionError("must reject before IO")

    monkeypatch.setattr(module, "RunCatalog", forbidden)
    monkeypatch.setattr(module.socket, "socket", forbidden)
    assert main(["analyze", "--archive-root", str(tmp_path / "runs")]) == 2
    assert capsys.readouterr().err == "error: invalid_configuration\n"
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("kind", ["file", "symlink", "parentlink", "traversal"])
def test_unsafe_root_rejected(tmp_path, kind, capsys):
    root = tmp_path / "runs"
    if kind == "file":
        root.write_text("private")
    elif kind == "symlink":
        root.symlink_to(tmp_path, target_is_directory=True)
    elif kind == "parentlink":
        (tmp_path / "link").symlink_to(tmp_path, target_is_directory=True)
        root = tmp_path / "link" / "absent"
    else:
        root = tmp_path / "x" / ".." / "absent"
    assert main(args(tmp_path, "--archive-root", str(root)), stop_control=Stop()) == 2
    assert capsys.readouterr().err == "error: invalid_configuration\n"
    assert not (tmp_path / "token").exists()


def test_analysis_bypasses_runtime_and_restores_signals(tmp_path, monkeypatch):
    from living_world import cli
    from living_world.archives import RunCatalog
    from living_world.archives.lease import AttemptLease
    from living_world.runtime.controller import RunController
    from living_world.runtime.service import RuntimeService

    def forbidden(*a, **kw):
        raise AssertionError("runtime reached")

    monkeypatch.setattr(cli, "validate_archived_options", forbidden)
    for owner in (AttemptLease, RunController, RuntimeService):
        monkeypatch.setattr(owner, "__init__", forbidden)
    for name in ("attempts", "reserve", "reserve_setup", "reserve_fork_setup"):
        monkeypatch.setattr(RunCatalog, name, forbidden)
    before = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    assert main(["analyze"], engine_factory=forbidden) == 2
    assert {s: signal.getsignal(s) for s in before} == before
    assert main(args(tmp_path), stop_control=Stop(), engine_factory=forbidden) == 0
    assert not (tmp_path / "runs").exists()
    assert not (tmp_path / "token").exists()


@contextmanager
def child(tmp_path):
    process = subprocess.Popen(
        [sys.executable, "-m", "living_world.cli", *args(tmp_path)],
        env={**os.environ, "PYTHONPATH": "src"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert select.select([process.stdout], [], [], 8)[0], "readiness timeout"
        line = process.stdout.readline().strip()
        assert line.startswith("analysis_url="), line
        base = line.split("=", 1)[1].removesuffix("/analysis/status")
        assert (
            process.stdout.readline().strip() == f"analysis_browser_url={base}/analysis"
        )
        yield process, base
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            process.wait(8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(3)
            raise
        process.stdout.close()
        process.stderr.close()


def request(base, token, path, *, origin=None, method="GET"):
    headers = {} if token is None else {"Authorization": "Bearer " + token}
    if origin:
        headers["Origin"] = origin
    try:
        return urlopen(Request(base + path, headers=headers, method=method), timeout=3)
    except HTTPError as error:
        return error


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize("populated", [False, True])
def test_actual_readonly_http_and_signal_cleanup(tmp_path, signum, populated):
    from test_trace_analysis_reader import create, fail, mutate, snapshot, start

    from living_world.archives import InferenceBlob

    root = tmp_path / "runs"
    if populated:
        archive = create(root, checkpoint=False)
        start(archive)
        body = b"\xff\x00"
        fail(archive, body)
        legacy = create(root)
        from test_inference_trace_storage import request as trace_request

        legacy.append(trace_request(None))
        mutate(legacy, "UPDATE archive_meta SET payload=json_set(payload,'$.format',1)")
        from living_world.archives import AttemptConfig, RunCatalog

        catalog = RunCatalog(root)
        failed = catalog.reserve_setup(
            AttemptConfig("ollama", "founders", 7, "revision", {})
        )
        from living_world.archives.lease import AttemptLease

        with AttemptLease(failed):
            catalog.fail_setup(failed, "setup_failed")
        before = snapshot(root)
    with child(tmp_path) as (process, base):
        token = (tmp_path / "token").read_text().strip()
        with request(base, None, "/analysis/status") as result:
            assert result.status == 401
        with request(
            base, token, "/analysis/status", origin="http://evil.invalid"
        ) as result:
            assert result.status == 403
        with request(base, token, "/analysis/status") as result:
            assert json.load(result)["mode"] == "offline"
            assert result.headers["Cache-Control"] == "no-store"
        with request(base, token, "/analysis/status", method="POST") as result:
            assert result.status == 405
        with request(base, token, "/analysis/attempts") as result:
            entries = json.load(result)["attempts"]
            assert len(entries) == (3 if populated else 0)
        if populated:
            prefix = "/analysis/attempts/" + archive.ref.attempt_id
            with request(base, token, prefix + "/traces") as result:
                page = json.load(result)
                assert len(page["calls"]) == 1
            boundary = page["boundary"]
            path = prefix + "/bodies/" + InferenceBlob(body).sha256
            path += f'?through_sequence={boundary["sequence"]}&journal_digest={boundary["digest"]}'
            with request(base, token, path) as result:
                assert result.read() == body
                assert result.headers["Cache-Control"] == "no-store"
        process.send_signal(signum)
        assert process.wait(8) == 0
        output = process.stdout.read() + process.stderr.read()
        assert (
            token not in output
            and "Traceback" not in output
            and "private" not in output
        )
        assert not (tmp_path / "token").exists()
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", int(base.rsplit(":", 1)[1]))) != 0
    if populated:
        assert snapshot(root) == before
    else:
        assert not root.exists()


@pytest.mark.parametrize(
    "location", ["inside", "ancestor", "missing", "existing", "link", "hardlink"]
)
def test_public_custody_rejects_unsafe_targets(tmp_path, location):
    from living_world.api.local_admin import AdminTokenFile, ServeCLIError

    root = tmp_path / "runs"
    root.mkdir()
    target = tmp_path / "token"
    if location == "inside":
        target = root / "token"
    elif location == "ancestor":
        target = tmp_path
    elif location == "missing":
        target = tmp_path / "missing" / "token"
    elif location in {"existing", "link", "hardlink"}:
        source = tmp_path / "source"
        source.write_text("original")
        if location == "existing":
            target.write_text("original")
        elif location == "link":
            target.symlink_to(source)
        else:
            os.link(source, target)
    with pytest.raises(ServeCLIError) as error:
        AdminTokenFile.open(target, [root])
    assert (error.value.exit_code, error.value.reason) == (2, "invalid_configuration")


@pytest.mark.parametrize("change", ["modify", "replace", "hardlink"])
def test_public_custody_preserves_changed_token(tmp_path, change):
    from living_world.api.local_admin import AdminTokenFile

    path = tmp_path / "token"
    custody = AdminTokenFile.open(path, [tmp_path / "runs"])
    custody.publish("secret")
    if change == "modify":
        path.write_text("changed")
    elif change == "replace":
        path.unlink()
        path.write_text("replacement")
    else:
        os.link(path, tmp_path / "other")
    expected = path.read_bytes()
    custody.close()
    assert path.read_bytes() == expected


@pytest.mark.parametrize(
    "failure,code,reason",
    [
        ("import", 2, "server_unavailable"),
        ("bind", 5, "server_failed"),
        ("http", 5, "server_failed"),
        ("start", 5, "service_failed"),
        ("join", 5, "service_failed"),
        ("control", 5, "service_failed"),
        ("write", 4, "credential_file_failed"),
        ("close", 4, "credential_file_failed"),
        ("http_close", 5, "server_failed"),
        ("join_close", 5, "service_failed"),
        ("timeout", 5, "server_failed"),
        ("socket_close", 5, "service_failed"),
    ],
)
def test_fixed_adapter_failures_cleanup(
    tmp_path, monkeypatch, capsys, failure, code, reason
):
    import uvicorn

    from living_world.api import analysis_serving as module
    from living_world.api.local_admin import AdminTokenFile, ServeCLIError

    def broken(*a, **kw):
        raise RuntimeError("PRIVATE diagnostic")

    control = Stop()
    if failure == "import":
        monkeypatch.setitem(sys.modules, "uvicorn", None)
    elif failure == "bind":

        class BadSocket(socket.socket):
            def bind(self, address):
                raise OSError("PRIVATE address")

        monkeypatch.setattr(module.socket, "socket", BadSocket)
    elif failure in {"http", "http_close"}:
        monkeypatch.setattr(uvicorn.Server, "run", broken)

        class KeepRunning:
            def stop_requested(self):
                return False

        control = KeepRunning()
    elif failure in {"start", "join", "join_close"}:
        original = module.Thread

        class BadThread(original):
            def start(self):
                if failure == "start":
                    broken()
                super().start()

            def join(self, timeout=None):
                super().join(timeout)
                if failure in {"join", "join_close"}:
                    broken()

        monkeypatch.setattr(module, "Thread", BadThread)
    elif failure == "control":

        class BadControl:
            stop_requested = broken

        control = BadControl()
    elif failure == "write":

        def fail_write(*a, **kw):
            raise OSError("PRIVATE token")

        monkeypatch.setattr(os, "write", fail_write)
    elif failure == "timeout":

        class NeverStarts:
            started = False
            should_exit = False

            def __init__(self, config):
                pass

            def run(self, sockets):
                while not self.should_exit:
                    time.sleep(0.001)

        monkeypatch.setattr(uvicorn, "Server", NeverStarts)
        times = iter([0, 6])
        monkeypatch.setattr(module.time, "monotonic", lambda: next(times))

        class KeepRunning:
            def stop_requested(self):
                return False

        control = KeepRunning()
    elif failure == "socket_close":

        class CloseFailure(socket.socket):
            def close(self):
                super().close()
                raise OSError("PRIVATE socket")

        monkeypatch.setattr(module.socket, "socket", CloseFailure)

        class QuietServer:
            started = True
            should_exit = False

            def __init__(self, config):
                pass

            def run(self, sockets):
                while not self.should_exit:
                    time.sleep(0.001)

        monkeypatch.setattr(uvicorn, "Server", QuietServer)
    if failure in {"close", "http_close", "join_close"}:
        original_close = AdminTokenFile.close

        def fail_close(self):
            original_close(self)
            raise ServeCLIError(4, "credential_file_failed")

        monkeypatch.setattr(AdminTokenFile, "close", fail_close)
    assert main(args(tmp_path), stop_control=control) == code
    captured = capsys.readouterr()
    assert captured.err == f"error: {reason}\n"
    assert "PRIVATE" not in captured.out
    assert not (tmp_path / "token").exists()
    assert not (tmp_path / "runs").exists()


def test_actual_console_help_and_invalid_port():
    for extra, expected in ((["--help"], 0), (["--port", "65536"], 2)):
        result = subprocess.run(
            [sys.executable, "-m", "living_world.cli", "analyze", *extra],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
            env={**os.environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == expected
        assert "Traceback" not in result.stderr
        if expected == 0:
            assert "--admin-token-file" in result.stdout
            assert "--model" not in result.stdout


@pytest.mark.parametrize(
    "stdout_tty,stderr_tty", [(True, False), (False, True), (True, True)]
)
def test_terminal_delivery_requires_both_ttys(
    tmp_path, monkeypatch, capsys, stdout_tty, stderr_tty
):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: stdout_tty)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: stderr_tty)
    result = main(
        ["analyze", "--archive-root", str(tmp_path / "runs"), "--port", "0"],
        stop_control=Stop(),
    )
    captured = capsys.readouterr()
    assert result == (0 if stdout_tty and stderr_tty else 2)
    assert "Admin token:" not in captured.out
    assert ("Admin token:" in captured.err) == (stdout_tty and stderr_tty)
    assert not (tmp_path / "runs").exists()


def test_malformed_selected_source_stays_sanitized_and_unmodified(tmp_path):
    from test_trace_analysis_reader import create, snapshot

    archive = create(tmp_path / "runs")
    archive.database_path.write_bytes(b"PRIVATE malformed SQLite")
    before = snapshot(tmp_path / "runs")
    with child(tmp_path) as (_process, base):
        token = (tmp_path / "token").read_text().strip()
        with request(base, token, "/analysis/attempts") as result:
            assert len(json.load(result)["attempts"]) == 1
        with request(
            base, token, "/analysis/attempts/" + archive.ref.attempt_id + "/traces"
        ) as result:
            assert result.status == 409
            assert json.load(result) == {"detail": "trace_unavailable"}
    assert snapshot(tmp_path / "runs") == before


def test_normal_stop_leaves_no_owned_http_thread(tmp_path):
    import threading

    assert main(args(tmp_path), stop_control=Stop()) == 0
    assert not any(
        t.name == "living-world-analysis-http" for t in threading.enumerate()
    )
