"""Existing canonical founders composition behind detached durable candidates."""

from __future__ import annotations

import hashlib
from typing import Literal, cast
from weakref import WeakKeyDictionary, proxy

from living_world.archives import (
    ArchiveFormatError,
    AttemptArchive,
    Checkpoint,
    RetainedInputs,
)
from living_world.archives.model import canonical
from living_world.founders.model import FoundersPolicy
from living_world.founders.runtime import (
    FoundersPreparation,
    founders_terminal_conditions,
)
from living_world.replay.loader import YAMLProposalTapeLoader
from living_world.replay.model import ProposalTapeError
from living_world.replay.runtime import ReplayPreparation
from living_world.repositories.sqlite_repository import RepositorySaveError
from living_world.repositories.world_snapshot import (
    WorldSnapshot,
    decode_world,
    encode_world,
)
from living_world.running import RunResult, StopReason
from living_world.scenarios.scenario import LoadedScenario
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState

from .contracts import DriverCommit
from .legacy import legacy_cursor


class SnapshotRepository:
    def __init__(self, snapshot: WorldSnapshot) -> None:
        decode_world(snapshot)
        self._snapshot = snapshot

    def load_world(self) -> WorldState:
        return decode_world(self._snapshot)

    def save_world(self, state: WorldState) -> None:
        raise RepositorySaveError("Candidate writes require an archive commit.")


class RecordedScenarioComposition:
    def __init__(
        self,
        inputs: RetainedInputs,
        *,
        finalize_proposals: bool = True,
        max_ticks: int | None = None,
    ) -> None:
        if not isinstance(inputs, RetainedInputs):
            raise ArchiveFormatError(
                "Recorded composition requires retained tape inputs."
            )
        if type(finalize_proposals) is not bool:
            raise TypeError("finalize_proposals must be boolean.")
        for path in (inputs.scenario_path, inputs.definition_path) + (
            () if inputs.tape_path is None else (inputs.tape_path,)
        ):
            name = next(
                (
                    name
                    for name in inputs.hashes
                    if path.as_posix().endswith("/" + name)
                ),
                None,
            )
            if (
                name is None
                or hashlib.sha256(path.read_bytes()).hexdigest() != inputs.hashes[name]
            ):
                raise ArchiveFormatError("Retained input hash mismatch.")
        self._inputs = inputs
        self._tape = (
            None
            if inputs.tape_path is None
            else YAMLProposalTapeLoader().load(inputs.tape_path)
        )
        self._max_ticks = max_ticks
        self._finalize_proposals = finalize_proposals
        self._preparations: WeakKeyDictionary[
            SimulationEngine, tuple[ReplayPreparation | None, LoadedScenario]
        ] = WeakKeyDictionary()
        self._initial_tick: int | None = None
        self._terminals: WeakKeyDictionary[SimulationEngine, str | None] = (
            WeakKeyDictionary()
        )

    def _compose(self, snapshot: WorldSnapshot) -> SimulationEngine:
        engine = SimulationEngine(SnapshotRepository(snapshot))
        scenario = engine.load_scenario(self._inputs.scenario_path)
        canonical = scenario.key == "canonical_founders_v1" or any(
            "founders_policy" in item.attributes for item in scenario.entities
        )
        predicates = founders_terminal_conditions() if canonical else {}
        if any(
            name not in {"tick_limit", "operator_stop", *predicates}
            for name in scenario.terminal_conditions
        ):
            raise ValueError("Unknown recorded terminal condition.")
        if canonical:
            FoundersPolicy.from_scenario(scenario)
            if self._tape is None:
                raise ArchiveFormatError(
                    "Canonical recorded composition requires tape."
                )
            preparation: ReplayPreparation | None = FoundersPreparation(self._tape)
        else:
            preparation = None if self._tape is None else ReplayPreparation(self._tape)
        if preparation is None and engine.state.replay_binding is not None:
            raise ProposalTapeError("missing_replay_preparation")
        # The preparation's offer provider retains its engine. A weak proxy keeps
        # the weak-key preparation cache from retaining every discarded candidate.
        if preparation is not None:
            preparation.prepare(cast(SimulationEngine, proxy(engine)), scenario)
        engine._check_failed_tick()
        engine._check_replay_preparation()
        self._preparations[engine] = (preparation, scenario)
        if self._initial_tick is None:
            self._initial_tick = engine.state.tick
        return engine

    def initialize(self) -> SimulationEngine:
        return self._compose(encode_world(WorldState()))

    def restore(self, snapshot: WorldSnapshot) -> SimulationEngine:
        return self._compose(snapshot)

    def terminal_condition(self, engine: SimulationEngine) -> str | None:
        _, scenario = self._preparations[engine]
        predicates = founders_terminal_conditions()
        for name in scenario.terminal_conditions:
            if name in ("tick_limit", "operator_stop"):
                continue
            if name not in predicates:
                raise ValueError("Unknown founders terminal condition.")
            result = predicates[name](engine)
            if type(result) is not bool:
                raise TypeError("Terminal condition must return bool.")
            if result:
                self._terminals[engine] = name
                return name
        if (
            self._max_ticks is not None
            and self._initial_tick is not None
            and engine.state.tick > self._initial_tick
            and engine.state.tick - self._initial_tick >= self._max_ticks
            and "tick_limit" in scenario.terminal_conditions
        ):
            self._terminals[engine] = "tick_limit"
            return "tick_limit"
        self._terminals[engine] = None
        return None

    def finalize(self, engine: SimulationEngine, *, stopped: bool) -> None:
        preparation, scenario = self._preparations[engine]
        if preparation is None:
            return
        terminal = None if stopped else self._terminals.get(engine)
        reason = (
            StopReason.OPERATOR_STOP
            if stopped
            else StopReason.TERMINAL_CONDITION if terminal else StopReason.TICK_LIMIT
        )
        preparation.finish(
            engine,
            RunResult(
                scenario.key,
                self._initial_tick or 0,
                engine.state.tick,
                (self._initial_tick or 0) > 0,
                reason,
                terminal,
            ),
            finalize_proposals=self._finalize_proposals,
        )


