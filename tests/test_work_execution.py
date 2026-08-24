from copy import deepcopy
from dataclasses import replace

import pytest
from test_work_orders import _create, _engine

from living_world.core.definition import Definition
from living_world.external_world import ContactState
from living_world.managers.event_manager import EventManager
from living_world.needs import (
    ConsumptionPolicy,
    MaintenancePolicy,
    MaintenanceRequirement,
    NeedDefinition,
    NeedKind,
)
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial import Bounds, BoundsKind, Point
from living_world.work import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    MaintenanceWorkTarget,
    ResourceWorkTarget,
    WorkCategory,
    WorkExecutionSystem,
    WorkStatus,
)


def test_engine_registers_work_execution_before_consequences() -> None:
    engine = SimulationEngine()
    systems = engine._scheduler._systems
    work_index = next(
        i for i, system in enumerate(systems) if isinstance(system, WorkExecutionSystem)
    )
    consequence_index = next(
        i
        for i, system in enumerate(systems)
        if type(system).__name__ == "ConsequenceSystem"
    )
    assert work_index < consequence_index


def test_food_work_charges_once_progresses_and_applies_one_effect() -> None:
    engine, settlement_id, _ = _engine()
    work = _create(engine, settlement_id, labor_required=0, required_progress=3)

    engine.run(3)

    state = engine.state.work_states[work.id]
    assert state.status.value == "completed"
    assert state.inputs_charged_tick == 0
    assert engine.state.entities[settlement_id].attributes["resources"] == {
        "basket": 2,
        "seed": 3,
        "food": 5,
    }
    kinds = [event.kind for event in engine.state.events.values()]
    assert kinds.count("work_inputs_charged") == 1
    assert kinds.count("work_resource_produced") == 1
    assert kinds.count("work_progress_threshold_reached") == 3

    engine.step()

    assert [event.kind for event in engine.state.events.values()] == kinds


def test_charge_event_has_exact_sorted_payload() -> None:
    engine, settlement_id, _ = _engine()
    work = _create(engine, settlement_id, labor_required=0, required_progress=2)
    engine.step()
    event = next(
        e for e in engine.state.events.values() if e.kind == "work_inputs_charged"
    )
    reservation = engine.work.reservations_for(work.id)[0]
    assert event.subject_id == work.id
    assert dict(event.attributes) == {
        "reservation_id": reservation.id,
        "resources": ({"resource": "seed", "quantity": 2},),
    }


def test_priority_then_creation_then_id_controls_labor_competition() -> None:
    engine, settlement_id, _ = _engine()
    low = _create(engine, settlement_id, public_label="Low", priority=1)
    first_high = _create(engine, settlement_id, public_label="First high", priority=5)
    second_high = _create(engine, settlement_id, public_label="Second high", priority=5)
    engine.step()
    assert engine.state.work_states[first_high.id].status is WorkStatus.ACTIVE
    assert engine.state.work_states[low.id].status is WorkStatus.BLOCKED
    assert engine.state.work_states[second_high.id].status is WorkStatus.BLOCKED


def test_creation_tick_precedes_work_id_when_equal_priority_competes() -> None:
    engine, settlement_id, _ = _engine()
    lower_id = _create(
        engine,
        settlement_id,
        public_label="Lower ID but later creation",
        priority=5,
        tools=(),
        resources=(),
    )
    engine.state.tick = 1
    higher_id = _create(
        engine,
        settlement_id,
        public_label="Higher ID but earlier creation",
        priority=5,
        tools=(),
        resources=(),
    )
    engine.state.work_definitions[lower_id.id] = replace(lower_id, created_tick=1)
    engine.state.work_definitions[higher_id.id] = replace(higher_id, created_tick=0)

    engine.step()

    assert higher_id.id > lower_id.id
    assert engine.state.work_states[higher_id.id].status is WorkStatus.ACTIVE
    assert engine.state.work_states[lower_id.id].status is WorkStatus.BLOCKED


