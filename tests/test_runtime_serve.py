"""Public local serving: real HTTP lifetime and credential custody."""

import json
import os
import select
import signal
import stat
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from living_world.archives import RunCatalog
from living_world.cli import main


def args(tmp_path, *extra):
    return [
        "serve",
        *(
            []
            if "--resume-attempt" in extra
            or "--fork-attempt" in extra
            or "--preset" in extra
            else ["--founders", "success"]
        ),
        "--archive-root",
        str(tmp_path / "runs"),
        "--admin-token-file",
        str(tmp_path / "token"),
        "--port",
        "0",
        *extra,
    ]


def wait_until(check, seconds=6):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError("condition did not become ready")


@contextmanager
def child(tmp_path, *extra):
    process = subprocess.Popen(
        [sys.executable, "-m", "living_world.cli", *args(tmp_path, *extra)],
        env={**os.environ, "PYTHONPATH": "src"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert select.select([process.stdout], [], [], 6)[0], "HTTP readiness timeout"
        line = process.stdout.readline().strip()
        assert line.startswith("runtime_url="), (
            process.stderr.read() if process.poll() is not None else line
        )
        yield process, line.split("=", 1)[1].removesuffix("/runtime")
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            process.wait(8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(3)
            raise


def request(base, token, path, body=None, nonce=None):
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers.update(
            {"Origin": base, "X-CSRF-Token": nonce, "Content-Type": "application/json"}
        )
    with urlopen(
        Request(
            base + path,
            headers=headers,
            data=None if body is None else json.dumps(body).encode(),
        ),
        timeout=3,
    ) as response:
        return json.load(response), response.headers.get("x-csrf-token")


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_public_paused_step_signal_and_exact_resume(tmp_path, signum):
    with child(tmp_path) as (process, base):
        token = (tmp_path / "token").read_text().strip()
        assert stat.S_IMODE((tmp_path / "token").stat().st_mode) == 0o600

        def live():
            return request(base, token, "/runtime/status")[0]["live"]

        initial = wait_until(live)
        assert initial["state"] == "paused" and initial["tick"] == 0
        for _ in range(5):
            assert live()["tick"] == 0
        _, nonce = request(base, token, "/runtime/status")
        receipt, _ = request(
            base,
            token,
            "/runtime/commands",
            {
                "command_id": "one",
                "action": "step",
                "expected_state_version": initial["state_version"],
            },
            nonce,
        )
        assert receipt["status"] == "queued"
        wait_until(lambda: live()["tick"] == 1 and live()["state"] == "paused")
        process.send_signal(signum)
        out, err = process.communicate(timeout=8)
        assert process.returncode == 0, err
        assert "scenario=" not in out and "Traceback" not in err
        assert token not in out + err and err.count("attempt=") == 1
    assert not (tmp_path / "token").exists()
    catalog = RunCatalog(tmp_path / "runs")
    source = catalog.attempts()[0].ref
    before = {p: p.read_bytes() for p in source.directory.rglob("*") if p.is_file()}
    with catalog.open_attempt(source.attempt_id) as archive:
        checkpoint = archive.checkpoint()
    with child(tmp_path, "--resume-attempt", source.attempt_id) as (_, base):
        token = (tmp_path / "token").read_text().strip()
        live = wait_until(lambda: request(base, token, "/runtime/status")[0]["live"])
        assert live["tick"] == 1 and live["state"] == "paused"
        children = [item for item in catalog.attempts() if item.parent is not None]
        with catalog.open_attempt(children[0].ref.attempt_id) as archive:
            restored = archive.checkpoint(0)
            assert restored.snapshot == checkpoint.snapshot
            assert restored.driver_cursor == checkpoint.driver_cursor
            assert restored.feedback_cursor == checkpoint.feedback_cursor
    assert before == {
        p: p.read_bytes() for p in source.directory.rglob("*") if p.is_file()
    }
    assert checkpoint.revision >= 1


def test_redirected_credentials_required_before_allocation(tmp_path, capsys):
    assert (
        main(
            ["serve", "--founders", "success", "--archive-root", str(tmp_path / "runs")]
        )
        == 2
    )
    assert not (tmp_path / "runs").exists()
    assert capsys.readouterr().err == "error: invalid_configuration\n"


@pytest.mark.parametrize(
    "extra",
    [
        ["--model", "secret"],
        ["--checkpoint", "0"],
        ["--port", "65536"],
        ["--replay-attempt", "abc"],
    ],
)
def test_invalid_serve_options_do_not_allocate(tmp_path, extra):
    with pytest.raises(SystemExit):
        main(args(tmp_path, *extra))
    assert not (tmp_path / "runs").exists()


def test_credential_nooverwrite_and_symlink(tmp_path, capsys):
    token = tmp_path / "token"
    token.write_text("owned")
    assert main(args(tmp_path)) == 2
    assert token.read_text() == "owned"
    token.unlink()
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / "link").symlink_to(target, target_is_directory=True)
    assert (
        main(args(tmp_path, "--admin-token-file", str(tmp_path / "link" / "token")))
        == 2
    )
    assert not (tmp_path / "runs").exists()
    assert "target" not in capsys.readouterr().err


def test_credential_custody_modified_and_replaced(tmp_path):
    from living_world.runtime.serving import _Credential

    token = tmp_path / "token"
    owned = _Credential.open(token, [tmp_path / "runs"])
    owned.publish("secret")
    token.write_text("changed")
    owned.close()
    assert token.read_text() == "changed"
    token.unlink()
    owned = _Credential.open(token, [tmp_path / "runs"])
    owned.publish("secret")
    replacement = tmp_path / "replacement"
    replacement.write_text("secret\n")
    replacement.replace(token)
    owned.close()
    assert token.read_text() == "secret\n"


@pytest.mark.parametrize("failure", ["write", "fchmod", "fsync", "close"])
def test_partial_credential_failure_removes_only_owned_bytes(
    tmp_path, monkeypatch, failure
):
    from living_world.runtime import serving

    credential = serving._Credential.open(tmp_path / "token", [tmp_path / "runs"])
    original = getattr(os, failure)
    writes = 0
    real_write = os.write

    def short_write(fd, data):
        nonlocal writes
        writes += 1
        if failure == "write" and writes == 2:
            raise OSError("PRIVATE")
        return real_write(fd, data[:2])

    def broken(*values):
        if failure == "close":
            original(*values)
        raise OSError("PRIVATE")

    monkeypatch.setattr(os, "write", short_write)
    if failure != "write":
        monkeypatch.setattr(os, failure, broken)
    with pytest.raises(serving.ServeCLIError) as error:
        credential.publish("secret")
    monkeypatch.undo()
    assert error.value.exit_code == 4 and str(error.value) == "credential_file_failed"
    credential.close()
    assert not (tmp_path / "token").exists()


def test_short_credential_writes_complete(tmp_path, monkeypatch):
    from living_world.runtime.serving import _Credential

    credential = _Credential.open(tmp_path / "token", [tmp_path / "runs"])
    original = os.write
    monkeypatch.setattr(os, "write", lambda fd, data: original(fd, data[:2]))
    credential.publish("secret")
    assert (tmp_path / "token").read_bytes() == b"secret\n"
    credential.close()
    assert not (tmp_path / "token").exists()


def test_symlink_component_before_dotdot_rejected(tmp_path):
    from living_world.runtime.serving import ServeCLIError, _Credential

    (tmp_path / "directory").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "directory", target_is_directory=True)
    with pytest.raises(ServeCLIError):
        _Credential.open(tmp_path / "link" / ".." / "token", [tmp_path / "runs"])


@pytest.mark.parametrize(
    "destination", ["runs", "runs/token", ".", "mirror", "mirror/token"]
)
def test_credential_overlap_before_allocation(tmp_path, destination):
    assert (
        main(
            args(
                tmp_path,
                "--admin-token-file",
                str(tmp_path / destination),
                "--database",
                str(tmp_path / "mirror"),
            )
        )
        == 2
    )
    assert not (tmp_path / "runs").exists()


def test_credential_replacement_survives_failed_write(tmp_path, monkeypatch):
    from living_world.runtime import serving

    token = tmp_path / "token"
    credential = serving._Credential.open(token, [tmp_path / "runs"])

    def replace_then_fail(_fd, _data):
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"external")
        replacement.replace(token)
        raise OSError("PRIVATE")

    monkeypatch.setattr(os, "write", replace_then_fail)
    with pytest.raises(serving.ServeCLIError):
        credential.publish("secret")
    credential.close()
    assert token.read_bytes() == b"external"


