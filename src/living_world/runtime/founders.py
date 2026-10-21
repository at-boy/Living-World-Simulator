"""Model-free, tape-independent canonical founders composition."""

from __future__ import annotations

import hashlib
from weakref import WeakKeyDictionary

from living_world.archives import ArchiveFormatError, RetainedInputs
from living_world.founders.runtime import (
    founders_terminal_conditions,
    prepare_live_founders_world,
)
from living_world.repositories.world_snapshot import WorldSnapshot, encode_world
from living_world.scenarios.scenario import LoadedScenario
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState

from .recorded import SnapshotRepository


class FoundersLiveComposition:
    def __init__(self, inputs: RetainedInputs) -> None:
        if not isinstance(inputs, RetainedInputs):
            raise ArchiveFormatError("Expected retained founders inputs.")
        for path in (inputs.scenario_path, inputs.definition_path):
            matches = [
                name for name in inputs.hashes if path.as_posix().endswith("/" + name)
            ]
            if (
                len(matches) != 1
                or hashlib.sha256(path.read_bytes()).hexdigest()
                != inputs.hashes[matches[0]]
            ):
                raise ArchiveFormatError("Retained input hash mismatch.")
        self._inputs = inputs
        self._scenarios: WeakKeyDictionary[SimulationEngine, LoadedScenario] = (
            WeakKeyDictionary()
        )

    def _compose(self, snapshot: WorldSnapshot) -> SimulationEngine:
        engine = SimulationEngine(SnapshotRepository(snapshot))
        scenario = engine.load_scenario(self._inputs.scenario_path)
        prepare_live_founders_world(engine, scenario)
        self._scenarios[engine] = scenario
        return engine

    def initialize(self) -> SimulationEngine:
        return self._compose(encode_world(WorldState()))

    def restore(self, snapshot: WorldSnapshot) -> SimulationEngine:
        engine = self._compose(snapshot)
        if encode_world(engine.state) != snapshot:
            raise ArchiveFormatError("Restoration changed the saved world.")
        return engine

    def terminal_condition(self, engine: SimulationEngine) -> str | None:
        scenario = self._scenarios[engine]
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
                return name
        return None

    def finalize(self, engine: SimulationEngine, *, stopped: bool) -> None:
        if type(stopped) is not bool:
            raise TypeError("stopped must be boolean.")
        prepare_live_founders_world(engine, self._scenarios[engine])