def test_unscheduled_and_working_labor_are_eligible_but_other_schedule_is_not() -> None:
    engine, settlement_id, unscheduled = _engine()
    for name, activity in (("Working", "working"), ("Sleeping", "sleeping")):
        npc = engine.entities.create(
            definition_key="npc",
            name=name,
            attributes={
                "npc_identity": {
                    "name": name,
                    "description": "Worker.",
                    "capability_descriptions": [],
                },
                "schedule": [{"start_tick": 0, "end_tick": 1, "activity": activity}],
                "active_activity": activity,
            },
        )
        engine.spatial.place(
            entity_id=npc.id, geometry=Point(2, 2), containing_entity_id=settlement_id
        )
    work = _create(
        engine,
        settlement_id,
        labor_required=2,
        tools=(),
        resources=(),
        required_progress=3,
    )
    engine.step()
    reservation = engine.work.reservations_for(work.id)[0]
    assert reservation.labor_entity_ids == (unscheduled, "entity_000003")


def test_deadline_is_exclusive_and_consumable_shortage_blocks() -> None:
    engine, settlement_id, _ = _engine()
    deadline = _create(
        engine,
        settlement_id,
        public_label="Deadline",
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=2,
        deadline_tick=1,
        priority=5,
    )
    short = _create(
        engine,
        settlement_id,
        public_label="Short",
        labor_required=0,
        tools=(),
        required_progress=1,
    )
    engine.state.entities[settlement_id].attributes["resources"]["seed"] = 0
    engine.step()
    assert engine.state.work_states[deadline.id].progress == 1
    assert (
        engine.state.work_states[short.id].status_reason
        == "Required consumables are unavailable."
    )
    engine.step()
    assert (
        engine.state.work_states[deadline.id].status_reason
        == "The work deadline expired."
    )


def test_work_effect_is_visible_to_consequences_needs_and_goals_in_same_tick() -> None:
    engine, settlement_id, _ = _engine()
    settlement = engine.state.entities[settlement_id]
    settlement.attributes["population"] = 1
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", settlement_id, 1, 1)
    )
    engine.needs.create(
        NeedDefinition("need_food", settlement_id, NeedKind.FOOD, 1, 0.2, 0.5, 2)
    )
    _create(
        engine,
        settlement_id,
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=1,
    )
    engine.step()
    assert engine.state.entities[settlement_id].attributes["resources"]["food"] == 4
    assert engine.state.need_states["need_food"].current.available == 4
    objective = engine.state.objective_states["objective_food"]
    assert "4 of 5 required" in objective.evidence[-1].description
    kinds = [event.kind for event in engine.state.events.values()]
    assert (
        kinds.index("work_resource_produced")
        < kinds.index("consumption_applied")
        < kinds.index("need_level_changed")
    )


@pytest.mark.parametrize("terminal", (WorkStatus.FAILED, WorkStatus.CANCELLED))
def test_terminal_prerequisite_fails_dependent_work(terminal) -> None:
    engine, settlement_id, _ = _engine()
    prerequisite = _create(
        engine,
        settlement_id,
        public_label="Prerequisite",
        labor_required=0,
        required_progress=2,
    )
    dependent = _create(
        engine,
        settlement_id,
        public_label="Dependent",
        prerequisite_work_ids=(prerequisite.id,),
        labor_required=0,
    )
    (engine.work.fail if terminal is WorkStatus.FAILED else engine.work.cancel)(
        prerequisite.id, "Stopped."
    )
    engine.step()
    assert engine.state.work_states[dependent.id].status is WorkStatus.FAILED
    assert (
        engine.state.work_states[dependent.id].status_reason
        == "A prerequisite cannot complete."
    )