def test_start_running_completion_remains_inspectable(tmp_path):
    with child(tmp_path, "--start-running") as (process, base):
        token = (tmp_path / "token").read_text().strip()

        def live():
            return request(base, token, "/runtime/status")[0]["live"]

        wait_until(lambda: live() and live()["state"] == "completed")
        assert process.poll() is None
        archives, _ = request(base, token, "/archives")
        assert archives
        assert request(base, token, "/runtime/status")[0]["live"]["tick"] == 10


def test_blocked_setup_http_ready_and_interrupt(tmp_path):
    from test_runtime_cli import provider

    with (
        provider(block="GET") as (url, calls, entered),
        child(
            tmp_path,
            "--preset",
            "founders",
            "--driver",
            "ollama",
            "--model",
            "tiny",
            "--base-url",
            url,
        ) as (process, base),
    ):
        assert entered.wait(3)
        token = (tmp_path / "token").read_text().strip()
        assert request(base, token, "/runtime/status")[0]["live"] is None
        assert request(base, token, "/archives")[0]
        process.send_signal(signal.SIGTERM)
        _, error = process.communicate(timeout=8)
        assert process.returncode == 0, error
        assert calls == ["GET"]
        assert error.count("attempt=") == 1 and "Traceback" not in error
    assert len(RunCatalog(tmp_path / "runs").attempts()) == 1


