from living_world.core.entity import Entity
from living_world.perception.deterministic_perception_engine import (
    DeterministicPerceptionEngine,
)
from living_world.perception.perception_context import PerceptionContext
from living_world.state.world_state import WorldState


def make_context(
    *,
    woodcraft: int,
) -> PerceptionContext:
    observer = Entity(
        id="entity_000001",
        definition_key="npc",
        name="Erik",
        attributes={},
        created_tick=0,
    )

    subject = Entity(
        id="entity_000002",
        definition_key="tree",
        name="Old Oak",
        attributes={
            "growth": 87,
            "health": 92,
            "wood": 120,
        },
        created_tick=0,
    )

    return PerceptionContext(
        observer=observer,
        subject=subject,
        world_state=WorldState(),
        capabilities={
            "woodcraft": woodcraft,
        },
        relationships=(),
        tick=42,
    )


def test_produces_observation() -> None:
    engine = DeterministicPerceptionEngine()

    observation = engine.perceive(
        make_context(woodcraft=80),
    )

    assert observation.tick == 42
    assert observation.observer == "entity_000001"
    assert observation.subject == "entity_000002"
    assert observation.description == (
        "The Old Oak appears mature and healthy " "and looks suitable for harvesting."
    )


def test_high_skill_produces_detailed_perception() -> None:
    engine = DeterministicPerceptionEngine()

    observation = engine.perceive(
        make_context(woodcraft=80),
    )

    assert "mature" in observation.description
    assert "healthy" in observation.description
    assert "suitable for harvesting" in observation.description


def test_medium_skill_produces_less_detailed_perception() -> None:
    engine = DeterministicPerceptionEngine()

    observation = engine.perceive(
        make_context(woodcraft=40),
    )

    assert observation.description == "The Old Oak appears mature."


def test_low_skill_produces_basic_perception() -> None:
    engine = DeterministicPerceptionEngine()

    observation = engine.perceive(
        make_context(woodcraft=10),
    )

    assert observation.description == "The Old Oak is a tree."


def test_observation_contains_internal_evidence() -> None:
    engine = DeterministicPerceptionEngine()

    observation = engine.perceive(
        make_context(woodcraft=80),
    )

    assert observation.evidence["subject_attributes"] == {
        "growth": 87,
        "health": 92,
        "wood": 120,
    }

    assert observation.evidence["observer_capabilities"] == {
        "woodcraft": 80,
    }


def test_observation_does_not_expose_raw_attributes_in_description() -> None:
    engine = DeterministicPerceptionEngine()

    observation = engine.perceive(
        make_context(woodcraft=80),
    )

    assert "87" not in observation.description
    assert "92" not in observation.description
    assert "120" not in observation.description


def test_confidence_increases_with_capability() -> None:
    engine = DeterministicPerceptionEngine()

    low = engine.perceive(make_context(woodcraft=10))
    high = engine.perceive(make_context(woodcraft=80))

    assert high.confidence > low.confidence


def test_perception_is_deterministic() -> None:
    engine = DeterministicPerceptionEngine()

    first = engine.perceive(make_context(woodcraft=80))
    second = engine.perceive(make_context(woodcraft=80))

    assert first.description == second.description
    assert first.confidence == second.confidence
    assert first.evidence == second.evidence
    assert first.metadata == second.metadata
