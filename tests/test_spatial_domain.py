import json
import sqlite3
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest

from living_world.api.inspection import EngineWorldInspector
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.core.definition import Definition
from living_world.managers.entity_manager import EntityManager
from living_world.repositories.sqlite_repository import (
    RepositoryLoadError,
    SQLiteRepository,
)
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial import (
    Bounds,
    BoundsKind,
    OverlapPolicy,
    Placement,
    Point,
    SpatialManager,
)


def _engine_with_entities(*names: str) -> tuple[SimulationEngine, tuple[str, ...]]:
    engine = SimulationEngine()
    engine.definitions.register(Definition("thing"))
    entities = tuple(
        engine.entities.create(definition_key="thing", name=name) for name in names
    )
    return engine, tuple(entity.id for entity in entities)


def test_geometry_and_placement_values_validate_exact_contract() -> None:
    outer = Bounds(0, 0, 4, 4)
    assert outer.contains(Point(0, 0))
    assert outer.contains(Point(3, 3))
    assert not outer.contains(Point(4, 3))
    assert outer.contains(Bounds(1, 1, 3, 3))
    assert outer.overlaps(Bounds(3, 3, 2, 2))
    assert not outer.overlaps(Bounds(4, 0, 1, 1))

    with pytest.raises(TypeError, match="integer"):
        Point(True, 0)
    with pytest.raises(ValueError, match="positive"):
        Bounds(0, 0, 0, 1)
    with pytest.raises(ValueError, match="bounds kind"):
        Placement("entity", Bounds(0, 0, 1, 1))
    with pytest.raises(ValueError, match="Point placement"):
        Placement("entity", Point(0, 0), bounds_kind=BoundsKind.AREA)
    with pytest.raises(ValueError, match="Point placement must reject"):
        Placement(
            "entity",
            Point(0, 0),
            overlap_policy=OverlapPolicy.ALLOW_SIBLING_OVERLAP,
        )
    with pytest.raises(ValueError, match="Unplaced state"):
        Placement("entity", None, containing_entity_id="parent")


def test_manager_places_contained_geometry_and_records_immutable_events() -> None:
    engine, (area_id, point_id) = _engine_with_entities("Area", "Person")
    area = engine.spatial.place(
        entity_id=area_id,
        geometry=Bounds(0, 0, 10, 10),
        bounds_kind=BoundsKind.AREA,
    )
    point = engine.spatial.place(
        entity_id=point_id,
        geometry=Point(9, 9),
        containing_entity_id=area_id,
    )

    assert engine.spatial.get(area_id) is area
    assert engine.spatial.get(point_id) is point
    event = tuple(engine.state.events.values())[-1]
    assert event.kind == "spatial_placement_created"
    assert event.subject_id == point_id
    current = cast(MutableMapping[str, object], event.attributes["current"])
    with pytest.raises(TypeError):
        current["bounds_kind"] = "area"
    with pytest.raises(FrozenInstanceError):
        point.geometry.x = 2  # type: ignore[misc,union-attr]


def test_lifecycle_uses_the_complete_spatial_event_taxonomy() -> None:
    engine, (entity_id,) = _engine_with_entities("Entity")
    engine.spatial.place(entity_id=entity_id, geometry=Point(0, 0))
    engine.spatial.replace(entity_id=entity_id, geometry=Point(1, 1))
    engine.spatial.unplace(entity_id)
    engine.spatial.remove(entity_id)

    events = tuple(engine.state.events.values())
    assert tuple(event.kind for event in events) == (
        "spatial_placement_created",
        "spatial_placement_replaced",
        "spatial_placement_unplaced",
        "spatial_placement_removed",
    )
    assert set(events[0].attributes) == {"current"}
    assert set(events[1].attributes) == {"previous", "current"}
    assert set(events[2].attributes) == {"previous", "current"}
    assert set(events[3].attributes) == {"previous"}


