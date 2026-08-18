import json
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.npc_cognition_client import ActionRequest
from living_world.core.definition import Definition
from living_world.core.run_metadata import RunMetadata
from living_world.external_world import ContactState
from living_world.external_world.dispatch import DispatchDirection, DispatchStatus
from living_world.external_world.dispatch_action import (
    DispatchOffer,
    ExternalDispatchActionHandler,
)
from living_world.managers.entity_manager import EntityManager
from living_world.repositories.sqlite_repository import (
    RepositoryLoadError,
    SQLiteRepository,
)
from living_world.simulation.simulation_engine import SimulationEngine


def _world(*, reliability: float = 1.0, delay: int = 1):
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    source = engine.entities.create(
        definition_key="settlement",
        name="Oakford",
        attributes={"resources": {"grain": 8, "tools": 0, "coin": 20}},
    )
    reference = engine.external_world_references.create(
        name="River Guild",
        role="regional exchange",
        allowed_imports=("grain",),
        allowed_exports=("tools",),
        capacity=5,
        delay_ticks=delay,
        cost_per_unit=2,
        reliability=reliability,
        contact_state=ContactState.CONTACTABLE,
    )
    engine.state.run_metadata = RunMetadata("test", 1, 42, "fingerprint")
    return engine, source, reference


def test_create_reserves_resources_and_reject_restores_atomically() -> None:
    engine, source, reference = _world()
    dispatch = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=3,
    )
    assert source.attributes["resources"] == {"grain": 5, "tools": 0, "coin": 14}
    assert dispatch.status is DispatchStatus.PENDING
    rejected = engine.external_dispatches.reject(dispatch.id)
    assert rejected.status is DispatchStatus.REJECTED
    assert source.attributes["resources"] == {"grain": 8, "tools": 0, "coin": 20}


def test_inbound_arrival_adds_goods_and_lost_dispatch_consumes_cost() -> None:
    engine, source, reference = _world(reliability=1.0, delay=1)
    dispatch = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.INBOUND,
        good="tools",
        quantity=2,
    )
    engine.step()
    assert (
        engine.external_dispatches.get(dispatch.id).status is DispatchStatus.IN_TRANSIT
    )
    engine.step()
    assert engine.external_dispatches.get(dispatch.id).status is DispatchStatus.ARRIVED
    assert source.attributes["resources"] == {"grain": 8, "tools": 2, "coin": 16}

    lost_engine, lost_source, lost_reference = _world(reliability=0.0, delay=0)
    lost = lost_engine.external_dispatches.create(
        source_entity_id=lost_source.id,
        reference_id=lost_reference.id,
        direction=DispatchDirection.INBOUND,
        good="tools",
        quantity=2,
    )
    lost_engine.step()
    assert lost_engine.external_dispatches.get(lost.id).status is DispatchStatus.LOST
    assert lost_source.attributes["resources"] == {"grain": 8, "tools": 0, "coin": 16}


@pytest.mark.parametrize(
    ("direction", "good", "quantity", "message"),
    (
        (DispatchDirection.OUTBOUND, "tools", 1, "not allowed"),
        (DispatchDirection.INBOUND, "grain", 1, "not allowed"),
        (DispatchDirection.OUTBOUND, "grain", 6, "capacity"),
        (DispatchDirection.OUTBOUND, "grain", 0, "positive"),
    ),
)
def test_invalid_dispatches_do_not_mutate_resources_or_history(
    direction: DispatchDirection, good: str, quantity: int, message: str
) -> None:
    engine, source, reference = _world()
    resources_before = dict(source.attributes["resources"])
    events_before = dict(engine.state.events)
    with pytest.raises(ValueError, match=message):
        engine.external_dispatches.create(
            source_entity_id=source.id,
            reference_id=reference.id,
            direction=direction,
            good=good,
            quantity=quantity,
        )
    assert source.attributes["resources"] == resources_before
    assert engine.state.events == events_before
    assert engine.state.external_dispatches == {}


def test_partial_event_failure_rolls_back_reservation_and_identifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, source, reference = _world()
    original = engine.events.record
    events_before = dict(engine.state.events)

    def broken(**arguments: object):
        original(**arguments)  # type: ignore[arg-type]
        raise RuntimeError("partial event failure")

    monkeypatch.setattr(engine.events, "record", broken)
    with pytest.raises(RuntimeError):
        engine.external_dispatches.create(
            source_entity_id=source.id,
            reference_id=reference.id,
            direction=DispatchDirection.OUTBOUND,
            good="grain",
            quantity=2,
        )
    assert source.attributes["resources"] == {"grain": 8, "tools": 0, "coin": 20}
    assert engine.state.events == events_before
    monkeypatch.setattr(engine.events, "record", original)
    assert (
        engine.external_dispatches.create(
            source_entity_id=source.id,
            reference_id=reference.id,
            direction=DispatchDirection.OUTBOUND,
            good="grain",
            quantity=2,
        ).id
        == "external_dispatch_000001"
    )


