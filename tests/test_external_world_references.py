import json
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from living_world.api.inspection import EngineWorldInspector
from living_world.api.server import create_app
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.core.definition import Definition
from living_world.external_world import ContactState, ExternalWorldReference
from living_world.repositories.sqlite_repository import (
    RepositoryLoadError,
    SQLiteRepository,
)
from living_world.simulation.simulation_engine import SimulationEngine


def _create_reference(engine: SimulationEngine, *, name: str = "River Guild"):
    return engine.external_world_references.create(
        name=name,
        role="regional grain supplier",
        allowed_imports=("tools",),
        allowed_exports=("grain",),
        capacity=40,
        delay_ticks=3,
        cost_per_unit=2,
        reliability=0.8,
    )


def test_reference_values_validate_strict_partial_contract() -> None:
    engine = SimulationEngine()
    reference = _create_reference(engine)
    assert reference.reliability == 0.8

    with pytest.raises(TypeError, match="capacity"):
        engine.external_world_references.create(
            name="Bad",
            role="supplier",
            capacity=True,
            delay_ticks=1,
            cost_per_unit=1,
            reliability=0.5,
        )
    with pytest.raises(ValueError, match="between zero and one"):
        engine.external_world_references.create(
            name="Bad",
            role="supplier",
            capacity=1,
            delay_ticks=1,
            cost_per_unit=1,
            reliability=1.1,
        )
    with pytest.raises(ValueError, match="duplicates"):
        engine.external_world_references.create(
            name="Bad",
            role="supplier",
            allowed_imports=("wood", "wood"),
            capacity=1,
            delay_ticks=1,
            cost_per_unit=1,
            reliability=0.5,
        )
    with pytest.raises(ValueError, match="internal ID"):
        engine.external_world_references.create(
            name="entity_000001",
            role="supplier",
            capacity=1,
            delay_ticks=1,
            cost_per_unit=1,
            reliability=0.5,
        )


@pytest.mark.parametrize(
    ("field", "value", "error"),
    (
        ("capacity", 0, ValueError),
        ("capacity", -1, ValueError),
        ("delay_ticks", -1, ValueError),
        ("delay_ticks", True, TypeError),
        ("cost_per_unit", -1, ValueError),
        ("cost_per_unit", 1.5, TypeError),
        ("reliability", True, TypeError),
        ("reliability", float("nan"), TypeError),
        ("reliability", float("inf"), TypeError),
        ("contact_state", "known", TypeError),
        ("allowed_imports", ["wood"], TypeError),
        ("allowed_exports", (1,), TypeError),
    ),
)
def test_reference_rejects_strict_boundary_values(
    field: str, value: object, error: type[Exception]
) -> None:
    arguments: dict[str, object] = {
        "name": "Guild",
        "role": "supplier",
        "capacity": 1,
        "delay_ticks": 1,
        "cost_per_unit": 1,
        "reliability": 0.5,
    }
    arguments[field] = value
    with pytest.raises(error):
        SimulationEngine().external_world_references.create(**arguments)  # type: ignore[arg-type]


def test_manager_enforces_unique_names_order_transitions_and_events() -> None:
    engine = SimulationEngine()
    first = _create_reference(engine, name="Zeta")
    second = _create_reference(engine, name="Alpha")
    assert (first.id, second.id) == (
        "external_reference_000001",
        "external_reference_000002",
    )
    assert tuple(item.id for item in engine.external_world_references.all()) == (
        first.id,
        second.id,
    )
    with pytest.raises(ValueError, match="unique"):
        _create_reference(engine, name=" zETA ")
    with pytest.raises(ValueError, match="Invalid contact transition"):
        engine.external_world_references.transition_contact(
            first.id, ContactState.CONTACTABLE
        )
    engine.external_world_references.transition_contact(first.id, ContactState.KNOWN)
    updated = engine.external_world_references.transition_contact(
        first.id, ContactState.CONTACTABLE
    )
    assert updated.contact_state is ContactState.CONTACTABLE
    event = tuple(engine.state.events.values())[-1]
    assert event.kind == "external_contact_state_changed"
    with pytest.raises(FrozenInstanceError):
        event.kind = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        event.attributes["current"] = "changed"  # type: ignore[index]


