from collections.abc import MutableMapping
from typing import cast

import pytest

from living_world.core.entity import Entity
from living_world.core.observation import Observation
from living_world.perception.perception_context import PerceptionContext
from living_world.perception.perception_engine import PerceptionEngine
from living_world.state.world_state import WorldState


class StubPerceptionEngine:
    """Minimal implementation used to verify the perception contract."""

    def perceive(
        self,
        context: PerceptionContext,
    ) -> Observation:
        return Observation(
            id="observation_000001",
            tick=context.tick,
            observer=context.observer.id,
            subject=context.subject.id,
            description=(
                f"{context.observer.name} observes " f"{context.subject.name}."
            ),
            confidence=1.0,
            evidence={
                "subject_attributes": dict(context.subject.attributes),
            },
            metadata={
                "engine": "stub",
            },
        )


def make_context() -> PerceptionContext:
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
            "woodcraft": 80,
            "botany": 20,
        },
        relationships=(),
        tick=42,
    )


def test_perception_context_stores_expected_values() -> None:
    context = make_context()

    assert context.observer.id == "entity_000001"
    assert context.subject.id == "entity_000002"
    assert context.subject.attributes["wood"] == 120
    assert context.capabilities["woodcraft"] == 80
    assert context.capabilities["botany"] == 20
    assert context.relationships == ()
    assert context.tick == 42


def test_perception_context_capabilities_are_immutable() -> None:
    context = make_context()

    with pytest.raises(TypeError):
        capabilities = cast(MutableMapping[str, object], context.capabilities)
        capabilities["woodcraft"] = 100


def test_perception_engine_contract() -> None:
    context = make_context()

    engine: PerceptionEngine = StubPerceptionEngine()

    observation = engine.perceive(context)

    assert isinstance(observation, Observation)
    assert observation.tick == 42
    assert observation.observer == "entity_000001"
    assert observation.subject == "entity_000002"
    assert observation.description == "Erik observes Old Oak."
    assert observation.confidence == 1.0


def test_perception_engine_can_use_objective_data_as_evidence() -> None:
    context = make_context()

    engine: PerceptionEngine = StubPerceptionEngine()

    observation = engine.perceive(context)

    assert observation.evidence["subject_attributes"] == {
        "growth": 87,
        "health": 92,
        "wood": 120,
    }