def test_setup_failure_keeps_catalog_until_quit(tmp_path):
    from test_runtime_preflight import tags_server

    with (
        tags_server({"models": []}) as url,
        child(
            tmp_path,
            "--preset",
            "founders",
            "--driver",
            "ollama",
            "--model",
            "tiny",
            "--base-url",
            url,
        ) as (process, base),
    ):
        token = (tmp_path / "token").read_text().strip()
        catalog = RunCatalog(tmp_path / "runs")
        wait_until(
            lambda: catalog.attempts()
            and catalog.attempts()[0].failure_code == "model_missing"
        )
        assert process.poll() is None
        assert request(base, token, "/archives")[0]
        process.send_signal(signal.SIGINT)
        _, error = process.communicate(timeout=8)
        assert process.returncode == 6, error
        assert error.count("error: model_missing") == 1 and "Traceback" not in error


def test_signals_restored_and_injected_control_does_not_install(tmp_path, monkeypatch):
    from living_world import cli

    prior = {
        value: signal.getsignal(value) for value in (signal.SIGINT, signal.SIGTERM)
    }
    assert (
        main(args(tmp_path, "--admin-token-file", str(tmp_path / "absent" / "token")))
        == 2
    )
    assert prior == {value: signal.getsignal(value) for value in prior}

    class Stop:
        def stop_requested(self):
            return True

    def forbidden(*_values):
        raise AssertionError("injected control must not install signal handlers")

    monkeypatch.setattr(cli.signal, "signal", forbidden)
    assert main(args(tmp_path), stop_control=Stop()) == 0
    assert not (tmp_path / "runs").exists()