def test_tool_undercollateralization_blocks_later_stable_work_and_recovers_once() -> (
    None
):
    engine, settlement_id, first_npc = _engine()
    second_npc = engine.entities.create(
        definition_key="npc",
        name="Nara",
        attributes={
            "npc_identity": {
                "name": "Nara",
                "description": "Worker.",
                "capability_descriptions": [],
            }
        },
    )
    engine.spatial.place(
        entity_id=second_npc.id,
        geometry=engine.state.placements[first_npc].geometry,
        containing_entity_id=settlement_id,
    )
    first = _create(
        engine, settlement_id, public_label="First", resources=(), required_progress=4
    )
    second = _create(
        engine, settlement_id, public_label="Second", resources=(), required_progress=4
    )
    for work, npc in ((first, first_npc), (second, second_npc.id)):
        engine.work.mark_ready(work.id)
        engine.work.assign_and_reserve(work.id, (npc,))
        engine.work.record_inputs_charged(work.id)
        engine.work.activate(work.id)
    engine.state.entities[settlement_id].attributes["resources"]["basket"] = 1

    engine.step()

    assert engine.state.work_states[first.id].status is WorkStatus.ACTIVE
    assert engine.state.work_states[second.id].status is WorkStatus.BLOCKED
    engine.state.entities[settlement_id].attributes["resources"]["basket"] = 2
    engine.step()
    assert engine.state.work_states[second.id].status is WorkStatus.ACTIVE
    recovered = [
        e
        for e in engine.state.events.values()
        if e.kind == "work_order_recovered" and e.subject_id == second.id
    ]
    assert len(recovered) == 1
    assert dict(recovered[0].attributes) == {
        "previous_status": "blocked",
        "current_status": "ready",
    }


def test_existing_reserved_higher_id_labor_continues_when_lower_id_is_free() -> None:
    engine, settlement_id, lower_id = _engine()
    higher = engine.entities.create(
        definition_key="npc",
        name="Nara",
        attributes={
            "npc_identity": {
                "name": "Nara",
                "description": "Worker.",
                "capability_descriptions": [],
            }
        },
    )
    engine.spatial.place(
        entity_id=higher.id, geometry=Point(2, 2), containing_entity_id=settlement_id
    )
    work = _create(engine, settlement_id, resources=(), required_progress=3)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (higher.id,))
    engine.work.record_inputs_charged(work.id)
    engine.work.activate(work.id)
    engine.step()
    current = engine.state.work_states[work.id]
    assert current.status is WorkStatus.ACTIVE
    assert engine.state.work_reservations[current.reservation_id].labor_entity_ids == (
        higher.id,
    )
    assert lower_id < higher.id


@pytest.mark.parametrize("location_kind", ("point", "bounds"))
def test_construction_uses_point_parent_but_bounds_location_as_parent(
    location_kind,
) -> None:
    engine, settlement_id, _ = _engine()
    engine.definitions.register(Definition("district"))
    engine.definitions.register(Definition("shelter"))
    district = engine.entities.create(definition_key="district", name="District")
    geometry = Point(3, 3) if location_kind == "point" else Bounds(2, 2, 4, 4)
    engine.spatial.place(
        entity_id=district.id,
        geometry=geometry,
        containing_entity_id=settlement_id,
        bounds_kind=None if location_kind == "point" else BoundsKind.AREA,
    )
    _create(
        engine,
        settlement_id,
        category=WorkCategory.BUILD_SHELTER,
        target=CapabilityWorkTarget("shelter", 1),
        location_id=district.id,
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=1,
    )
    engine.step()
    event = next(
        e
        for e in engine.state.events.values()
        if e.kind == "work_capability_constructed"
    )
    assert engine.state.placements[event.subject_id].containing_entity_id == (
        settlement_id if location_kind == "point" else district.id
    )