def test_coin_cannot_be_dispatch_good_or_break_gateway_validation() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    source = engine.entities.create(
        definition_key="settlement",
        name="Oakford",
        attributes={"resources": {"coin": 3}},
    )
    reference = engine.external_world_references.create(
        name="Mint",
        role="exchange",
        allowed_imports=("coin",),
        capacity=3,
        delay_ticks=0,
        cost_per_unit=1,
        reliability=1,
        contact_state=ContactState.CONTACTABLE,
    )
    with pytest.raises(ValueError, match="cannot be used"):
        engine.external_dispatches.create(
            source_entity_id=source.id,
            reference_id=reference.id,
            direction=DispatchDirection.OUTBOUND,
            good="coin",
            quantity=2,
        )
    handler = ExternalDispatchActionHandler(
        engine.external_dispatches,
        (
            DispatchOffer(
                "Send coins", reference.id, DispatchDirection.OUTBOUND, "coin", 2
            ),
        ),
    )
    result = NPCActionResolver((handler.action_option,), (handler,)).resolve(
        actor_id=source.id,
        request=ActionRequest(handler.action_option.key, "Send coins", "Trade."),
    )
    assert not result.accepted
    assert source.attributes["resources"] == {"coin": 3}


def test_invalid_transitions_and_partial_transition_events_are_atomic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, source, reference = _world()
    dispatch = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    with pytest.raises(ValueError, match="in-transit"):
        engine.external_dispatches.resolve(dispatch.id, arrived=True)
    departed = engine.external_dispatches.depart(dispatch.id)
    with pytest.raises(ValueError, match="pending"):
        engine.external_dispatches.reject(dispatch.id)

    original = engine.events.record
    events_before = dict(engine.state.events)

    def broken(**arguments: object):
        original(**arguments)  # type: ignore[arg-type]
        raise RuntimeError("partial transition event")

    monkeypatch.setattr(engine.events, "record", broken)
    with pytest.raises(RuntimeError):
        engine.external_dispatches.resolve(dispatch.id, arrived=True)
    assert engine.external_dispatches.get(dispatch.id) is departed
    assert engine.state.events == events_before


def test_action_gateway_accepts_only_offered_label_and_no_policy_arguments() -> None:
    engine, source, reference = _world()
    handler = ExternalDispatchActionHandler(
        engine.external_dispatches,
        (
            DispatchOffer(
                "Send grain", reference.id, DispatchDirection.OUTBOUND, "grain", 2
            ),
        ),
    )
    resolver = NPCActionResolver((handler.action_option,), (handler,))
    accepted = resolver.resolve(
        actor_id=source.id,
        request=ActionRequest(handler.action_option.key, "Send grain", "Trade."),
    )
    assert accepted.accepted and handler.last_created is not None
    rejected = resolver.resolve(
        actor_id=source.id,
        request=ActionRequest(
            handler.action_option.key,
            "Send grain",
            "Choose outcome.",
            {"outcome": "arrived"},
        ),
    )
    assert not rejected.accepted
    assert len(engine.state.external_dispatches) == 1
    unauthorized = resolver.resolve(
        actor_id="entity_999999",
        request=ActionRequest(handler.action_option.key, "Send grain", "Trade."),
    )
    assert not unauthorized.accepted
    malformed_label = resolver.resolve(
        actor_id=source.id,
        request=ActionRequest(handler.action_option.key, "Unknown", "Trade."),
    )
    assert not malformed_label.accepted


@pytest.mark.parametrize(
    "label",
    (
        "contact external_reference_000001",
        "dispatch external_dispatch_000001",
    ),
)
def test_dispatch_offer_rejects_internal_ids(label: str) -> None:
    with pytest.raises(ValueError, match="internal ID"):
        DispatchOffer(label, "reference", DispatchDirection.OUTBOUND, "grain", 1)


