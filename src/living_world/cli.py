from __future__ import annotations

import argparse
import signal
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from types import FrameType

from living_world.repositories.sqlite_repository import (
    RepositoryError,
    SQLiteRepository,
)
from living_world.running import (
    RunConfiguration,
    RunPersistenceError,
    RunSimulationError,
    ScenarioRunner,
    StopControl,
)
from living_world.scenarios import ScenarioCompatibilityError, ScenarioLoadError
from living_world.simulation.simulation_engine import SimulationEngine

INVALID_CONFIGURATION = 2
INCOMPATIBLE_SAVE = 3
PERSISTENCE_FAILURE = 4
SIMULATION_FAILURE = 5


class SignalStopControl:
    """Translate SIGINT into a cooperative stop request between ticks."""

    def __init__(self) -> None:
        self._requested = False

    def request_stop(self) -> None:
        self._requested = True

    def stop_requested(self) -> bool:
        return self._requested

    def handle_signal(self, _signum: int, _frame: FrameType | None) -> None:
        self.request_stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="living-world")
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run", help="Run or resume a world scenario.")
    run.add_argument("scenario", type=Path)
    run.add_argument("--database", type=Path, default=Path("world.sqlite3"))
    limits = run.add_mutually_exclusive_group()
    limits.add_argument("--max-ticks", type=_non_negative_integer)
    limits.add_argument("--continuous", action="store_true")
    run.add_argument("--save-every", type=_positive_integer, default=1)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stop_control: StopControl | None = None,
    engine_factory: Callable[[SQLiteRepository], SimulationEngine] = SimulationEngine,
) -> int:
    arguments = build_parser().parse_args(argv)
    control = stop_control or SignalStopControl()
    previous_handler: signal.Handlers | None = None
    if isinstance(control, SignalStopControl):
        previous_handler = signal.signal(signal.SIGINT, control.handle_signal)
    try:
        try:
            repository = SQLiteRepository(str(arguments.database))
            engine = engine_factory(repository)
            result = ScenarioRunner(engine).run(
                arguments.scenario,
                RunConfiguration(
                    max_ticks=arguments.max_ticks,
                    save_every=arguments.save_every,
                    continuous=arguments.continuous,
                ),
                stop_control=control,
            )
        except ScenarioCompatibilityError as exc:
            return _error(INCOMPATIBLE_SAVE, exc)
        except (ScenarioLoadError, TypeError, ValueError) as exc:
            return _error(INVALID_CONFIGURATION, exc)
        except (RepositoryError, RunPersistenceError) as exc:
            return _error(PERSISTENCE_FAILURE, exc)
        except RunSimulationError as exc:
            return _error(SIMULATION_FAILURE, exc)
        status = "resumed" if result.resumed else "new"
        reason = result.stop_reason.value
        if result.terminal_condition is not None:
            reason = f"{reason}:{result.terminal_condition}"
        print(
            f"scenario={result.scenario_key} status={status} "
            f"start_tick={result.start_tick} end_tick={result.end_tick} "
            f"stop_reason={reason}"
        )
        return 0
    finally:
        if previous_handler is not None:
            signal.signal(signal.SIGINT, previous_handler)


def _non_negative_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _error(exit_code: int, error: Exception) -> int:
    print(f"error: {error}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
