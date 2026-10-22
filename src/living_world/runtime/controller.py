"""Single owner controller: mutate detached candidates, publish only complete commits."""

from __future__ import annotations

from collections import deque
from contextlib import suppress
from dataclasses import asdict
from threading import get_ident
from typing import Literal

from living_world.archives import (
    AttemptArchive,
    Checkpoint,
    CommandEnvelope,
    CommandReceipt,
    JournalEntry,
)
from living_world.archives.model import canonical, envelope, integer
from living_world.repositories.world_snapshot import decode_world, encode_world
from living_world.simulation.simulation_engine import SimulationEngine

from .broker import ERROR_CODES
from .contracts import (
    DriverCommit,
    RuntimeState,
    RuntimeStatus,
    ScenarioComposition,
    TickDriver,
    TickPreparation,
)
from .publication import Publication


class CommandConflictError(ValueError):
    """An immutable command identity was reused with a different envelope."""


class RunController:
    def __init__(
        self,
        archive: AttemptArchive,
        composition: ScenarioComposition,
        driver: TickDriver,
        *,
        max_ticks: int | None,
        start_paused: bool,
        initial_stop_precedes_terminal: bool = False,
    ) -> None:
        if (
            not isinstance(archive, AttemptArchive)
            or archive._read_only
            or archive._closed
            or archive._owner != get_ident()
        ):
            raise ValueError("Controller requires a current-owner writable archive.")
        if max_ticks is not None:
            integer(max_ticks)
        if type(start_paused) is not bool:
            raise TypeError("start_paused must be boolean.")
        if any(
            not callable(getattr(composition, name, None))
            for name in ("initialize", "restore", "terminal_condition", "finalize")
        ) or any(
            not callable(getattr(driver, name, None))
            for name in ("initialize", "prepare")
        ):
            raise TypeError("Invalid controller composition or driver.")
        if type(initial_stop_precedes_terminal) is not bool:
            raise TypeError("initial_stop_precedes_terminal must be boolean.")
        self._initial_stop_precedes_terminal = initial_stop_precedes_terminal
        self._owner = get_ident()
        self._archive, self._composition, self._driver = archive, composition, driver
        self._max_ticks, self._start_paused = max_ticks, start_paused
        self._state, self._version = RuntimeState.INITIALIZING, 0
        self._checkpoint: Checkpoint | None = None
        self._initial_tick: int | None = None
        self._queue: deque[CommandEnvelope] = deque()
        self._initial_controls: list[CommandEnvelope] = []
        self._pause_controls: list[CommandEnvelope] = []
        self._step: CommandEnvelope | None = None
        self._intent = "paused" if start_paused else "running"
        self._candidate: SimulationEngine | None = None
        self._preparation: TickPreparation | None = None
        self._active_control: CommandEnvelope | None = None
        self._closed = False
        self._publication = Publication(
            RuntimeStatus(archive.ref, self._state, 0, None, None, None, None)
        )

    def _check_owner(self) -> None:
        if self._owner != get_ident():
            raise RuntimeError("Controller operation requires its owner thread.")
        if self._closed:
            raise RuntimeError("Controller is closed.")

    def status(self) -> RuntimeStatus:
        return self._publication.status()

    def published(self, revision: int | None = None) -> Checkpoint:
        return self._publication.checkpoint(revision)

    def _publish(
        self,
        state: RuntimeState,
        *,
        checkpoint: Checkpoint | None = None,
        activity: str | None = None,
        error: str | None = None,
        advance: bool = True,
    ) -> None:
        if advance:
            self._version += 1
        if checkpoint is not None:
            self._checkpoint = checkpoint
        self._state = state
        current = self._checkpoint
        self._publication.update(
            RuntimeStatus(
                self._archive.ref,
                state,
                self._version,
                None if current is None else current.revision,
                None if current is None else decode_world(current.snapshot).tick,
                activity,
                error,
            ),
            checkpoint,
        )

    def _revision(self) -> int:
        return 0 if self._checkpoint is None else self._checkpoint.revision

    def _result(
        self,
        command: CommandEnvelope,
        status: Literal["applied", "rejected"] = "applied",
        reason: str | None = None,
        *,
        version: int | None = None,
        revision: int | None = None,
    ) -> JournalEntry:
        result = CommandReceipt(
            command.command_id,
            status,
            self._version if version is None else version,
            self._revision() if revision is None else revision,
            reason,
        )
        return JournalEntry("control_resolved", {"receipt": asdict(result)})

    def _allowed(self, action: str) -> str | None:
        if self._state.terminal:
            return "terminal_attempt"
        if self._state is RuntimeState.PROVIDER_ERROR_PAUSED and action in (
            "resume",
            "step",
        ):
            return "provider_retry_required"
        allowed = {
            RuntimeState.INITIALIZING: ("pause", "stop"),
            RuntimeState.PAUSED: ("resume", "step", "stop"),
            RuntimeState.RUNNING: ("pause", "stop"),
            RuntimeState.AWAITING_MODEL: ("pause", "stop"),
            RuntimeState.STEPPING: ("pause",),
            RuntimeState.PROVIDER_ERROR_PAUSED: ("retry", "stop"),
        }
        return None if action in allowed.get(self._state, ()) else "lifecycle_conflict"

    def submit(self, command: CommandEnvelope) -> CommandReceipt:
        self._check_owner()
        if not isinstance(command, CommandEnvelope):
            raise TypeError("Expected command envelope.")
        CommandEnvelope(**asdict(command))
        previous = self._archive.command(command.command_id)
        if previous is not None:
            original = next(
                e.payload["envelope"]
                for e in self._archive.entries()
                if e.kind == "control_requested"
                and e.payload["envelope"]["command_id"] == command.command_id
            )
            if canonical(original) != canonical(asdict(command)):
                raise CommandConflictError("Command identity has a different envelope.")
            return previous
        requested = JournalEntry(
            "control_requested",
            {"envelope": asdict(command), "admitted_state_version": self._version},
        )
        reason = (
            "stale_state_version"
            if command.expected_state_version != self._version
            else self._allowed(command.action)
        )
        entries = (
            (requested,)
            if reason is None
            else (requested, self._result(command, "rejected", reason))
        )
        self._archive.record(entries)
        if reason is None:
            self._queue.append(command)
        result = self._archive.command(command.command_id)
        assert result is not None
        return result

    def _transition(
        self, state: RuntimeState, entries: tuple[JournalEntry, ...] = ()
    ) -> None:
        self._archive.record(entries, lifecycle=state.value)
        self._publish(state)

    def _discard(self) -> None:
        preparation, self._preparation = self._preparation, None
        self._candidate = None
        if preparation is not None:
            preparation.close()

    def _finished(
        self, state: RuntimeState, revision: int | None, outcome: str | None = None
    ) -> JournalEntry:
        return JournalEntry(
            "attempt_finished",
            {"lifecycle": state.value, "outcome": outcome, "last_revision": revision},
        )

    def _fail(self, code: str, *, committed: Checkpoint | None = None) -> None:
        # Best effort cleanup must never conceal an already committed checkpoint.
        try:
            self._discard()
        except Exception:  # noqa: BLE001, S110
            pass
        if committed is not None:
            self._checkpoint = committed
        pending = (
            list(self._initial_controls)
            + list(self._pause_controls)
            + list(self._queue)
        )
        if self._step is not None:
            pending.append(self._step)
        if self._active_control is not None and self._active_control not in pending:
            pending.append(self._active_control)
        # Admission can durably write before an IO error prevents in-memory
        # queue insertion. Failure settlement also resolves that accepted row.
        with suppress(Exception):
            for entry in self._archive.entries():
                if entry.kind == "control_requested":
                    command = envelope(entry.payload["envelope"])
                    if command not in pending:
                        pending.append(command)
        entries = []
        for command in pending:
            try:
                receipt = self._archive.command(command.command_id)
                if receipt is not None and receipt.status == "queued":
                    entries.append(
                        self._result(
                            command,
                            "rejected",
                            (
                                "initialization_failed"
                                if self._checkpoint is None
                                else code
                            ),
                            version=self._version + 1,
                        )
                    )
            except Exception:  # noqa: BLE001, S110
                pass
        entries.append(
            self._finished(
                RuntimeState.FAILED,
                None if self._checkpoint is None else self._checkpoint.revision,
                code,
            )
        )
        try:
            self._archive.record(tuple(entries))
        except Exception:  # noqa: BLE001, S110
            pass
        self._queue.clear()
        self._initial_controls.clear()
        self._pause_controls.clear()
        self._step = None
        self._publish(RuntimeState.FAILED, checkpoint=self._checkpoint, error=code)

    def _restore(self) -> SimulationEngine:
        assert self._checkpoint is not None
        candidate = self._composition.restore(self._checkpoint.snapshot)
        if encode_world(candidate.state) != encode_world(
            decode_world(self._checkpoint.snapshot)
        ):
            raise ValueError("Restoration changed the durable world.")
        return candidate

    def _initialize(self) -> None:
        history = self._archive.lifecycle()
        latest = self._archive.latest_revision
        if history and RuntimeState(history[-1]["state"]).terminal:
            self._checkpoint = None if latest is None else self._archive.checkpoint()
            terminal_state = RuntimeState(history[-1]["state"])
            entries = tuple(
                self._result(
                    c, "rejected", "terminal_attempt", version=self._version + 1
                )
                for c in self._initial_controls
            )
            if entries:
                self._archive.record(entries)
            self._initial_controls.clear()
            self._publish(
                terminal_state,
                checkpoint=self._checkpoint,
                error=(
                    history[-1]["reason"]
                    if terminal_state is RuntimeState.FAILED
                    else None
                ),
            )
            return
        if latest is None:
            candidate = self._composition.initialize()
            commit = self._driver.initialize(candidate, self._archive)
        else:
            self._checkpoint = self._archive.checkpoint()
            candidate = self._restore()
            commit = DriverCommit(
                self._checkpoint.driver_cursor, self._checkpoint.feedback_cursor, ()
            )
        self._initial_tick = candidate.state.tick
        stopped = any(c.action == "stop" for c in self._initial_controls)
        stop_first = stopped and self._initial_stop_precedes_terminal
        terminal = (
            None if stop_first else self._composition.terminal_condition(candidate)
        )
        done = not stop_first and (terminal is not None or self._max_ticks == 0)
        if done or stopped:
            self._composition.finalize(candidate, stopped=stopped and not done)
        target = (
            RuntimeState.COMPLETED
            if done
            else (
                RuntimeState.STOPPED
                if stopped
                else (
                    RuntimeState.PAUSED
                    if self._start_paused or self._initial_controls
                    else RuntimeState.RUNNING
                )
            )
        )
        checkpoint = self._checkpoint
        # A restored source remains byte-exact; only genuinely changed finalization
        # needs a new saved revision.
        if checkpoint is None or encode_world(candidate.state) != encode_world(
            decode_world(checkpoint.snapshot)
        ):
            checkpoint = self._archive.commit(
                encode_world(candidate.state),
                expected_revision=latest,
                driver_cursor=commit.driver_cursor,
                feedback_cursor=commit.feedback_cursor,
                entries=commit.journal_entries,
            )
        assert checkpoint is not None
        self._checkpoint = checkpoint
        entries = tuple(
            self._result(c, version=self._version + 1) for c in self._initial_controls
        )
        if target.terminal:
            entries += (self._finished(target, checkpoint.revision, terminal),)
        try:
            self._archive.record(
                entries, lifecycle=None if target.terminal else target.value
            )
        except Exception:  # noqa: BLE001
            self._fail("audit_failed", committed=checkpoint)
            return
        self._initial_controls.clear()
        self._publish(target, checkpoint=checkpoint)

    def _dispatch(self, command: CommandEnvelope) -> None:
        reason = (
            "stale_state_version"
            if command.expected_state_version != self._version
            else self._allowed(command.action)
        )
        if reason is not None:
            self._archive.record((self._result(command, "rejected", reason),))
            return
        if self._state is RuntimeState.INITIALIZING:
            self._initial_controls.append(command)
            # Latch controls, acknowledging only once a complete boundary exists.
            self._publish(RuntimeState.INITIALIZING)
            return
        action = command.action
        if action in ("step", "resume"):
            self._intent = "step" if action == "step" else "running"
            if action == "step":
                self._step = command
                self._transition(RuntimeState.STEPPING)
            else:
                self._transition(
                    RuntimeState.RUNNING,
                    (self._result(command, version=self._version + 1),),
                )
        elif action == "retry":
            target = (
                RuntimeState.STEPPING
                if self._intent == "step"
                else RuntimeState.RUNNING
            )
            self._transition(
                target, (self._result(command, version=self._version + 1),)
            )
        elif action == "pause":
            self._intent = "paused"
            self._pause_controls.append(command)
            self._transition(RuntimeState.PAUSE_REQUESTED)
            if self._preparation is not None:
                self._preparation.request_pause()
            else:
                self._paused()
        elif action == "stop":
            self._stop(command)

    def _paused(self, *, error: str | None = None) -> None:
        entries = tuple(
            self._result(c, version=self._version + 1) for c in self._pause_controls
        )
        if self._step is not None:
            entries += (
                self._result(
                    self._step, "rejected", "operator_paused", version=self._version + 1
                ),
            )
        target = RuntimeState.PROVIDER_ERROR_PAUSED if error else RuntimeState.PAUSED
        self._archive.record(entries, lifecycle=target.value, reason=error)
        self._step = None
        self._pause_controls.clear()
        self._discard()
        self._publish(target, error=error)

    def _stop(
        self, command: CommandEnvelope | None = None, *, reason: str | None = None
    ) -> None:
        self._discard()
        if self._checkpoint is None:
            raise RuntimeError("Stop requires an initialized boundary.")
        candidate = self._restore()
        self._composition.finalize(candidate, stopped=True)
        entries = (
            ()
            if command is None
            else (
                self._result(
                    command,
                    version=self._version + 1,
                    revision=self._checkpoint.revision + 1,
                ),
            )
        )
        if self._step is not None:
            entries += (
                self._result(
                    self._step,
                    "rejected",
                    "operator_stopped",
                    version=self._version + 1,
                    revision=self._checkpoint.revision + 1,
                ),
            )
        entries += tuple(
            self._result(
                c,
                "rejected",
                "operator_stopped",
                version=self._version + 1,
                revision=self._checkpoint.revision + 1,
            )
            for c in self._pause_controls
        )
        entries += (
            self._finished(RuntimeState.STOPPED, self._checkpoint.revision + 1, reason),
        )
        checkpoint = self._archive.commit(
            encode_world(candidate.state),
            expected_revision=self._checkpoint.revision,
            driver_cursor=self._checkpoint.driver_cursor,
            feedback_cursor=self._checkpoint.feedback_cursor,
            entries=entries,
        )
        self._step = None
        self._pause_controls.clear()
        try:
            self._archive.record(
                (), lifecycle=RuntimeState.STOPPED.value, reason=reason
            )
            self._publish(RuntimeState.STOPPED, checkpoint=checkpoint)
        except Exception:  # noqa: BLE001
            self._fail("audit_failed", committed=checkpoint)

    def stop_for_budget(self) -> None:
        self._check_owner()
        if (
            self._state is not RuntimeState.PROVIDER_ERROR_PAUSED
            or self.status().error_code != "request_budget_exhausted"
        ):
            raise ValueError("Request budget stop requires exhausted provider state.")
        self._stop(reason="request_budget_exhausted")

    def fail_service(self, code: str) -> None:
        self._check_owner()
        if code not in ERROR_CODES | {"mirror_failed", "service_failed"}:
            raise ValueError("Unknown service failure code.")
        self._fail(code)

    def _advance(self) -> None:
        assert self._checkpoint is not None
        if self._preparation is None:
            self._candidate = self._restore()
            self._preparation = self._driver.prepare(
                self._candidate, self._checkpoint, self._archive
            )
        preparation = self._preparation
        result = preparation.poll()
        if result == "waiting":
            target = (
                RuntimeState.PAUSE_REQUESTED
                if self._state is RuntimeState.PAUSE_REQUESTED
                else RuntimeState.AWAITING_MODEL
            )
            if target != self._state:
                self._transition(target)
            self._publish(target, activity=preparation.activity, advance=False)
            return
        if result == "provider_error":
            error = preparation.error_code or "provider_error"
            if self._intent == "paused":
                self._paused(error=error)
            else:
                self._discard()
                self._archive.record(
                    (), lifecycle=RuntimeState.PROVIDER_ERROR_PAUSED.value, reason=error
                )
                self._publish(RuntimeState.PROVIDER_ERROR_PAUSED, error=error)
            return
        if result not in ("ready", "paused"):
            raise ValueError("Invalid preparation status.")
        if self._intent == "paused" or result == "paused":
            self._paused()
            return
        candidate = self._candidate
        assert candidate is not None
        previous_tick = candidate.state.tick
        preparation.install()
        candidate.step()
        if candidate.state.tick != previous_tick + 1:
            raise ValueError("Candidate did not advance exactly one tick.")
        terminal = self._composition.terminal_condition(candidate)
        done = terminal is not None or (
            self._max_ticks is not None
            and candidate.state.tick - self._initial_tick >= self._max_ticks
        )
        if done:
            self._composition.finalize(candidate, stopped=False)
        commit = preparation.finish_tick()
        target = (
            RuntimeState.COMPLETED
            if done
            else RuntimeState.PAUSED if self._intent == "step" else RuntimeState.RUNNING
        )
        revision = self._checkpoint.revision + 1
        entries = commit.journal_entries
        if self._step is not None:
            entries += (
                self._result(self._step, version=self._version + 1, revision=revision),
            )
        if done:
            entries += (self._finished(target, revision, terminal),)
        checkpoint = self._archive.commit(
            encode_world(candidate.state),
            expected_revision=self._checkpoint.revision,
            driver_cursor=commit.driver_cursor,
            feedback_cursor=commit.feedback_cursor,
            entries=entries,
        )
        self._step = None
        try:
            self._discard()
            self._archive.record((), lifecycle=target.value)
            self._publish(target, checkpoint=checkpoint)
        except Exception:  # noqa: BLE001
            self._fail("audit_failed", committed=checkpoint)

    def poll(self) -> RuntimeStatus:
        self._check_owner()
        if self._state.terminal:
            return self.status()
        try:
            if self._queue:
                self._active_control = self._queue.popleft()
                self._dispatch(self._active_control)
                self._active_control = None
                if self._state.terminal or self._queue:
                    return self.status()
            if self._state is RuntimeState.INITIALIZING:
                self._initialize()
            elif self._state in (
                RuntimeState.RUNNING,
                RuntimeState.STEPPING,
                RuntimeState.AWAITING_MODEL,
                RuntimeState.PAUSE_REQUESTED,
            ):
                self._advance()
        except Exception:  # noqa: BLE001
            self._fail(
                "initialization_failed"
                if self._state is RuntimeState.INITIALIZING
                else "tick_failed"
            )
        return self.status()

    def settle_shutdown(self) -> None:
        """Settle pending controls and Stop while leaving the archive open."""
        self._check_owner()
        try:
            if not self._state.terminal:
                if self._checkpoint is None:
                    # Shutdown establishes the initial boundary without depending on
                    # ordinary poll's one-command dispatch budget or starting ticks.
                    try:
                        while self._queue:
                            self._active_control = self._queue.popleft()
                            self._dispatch(self._active_control)
                            self._active_control = None
                        self._initialize()
                    except Exception:  # noqa: BLE001
                        self._fail("initialization_failed")
                if not self._state.terminal:
                    self._stop()
            for command in self._queue:
                self._archive.record(
                    (self._result(command, "rejected", "operator_stopped"),)
                )
            self._queue.clear()
            self._discard()
        except Exception:  # noqa: BLE001
            self._fail("shutdown_failed")

    def close(self) -> None:
        if self._owner != get_ident():
            raise RuntimeError("Controller operation requires its owner thread.")
        if self._closed:
            return
        try:
            self.settle_shutdown()
        finally:
            self._archive.close()
            self._closed = True