def test_entity_removal_cannot_orphan_active_or_terminal_dispatch_history() -> None:
    engine, source, reference = _world()
    dispatch = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    direct = EntityManager(engine.state, engine.definitions)
    for manager in (engine.entities, direct):
        with pytest.raises(ValueError, match="dispatch history"):
            manager.remove(source.id)
    engine.external_dispatches.reject(dispatch.id)
    with pytest.raises(ValueError, match="dispatch history"):
        direct.remove(source.id)
    assert source.id in engine.state.entities


def test_safe_perception_omits_ids_policy_and_exact_timing() -> None:
    engine, source, reference = _world()
    dispatch = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    perception = engine.external_dispatches.perception(dispatch.id)
    assert set(perception.__dataclass_fields__) == {"reference_name", "description"}
    assert dispatch.id not in repr(perception)
    with pytest.raises(FrozenInstanceError):
        perception.description = "changed"  # type: ignore[misc]


def test_deterministic_system_is_idempotent_after_terminal_event() -> None:
    first, source, reference = _world(reliability=0.5, delay=0)
    dispatch = first.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    first.step()
    status = first.external_dispatches.get(dispatch.id).status
    event_count = len(first.state.events)
    first.step()
    assert first.external_dispatches.get(dispatch.id).status is status
    assert len(first.state.events) == event_count

    second, source2, reference2 = _world(reliability=0.5, delay=0)
    dispatch2 = second.external_dispatches.create(
        source_entity_id=source2.id,
        reference_id=reference2.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    second.step()
    assert second.external_dispatches.get(dispatch2.id).status is status


@pytest.mark.parametrize("legacy_version", (1, 2, 3, 4))
def test_schema_five_roundtrip_resume_and_legacy_empty(
    tmp_path: Path, legacy_version: int
) -> None:
    database = tmp_path / f"world-{legacy_version}.sqlite3"
    repository = SQLiteRepository(str(database))
    engine, source, reference = _world(reliability=1.0, delay=2)
    dispatch = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.INBOUND,
        good="tools",
        quantity=2,
    )
    engine.step()
    repository.save_world(engine.state)
    resumed = SimulationEngine(repository)
    resumed.definitions.register(Definition("settlement"))
    assert (
        resumed.external_dispatches.get(dispatch.id).status is DispatchStatus.IN_TRANSIT
    )
    resumed.run(2)
    assert resumed.external_dispatches.get(dispatch.id).status is DispatchStatus.ARRIVED
    assert resumed.entities.get(source.id).attributes["resources"]["tools"] == 2

    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        connection.execute(
            "UPDATE world_snapshots SET schema_version = ?, payload = ? WHERE id = 1",
            (legacy_version, json.dumps(payload)),
        )
    assert repository.load_world().external_dispatches == {}


def test_schema_five_rejects_malformed_dispatch_reference(tmp_path: Path) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine, source, reference = _world()
    engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    repository.save_world(engine.state)
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        payload["external_dispatches"][0]["reference_id"] = "missing"
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(payload),),
        )
    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_entity_id", "missing"),
        ("reserved_cost", 999),
        ("quantity", 999),
        ("created_tick", 5),
    ),
)
def test_schema_five_rejects_malformed_dispatch_policy_and_timing(
    tmp_path: Path, field: str, value: object
) -> None:
    database = tmp_path / f"malformed-{field}.sqlite3"
    repository = SQLiteRepository(str(database))
    engine, source, reference = _world()
    dispatch = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    engine.external_dispatches.depart(dispatch.id)
    repository.save_world(engine.state)
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        payload["external_dispatches"][0][field] = value
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(payload),),
        )
    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


def test_multiple_dispatches_process_in_lexical_identifier_order() -> None:
    engine, source, reference = _world(delay=5)
    first = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    second = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    engine.state.external_dispatches = {second.id: second, first.id: first}
    engine.step()
    departed = [
        event.subject_id
        for event in engine.state.events.values()
        if event.kind == "external_dispatch_departed"
    ]
    assert departed == [first.id, second.id]


def test_privileged_dispatch_inspection_is_detached_and_ordered() -> None:
    engine, source, reference = _world()
    dispatch = engine.external_dispatches.create(
        source_entity_id=source.id,
        reference_id=reference.id,
        direction=DispatchDirection.OUTBOUND,
        good="grain",
        quantity=1,
    )
    from living_world.api.inspection import EngineWorldInspector

    snapshot = EngineWorldInspector(engine).external_dispatches()
    assert snapshot[0]["id"] == dispatch.id
    snapshot[0]["status"] = "lost"
    assert dispatch.status is DispatchStatus.PENDING
    assert EngineWorldInspector(engine).world_summary()["external_dispatch_count"] == 1