def test_control_failure_no_false_success_or_attempt(tmp_path, capsys):
    class Broken:
        def stop_requested(self):
            raise ValueError("PRIVATE")

    assert main(args(tmp_path), stop_control=Broken()) == 5
    assert not (tmp_path / "runs").exists()
    assert "PRIVATE" not in capsys.readouterr().err


def test_provider_error_remains_paused_until_explicit_retry(tmp_path):
    from test_runtime_cli import provider

    with (
        provider(fail=True) as (url, calls, _entered),
        child(
            tmp_path,
            "--preset",
            "founders",
            "--driver",
            "ollama",
            "--model",
            "tiny",
            "--base-url",
            url,
        ) as (process, base),
    ):
        token = (tmp_path / "token").read_text().strip()

        def live():
            return request(base, token, "/runtime/status")[0]["live"]

        initial = wait_until(live)
        assert calls == ["GET"]
        _, nonce = request(base, token, "/runtime/status")
        request(
            base,
            token,
            "/runtime/commands",
            {
                "command_id": "step",
                "action": "step",
                "expected_state_version": initial["state_version"],
            },
            nonce,
        )
        wait_until(lambda: live()["state"] == "provider_error_paused")
        assert process.poll() is None and calls == ["GET", "POST"]
        status = live()
        request(
            base,
            token,
            "/runtime/commands",
            {
                "command_id": "retry",
                "action": "retry",
                "expected_state_version": status["state_version"],
            },
            nonce,
        )
        wait_until(
            lambda: len(calls) == 3 and live()["state"] == "provider_error_paused"
        )
        assert calls == ["GET", "POST", "POST"]


def test_blocked_step_allows_http_pause_and_signal_cleanup(tmp_path):
    from test_runtime_cli import provider

    with (
        provider(block="POST") as (url, _calls, entered),
        child(
            tmp_path,
            "--preset",
            "founders",
            "--driver",
            "ollama",
            "--model",
            "tiny",
            "--base-url",
            url,
        ) as (process, base),
    ):
        token = (tmp_path / "token").read_text().strip()

        def live():
            return request(base, token, "/runtime/status")[0]["live"]

        initial = wait_until(live)
        _, nonce = request(base, token, "/runtime/status")
        request(
            base,
            token,
            "/runtime/commands",
            {
                "command_id": "step",
                "action": "step",
                "expected_state_version": initial["state_version"],
            },
            nonce,
        )
        assert entered.wait(3)
        current = live()
        receipt, _ = request(
            base,
            token,
            "/runtime/commands",
            {
                "command_id": "pause",
                "action": "pause",
                "expected_state_version": current["state_version"],
            },
            nonce,
        )
        assert receipt["status"] in {"queued", "applied"}
        wait_until(lambda: live()["state"] in {"paused", "pause_requested"})
        assert live()["tick"] == 0
        process.send_signal(signal.SIGINT)
        _, error = process.communicate(timeout=8)
        assert process.returncode == 0, error


def test_missing_server_import_and_bind_failure_do_not_allocate(
    tmp_path, monkeypatch, capsys
):
    import socket

    monkeypatch.setitem(sys.modules, "uvicorn", None)
    assert main(args(tmp_path)) == 2
    assert "server_unavailable" in capsys.readouterr().err
    monkeypatch.undo()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        assert main(args(tmp_path, "--port", str(sock.getsockname()[1]))) == 5
    assert "server_failed" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists() and not (tmp_path / "token").exists()


def test_http_thread_startup_failure_is_closed_without_attempt(
    tmp_path, monkeypatch, capsys
):
    import uvicorn

    def broken(*_args, **_kwargs):
        raise RuntimeError("PRIVATE SERVER ERROR")

    monkeypatch.setattr(uvicorn.Server, "run", broken)
    assert main(args(tmp_path)) == 5
    assert capsys.readouterr().err == "error: server_failed\n"
    assert not (tmp_path / "runs").exists() and not (tmp_path / "token").exists()