def test_manager_rejects_invalid_entities_containment_cycles_and_kind() -> None:
    engine, (parent_id, child_id, other_id) = _engine_with_entities(
        "Parent", "Child", "Other"
    )
    with pytest.raises(ValueError, match="Unknown entity"):
        engine.spatial.place(entity_id="missing", geometry=Point(0, 0))
    engine.state.entities[other_id].destroyed_tick = 1
    with pytest.raises(ValueError, match="Destroyed entity"):
        engine.spatial.place(entity_id=other_id, geometry=Point(0, 0))

    engine.spatial.place(
        entity_id=parent_id,
        geometry=Bounds(0, 0, 10, 10),
        bounds_kind=BoundsKind.AREA,
    )
    with pytest.raises(ValueError, match="inside"):
        engine.spatial.place(
            entity_id=child_id,
            geometry=Point(10, 1),
            containing_entity_id=parent_id,
        )
    engine.spatial.place(
        entity_id=child_id,
        geometry=Bounds(0, 0, 10, 10),
        containing_entity_id=parent_id,
        bounds_kind=BoundsKind.AREA,
    )
    with pytest.raises(ValueError, match="cycle"):
        engine.spatial.replace(
            entity_id=parent_id,
            geometry=Bounds(0, 0, 10, 10),
            containing_entity_id=child_id,
            bounds_kind=BoundsKind.AREA,
        )
    with pytest.raises(ValueError, match="cannot contain an area"):
        engine.spatial.replace(
            entity_id=parent_id,
            geometry=Bounds(0, 0, 10, 10),
            bounds_kind=BoundsKind.STRUCTURE,
        )


def test_parent_changes_and_entity_removal_are_leaf_first() -> None:
    engine, (parent_id, child_id) = _engine_with_entities("Parent", "Child")
    engine.spatial.place(
        entity_id=parent_id,
        geometry=Bounds(0, 0, 10, 10),
        bounds_kind=BoundsKind.AREA,
    )
    engine.spatial.place(
        entity_id=child_id,
        geometry=Bounds(7, 7, 2, 2),
        containing_entity_id=parent_id,
        bounds_kind=BoundsKind.STRUCTURE,
    )

    with pytest.raises(ValueError, match="outside"):
        engine.spatial.replace(
            entity_id=parent_id,
            geometry=Bounds(0, 0, 8, 8),
            bounds_kind=BoundsKind.AREA,
        )
    with pytest.raises(ValueError, match="children"):
        engine.spatial.unplace(parent_id)
    with pytest.raises(ValueError, match="children"):
        engine.spatial.remove(parent_id)
    with pytest.raises(ValueError, match="spatial state"):
        engine.entities.remove(parent_id)

    engine.spatial.unplace(child_id)
    engine.spatial.remove(child_id)
    engine.entities.remove(child_id)
    engine.spatial.remove(parent_id)
    engine.entities.remove(parent_id)
    assert engine.state.entities == {}


def test_direct_entity_manager_cannot_bypass_spatial_removal_guard() -> None:
    engine, (entity_id,) = _engine_with_entities("Entity")
    engine.spatial.place(entity_id=entity_id, geometry=Point(0, 0))
    directly_composed = EntityManager(engine.state, engine.definitions)

    with pytest.raises(ValueError, match="spatial state"):
        directly_composed.remove(entity_id)

    assert entity_id in engine.state.entities
    assert entity_id in engine.state.placements


def test_sibling_bounds_require_mutual_overlap_permission() -> None:
    engine, (parent_id, first_id, second_id) = _engine_with_entities(
        "Parent", "First", "Second"
    )
    engine.spatial.place(
        entity_id=parent_id,
        geometry=Bounds(0, 0, 10, 10),
        bounds_kind=BoundsKind.AREA,
    )
    engine.spatial.place(
        entity_id=first_id,
        geometry=Bounds(1, 1, 4, 4),
        containing_entity_id=parent_id,
        bounds_kind=BoundsKind.STRUCTURE,
        overlap_policy=OverlapPolicy.ALLOW_SIBLING_OVERLAP,
    )
    with pytest.raises(ValueError, match="mutual opt-in"):
        engine.spatial.place(
            entity_id=second_id,
            geometry=Bounds(2, 2, 4, 4),
            containing_entity_id=parent_id,
            bounds_kind=BoundsKind.STRUCTURE,
        )
    engine.spatial.place(
        entity_id=second_id,
        geometry=Bounds(2, 2, 4, 4),
        containing_entity_id=parent_id,
        bounds_kind=BoundsKind.STRUCTURE,
        overlap_policy=OverlapPolicy.ALLOW_SIBLING_OVERLAP,
    )


