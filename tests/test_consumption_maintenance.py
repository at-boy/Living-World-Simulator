from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from living_world.api.inspection import EngineWorldInspector
from living_world.api.server import create_app
from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.retrieval import RetrievedCognition
from living_world.core.definition import Definition
from living_world.needs import (
    ConsumptionPolicy,
    MaintenancePolicy,
    MaintenanceRequirement,
    NPCConsequenceInterpretation,
    StoragePolicy,
    StorageResourceRule,
)
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.simulation.simulation_engine import SimulationEngine


def _world() -> tuple[SimulationEngine, str, str]:
    engine = SimulationEngine()
    engine.definitions.register(Definition("thing", {}))
    owner = engine.entities.create(
        definition_key="thing",
        name="Town",
        attributes={
            "population": 2,
            "resources": {"food": 5, "water": 2, "wood": 1},
            "storage_capacity": 3,
        },
    )
    capability = engine.entities.create(
        definition_key="thing",
        name="Well",
        attributes={"is_constructed": True, "resources": {}, "storage_capacity": 2},
    )
    engine.relationships.create(
        kind="owns", source_id=owner.id, target_id=capability.id
    )
    return engine, owner.id, capability.id


def test_records_are_frozen_and_reject_bool_and_bad_ids() -> None:
    policy = ConsumptionPolicy("consumption_town", "owner", 1, 2)
    with pytest.raises(FrozenInstanceError):
        policy.owner_id = "other"  # type: ignore[misc]
    with pytest.raises((TypeError, ValueError)):
        ConsumptionPolicy("bad", "owner", True, 1)


def test_phase_order_arithmetic_events_and_same_tick_noop() -> None:
    engine, owner, capability = _world()
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 2, 1)
    )
    engine.consequences.create_maintenance(
        MaintenancePolicy(
            "maintenance_well",
            owner,
            capability,
            "Village well",
            (MaintenanceRequirement("wood", 1),),
            2,
            3,
            1,
            1,
        )
    )
    engine.consequences.create_storage(
        StoragePolicy(
            "storage_town",
            owner,
            (StorageResourceRule("food", 1), StorageResourceRule("water", 0)),
        )
    )
    engine.consequences.apply()
    assert engine.state.entities[owner].attributes["resources"] == {
        "food": 0,
        "water": 0,
        "wood": 0,
    }
    assert engine.state.maintenance_states["maintenance_well"].condition == 3
    kinds = [event.kind for event in engine.state.events.values()]
    assert kinds[-4:] == [
        "consumption_applied",
        "capability_upkeep_applied",
        "capability_recovered",
        "storage_spoilage_applied",
    ]
    count = len(kinds)
    engine.consequences.apply()
    assert len(engine.state.events) == count


def test_partial_consumption_and_transition_then_terminal_destruction_once() -> None:
    engine, owner, capability = _world()
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 3, 2)
    )
    engine.consequences.create_maintenance(
        MaintenancePolicy(
            "maintenance_well",
            owner,
            capability,
            "Village well",
            (MaintenanceRequirement("stone", 1),),
            1,
            2,
            1,
            1,
        )
    )
    engine.consequences.apply()
    assert engine.state.entities[owner].attributes["resources"]["food"] == 0
    assert engine.state.consumption_states["consumption_town"].food_shortage
    assert engine.state.entities[capability].destroyed_tick == 0
    assert [e.kind for e in engine.state.events.values()].count(
        "capability_destroyed"
    ) == 1
    engine.state.tick = 1
    engine.consequences.apply()
    assert engine.state.maintenance_states["maintenance_well"].last_processed_tick == 1
    assert [e.kind for e in engine.state.events.values()].count(
        "capability_destroyed"
    ) == 1


def test_storage_overflow_is_rule_ordered_then_routine_spoilage() -> None:
    engine, owner, _ = _world()
    engine.consequences.create_storage(
        StoragePolicy(
            "storage_town",
            owner,
            (StorageResourceRule("food", 1), StorageResourceRule("water", 1)),
        )
    )
    engine.consequences.apply()
    resources = engine.state.entities[owner].attributes["resources"]
    assert resources["food"] == 2 and resources["water"] == 1
    event = next(
        e for e in engine.state.events.values() if e.kind == "storage_spoilage_applied"
    )
    assert event.attributes["capacity"] == 5
    assert event.attributes["overflow"] == 2