@pytest.mark.parametrize(
    ("source", "target", "allowed"),
    tuple(
        (
            source,
            target,
            (source, target)
            in {
                (ContactState.UNKNOWN, ContactState.KNOWN),
                (ContactState.KNOWN, ContactState.CONTACTABLE),
                (ContactState.KNOWN, ContactState.UNAVAILABLE),
                (ContactState.CONTACTABLE, ContactState.UNAVAILABLE),
                (ContactState.UNAVAILABLE, ContactState.CONTACTABLE),
            },
        )
        for source in ContactState
        for target in ContactState
    ),
)
def test_complete_contact_transition_matrix(
    source: ContactState, target: ContactState, allowed: bool
) -> None:
    engine = SimulationEngine()
    reference = engine.external_world_references.create(
        name="Guild",
        role="supplier",
        capacity=1,
        delay_ticks=0,
        cost_per_unit=0,
        reliability=1.0,
        contact_state=source,
    )
    if allowed:
        assert (
            engine.external_world_references.transition_contact(
                reference.id, target
            ).contact_state
            is target
        )
    else:
        with pytest.raises(ValueError, match="Invalid contact transition"):
            engine.external_world_references.transition_contact(reference.id, target)


@pytest.mark.parametrize("operation", ("create", "transition"))
def test_partial_event_failure_rolls_back_state_history_and_id(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    engine = SimulationEngine()
    existing = _create_reference(engine) if operation == "transition" else None
    events_before = dict(engine.state.events)
    original_record = engine.events.record

    def partial_record(**arguments: object) -> object:
        original_record(**arguments)  # type: ignore[arg-type]
        raise RuntimeError("recording failed after mutation")

    monkeypatch.setattr(engine.events, "record", partial_record)
    with pytest.raises(RuntimeError, match="after mutation"):
        if operation == "create":
            _create_reference(engine)
        else:
            assert existing is not None
            engine.external_world_references.transition_contact(
                existing.id, ContactState.KNOWN
            )

    assert engine.state.events == events_before
    if operation == "create":
        assert engine.state.external_world_references == {}
        monkeypatch.setattr(engine.events, "record", original_record)
        assert _create_reference(engine).id == "external_reference_000001"
    else:
        assert engine.external_world_references.get(existing.id) is existing


def test_npc_interpretation_filters_engine_policy_and_context_is_unchanged() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition("npc"))
    npc = engine.entities.create(definition_key="npc", name="Ari")
    before = NPCContextAssembler(engine.state).assemble(holder_id=npc.id)
    reference = _create_reference(engine)
    after = NPCContextAssembler(engine.state).assemble(holder_id=npc.id)

    assert before == after
    visible = engine.external_world_references.npc_interpretation(reference.id)
    assert visible.name == "River Guild"
    assert visible.role == "regional grain supplier"
    assert set(visible.__dataclass_fields__) == {"name", "role", "contact_description"}
    assert reference.id not in repr(visible)


def test_schema_four_roundtrip_and_legacy_versions_default_empty(
    tmp_path: Path,
) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    reference = _create_reference(engine)
    engine.external_world_references.transition_contact(
        reference.id, ContactState.KNOWN
    )
    engine.save_world()
    assert repository.load_world().external_world_references == (
        engine.state.external_world_references
    )

    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        for legacy_version in (1, 2, 3):
            connection.execute(
                "UPDATE world_snapshots SET schema_version = ?, payload = ? WHERE id = 1",
                (legacy_version, json.dumps(payload)),
            )
            connection.commit()
            assert repository.load_world().external_world_references == {}


def test_schema_four_rejects_duplicate_normalized_names(tmp_path: Path) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    _create_reference(engine, name="Guild")
    _create_reference(engine, name="Market")
    engine.save_world()
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        payload["external_world_references"][1]["name"] = " guild "
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(payload),),
        )
    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


def test_privileged_inspection_is_ordered_detached_and_http_exposed() -> None:
    engine = SimulationEngine()
    reference = _create_reference(engine)
    snapshot = EngineWorldInspector(engine).external_world_references()
    assert snapshot[0]["id"] == reference.id
    assert snapshot[0]["allowed_exports"] == ["grain"]
    snapshot[0]["allowed_exports"].append("ore")  # type: ignore[union-attr]
    assert reference.allowed_exports == ("grain",)
    assert (
        EngineWorldInspector(engine).world_summary()["external_world_reference_count"]
        == 1
    )

    # Exercise the route table without coupling this domain test to an HTTP client.
    paths = {route.path for route in create_app(engine).routes}
    assert "/world/external-references" in paths


def test_frozen_reference_cannot_be_mutated() -> None:
    reference = ExternalWorldReference(
        id="external_reference_000001",
        name="Guild",
        role="supplier",
        allowed_imports=(),
        allowed_exports=(),
        capacity=1,
        delay_ticks=0,
        cost_per_unit=0,
        reliability=1,
        contact_state=ContactState.UNKNOWN,
        created_tick=0,
    )
    with pytest.raises(FrozenInstanceError):
        reference.capacity = 2  # type: ignore[misc]