def test_queries_use_the_exact_canonical_order() -> None:
    engine, ids = _engine_with_entities("Z", "A", "Area", "Child", "Unplaced")
    z_id, a_id, area_id, child_id, unplaced_id = ids
    engine.spatial.place(entity_id=z_id, geometry=Point(5, 0))
    engine.spatial.place(entity_id=a_id, geometry=Point(1, 0))
    engine.spatial.place(
        entity_id=area_id,
        geometry=Bounds(10, 10, 5, 5),
        bounds_kind=BoundsKind.AREA,
    )
    engine.spatial.place(
        entity_id=child_id,
        geometry=Point(11, 11),
        containing_entity_id=area_id,
    )
    engine.spatial.place(entity_id=unplaced_id, geometry=Point(20, 20))
    engine.spatial.unplace(unplaced_id)

    assert tuple(item.entity_id for item in engine.spatial.all()) == (
        a_id,
        z_id,
        area_id,
        unplaced_id,
        child_id,
    )
    assert engine.spatial.for_container(area_id)[0].entity_id == child_id


def test_spatial_state_round_trips_and_legacy_defaults_to_empty(tmp_path: Path) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    engine.definitions.register(Definition("thing"))
    placed = engine.entities.create(definition_key="thing", name="Placed")
    unplaced = engine.entities.create(definition_key="thing", name="Unplaced")
    engine.spatial.place(
        entity_id=placed.id,
        geometry=Bounds(-2, 3, 5, 7),
        bounds_kind=BoundsKind.AREA,
        overlap_policy=OverlapPolicy.ALLOW_SIBLING_OVERLAP,
    )
    engine.spatial.place(entity_id=unplaced.id, geometry=Point(8, 9))
    engine.spatial.unplace(unplaced.id)
    engine.save_world()

    loaded = repository.load_world()
    assert loaded.placements == engine.state.placements

    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        del payload["placements"]
        connection.execute(
            "UPDATE world_snapshots SET schema_version = 2, payload = ?",
            (json.dumps(payload),),
        )
    legacy = repository.load_world()
    assert legacy.placements == {}
    repository.save_world(legacy)
    with sqlite3.connect(database) as connection:
        version = connection.execute(
            "SELECT schema_version FROM world_snapshots WHERE id = 1"
        ).fetchone()[0]
    assert version == 6


@pytest.mark.parametrize("legacy_version", (1, 2))
def test_legacy_schema_ignores_stray_placement_payload(
    tmp_path: Path, legacy_version: int
) -> None:
    database = tmp_path / f"legacy-{legacy_version}.sqlite3"
    repository = SQLiteRepository(str(database))
    engine, (entity_id,) = _engine_with_entities("Entity")
    engine.spatial.place(entity_id=entity_id, geometry=Point(1, 2))
    repository.save_world(engine.state)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE world_snapshots SET schema_version = ? WHERE id = 1",
            (legacy_version,),
        )

    assert repository.load_world().placements == {}


def test_repository_rejects_invalid_persisted_spatial_references(
    tmp_path: Path,
) -> None:
    database = tmp_path / "invalid.sqlite3"
    repository = SQLiteRepository(str(database))
    repository.save_world(SimulationEngine().state)
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        payload["placements"] = [
            {
                "entity_id": "entity_missing",
                "geometry": {"kind": "point", "x": 0, "y": 0},
                "containing_entity_id": None,
                "bounds_kind": None,
                "overlap_policy": "reject",
            }
        ]
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(payload),),
        )

    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


def test_inspection_is_ordered_detached_and_absent_from_npc_context() -> None:
    engine, (npc_id, area_id) = _engine_with_entities("NPC", "Area")
    engine.spatial.place(entity_id=npc_id, geometry=Point(2, 3))
    engine.spatial.place(
        entity_id=area_id,
        geometry=Bounds(5, 6, 7, 8),
        bounds_kind=BoundsKind.AREA,
    )
    payload = EngineWorldInspector(engine).placements()

    assert tuple(item["entity_id"] for item in payload) == (npc_id, area_id)
    assert payload[0]["geometry"] == {"kind": "point", "x": 2, "y": 3}
    geometry = cast(MutableMapping[str, object], payload[0]["geometry"])
    geometry["x"] = 99
    assert cast(Point, engine.state.placements[npc_id].geometry).x == 2

    context = NPCContextAssembler(engine.state).assemble(holder_id=npc_id)
    assert "placement" not in repr(context).lower()
    assert "x': 2" not in repr(context)


class FailingEventManager:
    def record(self, **_values: object) -> None:
        raise RuntimeError("event failed")


def test_event_failure_leaves_placement_and_history_unchanged() -> None:
    engine, (entity_id,) = _engine_with_entities("Entity")
    manager = SpatialManager(engine.state, FailingEventManager())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="event failed"):
        manager.place(entity_id=entity_id, geometry=Point(0, 0))

    assert engine.state.placements == {}
    assert engine.state.events == {}
