"""Run packaged founders proposals and inspect bounded, persisted outcomes."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.founders import (
    FoundersOutcome,
    FoundersPreparation,
    founders_terminal_conditions,
    load_inspection_engine,
    materialize_founders_assets,
)
from living_world.replay.loader import YAMLProposalTapeLoader
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.running import RunConfiguration, ScenarioRunner
from living_world.simulation.simulation_engine import SimulationEngine

with TemporaryDirectory() as temporary, materialize_founders_assets() as assets:
    for outcome, expected_tick, expected_terminal in (
        (FoundersOutcome.SUCCESS, 10, "settlement_success"),
        (FoundersOutcome.STALL, 5, None),
        (FoundersOutcome.FAILURE, 13, "founding_failure"),
    ):
        database = Path(temporary) / f"{outcome.value}.sqlite3"
        engine = SimulationEngine(SQLiteRepository(str(database)))
        tape = YAMLProposalTapeLoader().load(assets.tape_for(outcome))
        result = ScenarioRunner(
            engine,
            FoundersPreparation(tape),
            terminal_conditions=founders_terminal_conditions(),
        ).run(
            assets.scenario,
            RunConfiguration(max_ticks=5 if outcome is FoundersOutcome.STALL else 16),
        )
        assert (result.end_tick, result.terminal_condition) == (
            expected_tick,
            expected_terminal,
        )
        assert engine.replay.current().next_index == expected_tick
        before = database.read_bytes()
        snapshot = load_inspection_engine(assets.scenario, database)
        assert snapshot.state.tick == expected_tick
        assert len(snapshot.state.need_states) == 4
        assert len(snapshot.state.goal_states) == 2
        assert database.read_bytes() == before
        print(f"{outcome.value}: tick={result.end_tick}, terminal={expected_terminal}")
    print("Recorded proposals pass ordinary gateways; inspection preserves each save.")