def test_server_death_after_launch_cleans_and_returns_failure(
    tmp_path, monkeypatch, capsys
):
    import uvicorn

    original = uvicorn.Server.run

    def die(server, **kwargs):
        # Real HTTP first, then simulate its independent early exit.
        from threading import Thread

        def request_exit():
            wait_until(lambda: RunCatalog(tmp_path / "runs").attempts())
            server.should_exit = True

        stopper = Thread(target=request_exit)
        stopper.start()
        try:
            original(server, **kwargs)
        finally:
            stopper.join(3)

    monkeypatch.setattr(uvicorn.Server, "run", die)
    assert main(args(tmp_path)) == 5
    assert "error: server_failed" in capsys.readouterr().err
    assert not (tmp_path / "token").exists()
    assert len(RunCatalog(tmp_path / "runs").attempts()) == 1
    assert not any(
        thread.name
        in {"living-world-http", "living-world-launch", "living-world-runtime"}
        for thread in __import__("threading").enumerate()
    )


@pytest.mark.parametrize("preset", [False, True])
def test_preowner_close_keeps_exactly_one_failed_identity(
    tmp_path, monkeypatch, capsys, preset
):
    import threading

    from living_world.runtime import entrypoints

    original = entrypoints.RuntimeService
    entered, release = threading.Event(), threading.Event()

    class Closed(original):
        def start(self, *values, **kwargs):
            entered.set()
            assert release.wait(3)
            return super().start(*values, **kwargs)

        def shutdown(self, **kwargs):
            super().shutdown(**kwargs)
            if threading.current_thread() is threading.main_thread():
                release.set()

    class Stop:
        def stop_requested(self):
            return entered.is_set()

    monkeypatch.setattr(entrypoints, "RuntimeService", Closed)
    extra = (
        ["--preset", "founders", "--driver", "ollama", "--model", "tiny"]
        if preset
        else []
    )
    assert main(args(tmp_path, *extra), stop_control=Stop()) == 0
    attempts = RunCatalog(tmp_path / "runs").attempts()
    assert len(attempts) == 1 and attempts[0].lifecycle == "failed"
    assert attempts[0].scenario != "uninitialized"
    assert capsys.readouterr().err.count("attempt=") == 1


def test_cleanup_failure_overrides_success(tmp_path, monkeypatch, capsys):
    from living_world.runtime import entrypoints

    original = entrypoints.RuntimeService

    class BrokenShutdown(original):
        def shutdown(self, **kwargs):
            super().shutdown(**kwargs)
            raise RuntimeError("PRIVATE cleanup")

    class Stop:
        def stop_requested(self):
            return True

    monkeypatch.setattr(entrypoints, "RuntimeService", BrokenShutdown)
    assert main(args(tmp_path), stop_control=Stop()) == 5
    assert capsys.readouterr().err == "error: service_failed\n"
    assert not (tmp_path / "token").exists()