@pytest.mark.parametrize(
    ("category", "target_kind", "event_kind"),
    (
        (WorkCategory.GATHER_WATER, "water", "work_resource_produced"),
        (WorkCategory.PRODUCE_FOOD, "food", "work_resource_produced"),
        (WorkCategory.BUILD_SHELTER, "shelter", "work_capability_constructed"),
        (WorkCategory.BUILD_STORAGE, "storage", "work_capability_constructed"),
        (
            WorkCategory.MAINTAIN_CAPABILITY,
            "maintenance",
            "capability_condition_restored",
        ),
        (
            WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION,
            "external",
            "external_contact_state_changed",
        ),
    ),
)
def test_all_six_effects_use_exact_authoritative_event_payloads(
    category, target_kind, event_kind
) -> None:
    engine, settlement_id, _ = _engine()
    if target_kind in {"water", "food"}:
        target = ResourceWorkTarget(target_kind, 4)
    elif target_kind in {"shelter", "storage"}:
        engine.definitions.register(Definition(target_kind))
        target = CapabilityWorkTarget(target_kind, 2 if target_kind == "shelter" else 1)
    elif target_kind == "maintenance":
        engine.definitions.register(Definition("capability"))
        capability = engine.entities.create(
            definition_key="capability",
            name="Well",
            attributes={"is_constructed": True},
        )
        engine.relationships.create(
            kind="owns", source_id=settlement_id, target_id=capability.id
        )
        engine.consequences.create_maintenance(
            MaintenancePolicy(
                "maintenance_well",
                settlement_id,
                capability.id,
                "Well",
                (MaintenanceRequirement("basket", 1),),
                1,
                3,
                1,
                2,
            )
        )
        target = MaintenanceWorkTarget("maintenance_well")
    else:
        reference = engine.external_world_references.create(
            name="Guild",
            role="trader",
            capacity=2,
            delay_ticks=1,
            cost_per_unit=1,
            reliability=1.0,
            contact_state=ContactState.KNOWN,
        )
        target = ExternalConnectionWorkTarget(reference.id)
    work = _create(
        engine,
        settlement_id,
        category=category,
        target=target,
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=1,
    )

    engine.step()

    effect = next(e for e in engine.state.events.values() if e.kind == event_kind)
    if event_kind == "work_resource_produced":
        assert dict(effect.attributes) == {
            "work_id": work.id,
            "category": category.value,
            "resource": target_kind,
            "quantity": 4,
        }
    elif event_kind == "work_capability_constructed":
        assert dict(effect.attributes) == {
            "work_id": work.id,
            "settlement_id": settlement_id,
            "definition_key": target_kind,
            "ordinal": 1,
            "location_id": settlement_id,
        }
        constructed = [e for e in engine.state.events.values() if e.kind == event_kind]
        assert [engine.state.entities[e.subject_id].name for e in constructed] == (
            ["Shelter 1", "Shelter 2"] if target_kind == "shelter" else ["Storage 1"]
        )
    elif event_kind == "capability_condition_restored":
        assert dict(effect.attributes)["amount"] == 2
    else:
        assert dict(effect.attributes) == {
            "previous": "known",
            "current": "contactable",
        }


def test_already_contactable_connection_completes_without_duplicate_contact_event() -> (
    None
):
    engine, settlement_id, _ = _engine()
    reference = engine.external_world_references.create(
        name="Guild",
        role="trader",
        capacity=2,
        delay_ticks=1,
        cost_per_unit=1,
        reliability=1.0,
        contact_state=ContactState.CONTACTABLE,
    )
    work = _create(
        engine,
        settlement_id,
        category=WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION,
        target=ExternalConnectionWorkTarget(reference.id),
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=1,
    )
    before = [e.kind for e in engine.state.events.values()].count(
        "external_contact_state_changed"
    )
    engine.step()
    assert engine.state.work_states[work.id].status is WorkStatus.COMPLETED
    assert [e.kind for e in engine.state.events.values()].count(
        "external_contact_state_changed"
    ) == before


@pytest.mark.parametrize(
    "failing_kind", ("work_resource_produced", "work_order_completed")
)
def test_late_effect_or_completion_failure_rolls_back_every_work_phase_field(
    monkeypatch, failing_kind
) -> None:
    engine, settlement_id, _ = _engine()
    _create(engine, settlement_id, labor_required=0, required_progress=1)
    before = (
        deepcopy(engine.state.entities),
        dict(engine.state.relationships),
        dict(engine.state.placements),
        dict(engine.state.maintenance_states),
        dict(engine.state.external_world_references),
        dict(engine.state.work_states),
        dict(engine.state.work_reservations),
        dict(engine.state.events),
    )
    original = EventManager.record

    def fail_complete(self, *, kind, subject_id, attributes):
        if kind == failing_kind:
            raise RuntimeError("late work failure")
        return original(self, kind=kind, subject_id=subject_id, attributes=attributes)

    monkeypatch.setattr(EventManager, "record", fail_complete)
    with pytest.raises(RuntimeError, match="late work failure"):
        engine.step()
    assert (
        engine.state.entities,
        engine.state.relationships,
        engine.state.placements,
        engine.state.maintenance_states,
        engine.state.external_world_references,
        engine.state.work_states,
        engine.state.work_reservations,
        engine.state.events,
    ) == before


