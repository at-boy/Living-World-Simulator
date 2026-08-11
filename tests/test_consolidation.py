from pathlib import Path

from living_world.cognition.consolidation import (
    DAY_LENGTH_TICKS,
    SleepCognitiveConsolidator,
)
from living_world.core.belief import Belief, BeliefStatus
from living_world.core.definition import Definition
from living_world.core.experience import Experience
from living_world.core.memory import Memory
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.simulation.simulation_engine import SimulationEngine


def _engine_with_sleeping_npc() -> tuple[SimulationEngine, str]:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="person"))
    npc = engine.entities.create(
        definition_key="person",
        name="Mira",
        attributes={"active_activity": "sleeping"},
    )
    return engine, npc.id


def _consolidator(engine: SimulationEngine) -> SleepCognitiveConsolidator:
    return SleepCognitiveConsolidator(
        entities=engine.entities,
        observations=engine.observations,
        memories=engine.memories,
        experiences=engine.experiences,
        beliefs=engine.beliefs,
    )


def test_sleep_consolidation_uses_only_prior_day_visible_descriptions() -> None:
    engine, holder_id = _engine_with_sleeping_npc()
    engine.state.tick = 3
    first = engine.observations.record(
        observer=holder_id,
        subject="tree_1",
        description="The old oak appears healthy.",
        confidence=0.8,
        evidence={"wood": 120, "health": 92},
    )
    engine.state.tick = 8
    second = engine.observations.record(
        observer=holder_id,
        subject="tree_1",
        description="The old oak still looks strong.",
        confidence=0.7,
        evidence={"wood": 120, "health": 92},
    )
    engine.state.tick = DAY_LENGTH_TICKS
    current_day = engine.observations.record(
        observer=holder_id,
        subject="tree_1",
        description="The oak looks unchanged this morning.",
        confidence=0.9,
        evidence={"wood": 120},
    )

    created = _consolidator(engine).consolidate(
        holder_id=holder_id,
        through_tick=DAY_LENGTH_TICKS,
    )

    memories = tuple(record for record in created if isinstance(record, Memory))
    experiences = tuple(record for record in created if isinstance(record, Experience))
    beliefs = tuple(record for record in created if isinstance(record, Belief))
    visible_text = "\n".join(
        record.summary if not isinstance(record, Belief) else record.proposition
        for record in created
    )

    assert [memory.source_observation_ids for memory in memories] == [
        (first.id,),
        (second.id,),
    ]
    assert len(experiences) == 1
    assert len(beliefs) == 1
    assert beliefs[0].status is BeliefStatus.CANDIDATE
    assert beliefs[0].supporting_observations == (first.id, second.id)
    assert current_day.id not in visible_text
    assert "120" not in visible_text
    assert "92" not in visible_text


def test_sleep_consolidation_requires_sleep_and_is_idempotent() -> None:
    engine, holder_id = _engine_with_sleeping_npc()
    engine.state.tick = 2
    engine.observations.record(
        observer=holder_id,
        subject="road_1",
        description="The road appears clear.",
        confidence=0.8,
    )
    engine.state.tick = DAY_LENGTH_TICKS
    consolidator = _consolidator(engine)

    engine.entities.set_attribute(
        entity_id=holder_id,
        key="active_activity",
        value="working",
    )
    assert (
        consolidator.consolidate(holder_id=holder_id, through_tick=DAY_LENGTH_TICKS)
        == ()
    )

    engine.entities.set_attribute(
        entity_id=holder_id,
        key="active_activity",
        value="sleeping",
    )
    first_result = consolidator.consolidate(
        holder_id=holder_id,
        through_tick=DAY_LENGTH_TICKS,
    )

    assert first_result
    assert (
        consolidator.consolidate(holder_id=holder_id, through_tick=DAY_LENGTH_TICKS)
        == ()
    )


def test_engine_runs_consolidation_after_schedule_sets_sleeping_activity() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="person"))
    npc = engine.entities.create(
        definition_key="person",
        name="Mira",
        attributes={
            "npc_identity": {
                "name": "Mira",
                "description": "A traveler.",
                "capability_descriptions": [],
            },
            "schedule": [{"start_tick": 24, "end_tick": 25, "activity": "sleeping"}],
            "active_activity": None,
        },
    )
    engine.state.tick = 3
    engine.observations.record(
        observer=npc.id,
        subject="road_1",
        description="The road appears clear.",
        confidence=0.8,
    )
    engine.state.tick = DAY_LENGTH_TICKS

    engine.step()

    assert engine.memories.memories_for(npc.id)


def test_persisted_provenance_prevents_repeat_consolidation(tmp_path: Path) -> None:
    engine, holder_id = _engine_with_sleeping_npc()
    engine.state.tick = 2
    engine.observations.record(
        observer=holder_id,
        subject="road_1",
        description="The road appears clear.",
        confidence=0.8,
    )
    engine.state.tick = DAY_LENGTH_TICKS
    _consolidator(engine).consolidate(
        holder_id=holder_id,
        through_tick=DAY_LENGTH_TICKS,
    )
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    repository.save_world(engine.state)
    reloaded_engine = SimulationEngine(repository)

    assert (
        _consolidator(reloaded_engine).consolidate(
            holder_id=holder_id,
            through_tick=DAY_LENGTH_TICKS,
        )
        == ()
    )
