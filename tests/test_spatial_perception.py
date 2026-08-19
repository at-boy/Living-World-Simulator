from __future__ import annotations

from dataclasses import replace

import pytest

from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.perception.perception_context import PerceptionContext
from living_world.perception.perception_engine import PerceptionEngine
from living_world.spatial import (
    Bounds,
    BoundsKind,
    Placement,
    Point,
    SpatialPerceptionEngine,
    SpatialPerceptionError,
)
from living_world.state.world_state import WorldState


def _state_with_entities(*entities: Entity) -> WorldState:
    state = WorldState(tick=8)
    state.entities.update((entity.id, entity) for entity in entities)
    return state


def _context(
    state: WorldState,
    observer: Entity,
    subject: Entity,
    *,
    relationships: tuple[Relationship, ...] = (),
) -> PerceptionContext:
    return PerceptionContext(
        observer=observer,
        subject=subject,
        world_state=state,
        capabilities={},
        relationships=relationships,
        tick=state.tick,
    )


@pytest.mark.parametrize(
    ("subject_point", "expected"),
    (
        (Point(0, 1), "north"),
        (Point(1, 1), "north-east"),
        (Point(1, 0), "east"),
        (Point(1, -1), "south-east"),
        (Point(0, -1), "south"),
        (Point(-1, -1), "south-west"),
        (Point(-1, 0), "west"),
        (Point(-1, 1), "north-west"),
    ),
)
def test_translates_every_compass_direction(
    subject_point: Point,
    expected: str,
) -> None:
    observer = Entity("observer", "npc", "Erik")
    subject = Entity("subject", "thing", "Well")
    state = _state_with_entities(observer, subject)
    state.placements[observer.id] = Placement(observer.id, Point(0, 0))
    state.placements[subject.id] = Placement(subject.id, subject_point)

    engine: PerceptionEngine = SpatialPerceptionEngine()
    result = engine.perceive(_context(state, observer, subject))

    assert result.description == f"Well is {expected} of Erik."
    assert result.evidence == {"spatial_relations": (expected.replace("-", "_"),)}
    assert result.observer == observer.id
    assert result.subject == subject.id
    assert result.id == ""
    assert result not in state.observations.values()


def test_uses_doubled_point_and_bounds_centers_without_exposing_geometry() -> None:
    observer = Entity("observer", "npc", "Erik")
    subject = Entity("subject", "building", "Storehouse")
    state = _state_with_entities(observer, subject)
    state.placements[observer.id] = Placement(observer.id, Point(2, 2))
    state.placements[subject.id] = Placement(
        subject.id,
        Bounds(0, 0, 4, 4),
        bounds_kind=BoundsKind.STRUCTURE,
    )

    result = SpatialPerceptionEngine().perceive(_context(state, observer, subject))

    assert result.description == "Storehouse occupies the same place as Erik."
    assert result.evidence == {"spatial_relations": ("co_located",)}
    assert result.metadata == {"engine": "spatial_perception"}
    assert all(
        term not in result.description.casefold()
        for term in ("coordinate", "bounds", "placement", "width", "height")
    )


def test_composes_shared_container_direction_and_direct_road_stably() -> None:
    observer = Entity("observer", "npc", "Erik")
    subject = Entity("subject", "thing", "Well")
    settlement = Entity("settlement", "settlement", "Oakford")
    other = Entity("other", "thing", "Granary")
    state = _state_with_entities(observer, subject, settlement, other)
    state.placements[settlement.id] = Placement(
        settlement.id,
        Bounds(40, 80, 20, 20),
        bounds_kind=BoundsKind.AREA,
    )
    state.placements[observer.id] = Placement(
        observer.id,
        Point(47, 83),
        containing_entity_id=settlement.id,
    )
    state.placements[subject.id] = Placement(
        subject.id,
        Point(48, 84),
        containing_entity_id=settlement.id,
    )
    road = Relationship("road-visible", "road", observer.id, subject.id)
    unrelated = Relationship("road-hidden", "road", observer.id, other.id)
    state.relationships.update((item.id, item) for item in (road, unrelated))

    first = SpatialPerceptionEngine().perceive(
        _context(state, observer, subject, relationships=(unrelated, road))
    )
    second = SpatialPerceptionEngine().perceive(
        _context(state, observer, subject, relationships=(road, unrelated))
    )

    assert (
        first.description
        == second.description
        == (
            "Well and Erik are inside Oakford. "
            "Well is north-east of Erik. "
            "A road directly connects Erik and Well."
        )
    )
    assert first.evidence == {
        "spatial_relations": ("shared_container", "north_east", "direct_road")
    }
    assert "47" not in first.description
    assert "83" not in first.description
    assert "road-visible" not in first.description


def test_describes_subject_container_and_subject_containing_observer() -> None:
    observer = Entity("observer", "npc", "Erik")
    subject = Entity("subject", "building", "Storehouse")
    settlement = Entity("settlement", "settlement", "Oakford")
    state = _state_with_entities(observer, subject, settlement)
    state.placements[settlement.id] = Placement(
        settlement.id,
        Bounds(0, 0, 20, 20),
        bounds_kind=BoundsKind.AREA,
    )
    state.placements[observer.id] = Placement(observer.id, Point(18, 18))
    state.placements[subject.id] = Placement(
        subject.id,
        Bounds(2, 2, 5, 5),
        containing_entity_id=settlement.id,
        bounds_kind=BoundsKind.STRUCTURE,
    )

    result = SpatialPerceptionEngine().perceive(_context(state, observer, subject))
    assert result.description.startswith("Storehouse is inside Oakford. ")

    state.placements[observer.id] = Placement(
        observer.id,
        Point(3, 3),
        containing_entity_id=subject.id,
    )
    state.placements[subject.id] = replace(
        state.placements[subject.id],
        containing_entity_id=None,
    )
    contained = SpatialPerceptionEngine().perceive(_context(state, observer, subject))
    assert contained.description.startswith("Storehouse contains Erik. ")


