from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Protocol

from living_world.replay.model import ProposalTapeError
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
    finalize_proposals: bool = True

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
        if not isinstance(self.finalize_proposals, bool):
            raise TypeError("finalize_proposals must be a boolean.")
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
    proposals_finalized: bool | None = None


class ScenarioPreparation(Protocol):
    def prepare(self, engine: SimulationEngine, scenario: LoadedScenario) -> None: ...

    def finish(
        self, engine: SimulationEngine, result: RunResult, *, finalize_proposals: bool
    ) -> None: ...


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

    def __init__(
        self,
        engine: SimulationEngine,
        preparation: ScenarioPreparation | None = None,
        *,
        terminal_conditions: (
            Mapping[str, Callable[[SimulationEngine], bool]] | None
        ) = None,
    ) -> None:
        custom = {} if terminal_conditions is None else dict(terminal_conditions)
        for name, predicate in custom.items():
            if (
                not isinstance(name, str)
                or re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", name) is None
                or name in self._SUPPORTED_TERMINAL_CONDITIONS
                or not callable(predicate)
            ):
                raise ValueError("Invalid terminal condition configuration.")
        self._custom_terminal_conditions = custom
        self._engine = engine
        self._preparation = preparation
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
        if self._engine.state.replay_binding is not None and self._preparation is None:
            raise ProposalTapeError("missing_replay_preparation")
        if self._preparation is not None:
            self._preparation.prepare(self._engine, scenario)
        self._engine._check_failed_tick()
        self._engine._check_replay_preparation()
        start_tick = self._engine.state.tick
        tick_limit = self._tick_limit(scenario, configuration)
        completed = 0
        terminal_condition: str | None = None
        checkpoints = checkpoint_control or IntervalCheckpointControl(
            configuration.save_every
        )

        while True:
            if stop_control is not None and stop_control.stop_requested():
                reason = StopReason.OPERATOR_STOP
                break
            terminal_condition = (
                self._matched_custom_condition(scenario) if completed == 0 else None
            )
            if terminal_condition is not None:
                reason = StopReason.TERMINAL_CONDITION
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
            stop_requested = stop_control is not None and stop_control.stop_requested()
            terminal_condition = self._matched_terminal_condition(
                scenario,
                completed=completed,
                tick_limit=tick_limit,
                stop_requested=stop_requested,
            )
            if terminal_condition is not None:
                reason = StopReason.TERMINAL_CONDITION
                break
            if tick_limit is not None and completed >= tick_limit:
                reason = StopReason.TICK_LIMIT
                break
            if stop_requested:
                reason = StopReason.OPERATOR_STOP
                break
            if checkpoints.checkpoint_due(completed):
                self._save()

        result = RunResult(
            scenario_key=scenario.key,
            start_tick=start_tick,
            end_tick=self._engine.state.tick,
            resumed=resumed,
            stop_reason=reason,
            terminal_condition=terminal_condition,
        )
        if self._preparation is not None:
            self._preparation.finish(
                self._engine,
                result,
                finalize_proposals=configuration.finalize_proposals,
            )
        if self._engine.state.replay_binding is not None:
            result = replace(
                result,
                proposals_finalized=configuration.finalize_proposals
                and reason != StopReason.OPERATOR_STOP
                and terminal_condition != "operator_stop",
            )
        self._save()
        return result

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
            set(scenario.terminal_conditions)
            - self._SUPPORTED_TERMINAL_CONDITIONS
            - self._custom_terminal_conditions.keys()
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
        custom = self._matched_custom_condition(scenario)
        if custom is not None:
            return custom
        for name in scenario.terminal_conditions:
            if name in self._custom_terminal_conditions:
                continue
            if self._terminal_predicates[name](completed, tick_limit, stop_requested):
                return name
        return None

    def _matched_custom_condition(self, scenario: LoadedScenario) -> str | None:
        for name in scenario.terminal_conditions:
            predicate = self._custom_terminal_conditions.get(name)
            if predicate is None:
                continue
            try:
                matched = predicate(self._engine)
                if type(matched) is not bool:
                    raise TypeError("Terminal condition must return bool.")
            except Exception as exc:
                raise RunSimulationError(
                    "Terminal condition evaluation failed."
                ) from exc
            if matched:
                return name
        return None

    def _save(self) -> None:
        try:
            self._engine.save_world()
        except Exception as exc:
            raise RunPersistenceError("Could not save the world checkpoint.") from exc