@pytest.mark.parametrize(
    "serving_failure", [None, "control", "server", "server_cleanup"]
)
def test_final_mirror_failure_after_join_overrides_stop(
    tmp_path, monkeypatch, capsys, serving_failure
):
    import threading

    from living_world.runtime import entrypoints
    from living_world.runtime import service as service_module

    original_service = entrypoints.RuntimeService
    original_mirror = service_module.write_checkpoint_mirror
    launched = threading.Event()
    joined = threading.Event()
    calls = 0

    class Service(original_service):
        def start(self, *values, **kwargs):
            controller = super().start(*values, **kwargs)
            launched.set()
            return controller

        def shutdown(self, **kwargs):
            if threading.current_thread() is threading.main_thread():
                joined.set()
            super().shutdown(**kwargs)
            if (
                serving_failure == "server_cleanup"
                and threading.current_thread() is threading.main_thread()
            ):
                raise RuntimeError("PRIVATE cleanup failure")

    def mirror(*values, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_mirror(*values, **kwargs)
        assert joined.wait(3)
        raise OSError("PRIVATE final mirror")

    class Stop:
        def stop_requested(self):
            if serving_failure == "control" and launched.is_set():
                raise RuntimeError("PRIVATE control failure")
            return serving_failure is None and launched.is_set()

    if serving_failure in {"server", "server_cleanup"}:
        import uvicorn

        class ExitingServer:
            def __init__(self, _config):
                self.started = False
                self.should_exit = False

            def run(self, **_kwargs):
                self.started = True
                assert launched.wait(3)

        monkeypatch.setattr(uvicorn, "Server", ExitingServer)

    monkeypatch.setattr(entrypoints, "RuntimeService", Service)
    monkeypatch.setattr(service_module, "write_checkpoint_mirror", mirror)
    assert main(
        args(tmp_path, "--database", str(tmp_path / "mirror")), stop_control=Stop()
    ) == (5 if serving_failure else 4)
    captured = capsys.readouterr()
    expected_reason = {
        None: "mirror_failed",
        "control": "service_failed",
        "server": "server_failed",
        "server_cleanup": "service_failed",
    }[serving_failure]
    assert f"error: {expected_reason}\n" in captured.err
    assert captured.err.count("error:") == 1 and "PRIVATE" not in captured.err
    assert RunCatalog(tmp_path / "runs").attempts()[0].failure_code == "mirror_failed"


def test_public_cli_chrome_login_control_fixed_history_and_disconnect(tmp_path):
    sync = pytest.importorskip("playwright.sync_api")
    executable = os.environ.get(
        "LIVING_WORLD_BROWSER_EXECUTABLE", "/usr/bin/google-chrome"
    )
    if not Path(executable).is_file():
        pytest.skip("Chrome absent")
    with child(tmp_path) as (process, base):
        token = (tmp_path / "token").read_text().strip()
        catalog = RunCatalog(tmp_path / "runs")
        wait_until(
            lambda: catalog.attempts()
            and catalog.attempts()[0].last_revision is not None
        )
        ref = catalog.attempts()[0].ref
        with sync.sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=executable, headless=True)
            try:
                page = browser.new_page()
                observed = []
                page.on("request", lambda req: observed.append((req.method, req.url)))
                page.goto(base + "/runtime")
                page.get_by_label("Administrator token").fill(token)
                page.get_by_role("button", name="Connect", exact=True).click()
                sync.expect(page.locator("#notice")).to_have_text("Connected.")
                sync.expect(page.locator("#live")).to_contain_text(
                    "Last committed tick: 0"
                )
                frame = page.frame_locator('iframe[title="World Inspector"]')
                sync.expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
                page.get_by_role("button", name="Step", exact=True).click()
                sync.expect(page.locator("#live")).to_contain_text(
                    "Last committed tick: 1"
                )
                page.get_by_role("button", name=ref.attempt_id, exact=True).click()
                sync.expect(page.locator("#controls")).to_be_hidden()
                page.get_by_label("Complete checkpoint").select_option("0")
                sync.expect(frame.locator("#tick")).to_have_text("Reported tick: 0")
                live, nonce = request(base, token, "/runtime/status")
                request(
                    base,
                    token,
                    "/runtime/commands",
                    {
                        "command_id": "outside-step",
                        "action": "step",
                        "expected_state_version": live["live"]["state_version"],
                    },
                    nonce,
                )
                wait_until(
                    lambda: request(base, token, "/runtime/status")[0]["live"]["tick"]
                    == 2
                )
                sync.expect(frame.locator("#tick")).to_have_text("Reported tick: 0")
                assert page.url == base + "/runtime"
                assert (
                    page.evaluate(
                        "JSON.stringify([localStorage,sessionStorage,document.cookie])"
                    )
                    == '[{},{},""]'
                )
                assert token not in page.content()
                page.get_by_role("button", name="Return to live", exact=True).click()
                sync.expect(frame.locator("#tick")).to_have_text("Reported tick: 2")
                page.get_by_role("button", name="Disconnect", exact=True).click()
                sync.expect(page.locator("#session")).to_be_hidden()
                sync.expect(page.locator("iframe")).to_have_count(0)
                assert page.get_by_label("Administrator token").input_value() == ""
                assert (
                    request(base, token, "/runtime/status")[0]["live"]["state"]
                    == "paused"
                )
                assert process.poll() is None
                assert len([url for method, url in observed if method == "POST"]) == 1
            finally:
                browser.close()