@pytest.mark.parametrize("missing_role", ("observer", "subject"))
def test_rejects_unknown_mismatched_destroyed_and_unplaced_entities(
    missing_role: str,
) -> None:
    observer = Entity("observer", "npc", "Erik")
    subject = Entity("subject", "thing", "Well")
    state = _state_with_entities(observer, subject)
    state.placements[observer.id] = Placement(observer.id, Point(0, 0))
    state.placements[subject.id] = Placement(subject.id, Point(1, 1))
    engine = SpatialPerceptionEngine()

    missing_entity = observer if missing_role == "observer" else subject
    removed = state.entities.pop(missing_entity.id)
    with pytest.raises(SpatialPerceptionError, match="known"):
        engine.perceive(_context(state, observer, subject))
    state.entities[removed.id] = removed

    detached = replace(subject)
    with pytest.raises(SpatialPerceptionError, match="authoritative"):
        engine.perceive(_context(state, observer, detached))

    subject.destroyed_tick = state.tick
    with pytest.raises(SpatialPerceptionError, match="live"):
        engine.perceive(_context(state, observer, subject))
    subject.destroyed_tick = None

    state.placements[subject.id] = Placement(subject.id, None)
    with pytest.raises(SpatialPerceptionError, match="placed"):
        engine.perceive(_context(state, observer, subject))

    assert state.observations == {}


def test_ignores_unavailable_relationships_and_deduplicates_direct_roads() -> None:
    observer = Entity("observer", "npc", "Erik")
    subject = Entity("subject", "thing", "Well")
    other = Entity("other", "thing", "Storehouse")
    state = _state_with_entities(observer, subject, other)
    state.placements[observer.id] = Placement(observer.id, Point(0, 0))
    state.placements[subject.id] = Placement(subject.id, Point(1, 0))
    relationships = (
        Relationship("unrelated", "road", observer.id, other.id),
        Relationship("future", "road", observer.id, subject.id, created_tick=9),
        Relationship(
            "destroyed",
            "road",
            observer.id,
            subject.id,
            destroyed_tick=7,
        ),
        Relationship("not-road", "knows", observer.id, subject.id),
        Relationship("direct-a", "road", observer.id, subject.id),
        Relationship("direct-b", "road", subject.id, observer.id),
    )
    state.relationships.update((item.id, item) for item in relationships)

    hidden = SpatialPerceptionEngine().perceive(_context(state, observer, subject))
    visible = SpatialPerceptionEngine().perceive(
        _context(state, observer, subject, relationships=relationships)
    )

    assert "road" not in hidden.description
    assert visible.description.count("road") == 1
    assert visible.evidence["spatial_relations"].count("direct_road") == 1


def test_rejects_malformed_context_and_internal_id_public_name() -> None:
    engine = SpatialPerceptionEngine()
    with pytest.raises(TypeError, match="PerceptionContext"):
        engine.perceive(object())  # type: ignore[arg-type]

    observer = Entity("observer-private", "npc", "Erik")
    subject = Entity("subject-private", "thing", "subject-private")
    state = _state_with_entities(observer, subject)
    state.placements[observer.id] = Placement(observer.id, Point(0, 0))
    state.placements[subject.id] = Placement(subject.id, Point(1, 0))

    with pytest.raises(ValueError, match="internal ID"):
        engine.perceive(_context(state, observer, subject))

    malformed_state = replace(
        _context(state, observer, subject),
        world_state=object(),  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="WorldState"):
        engine.perceive(malformed_state)

    malformed_relationships = replace(
        _context(state, observer, subject),
        relationships=(object(),),  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="Relationships"):
        engine.perceive(malformed_relationships)


def test_rejects_mismatched_authoritative_placement_record() -> None:
    observer = Entity("observer", "npc", "Erik")
    subject = Entity("subject", "thing", "Well")
    state = _state_with_entities(observer, subject)
    state.placements[observer.id] = Placement(observer.id, Point(0, 0))
    state.placements[subject.id] = Placement("different", Point(1, 0))

    with pytest.raises(SpatialPerceptionError, match="match authoritative"):
        SpatialPerceptionEngine().perceive(_context(state, observer, subject))


def test_rejects_mismatched_authoritative_container_placement_record() -> None:
    observer = Entity("observer", "npc", "Erik")
    subject = Entity("subject", "thing", "Well")
    container = Entity("container", "place", "Oakford")
    state = _state_with_entities(observer, subject, container)
    state.placements[observer.id] = Placement(observer.id, Point(0, 0))
    state.placements[subject.id] = Placement(
        subject.id,
        Point(2, 2),
        containing_entity_id=container.id,
    )
    state.placements[container.id] = Placement(
        "different",
        Bounds(0, 0, 10, 10),
        bounds_kind=BoundsKind.AREA,
    )

    with pytest.raises(SpatialPerceptionError, match="match authoritative"):
        SpatialPerceptionEngine().perceive(_context(state, observer, subject))
