"""Owned loopback HTTP lifetime for inert saved-trace analysis."""

# Adapter failures must never expose credentials or filesystem diagnostics.
# ruff: noqa: BLE001

from __future__ import annotations

import argparse
import socket
import sys
import time
from concurrent.futures import Future
from threading import Thread

from living_world.api.auth import AdminSession
from living_world.api.local_admin import AdminTokenFile, ServeCLIError
from living_world.api.trace_analysis import create_analysis_app
from living_world.archives import RunCatalog
from living_world.running import StopControl


def run_analysis(arguments: argparse.Namespace, control: StopControl) -> int:
    """Serve only authenticated archive reads, until explicit operator stop."""
    credential: AdminTokenFile | None = None
    sock: socket.socket | None = None
    server_thread: Thread | None = None
    server = None
    server_result: Future[None] = Future()
    outcome: ServeCLIError | None = None
    stopping = False

    def stopped() -> bool:
        try:
            return control.stop_requested()
        except Exception:
            raise ServeCLIError(5, "service_failed") from None

    def server_failed() -> bool:
        return server_thread is not None and (
            server_result.done() or not server_thread.is_alive()
        )

    try:
        if arguments.admin_token_file is None and not (
            sys.stdout.isatty() and sys.stderr.isatty()
        ):
            raise ServeCLIError(2, "invalid_configuration")
        try:
            catalog = RunCatalog(arguments.archive_root or RunCatalog.default_root())
            # Catalog construction rejects traversal and symlink components without
            # initializing storage; an existing final node must be a directory.
            if catalog.root.exists() and not catalog.root.is_dir():
                raise ValueError()
        except Exception:
            raise ServeCLIError(2, "invalid_configuration") from None
        if arguments.admin_token_file is not None:
            credential = AdminTokenFile.open(arguments.admin_token_file, [catalog.root])
        try:
            import uvicorn
        except ImportError:
            raise ServeCLIError(2, "server_unavailable") from None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", arguments.port))
            sock.listen()
        except OSError:
            raise ServeCLIError(5, "server_failed") from None
        origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
        auth = AdminSession.issue(origin=origin)
        if credential is not None:
            credential.publish(auth.token)
        else:
            print(f"Admin token: {auth.token}", file=sys.stderr, flush=True)
        server = uvicorn.Server(
            uvicorn.Config(
                create_analysis_app(catalog, auth=auth),
                access_log=False,
                log_level="error",
                log_config={
                    "version": 1,
                    "disable_existing_loggers": False,
                    "handlers": {"quiet": {"class": "logging.NullHandler"}},
                    "loggers": {
                        "uvicorn": {"handlers": ["quiet"], "propagate": False},
                        "uvicorn.error": {"handlers": ["quiet"], "propagate": False},
                        "uvicorn.access": {"handlers": ["quiet"], "propagate": False},
                    },
                },
            )
        )

        def http() -> None:
            try:
                assert server is not None
                server.run(sockets=[sock])
                server_result.set_result(None)
            except BaseException:
                server_result.set_exception(ServeCLIError(5, "server_failed"))

        server_thread = Thread(
            target=http, name="living-world-analysis-http", daemon=False
        )
        server_thread.start()
        deadline = time.monotonic() + 5
        while not server.started:
            if stopped():
                stopping = True
                break
            if server_failed() or time.monotonic() >= deadline:
                raise ServeCLIError(5, "server_failed")
            time.sleep(0.01)
        if not stopping:
            if server_failed():
                raise ServeCLIError(5, "server_failed")
            if stopped():
                stopping = True
            else:
                print(f"analysis_url={origin}/analysis/status", flush=True)
                print(f"analysis_browser_url={origin}/analysis", flush=True)
        while not stopping:
            if stopped():
                stopping = True
                break
            if server_failed():
                raise ServeCLIError(5, "server_failed")
            time.sleep(0.01)
    except ServeCLIError as error:
        outcome = error
    except Exception:
        outcome = ServeCLIError(5, "service_failed")
    finally:
        cleanup_failed = False
        if server is not None:
            try:
                server.should_exit = True
            except Exception:
                cleanup_failed = True
        if server_thread is not None:
            try:
                server_thread.join(timeout=12)
                cleanup_failed = server_thread.is_alive() or cleanup_failed
            except Exception:
                cleanup_failed = True
            if (
                server_result.done()
                and server_result.exception() is not None
                and outcome is None
            ):
                outcome = ServeCLIError(5, "server_failed")
        if sock is not None:
            try:
                sock.close()
            except Exception:
                cleanup_failed = True
        if credential is not None:
            try:
                credential.close()
            except Exception:
                if outcome is None and not cleanup_failed:
                    outcome = ServeCLIError(4, "credential_file_failed")
        if cleanup_failed and outcome is None:
            outcome = ServeCLIError(5, "service_failed")
    if outcome is not None:
        raise outcome from None
    return 0