def test_phase_rolls_back_all_mutation_on_late_event_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, owner, _ = _world()
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 1, 1)
    )
    engine.consequences.create_storage(
        StoragePolicy("storage_town", owner, (StorageResourceRule("food", 1),))
    )
    resources = dict(engine.state.entities[owner].attributes["resources"])
    event_ids = set(engine.state.events)
    original = engine.events.record

    def fail(*, kind: str, subject_id: str, attributes: dict[str, object]):
        if kind == "storage_spoilage_applied":
            raise RuntimeError("boom")
        return original(kind=kind, subject_id=subject_id, attributes=attributes)

    monkeypatch.setattr(engine.events, "record", fail)
    with pytest.raises(RuntimeError, match="boom"):
        engine.consequences.apply()
    assert engine.state.entities[owner].attributes["resources"] == resources
    assert set(engine.state.events) == event_ids


def test_safe_interpretations_contain_no_ids_or_numbers() -> None:
    engine, owner, _ = _world()
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 1, 1)
    )
    interpretation = engine.consequences.npc_interpretation("consumption_town")
    assert interpretation.label == "Food and water"
    assert interpretation.description == "Food and water use has not yet been assessed."


def test_schema_eight_round_trip_and_resume(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    engine = SimulationEngine(repository)
    engine.definitions.register(Definition("thing", {}))
    owner = engine.entities.create(
        definition_key="thing",
        name="Town",
        attributes={"population": 1, "resources": {"food": 4, "water": 4}},
    )
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner.id, 1, 1)
    )
    engine.step()
    engine.save_world()
    resumed = SimulationEngine(repository)
    resumed.definitions.register(Definition("thing", {}))
    assert resumed.state.consumption_policies == engine.state.consumption_policies
    assert resumed.state.consumption_states == engine.state.consumption_states
    resumed.step()
    assert resumed.state.entities[owner.id].attributes["resources"] == {
        "food": 2,
        "water": 2,
    }


def test_privileged_inspection_is_detached_and_get_only() -> None:
    engine, owner, _ = _world()
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_z", owner, 1, 1)
    )
    snapshot = EngineWorldInspector(engine).consequences()
    assert list(snapshot) == ["consumption", "storage", "maintenance"]
    consumption = snapshot["consumption"]
    assert isinstance(consumption, list)
    assert consumption[0]["policy"]["id"] == "consumption_z"
    consumption.clear()
    assert engine.state.consumption_policies
    routes = {route.path: route.methods for route in create_app(engine).routes}
    assert routes["/world/consequences"] == {"GET"}


def test_boundary_rejects_consequence_id_and_number_but_allows_safe_prose() -> None:
    engine, owner, _ = _world()
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 7, 1)
    )
    boundary = NPCInformationBoundary(engine.state)

    def context(text: str) -> NPCContext:
        record = RetrievedCognition("memory", text, 0.5, False)
        return NPCContext("Settler", (), (), (record,), ())

    with pytest.raises(ValueError, match="internal IDs"):
        boundary.validate_context(context("I saw consumption_town."))
    with pytest.raises(ValueError, match="numeric"):
        boundary.validate_context(context("The rate was 7."))
    boundary.validate_context(context("Food and water use is currently supplied."))


def test_late_ordinary_system_runs_before_consequences_and_needs() -> None:
    engine, owner, _ = _world()

    class Supply:
        def step(self, state: object) -> None:
            engine.state.entities[owner].attributes["resources"]["food"] += 1

    engine.register_system(Supply())
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 3, 1)
    )
    engine.step()
    assert engine.state.entities[owner].attributes["resources"]["food"] == 0


def test_mark_destroyed_requires_current_tick_and_is_same_tick_idempotent() -> None:
    engine, _, capability = _world()
    with pytest.raises(TypeError):
        engine.entities.mark_destroyed(capability, True)
    with pytest.raises(ValueError):
        engine.entities.mark_destroyed(capability, 1)
    engine.entities.mark_destroyed(capability, 0)
    engine.entities.mark_destroyed(capability, 0)
    assert engine.state.entities[capability].destroyed_tick == 0


