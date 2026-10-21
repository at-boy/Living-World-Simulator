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
from living_world.founders.runtime import (
    FoundersPreparation,
    founders_terminal_conditions,
)
from living_world.replay.loader import YAMLProposalTapeLoader
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


class SnapshotRepository:
    def __init__(self, snapshot: WorldSnapshot) -> None:
        decode_world(snapshot)
        self._snapshot = snapshot

    def load_world(self) -> WorldState:
        return decode_world(self._snapshot)

    def save_world(self, state: WorldState) -> None:
        raise RepositorySaveError("Candidate writes require an archive commit.")


class RecordedFoundersComposition:
    def __init__(
        self, inputs: RetainedInputs, *, finalize_proposals: bool = True
    ) -> None:
        if not isinstance(inputs, RetainedInputs) or inputs.tape_path is None:
            raise ArchiveFormatError(
                "Recorded composition requires retained tape inputs."
            )
        if type(finalize_proposals) is not bool:
            raise TypeError("finalize_proposals must be boolean.")
        for path in (inputs.scenario_path, inputs.definition_path, inputs.tape_path):
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
        self._tape = YAMLProposalTapeLoader().load(inputs.tape_path)
        self._finalize_proposals = finalize_proposals
        self._preparations: WeakKeyDictionary[
            SimulationEngine, tuple[FoundersPreparation, LoadedScenario]
        ] = WeakKeyDictionary()
        self._initial_tick: int | None = None
        self._terminals: WeakKeyDictionary[SimulationEngine, str | None] = (
            WeakKeyDictionary()
        )

    def _compose(self, snapshot: WorldSnapshot) -> SimulationEngine:
        engine = SimulationEngine(SnapshotRepository(snapshot))
        scenario = engine.load_scenario(self._inputs.scenario_path)
        preparation = FoundersPreparation(self._tape)
        # The preparation's offer provider retains its engine. A weak proxy keeps
        # the weak-key preparation cache from retaining every discarded candidate.
        preparation.prepare(cast(SimulationEngine, proxy(engine)), scenario)
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
        self._terminals[engine] = None
        return None

    def finalize(self, engine: SimulationEngine, *, stopped: bool) -> None:
        preparation, scenario = self._preparations[engine]
        terminal = self._terminals.get(engine)
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

    def __init__(self, candidate: SimulationEngine) -> None:
        self._candidate = candidate
        self._paused = False

    def poll(self) -> Literal["paused", "ready"]:
        return "paused" if self._paused else "ready"

    def request_pause(self) -> None:
        self._paused = True

    def install(self) -> None:
        pass

    def finish_tick(self) -> DriverCommit:
        return _cursor(self._candidate)

    def close(self) -> None:
        pass


class RecordedTickDriver:
    def initialize(
        self, candidate: SimulationEngine, archive: AttemptArchive
    ) -> DriverCommit:
        return _cursor(candidate)

    def prepare(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> _RecordedPreparation:
        actual = _cursor(candidate)
        if (
            canonical(actual.driver_cursor) != canonical(base.driver_cursor)
            or base.feedback_cursor
        ):
            raise ArchiveFormatError("Recorded cursor does not match the world.")
        return _RecordedPreparation(candidate)
