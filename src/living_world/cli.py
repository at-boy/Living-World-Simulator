from __future__ import annotations

import argparse
import signal
import sys
from collections.abc import Callable, Sequence
from contextlib import ExitStack
from pathlib import Path
from types import FrameType

from living_world.founders import (
    FoundersConfigurationError,
    FoundersOutcome,
    FoundersPolicy,
    FoundersPreparation,
    founders_terminal_conditions,
    load_inspection_engine,
    materialize_founders_assets,
)
from living_world.replay.loader import YAMLProposalTapeLoader
from living_world.replay.model import ProposalTapeError
from living_world.replay.runtime import ReplayPreparation
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
from living_world.scenarios.scenario import YAMLScenarioLoader
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
    run.add_argument("scenario", type=Path, nargs="?")
    run.add_argument(
        "--founders", choices=[outcome.value for outcome in FoundersOutcome]
    )
    run.add_argument("--database", type=Path, default=Path("world.sqlite3"))
    limits = run.add_mutually_exclusive_group()
    limits.add_argument("--max-ticks", type=_non_negative_integer)
    limits.add_argument("--continuous", action="store_true")
    run.add_argument("--save-every", type=_positive_integer, default=1)
    run.add_argument("--proposal-tape", type=Path)
    run.add_argument("--checkpoint-only", action="store_true")
    inspect = subcommands.add_parser(
        "inspect", help="Serve an existing saved snapshot."
    )
    inspect.add_argument("scenario", type=Path, nargs="?")
    inspect.add_argument("--founders", action="store_true")
    inspect.add_argument("--database", type=Path, required=True)
    inspect.add_argument("--port", type=_port, default=8000)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stop_control: StopControl | None = None,
    engine_factory: Callable[[SQLiteRepository], SimulationEngine] = SimulationEngine,
) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if bool(arguments.scenario) == bool(arguments.founders):
        parser.error("Choose exactly one scenario path or --founders.")
    if arguments.command == "run" and arguments.founders and arguments.proposal_tape:
        parser.error("--founders and --proposal-tape cannot be combined.")
    control = stop_control or SignalStopControl()
    previous_handler: signal.Handlers | None = None
    if isinstance(control, SignalStopControl):
        previous_handler = signal.signal(signal.SIGINT, control.handle_signal)
    try:
        try:
            with ExitStack() as assets_lifetime:
                if arguments.founders:
                    assets = assets_lifetime.enter_context(
                        materialize_founders_assets()
                    )
                    arguments.scenario = assets.scenario
                    if arguments.command == "run":
                        arguments.proposal_tape = assets.tape_for(
                            FoundersOutcome(arguments.founders)
                        )
                        if (
                            arguments.founders == "stall"
                            and arguments.max_ticks is None
                            and not arguments.continuous
                        ):
                            arguments.max_ticks = 5
                if arguments.command == "inspect":
                    snapshot = load_inspection_engine(
                        arguments.scenario, arguments.database
                    )
                    _serve_inspection(snapshot, arguments.port)
                    return 0
                scenario = YAMLScenarioLoader().load(arguments.scenario)
                canonical = scenario.key == "canonical_founders_v1" or any(
                    "founders_policy" in item.attributes for item in scenario.entities
                )
                if canonical:
                    FoundersPolicy.from_scenario(scenario)
                    if arguments.proposal_tape is None:
                        raise FoundersConfigurationError("missing_tape")
                repository = SQLiteRepository(str(arguments.database))
                engine = engine_factory(repository)
                preparation = (
                    None
                    if arguments.proposal_tape is None
                    else (FoundersPreparation if canonical else ReplayPreparation)(
                        YAMLProposalTapeLoader().load(arguments.proposal_tape)
                    )
                )
                result = ScenarioRunner(
                    engine,
                    preparation,
                    terminal_conditions=(
                        founders_terminal_conditions() if canonical else None
                    ),
                ).run(
                    arguments.scenario,
                    RunConfiguration(
                        max_ticks=arguments.max_ticks,
                        save_every=arguments.save_every,
                        continuous=arguments.continuous,
                        finalize_proposals=not arguments.checkpoint_only,
                    ),
                    stop_control=control,
                )
        except FoundersConfigurationError as exc:
            return _error(
                (
                    INCOMPATIBLE_SAVE
                    if exc.code == "setup_mismatch"
                    else INVALID_CONFIGURATION
                ),
                exc,
            )
        except ProposalTapeError as exc:
            incompatible = {
                "scenario_mismatch",
                "actor_mismatch",
                "missing_replay_preparation",
                "replay_state_invalid",
            }
            return _error(
                (
                    INCOMPATIBLE_SAVE
                    if exc.code in incompatible
                    else INVALID_CONFIGURATION
                ),
                exc,
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
            + (
                ""
                if result.proposals_finalized is None
                else f" proposals_finalized={result.proposals_finalized}"
            )
        )
        return 0
    finally:
        if previous_handler is not None:
            signal.signal(signal.SIGINT, previous_handler)


def _serve_inspection(engine: SimulationEngine, port: int) -> None:
    try:
        import uvicorn
    except ImportError:
        raise ValueError(
            "Install living-world-simulator[server] to serve inspection."
        ) from None
    from living_world.api.server import create_app

    uvicorn.run(create_app(engine), host="127.0.0.1", port=port)


def _port(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 65535:
        raise argparse.ArgumentTypeError("must be between 1 and 65535")
    return parsed


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