def test_maintenance_capability_cannot_later_own_need_or_consequence() -> None:
    engine, owner, capability = _world()
    engine.consequences.create_maintenance(
        MaintenancePolicy(
            "maintenance_well",
            owner,
            capability,
            "Village well",
            (MaintenanceRequirement("wood", 1),),
            2,
            3,
            1,
            1,
        )
    )
    with pytest.raises(ValueError, match="live-required role"):
        engine.consequences.create_consumption(
            ConsumptionPolicy("consumption_well", capability, 1, 1)
        )


def test_creation_rolls_back_policy_state_and_partial_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, owner, _ = _world()

    def fail(**kwargs: object) -> None:
        engine.state.events["event_partial"] = next(iter(engine.state.events.values()), None)  # type: ignore[assignment]
        raise RuntimeError("creation failed")

    monkeypatch.setattr(engine.events, "record", fail)
    with pytest.raises(RuntimeError, match="creation failed"):
        engine.consequences.create_consumption(
            ConsumptionPolicy("consumption_town", owner, 1, 1)
        )
    assert engine.state.consumption_policies == {}
    assert engine.state.consumption_states == {}
    assert "event_partial" not in engine.state.events


def test_maintenance_owner_cannot_already_be_a_maintenance_capability() -> None:
    engine, owner, capability = _world()
    third = engine.entities.create(
        definition_key="thing", name="Mill", attributes={"is_constructed": True}
    )
    engine.relationships.create(kind="owns", source_id=capability, target_id=third.id)
    engine.consequences.create_maintenance(
        MaintenancePolicy(
            "maintenance_well",
            owner,
            capability,
            "Well",
            (MaintenanceRequirement("wood", 1),),
            2,
            2,
            1,
            1,
        )
    )
    before = set(engine.state.events)
    with pytest.raises(ValueError, match="live-required role"):
        engine.consequences.create_maintenance(
            MaintenancePolicy(
                "maintenance_mill",
                capability,
                third.id,
                "Mill",
                (MaintenanceRequirement("wood", 1),),
                2,
                2,
                1,
                1,
            )
        )
    assert "maintenance_mill" not in engine.state.maintenance_policies
    assert set(engine.state.events) == before


@pytest.mark.parametrize(
    "method", ("create_consumption", "create_storage", "create_maintenance")
)
def test_creation_rejects_duck_typed_policy_before_mutation(method: str) -> None:
    engine, owner, _ = _world()
    before = set(engine.state.events)
    fake = SimpleNamespace(id="consumption_fake", owner_id=owner)
    with pytest.raises(TypeError, match="policy must be"):
        getattr(engine.consequences, method)(fake)
    assert set(engine.state.events) == before


def test_loaded_validation_rejects_wrong_exact_record_types() -> None:
    engine, owner, _ = _world()
    engine.state.consumption_policies["consumption_fake"] = SimpleNamespace(id="consumption_fake", owner_id=owner)  # type: ignore[assignment]
    engine.state.consumption_states["consumption_fake"] = SimpleNamespace(policy_id="consumption_fake", last_processed_tick=None)  # type: ignore[assignment]
    with pytest.raises(TypeError, match="incorrect types"):
        engine.consequences.validate_loaded_state()


@pytest.mark.parametrize(
    "identifier",
    (
        "entity_000001",
        "need_food",
        "goal_found",
        "event_000001",
        "external_reference_000001",
        "external_dispatch_000001",
        "consumption_town",
    ),
)
def test_safe_consequence_text_rejects_every_canonical_engine_id(
    identifier: str,
) -> None:
    with pytest.raises(ValueError, match="engine identifier"):
        NPCConsequenceInterpretation(identifier, "Safe prose")
    _engine, owner, capability = _world()
    with pytest.raises(ValueError, match="engine identifier"):
        MaintenancePolicy(
            "maintenance_well",
            owner,
            capability,
            identifier,
            (MaintenanceRequirement("wood", 1),),
            1,
            1,
            1,
            1,
        )