def test_failed_construction_phase_preserves_next_entity_relationship_and_event_ids(
    monkeypatch,
) -> None:
    engine, settlement_id, _ = _engine()
    engine.definitions.register(Definition("shelter"))
    work = _create(
        engine,
        settlement_id,
        category=WorkCategory.BUILD_SHELTER,
        target=CapabilityWorkTarget("shelter", 1),
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=1,
    )
    original = EventManager.record

    def fail_complete(self, *, kind, subject_id, attributes):
        if kind == "work_order_completed":
            raise RuntimeError("completion failed")
        return original(self, kind=kind, subject_id=subject_id, attributes=attributes)

    monkeypatch.setattr(EventManager, "record", fail_complete)
    with pytest.raises(RuntimeError):
        engine.step()
    assert "entity_000003" not in engine.state.entities
    assert "relationship_000001" not in engine.state.relationships
    monkeypatch.setattr(EventManager, "record", original)
    engine.step()
    constructed = next(
        e
        for e in engine.state.events.values()
        if e.kind == "work_capability_constructed"
    )
    assert constructed.subject_id == "entity_000003"
    assert "relationship_000001" in engine.state.relationships
    assert engine.state.work_states[work.id].status is WorkStatus.COMPLETED


def test_permanently_lost_maintenance_target_fails_without_effect() -> None:
    engine, settlement_id, _ = _engine()
    engine.definitions.register(Definition("capability"))
    capability = engine.entities.create(
        definition_key="capability",
        name="Well",
        attributes={"is_constructed": True},
    )
    engine.relationships.create(
        kind="owns", source_id=settlement_id, target_id=capability.id
    )
    engine.consequences.create_maintenance(
        MaintenancePolicy(
            "maintenance_well",
            settlement_id,
            capability.id,
            "Well",
            (MaintenanceRequirement("basket", 1),),
            1,
            3,
            1,
            2,
        )
    )
    work = _create(
        engine,
        settlement_id,
        category=WorkCategory.MAINTAIN_CAPABILITY,
        target=MaintenanceWorkTarget("maintenance_well"),
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=1,
    )
    engine.state.tick = 1
    engine.state.entities[capability.id].destroyed_tick = 0
    engine.state.maintenance_states["maintenance_well"] = replace(
        engine.state.maintenance_states["maintenance_well"],
        condition=0,
        last_processed_tick=0,
    )

    engine.step()

    state = engine.state.work_states[work.id]
    assert state.status is WorkStatus.FAILED
    assert state.status_reason == "The work target is permanently unavailable."
    assert all(
        event.kind != "capability_condition_restored"
        for event in engine.state.events.values()
    )


@pytest.mark.parametrize(
    "checkpoint", ("assigned", "charged", "partial", "blocked", "completed")
)
def test_save_resume_matches_uninterrupted_execution_at_every_checkpoint(
    tmp_path, checkpoint
) -> None:
    left, settlement_id, npc_id = _engine()
    work = _create(left, settlement_id, required_progress=3)
    left.work.mark_ready(work.id)
    left.work.assign_and_reserve(work.id, (npc_id,))
    if checkpoint in {"charged", "partial", "blocked", "completed"}:
        left.work.record_inputs_charged(work.id)
        left.work.activate(work.id)
    if checkpoint in {"partial", "blocked", "completed"}:
        left.work.record_progress(work.id, 1)
    if checkpoint == "blocked":
        left.work.block(work.id, "Waiting for eligible labor.")
    if checkpoint == "completed":
        left.work.record_progress(work.id, 2)
        left.work.complete(work.id)
    repository = SQLiteRepository(str(tmp_path / f"{checkpoint}.sqlite3"))
    repository.save_world(left.state)
    right = SimulationEngine(repository)
    for definition in left.definitions.all():
        right.definitions.register(definition)
    left.run(4)
    right.run(4)
    assert right.state == left.state
