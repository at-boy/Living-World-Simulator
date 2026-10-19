import pytest

from living_world.core.entity import Entity
from living_world.core.observation import Observation
from living_world.perception.npc_perception_boundary import (
    DefaultNPCPerceptionBoundary,
)
from living_world.perception.perception_context import PerceptionContext
from living_world.spatial import Bounds, BoundsKind, Placement, Point
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


@pytest.mark.parametrize(
    "description",
    (
        "The well is at 47, 83.",
        "The well has x=47 and y=83.",
        "The well uses a placement record.",
        "The well has exact coordinates.",
        "The storehouse has bounds.",
        "The structures use an overlap policy.",
    ),
)
def test_boundary_rejects_privileged_spatial_prose(description: str) -> None:
    context = make_context()
    context.world_state.entities.update(
        ((context.observer.id, context.observer), (context.subject.id, context.subject))
    )
    context.world_state.placements[context.observer.id] = Placement(
        context.observer.id,
        Point(47, 83),
    )
    context.world_state.placements[context.subject.id] = Placement(
        context.subject.id,
        Bounds(40, 80, 20, 10),
        bounds_kind=BoundsKind.STRUCTURE,
    )

    with pytest.raises(ValueError):
        DefaultNPCPerceptionBoundary().visible_description(
            observation(description),
            context=context,
        )


def test_boundary_rejects_any_authoritative_spatial_number_or_identifier() -> None:
    context = make_context()
    context.world_state.entities.update(
        ((context.observer.id, context.observer), (context.subject.id, context.subject))
    )
    context.world_state.placements[context.subject.id] = Placement(
        context.subject.id,
        Point(47, 83),
    )

    for description in (
        "The well is 47 steps away.",
        "The well is at x 47.0 and y 83.00.",
        "I saw tree_1 nearby.",
    ):
        with pytest.raises(ValueError):
            DefaultNPCPerceptionBoundary().visible_description(
                observation(description),
                context=context,
            )

    safe_description = "Route47.0 remains open."
    assert (
        DefaultNPCPerceptionBoundary().visible_description(
            observation(safe_description),
            context=context,
        )
        == safe_description
    )


@pytest.mark.parametrize(
    "description",
    (
        "The well is at x-47.0 and y-83.0.",
        "The well is at x-4.7e1 and y-8.3e1.",
    ),
)
def test_boundary_rejects_attached_signed_coordinate_equivalents(
    description: str,
) -> None:
    context = make_context()
    context.world_state.entities.update(
        ((context.observer.id, context.observer), (context.subject.id, context.subject))
    )
    context.world_state.placements[context.subject.id] = Placement(
        context.subject.id,
        Point(-47, -83),
    )

    with pytest.raises(ValueError, match="coordinate notation"):
        DefaultNPCPerceptionBoundary().visible_description(
            observation(description),
            context=context,
        )


@pytest.mark.parametrize(
    "description",
    (
        "The width+20.0 is known.",
        "The height+3e1 is known.",
    ),
)
def test_boundary_rejects_attached_signed_dimension_equivalents(
    description: str,
) -> None:
    context = make_context()
    context.world_state.entities.update(
        ((context.observer.id, context.observer), (context.subject.id, context.subject))
    )
    context.world_state.placements[context.subject.id] = Placement(
        context.subject.id,
        Bounds(40, 80, 20, 30),
        bounds_kind=BoundsKind.STRUCTURE,
    )

    with pytest.raises(ValueError, match="coordinate notation"):
        DefaultNPCPerceptionBoundary().visible_description(
            observation(description),
            context=context,
        )


@pytest.mark.parametrize(
    "description",
    (
        "The well is at x47.0 and y8.3e1.",
        "The width20.0 and height3e1 are known.",
    ),
)
def test_boundary_rejects_attached_unsigned_spatial_equivalents(
    description: str,
) -> None:
    context = make_context()
    context.world_state.entities.update(
        ((context.observer.id, context.observer), (context.subject.id, context.subject))
    )
    context.world_state.placements[context.subject.id] = Placement(
        context.subject.id,
        Bounds(47, 83, 20, 30),
        bounds_kind=BoundsKind.STRUCTURE,
    )

    with pytest.raises(ValueError, match="coordinate notation"):
        DefaultNPCPerceptionBoundary().visible_description(
            observation(description),
            context=context,
        )