@pytest.mark.parametrize(
    ("population", "food", "water", "expected"),
    [(0, 3, 3, (0, 0)), (2, 10, 10, (4, 2)), (2, 1, 0, (1, 0))],
)
def test_consumption_full_partial_and_zero_population(
    population: int, food: int, water: int, expected: tuple[int, int]
) -> None:
    engine, owner, _ = _world()
    engine.entities.set_attribute(entity_id=owner, key="population", value=population)
    engine.entities.set_attribute(
        entity_id=owner, key="resources", value={"food": food, "water": water}
    )
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 2, 1)
    )
    engine.consequences.apply()
    event = next(
        e for e in engine.state.events.values() if e.kind == "consumption_applied"
    )
    assert event.subject_id == "consumption_town"
    assert tuple(event.attributes) == ("owner_id", "food", "water")
    assert (
        event.attributes["food"]["consumed"],
        event.attributes["water"]["consumed"],
    ) == expected


@pytest.mark.parametrize("population", [None, True, -1, 1.5])
def test_consumption_malformed_population_fails_before_mutation(
    population: object,
) -> None:
    engine, owner, _ = _world()
    if population is None:
        engine.state.entities[owner].attributes.pop("population")
    else:
        engine.state.entities[owner].attributes["population"] = population
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 1, 1)
    )
    resources = deepcopy(engine.state.entities[owner].attributes["resources"])
    with pytest.raises((TypeError, ValueError)):
        engine.consequences.apply()
    assert engine.state.entities[owner].attributes["resources"] == resources


def test_shortage_transitions_and_all_or_nothing_upkeep_recovery() -> None:
    engine, owner, capability = _world()
    engine.state.entities[owner].attributes["resources"] = {
        "food": 0,
        "water": 0,
        "wood": 1,
        "stone": 0,
    }
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 1, 1)
    )
    engine.consequences.create_maintenance(
        MaintenancePolicy(
            "maintenance_well",
            owner,
            capability,
            "Well",
            (MaintenanceRequirement("wood", 1), MaintenanceRequirement("stone", 1)),
            2,
            3,
            1,
            1,
        )
    )
    engine.consequences.apply()
    assert engine.state.entities[owner].attributes["resources"]["wood"] == 1
    assert engine.state.maintenance_states["maintenance_well"].condition == 1
    engine.state.tick = 1
    engine.state.entities[owner].attributes["resources"] = {
        "food": 2,
        "water": 2,
        "wood": 1,
        "stone": 1,
    }
    engine.consequences.apply()
    kinds = [e.kind for e in engine.state.events.values()]
    assert kinds.count("consumption_shortage_recovered") == 2
    assert "maintenance_shortage_recovered" in kinds and "capability_recovered" in kinds
    assert engine.state.entities[owner].attributes["resources"]["wood"] == 0


def test_current_tick_partial_state_rejected_and_new_policy_joins_next_tick() -> None:
    engine, owner, _ = _world()
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner, 1, 1)
    )
    engine.consequences.apply()
    engine.state.tick = 1
    engine.consequences.create_storage(
        StoragePolicy("storage_town", owner, (StorageResourceRule("food", 0),))
    )
    engine.consequences.apply()
    assert engine.state.storage_states["storage_town"].last_processed_tick == 1
    engine.state.tick = 2
    engine.state.consumption_states["consumption_town"] = replace(
        engine.state.consumption_states["consumption_town"], last_processed_tick=2
    )
    with pytest.raises(ValueError, match="partially processed"):
        engine.consequences.apply()


def test_consumption_may_undercollateralize_work_lock_without_mutating_ledger(
    tmp_path: Path,
) -> None:
    from test_work_orders import _create, _engine

    from living_world.work import ResourceRequirement

    engine, settlement_id, npc_id = _engine()
    owner = engine.state.entities[settlement_id]
    owner.attributes["population"] = 1
    owner.attributes["resources"]["food"] = 2
    work = _create(
        engine, settlement_id, resources=(ResourceRequirement("food", 2),), tools=()
    )
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_work", settlement_id, 2, 0)
    )
    engine.consequences.apply()
    assert owner.attributes["resources"]["food"] == 0
    assert engine.work.active_reservations()[0].resources == (
        ResourceRequirement("food", 2),
    )
    repository = SQLiteRepository(str(tmp_path / "under-work.sqlite3"))
    repository.save_world(engine.state)
    assert repository.load_world().work_reservations == engine.state.work_reservations
