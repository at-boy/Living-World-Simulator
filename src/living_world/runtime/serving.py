"""Local operator serving; runtime ownership remains entirely in RuntimeService."""

# Broad catches close adapter failures without exposing private diagnostics.
# ruff: noqa: BLE001

from __future__ import annotations

import argparse
import socket
import sys
import time
from concurrent.futures import Future
from threading import Thread

from living_world.api.auth import AdminSession
from living_world.api.local_admin import AdminTokenFile as _Credential
from living_world.api.local_admin import ServeCLIError
from living_world.api.operator import create_operator_app
from living_world.archives import ArchiveReservationError, AttemptRef, RunCatalog
from living_world.running import StopControl

from .contracts import RuntimeState
from .controller import RunController
from .entrypoints import (
    RuntimeCLIError,
    _exit,
    normalize_archived_failure,
    prepare_archived_launch,
    retain_failed_initialization,
)
from .launch import RuntimeStartupError
from .service import RuntimeService


def run_served(arguments: argparse.Namespace, control: StopControl) -> int:
    """Keep authenticated HTTP available independently of launch and world lifetime."""
    catalog = RunCatalog(arguments.archive_root or RunCatalog.default_root())
    credential: _Credential | None = None
    sock: socket.socket | None = None
    service: RuntimeService | None = None
    server_thread: Thread | None = None
    launch_thread: Thread | None = None
    server = None
    server_result: Future[None] = Future()
    launch_result: Future[RunController] = Future()
    outcome: RuntimeCLIError | ServeCLIError | None = None
    emitted: str | None = None
    ref: AttemptRef | None = None
    announced: set[str] = set()
    stopping = False

    def announce(value: AttemptRef) -> None:
        nonlocal ref
        ref = value
        if value.attempt_id not in announced:
            print(
                f"attempt={value.attempt_id} archive={value.directory.absolute()}",
                file=sys.stderr,
                flush=True,
            )
            announced.add(value.attempt_id)

    def launch_failure(error: Exception) -> RuntimeCLIError:
        if (
            isinstance(
                error, (RuntimeCLIError, RuntimeStartupError, ArchiveReservationError)
            )
            and error.ref is not None
        ):
            announce(error.ref)
        failure = normalize_archived_failure(error, ref)
        if ref is None:
            retain_failed_initialization(catalog, on_reserved=announce)
        return failure

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
        if arguments.admin_token_file is None:
            if not (sys.stdout.isatty() and sys.stderr.isatty()):
                raise ServeCLIError(2, "invalid_configuration")
        else:
            protected = [catalog.root]
            if arguments.database is not None:
                protected.append(arguments.database)
            credential = _Credential.open(arguments.admin_token_file, protected)
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
        try:
            prepared = prepare_archived_launch(
                arguments, catalog=catalog, on_reserved=announce
            )
        except Exception as error:
            raise launch_failure(error) from None
        service = prepared.service
        server = uvicorn.Server(
            uvicorn.Config(
                create_operator_app(service, None, auth=auth),
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

        server_thread = Thread(target=http, name="living-world-http", daemon=False)
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
            print(f"runtime_url={origin}/runtime", flush=True)
            if stopped():
                stopping = True
        if not stopping:

            def launch() -> None:
                try:
                    launch_result.set_result(
                        prepared.launch(paused=not arguments.start_running)
                    )
                except BaseException as error:
                    launch_result.set_exception(
                        error
                        if isinstance(error, Exception)
                        else RuntimeCLIError(5, "service_failed")
                    )

            launch_thread = Thread(
                target=launch, name="living-world-launch", daemon=False
            )
            launch_thread.start()
            handled = False
            while True:
                if stopped():
                    stopping = True
                    break
                if server_failed():
                    raise ServeCLIError(5, "server_failed")
                if launch_result.done() and not handled:
                    handled = True
                    try:
                        launch_result.result()
                    except Exception as error:
                        try:
                            outcome = launch_failure(error)
                        except RuntimeCLIError as failure:
                            outcome = failure
                        print(f"error: {outcome.reason}", file=sys.stderr, flush=True)
                        emitted = outcome.reason
                time.sleep(0.01)
    except (RuntimeCLIError, ServeCLIError) as error:
        outcome = error
    except Exception:
        outcome = ServeCLIError(5, "service_failed")
    finally:
        cleanup_failed = False
        if service is not None:
            try:
                service.shutdown()
            except Exception:
                cleanup_failed = True
        if server is not None:
            server.should_exit = True
        if server_thread is not None:
            try:
                server_thread.join(timeout=12)
                cleanup_failed = cleanup_failed or server_thread.is_alive()
            except Exception:
                cleanup_failed = True
            if (
                server_result.done()
                and server_result.exception() is not None
                and outcome is None
            ):
                outcome = ServeCLIError(5, "server_failed")
        if launch_thread is not None:
            try:
                launch_thread.join(timeout=6)
                cleanup_failed = cleanup_failed or launch_thread.is_alive()
            except Exception:
                cleanup_failed = True
            if launch_result.done():
                try:
                    launch_result.result()
                except Exception as error:
                    if not (
                        stopping
                        and isinstance(error, RuntimeStartupError)
                        and error.code in {"cancelled", "service_closed"}
                    ):
                        if outcome is None:
                            try:
                                outcome = launch_failure(error)
                            except RuntimeCLIError as failure:
                                outcome = failure
                    elif error.ref is not None:
                        announce(error.ref)
        if service is not None and service.controller is not None:
            try:
                status = service.controller.status()
                if status.state is RuntimeState.FAILED and not (
                    isinstance(outcome, ServeCLIError) and outcome.exit_code == 5
                ):
                    code = status.error_code or "service_failed"
                    outcome = RuntimeCLIError(_exit(code), code, ref)
            except Exception:
                cleanup_failed = True
        if cleanup_failed:
            outcome = ServeCLIError(5, "service_failed")
        if sock is not None:
            try:
                sock.close()
            except OSError:
                outcome = ServeCLIError(5, "service_failed")
        if credential is not None:
            try:
                credential.close()
            except ServeCLIError as error:
                if outcome is None:
                    outcome = error
    if outcome is not None:
        if emitted != outcome.reason:
            raise outcome from None
        return outcome.exit_code
    return 0