@pytest.mark.parametrize("change", ["mode", "hardlink", "symlink"])
def test_credential_cleanup_preserves_changed_identity_or_permissions(tmp_path, change):
    from living_world.runtime.serving import _Credential

    token = tmp_path / "token"
    owned = _Credential.open(token, [tmp_path / "runs"])
    owned.publish("secret")
    if change == "mode":
        token.chmod(0o640)
    elif change == "hardlink":
        os.link(token, tmp_path / "link")
    else:
        token.unlink()
        (tmp_path / "target").write_bytes(b"external")
        token.symlink_to(tmp_path / "target")
    owned.close()
    assert token.exists()
    if change == "symlink":
        assert token.is_symlink() and token.read_bytes() == b"external"


@pytest.mark.parametrize("otherwise_failed", [False, True])
def test_token_cleanup_failure_only_replaces_success(
    tmp_path, monkeypatch, capsys, otherwise_failed
):
    from living_world.runtime import serving

    original = serving._Credential.close

    def fail_close(credential):
        original(credential)
        raise serving.ServeCLIError(4, "credential_file_failed")

    class Stop:
        def stop_requested(self):
            if otherwise_failed:
                raise RuntimeError("PRIVATE")
            return True

    monkeypatch.setattr(serving._Credential, "close", fail_close)
    assert main(args(tmp_path), stop_control=Stop()) == (5 if otherwise_failed else 4)
    assert (
        capsys.readouterr().err
        == "error: "
        + ("service_failed" if otherwise_failed else "credential_file_failed")
        + "\n"
    )


@pytest.mark.parametrize(
    "stdout_tty,stderr_tty", [(True, False), (False, True), (False, False)]
)
def test_either_redirected_stream_requires_token_file(
    tmp_path, monkeypatch, stdout_tty, stderr_tty
):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: stdout_tty)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: stderr_tty)
    assert (
        main(
            [
                "serve",
                "--founders",
                "success",
                "--port",
                "0",
                "--archive-root",
                str(tmp_path / "runs"),
            ]
        )
        == 2
    )
    assert not (tmp_path / "runs").exists()


def test_interactive_token_is_stderr_only_and_tokenfile_suppresses_it(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)

    class Stop:
        def stop_requested(self):
            return True

    assert (
        main(
            [
                "serve",
                "--founders",
                "success",
                "--port",
                "0",
                "--archive-root",
                str(tmp_path / "runs"),
            ],
            stop_control=Stop(),
        )
        == 0
    )
    output = capsys.readouterr()
    assert (
        output.err.startswith("Admin token: ") and output.err.count("Admin token:") == 1
    )
    assert output.out == ""
    assert main(args(tmp_path), stop_control=Stop()) == 0
    assert "Admin token" not in capsys.readouterr().err
    assert not (tmp_path / "token").exists() and not (tmp_path / "runs").exists()


def test_finite_live_budget_remains_http_inspectable(tmp_path):
    from test_runtime_cli import provider

    with (
        provider() as (url, _calls, _entered),
        child(
            tmp_path,
            "--preset",
            "founders",
            "--driver",
            "ollama",
            "--model",
            "tiny",
            "--base-url",
            url,
            "--start-running",
            "--max-requests",
            "1",
        ) as (process, base),
    ):
        token = (tmp_path / "token").read_text().strip()

        def live():
            return request(base, token, "/runtime/status")[0]["live"]

        wait_until(lambda: live() and live()["state"] == "stopped")
        assert live()["tick"] == 0
        assert process.poll() is None
        assert request(base, token, "/archives")[0]