class RecordedFoundersComposition(RecordedScenarioComposition):
    """Strict historical canonical adapter with unchanged direct behavior."""

    def __init__(
        self, inputs: RetainedInputs, *, finalize_proposals: bool = True
    ) -> None:
        if not isinstance(inputs, RetainedInputs) or inputs.tape_path is None:
            raise ArchiveFormatError(
                "Recorded composition requires retained tape inputs."
            )
        super().__init__(inputs, finalize_proposals=finalize_proposals)

    def _compose(self, snapshot: WorldSnapshot) -> SimulationEngine:
        engine = super()._compose(snapshot)
        _, scenario = self._preparations[engine]
        FoundersPolicy.from_scenario(scenario)
        return engine


def _cursor(engine: SimulationEngine) -> DriverCommit:
    binding, replay = engine.state.replay_binding, engine.replay.current()
    if binding is None or replay is None:
        raise ArchiveFormatError("Recorded preparation is missing.")
    engine.replay.validate_loaded_state()
    return DriverCommit(
        {
            "format": 1,
            "mode": "recorded",
            "tape_fingerprint": binding.tape_fingerprint,
            "next_index": replay.next_index,
            "next_tick": engine.state.tick,
        },
        {},
        (),
    )


class _RecordedPreparation:
    activity = None
    error_code = None

    def __init__(self, candidate: SimulationEngine, driver: RecordedTickDriver) -> None:
        self._candidate = candidate
        self._driver = driver
        self._paused = False

    def poll(self) -> Literal["paused", "ready"]:
        return "paused" if self._paused else "ready"

    def request_pause(self) -> None:
        self._paused = True

    def install(self) -> None:
        pass

    def finish_tick(self) -> DriverCommit:
        return self._driver._commit(self._candidate)

    def close(self) -> None:
        pass


class RecordedTickDriver:
    def __init__(
        self, *, cursor_kind: Literal["recorded", "legacy_recorded"] = "recorded"
    ) -> None:
        if cursor_kind not in ("recorded", "legacy_recorded"):
            raise ValueError("Unknown recorded cursor kind.")
        self._cursor_kind = cursor_kind

    def _commit(self, candidate: SimulationEngine) -> DriverCommit:
        return (
            _cursor(candidate)
            if self._cursor_kind == "recorded"
            else DriverCommit(legacy_cursor(candidate), {}, ())
        )

    def validate_checkpoint(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> None:
        actual = self._commit(candidate)
        if (
            encode_world(candidate.state) != base.snapshot
            or canonical(actual.driver_cursor) != canonical(base.driver_cursor)
            or base.feedback_cursor
        ):
            raise ArchiveFormatError("Recorded cursor does not match the world.")

    def initialize(
        self, candidate: SimulationEngine, archive: AttemptArchive
    ) -> DriverCommit:
        return self._commit(candidate)

    def prepare(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> _RecordedPreparation:
        self.validate_checkpoint(candidate, base, archive)
        return _RecordedPreparation(candidate, self)
