"""One owner thread, FIFO command admission and bounded runtime cleanup."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from contextlib import suppress
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread, current_thread

from living_world.archives import (
    AttemptConfig,
    AttemptRef,
    CommandEnvelope,
    CommandReceipt,
    JournalEntry,
    RetainedInputs,
    RunCatalog,
    write_checkpoint_mirror,
)
from living_world.archives.model import identifier, integer

from .broker import ERROR_CODES
from .contracts import RuntimeState
from .controller import CommandConflictError, RunController
from .launch import RuntimeStartupError, _Launch, _LaunchFactory

_FAILURE_CODES = ERROR_CODES | {"mirror_failed", "service_failed"}


def _poll(controller: RunController) -> None:
    status = controller.poll()
    if (
        status.state is RuntimeState.PROVIDER_ERROR_PAUSED
        and status.error_code == "request_budget_exhausted"
    ):
        controller.stop_for_budget()


def _loop(
    controller: RunController,
    stop_event: Event,
    *,
    wake: Event,
    pump: Callable[[], None],
    after_poll: Callable[[], None],
) -> None:
    while not stop_event.is_set():
        wake.clear()
        pump()
        if stop_event.is_set():
            break
        _poll(controller)
        after_poll()
        status = controller.status()
        idle = status.state.terminal or status.state in (
            RuntimeState.PAUSED,
            RuntimeState.PROVIDER_ERROR_PAUSED,
        )
        wake.wait(0.05 if idle else 0.02)


def run_owner_loop(controller: RunController, *, stop_event: Event) -> None:
    """Run the same bounded poll loop in an already owning application thread."""
    if not isinstance(controller, RunController) or not isinstance(stop_event, Event):
        raise TypeError("Expected controller and stop event.")
    try:
        _loop(
            controller,
            stop_event,
            wake=Event(),
            pump=lambda: None,
            after_poll=lambda: None,
        )
    finally:
        controller.close()


class RuntimeService:
    def __init__(
        self,
        catalog: RunCatalog,
        *,
        on_reserved: Callable[[AttemptRef], None] | None = None,
        mirror_path: Path | None = None,
        save_every: int = 1,
    ) -> None:
        if not isinstance(catalog, RunCatalog) or (
            on_reserved is not None and not callable(on_reserved)
        ):
            raise TypeError("Expected catalog and optional callback.")
        if mirror_path is not None and not isinstance(mirror_path, Path):
            raise TypeError("Expected optional mirror path.")
        integer(save_every, minimum=1)
        self._catalog, self._on_reserved = catalog, on_reserved
        self._mirror_path, self._save_every = mirror_path, save_every
        self._lock = Lock()
        self._stop, self._wake = Event(), Event()
        self._commands: Queue[tuple[CommandEnvelope, Future[CommandReceipt]]] = Queue()
        self._thread: Thread | None = None
        self._claimed = self._closed = False
        self._controller: RunController | None = None
        self._ref: AttemptRef | None = None
        self._failure_code: str | None = None

    @property
    def catalog(self) -> RunCatalog:
        return self._catalog

    @property
    def controller(self) -> RunController | None:
        """Return the current publication association without acquiring ownership."""
        with self._lock:
            return self._controller

    def _launch(
        self, mode: str, args: tuple[object, ...], paused: bool
    ) -> RunController:
        if type(paused) is not bool:
            raise TypeError("paused must be boolean.")
        startup: Future[RunController] = Future()
        with self._lock:
            if self._closed or self._claimed:
                raise RuntimeStartupError(self._ref, "service_closed")
            self._claimed = True
            self._thread = Thread(
                target=self._owner,
                args=(mode, args, paused, startup),
                name="living-world-runtime",
                daemon=False,
            )
            self._thread.start()
        return startup.result()

    def start(
        self, config: AttemptConfig, inputs: RetainedInputs, *, paused: bool
    ) -> RunController:
        if not isinstance(config, AttemptConfig) or not isinstance(
            inputs, RetainedInputs
        ):
            raise TypeError("Expected configuration and retained inputs.")
        return self._launch("start", (config, inputs), paused)

    @staticmethod
    def _source(attempt_id: str, revision: int | None) -> None:
        identifier(attempt_id)
        if revision is not None:
            integer(revision)

    def resume(
        self, attempt_id: str, revision: int | None = None, *, paused: bool
    ) -> RunController:
        self._source(attempt_id, revision)
        return self._launch("resume", (attempt_id, revision), paused)

    def fork(
        self,
        attempt_id: str,
        revision: int | None = None,
        *,
        config: AttemptConfig,
        paused: bool,
    ) -> RunController:
        self._source(attempt_id, revision)
        if not isinstance(config, AttemptConfig):
            raise TypeError("Expected configuration.")
        return self._launch("fork", (attempt_id, revision, config), paused)

    def replay(
        self, attempt_id: str, revision: int | None = None, *, paused: bool
    ) -> RunController:
        self._source(attempt_id, revision)
        return self._launch("replay", (attempt_id, revision), paused)

    def submit(self, command: CommandEnvelope) -> Future[CommandReceipt]:
        if not isinstance(command, CommandEnvelope):
            raise TypeError("Expected command envelope.")
        future: Future[CommandReceipt] = Future()
        with self._lock:
            code = (
                "service_closed"
                if self._closed or self._stop.is_set()
                else "service_not_ready" if self._controller is None else None
            )
            if code is not None:
                future.set_exception(RuntimeStartupError(self._ref, code))
            else:
                self._commands.put((command, future))
                self._wake.set()
        return future

    def _pump(self, controller: RunController | None) -> None:
        while True:
            try:
                command, future = self._commands.get_nowait()
            except Empty:
                return
            if not future.set_running_or_notify_cancel():
                continue
            try:
                if controller is None:
                    raise RuntimeStartupError(self._ref, "service_closed")
                receipt = controller.submit(command)
            except (CommandConflictError, RuntimeStartupError) as error:
                future.set_exception(error)
            except BaseException:  # noqa: BLE001 - settle Future before failing owner
                failure = RuntimeStartupError(self._ref, "service_failed")
                future.set_exception(failure)
                raise failure from None
            else:
                future.set_result(receipt)

    def _owner(
        self,
        mode: str,
        args: tuple[object, ...],
        paused: bool,
        startup: Future[RunController],
    ) -> None:
        bundle: _Launch | None = None
        controller: RunController | None = None
        error: RuntimeStartupError | None = None
        mirror_checkpoint: Callable[[], None] | None = None

        def reserved(ref: AttemptRef) -> None:
            self._ref = ref
            if self._on_reserved is not None:
                self._on_reserved(ref)

        factory = _LaunchFactory(self._catalog, self._stop, reserved)
        try:
            # The public entry points validate their arguments before ownership starts.
            if mode == "start":
                bundle = factory.start(*args)  # type: ignore[arg-type]
            elif mode == "resume":
                bundle = factory.resume(*args)  # type: ignore[arg-type]
            elif mode == "fork":
                bundle = factory.fork(*args)  # type: ignore[arg-type]
            else:
                bundle = factory.replay(*args)  # type: ignore[arg-type]
            self._ref = bundle.ref
            controller = RunController(
                bundle.archive,
                bundle.composition,
                bundle.driver,
                max_ticks=bundle.max_ticks,
                start_paused=paused,
                initial_stop_precedes_terminal=bundle.archive.config.mode == "recorded",
            )
            initial_tick = controller.status().tick
            last_mirror: tuple[int | None, bool] | None = None
            mirror_failed = False

            def mirror() -> None:
                nonlocal initial_tick, last_mirror, mirror_failed
                if self._mirror_path is None or mirror_failed:
                    return
                status = controller.status()
                if status.revision is None or status.tick is None:
                    return
                if initial_tick is None:
                    initial_tick = status.tick
                boundary = status.tick, status.state.terminal
                if boundary == last_mirror:
                    return
                if (
                    last_mirror is None
                    or status.state.terminal
                    or (status.tick - initial_tick) % self._save_every == 0
                ):
                    try:
                        write_checkpoint_mirror(
                            controller.published(),
                            self._mirror_path,
                            attempt=bundle.ref,
                        )
                    except BaseException:  # noqa: BLE001
                        mirror_failed = True
                        controller.fail_service("mirror_failed")
                        raise RuntimeStartupError(bundle.ref, "mirror_failed") from None
                    last_mirror = boundary

            mirror_checkpoint = mirror
            if self._stop.is_set():
                controller.submit(
                    CommandEnvelope(
                        "service-initial-stop",
                        "stop",
                        controller.status().state_version,
                    )
                )
                raise RuntimeStartupError(bundle.ref, "cancelled")
            _poll(controller)
            if controller.status().state is RuntimeState.FAILED:
                raise RuntimeStartupError(
                    bundle.ref,
                    controller.status().error_code or "initialization_failed",
                )
            mirror()
            with self._lock:
                if self._stop.is_set():
                    raise RuntimeStartupError(bundle.ref, "cancelled")
                self._controller = controller
            startup.set_result(controller)
            _loop(
                controller,
                self._stop,
                wake=self._wake,
                pump=lambda: self._pump(controller),
                after_poll=mirror,
            )
            self._pump(controller)
            if (
                self._failure_code is not None
                and not controller.status().state.terminal
            ):
                controller.fail_service(self._failure_code)
        except BaseException as failure:  # noqa: BLE001 - no exception may escape owner
            self._ref = factory.ref
            error = (
                failure
                if isinstance(failure, RuntimeStartupError)
                else RuntimeStartupError(
                    self._ref, "cancelled" if self._stop.is_set() else "service_failed"
                )
            )
            if controller is None and bundle is not None:
                with suppress(BaseException):
                    bundle.archive.record(
                        (
                            JournalEntry(
                                "attempt_finished",
                                {
                                    "lifecycle": "failed",
                                    "outcome": error.code,
                                    "last_revision": bundle.archive.latest_revision,
                                },
                            ),
                        )
                    )
            if controller is not None:
                with suppress(BaseException):
                    if (
                        error.code != "cancelled"
                        and not controller.status().state.terminal
                    ):
                        controller.fail_service("service_failed")
        finally:
            with self._lock:
                self._closed = True
            self._pump(None)
            if controller is not None:
                try:
                    controller.settle_shutdown()
                    if mirror_checkpoint is not None:
                        mirror_checkpoint()
                except RuntimeStartupError as final_failure:
                    if final_failure.code == "mirror_failed" or error is None:
                        error = final_failure
                except BaseException:  # noqa: BLE001
                    error = RuntimeStartupError(self._ref, "service_failed")
                    with suppress(BaseException):
                        controller.fail_service("service_failed")
                finally:
                    with suppress(BaseException):
                        controller.close()
            if bundle is not None:
                with suppress(BaseException):
                    bundle.close()
            if not startup.done():
                startup.set_exception(
                    error or RuntimeStartupError(self._ref, "service_failed")
                )

    def shutdown(self, *, failure_code: str | None = None) -> None:
        if failure_code is not None and failure_code not in _FAILURE_CODES:
            raise ValueError("Unknown service failure code.")
        with self._lock:
            if failure_code is not None and self._failure_code is None:
                self._failure_code = failure_code
            self._closed = True
            self._stop.set()
            self._wake.set()
            thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join(timeout=5)
            if thread.is_alive():
                raise RuntimeStartupError(self._ref, "service_failed")
