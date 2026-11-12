"""Opt-in, bounded native-provider experiments using the ordinary runtime owner."""

from __future__ import annotations

import argparse
import json
import math
import signal
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from threading import Event, Lock, Thread
from typing import Literal
from uuid import uuid4

from living_world.archives import AttemptRef, CommandEnvelope, RunCatalog
from living_world.cli import SignalStopControl, build_parser
from living_world.repositories.world_snapshot import decode_world
from living_world.runtime.contracts import RuntimeState, RuntimeStatus
from living_world.runtime.controller import RunController
from living_world.runtime.entrypoints import (
    normalize_archived_failure,
    prepare_archived_launch,
    retain_failed_initialization,
    validate_archived_options,
)
from living_world.runtime.service import RuntimeService


@dataclass(frozen=True)
class ExperimentResult:
    attempt_id: str | None = None
    lineage_id: str | None = None
    start_tick: int | None = None
    end_tick: int | None = None
    start_revision: int | None = None
    end_revision: int | None = None
    steps_requested: int = 3
    steps_completed: int = 0
    state: str | None = None
    error_code: str | None = None
    exit_code: int = 0


def run_experiment(
    arguments: argparse.Namespace,
    *,
    disturbance: Literal["none", "resource_loss", "work_blockage"] | None = None,
    steps: int = 3,
    timeout_seconds: float = 600.0,
    stop_requested: Callable[[], bool] = lambda: False,
) -> ExperimentResult:
    """Commit at most ``steps`` ticks; deadlines include cooperative startup cleanup."""
    requested = steps if type(steps) is int else 0
    invalid = ExperimentResult(
        steps_requested=requested, exit_code=2, error_code="invalid_configuration"
    )
    try:
        if (
            type(steps) is not int
            or not 1 <= steps <= 20
            or type(timeout_seconds) not in (int, float)
            or not 0.05 <= timeout_seconds <= 3600
            or not math.isfinite(timeout_seconds)
            or not callable(stop_requested)
            or not isinstance(arguments, argparse.Namespace)
            or arguments.command != "run"
            or arguments.founders
            or disturbance not in (None, "none", "resource_loss", "work_blockage")
            or (arguments.replay_attempt and disturbance is not None)
        ):
            return invalid
        parser = build_parser()
        if not validate_archived_options(arguments, parser):
            return invalid
    except (AttributeError, TypeError, ValueError, SystemExit):
        return invalid

    ref: AttemptRef | None = None
    controller: RunController | None = None
    service: RuntimeService | None = None
    watcher: Thread | None = None
    initial: RuntimeStatus | None = None
    completed = 0
    failure: tuple[int, str] | None = None
    failure_lock = Lock()
    done = Event()
    deadline = time.monotonic() + timeout_seconds
    catalog: RunCatalog | None = None

    def fail(code: int, reason: str) -> None:
        nonlocal failure
        with failure_lock:
            if failure is None:
                failure = (code, reason)

    def announce(value: AttemptRef) -> None:
        nonlocal ref
        if ref is None:
            print(
                f"attempt={value.attempt_id} archive={value.directory.absolute()}",
                file=sys.stderr,
                flush=True,
            )
        ref = value

    def watch() -> None:
        while not done.wait(0.01):
            try:
                if stop_requested():
                    fail(130, "cancelled")
                elif time.monotonic() >= deadline:
                    fail(124, "experiment_deadline")
                else:
                    continue
            except BaseException:  # noqa: BLE001 - closed cleanup boundary
                fail(5, "service_failed")
            try:
                assert service is not None
                service.shutdown()
            except BaseException:  # noqa: BLE001 - closed cleanup boundary
                fail(5, "service_failed")
            return

    try:
        catalog = RunCatalog(arguments.archive_root or RunCatalog.default_root())
        prepared = prepare_archived_launch(
            arguments, catalog=catalog, on_reserved=announce, disturbance=disturbance
        )
        service = prepared.service
        watcher = Thread(
            target=watch, name="living-world-experiment-watch", daemon=False
        )
        watcher.start()
        controller = prepared.launch(paused=True)
        initial = controller.status()
        while completed < steps and failure is None:
            status = controller.status()
            if status.state.terminal:
                break
            if status.state is RuntimeState.PROVIDER_ERROR_PAUSED:
                if status.error_code == "request_budget_exhausted":
                    done.wait(0.01)
                    continue
                fail(6, status.error_code or "service_failed")
                break
            before = status.tick
            receipt = service.submit(
                CommandEnvelope(uuid4().hex, "step", status.state_version)
            ).result()
            if receipt.status == "rejected":
                fail(5, "service_failed")
                break
            while failure is None:
                status = controller.status()
                settled = status.state.terminal or status.state in (
                    RuntimeState.PAUSED,
                    RuntimeState.PROVIDER_ERROR_PAUSED,
                )
                if settled and status.error_code != "request_budget_exhausted":
                    if (
                        before is not None
                        and status.tick is not None
                        and status.tick > before
                    ):
                        completed += 1
                        break
                    if (
                        status.state.terminal
                        or status.state is RuntimeState.PROVIDER_ERROR_PAUSED
                    ):
                        break
                if status.state.terminal:
                    if (
                        before is not None
                        and status.tick is not None
                        and status.tick > before
                    ):
                        completed += 1
                    break
                done.wait(0.01)
        if controller.status().state is RuntimeState.FAILED:
            status = controller.status()
            fail(5, status.error_code or "service_failed")
    except KeyboardInterrupt:
        fail(130, "cancelled")
    except Exception as error:  # noqa: BLE001 - closed adapter failure boundary
        known = getattr(error, "ref", None)
        if known is not None:
            announce(known)
        normalized = normalize_archived_failure(error, ref)
        fail(normalized.exit_code, normalized.reason)
        if catalog is not None and ref is None and normalized.exit_code != 2:
            try:
                retain_failed_initialization(catalog, on_reserved=announce)
            except Exception:  # noqa: BLE001 - retain first closed failure
                fail(4, "archive_failed")
    finally:
        done.set()
        if service is not None:
            try:
                service.shutdown()
            except BaseException:  # noqa: BLE001 - closed cleanup boundary
                fail(5, "service_failed")
        if watcher is not None:
            watcher.join(6)
            if watcher.is_alive():
                fail(5, "service_failed")
    final = controller.status() if controller is not None else None
    if final is not None and final.state is RuntimeState.FAILED:
        fail(5, final.error_code or "service_failed")
    start_tick = initial.tick if initial else None
    end_tick = final.tick if final else None
    start_revision = initial.revision if initial else None
    end_revision = final.revision if final else None
    state = final.state.value if final else None
    if initial is None and ref is not None and catalog is not None:
        try:
            with catalog.open_attempt(ref.attempt_id) as archive:
                if archive.latest_revision is not None:
                    first, last = archive.checkpoint(0), archive.checkpoint()
                    start_tick, end_tick = (
                        decode_world(first.snapshot).tick,
                        decode_world(last.snapshot).tick,
                    )
                    start_revision, end_revision = first.revision, last.revision
                    lifecycle = archive.lifecycle()
                    if lifecycle:
                        state = str(lifecycle[-1]["state"])
        except Exception:  # noqa: BLE001 - preserve the original launch failure
            fail(4, "archive_failed")
    return ExperimentResult(
        attempt_id=ref.attempt_id if ref else None,
        lineage_id=ref.lineage_id if ref else None,
        start_tick=start_tick,
        end_tick=end_tick,
        start_revision=start_revision,
        end_revision=end_revision,
        steps_requested=steps,
        steps_completed=completed,
        state=state,
        error_code=failure[1] if failure else (final.error_code if final else None),
        exit_code=failure[0] if failure else 0,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Parse helper options before a required literal -- and production run options."""
    tokens = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument(
        "--disturbance", choices=("none", "resource_loss", "work_blockage")
    )
    result = ExperimentResult(exit_code=2, error_code="invalid_configuration")
    try:
        separator = tokens.index("--") if "--" in tokens else len(tokens)
        options = parser.parse_args(tokens[:separator])
        if separator == len(tokens) or not tokens[separator + 1 :]:
            raise ValueError("Missing production options")
        arguments = build_parser().parse_args(["run", *tokens[separator + 1 :]])
        control = SignalStopControl()
        previous = {
            sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)
        }
        try:
            for sig in previous:
                signal.signal(sig, control.handle_signal)
            result = run_experiment(
                arguments,
                steps=options.steps,
                timeout_seconds=options.timeout_seconds,
                disturbance=options.disturbance,
                stop_requested=control.stop_requested,
            )
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    except SystemExit as error:
        if error.code == 0:
            return 0
    except ValueError:
        pass
    print(
        json.dumps(
            {"format": "living-world-native-experiment-v1", **asdict(result)},
            sort_keys=True,
        )
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