def test_partial_recorded_run_explicit_checkpoint_only(tmp_path):
    with child(
        tmp_path, "--start-running", "--max-ticks", "1", "--checkpoint-only"
    ) as (process, base):
        token = (tmp_path / "token").read_text().strip()

        def live():
            return request(base, token, "/runtime/status")[0]["live"]

        wait_until(lambda: live() and live()["state"] == "completed")
        assert live()["tick"] == 1 and process.poll() is None
        catalog = RunCatalog(tmp_path / "runs")
        ref = catalog.attempts()[0].ref
        with catalog.open_attempt(ref.attempt_id) as archive:
            assert archive.config.settings["finalize_proposals"] is False
            finished = [
                entry for entry in archive.entries() if entry.kind == "attempt_finished"
            ][-1]
            assert finished.payload["outcome"] is None
            checkpoint = archive.checkpoint()
        assert request(base, token, "/archives")[0]
    before = {p: p.read_bytes() for p in ref.directory.rglob("*") if p.is_file()}
    with child(tmp_path, "--resume-attempt", ref.attempt_id) as (_, base):
        token = (tmp_path / "token").read_text().strip()
        live = wait_until(lambda: request(base, token, "/runtime/status")[0]["live"])
        assert live["state"] == "paused" and live["tick"] == 1
        child_ref = next(
            item.ref for item in catalog.attempts() if item.parent is not None
        )
        with catalog.open_attempt(child_ref.attempt_id) as archive:
            assert archive.config.settings["finalize_proposals"] is False
            restored = archive.checkpoint(0)
            assert restored.snapshot == checkpoint.snapshot
            assert restored.driver_cursor == checkpoint.driver_cursor
            assert restored.feedback_cursor == checkpoint.feedback_cursor
    assert before == {
        p: p.read_bytes() for p in ref.directory.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize(
    "target",
    [
        ["--preset", "founders", "--driver", "ollama", "--model", "tiny"],
        ["--resume-attempt", "a" * 32],
        ["--fork-attempt", "a" * 32],
    ],
)
def test_checkpoint_only_rejected_for_nonfresh_recorded_target(tmp_path, target):
    with pytest.raises(SystemExit):
        main(args(tmp_path, *target, "--checkpoint-only"))
    assert not (tmp_path / "runs").exists() and not (tmp_path / "token").exists()


def test_parent_descriptor_close_failure_is_credential_error(tmp_path, monkeypatch):
    from living_world.runtime.serving import ServeCLIError, _Credential

    original = os.close
    count = 0

    def close(fd):
        nonlocal count
        original(fd)
        count += 1
        if count == 1:
            raise OSError("PRIVATE")

    monkeypatch.setattr(os, "close", close)
    with pytest.raises(ServeCLIError) as caught:
        _Credential.open(tmp_path / "token", [tmp_path / "runs"])
    assert (
        caught.value.exit_code == 4 and caught.value.reason == "credential_file_failed"
    )


@pytest.mark.parametrize("failure", ["start", "join"])
def test_thread_lifecycle_error_is_closed_and_cleans_credentials(
    tmp_path, monkeypatch, capsys, failure
):
    from living_world.runtime import serving

    original = serving.Thread

    class Broken(original):
        def start(self):
            if failure == "start":
                raise RuntimeError("PRIVATE thread startup")
            super().start()

        def join(self, timeout=None):
            super().join(timeout)
            if failure == "join":
                raise RuntimeError("PRIVATE thread join")

    class Stop:
        def stop_requested(self):
            return True

    monkeypatch.setattr(serving, "Thread", Broken)
    assert main(args(tmp_path), stop_control=Stop()) == 5
    assert capsys.readouterr().err == "error: service_failed\n"
    assert not (tmp_path / "token").exists() and not (tmp_path / "runs").exists()
