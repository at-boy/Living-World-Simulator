from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from living_world.scenarios.scenario import LoadedScenario, ScenarioLoadError
from living_world.simulation.simulation_engine import SimulationEngine


class StopReason(str, Enum):
    TICK_LIMIT = "tick_limit"
    TERMINAL_CONDITION = "terminal_condition"
    OPERATOR_STOP = "operator_stop"


@dataclass(frozen=True, slots=True)
class RunConfiguration:
    max_ticks: int | None = None
    save_every: int = 1
    continuous: bool = False

    def __post_init__(self) -> None:
        if self.max_ticks is not None and (
            not isinstance(self.max_ticks, int) or isinstance(self.max_ticks, bool)
        ):
            raise TypeError("max_ticks must be an integer or None.")
        if self.max_ticks is not None and self.max_ticks < 0:
            raise ValueError("max_ticks must be non-negative.")
        if not isinstance(self.save_every, int) or isinstance(self.save_every, bool):
            raise TypeError("save_every must be an integer.")
        if self.save_every <= 0:
            raise ValueError("save_every must be positive.")
        if not isinstance(self.continuous, bool):
            raise TypeError("continuous must be a boolean.")
        if self.continuous and self.max_ticks is not None:
            raise ValueError("continuous and max_ticks cannot be combined.")


@dataclass(frozen=True, slots=True)
class RunResult:
    scenario_key: str
    start_tick: int
    end_tick: int
    resumed: bool
    stop_reason: StopReason
    terminal_condition: str | None = None


class StopControl(Protocol):
    def stop_requested(self) -> bool: ...


class CheckpointControl(Protocol):
    def checkpoint_due(self, completed_ticks: int) -> bool: ...


@dataclass(frozen=True, slots=True)
class IntervalCheckpointControl:
    interval: int

    def __post_init__(self) -> None:
        if not isinstance(self.interval, int) or isinstance(self.interval, bool):
            raise TypeError("checkpoint interval must be an integer.")
        if self.interval <= 0:
            raise ValueError("checkpoint interval must be positive.")

    def checkpoint_due(self, completed_ticks: int) -> bool:
        return completed_ticks % self.interval == 0


class Runner(Protocol):
    def run(
        self,
        scenario_path: Path,
        configuration: RunConfiguration,
        *,
        stop_control: StopControl | None = None,
        checkpoint_control: CheckpointControl | None = None,
    ) -> RunResult: ...


class RunPersistenceError(RuntimeError):
    """Raised when a required run checkpoint cannot be persisted."""


class RunSimulationError(RuntimeError):
    """Raised when a simulation tick fails."""


class ScenarioRunner:
    """Run one loaded scenario with deterministic checkpoints and stop rules."""

    _SUPPORTED_TERMINAL_CONDITIONS = frozenset({"tick_limit", "operator_stop"})

    def __init__(self, engine: SimulationEngine) -> None:
        self._engine = engine
        self._terminal_predicates: Mapping[
            str, Callable[[int, int | None, bool], bool]
        ] = {
            "tick_limit": lambda completed, limit, _stop: (
                limit is not None and completed >= limit
            ),
            "operator_stop": lambda _completed, _limit, stop: stop,
        }

    def run(
        self,
        scenario_path: Path,
        configuration: RunConfiguration,
        *,
        stop_control: StopControl | None = None,
        checkpoint_control: CheckpointControl | None = None,
    ) -> RunResult:
        if not self._engine.persistence_enabled:
            raise RunPersistenceError(
                "ScenarioRunner requires a persistence-backed engine."
            )
        resumed = self._engine.state.run_metadata is not None
        scenario = self._engine.load_scenario(scenario_path)
        self._validate_terminal_conditions(scenario)
        start_tick = self._engine.state.tick
        tick_limit = self._tick_limit(scenario, configuration)
        completed = 0
        last_saved_tick: int | None = None
        terminal_condition: str | None = None
        checkpoints = checkpoint_control or IntervalCheckpointControl(
            configuration.save_every
        )

        while True:
            if stop_control is not None and stop_control.stop_requested():
                reason = StopReason.OPERATOR_STOP
                break
            if tick_limit is not None and completed >= tick_limit:
                reason = StopReason.TICK_LIMIT
                break
            try:
                self._engine.step()
            except Exception as exc:
                raise RunSimulationError(
                    f"Simulation failed while advancing tick {self._engine.state.tick}."
                ) from exc
            completed += 1
            if checkpoints.checkpoint_due(completed):
                self._save()
                last_saved_tick = self._engine.state.tick
            terminal_condition = self._matched_terminal_condition(
                scenario,
                completed=completed,
                tick_limit=tick_limit,
                stop_requested=(
                    stop_control is not None and stop_control.stop_requested()
                ),
            )
            if terminal_condition is not None:
                reason = StopReason.TERMINAL_CONDITION
                break

        if last_saved_tick != self._engine.state.tick:
            self._save()
        return RunResult(
            scenario_key=scenario.key,
            start_tick=start_tick,
            end_tick=self._engine.state.tick,
            resumed=resumed,
            stop_reason=reason,
            terminal_condition=terminal_condition,
        )

    @staticmethod
    def _tick_limit(
        scenario: LoadedScenario, configuration: RunConfiguration
    ) -> int | None:
        if configuration.continuous:
            return None
        return (
            scenario.default_max_ticks
            if configuration.max_ticks is None
            else configuration.max_ticks
        )

    def _validate_terminal_conditions(self, scenario: LoadedScenario) -> None:
        unsupported = sorted(
            set(scenario.terminal_conditions) - self._SUPPORTED_TERMINAL_CONDITIONS
        )
        if unsupported:
            raise ScenarioLoadError(
                "Unsupported terminal condition(s): " + ", ".join(unsupported) + "."
            )

    def _matched_terminal_condition(
        self,
        scenario: LoadedScenario,
        *,
        completed: int,
        tick_limit: int | None,
        stop_requested: bool,
    ) -> str | None:
        for name in scenario.terminal_conditions:
            if self._terminal_predicates[name](completed, tick_limit, stop_requested):
                return name
        return None

    def _save(self) -> None:
        try:
            self._engine.save_world()
        except Exception as exc:
            raise RunPersistenceError("Could not save the world checkpoint.") from exc
