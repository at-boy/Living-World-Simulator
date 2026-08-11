import pytest

from living_world.core.entity import Entity
from living_world.core.observation import Observation
from living_world.perception.npc_perception_boundary import (
    DefaultNPCPerceptionBoundary,
)
from living_world.perception.perception_context import PerceptionContext
from living_world.state.world_state import WorldState


def make_context() -> PerceptionContext:
    return PerceptionContext(
        observer=Entity(
            id="npc_1",
            definition_key="npc",
            name="Erik",
            attributes={},
        ),
        subject=Entity(
            id="tree_1",
            definition_key="tree",
            name="Old Oak",
            attributes={"wood": {"available": 120}, "health": 92},
        ),
        world_state=WorldState(),
        capabilities={"skills": {"woodcraft": 80}},
        relationships=(),
        tick=4,
    )


def observation(description: str) -> Observation:
    return Observation(
        id="observation_1",
        tick=4,
        observer="npc_1",
        subject="tree_1",
        description=description,
        confidence=0.8,
        evidence={"wood": 120},
        metadata={"engine": "deterministic"},
    )


@pytest.mark.parametrize(
    "description",
    (
        "tree_1 appears mature.",
        "The oak contains 120 units of wood.",
        "The oak has wood=120.",
        "The evidence says the oak is healthy.",
        "The hidden state says the oak is healthy.",
        "WorldState reports the oak is healthy.",
    ),
)
def test_boundary_rejects_engine_data(description: str) -> None:
    with pytest.raises(ValueError):
        DefaultNPCPerceptionBoundary().visible_description(
            observation(description),
            context=make_context(),
        )


def test_boundary_recurses_through_nested_capabilities() -> None:
    with pytest.raises(ValueError, match="numeric"):
        DefaultNPCPerceptionBoundary().visible_description(
            observation("Erik has skill 80."),
            context=make_context(),
        )


def test_boundary_allows_qualitative_attribute_words_without_engine_context() -> None:
    description = "The old oak looks healthy and has useful wood."

    assert (
        DefaultNPCPerceptionBoundary().visible_description(observation(description))
        == description
    )
