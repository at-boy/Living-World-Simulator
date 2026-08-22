from dataclasses import FrozenInstanceError, replace

import pytest

from living_world.core.definition import Definition
from living_world.external_world.model import ContactState
from living_world.goals import (
    GoalDefinition,
    GoalOwnerKind,
    ObjectiveDefinition,
    ResourceMinimumCriterion,
)
from living_world.needs import (
    MaintenancePolicy,
    MaintenanceRequirement,
    MaintenanceState,
)
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial import Bounds, BoundsKind, Point
from living_world.work import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    MaintenanceWorkTarget,
    ResourceRequirement,
    ResourceWorkTarget,
    ToolRequirement,
    WorkCategory,
    WorkState,
    WorkStatus,
)


def _engine() -> tuple[SimulationEngine, str, str]:
    engine = SimulationEngine()
    for key in ("settlement", "npc"):
        engine.definitions.register(Definition(key))
    settlement = engine.entities.create(
        definition_key="settlement",
        name="Oakford",
        attributes={"resources": {"basket": 2, "seed": 5}},
    )
    npc = engine.entities.create(
        definition_key="npc",
        name="Mara",
        attributes={
            "npc_identity": {
                "name": "Mara",
                "description": "A careful worker.",
                "capability_descriptions": [],
            }
        },
    )
    engine.spatial.place(
        entity_id=settlement.id,
        geometry=Bounds(0, 0, 10, 10),
        bounds_kind=BoundsKind.AREA,
    )
    engine.spatial.place(
        entity_id=npc.id, geometry=Point(1, 1), containing_entity_id=settlement.id
    )
    objective = ObjectiveDefinition(
        "objective_food",
        "Produce food",
        "Produce food",
        "Grow a dependable food supply.",
        (ResourceMinimumCriterion("food", 5),),
        authorized_action_categories=("produce_food",),
    )
    goal = GoalDefinition(
        "goal_home",
        GoalOwnerKind.SETTLEMENT,
        settlement.id,
        "Build a home",
        "Build a home",
        "Help the settlement thrive.",
        (objective.id,),
        authorized_action_categories=("settlement_work",),
    )
    engine.goals.create(goal, (objective,))
    return engine, settlement.id, npc.id


def _create(engine: SimulationEngine, settlement_id: str, **changes):
    values = {
        "category": WorkCategory.PRODUCE_FOOD,
        "target": ResourceWorkTarget("food", 5),
        "public_label": "Plant the first crop",
        "settlement_id": settlement_id,
        "objective_id": "objective_food",
        "location_id": settlement_id,
        "labor_required": 1,
        "tools": (ToolRequirement("basket", 1),),
        "resources": (ResourceRequirement("seed", 2),),
        "required_progress": 3,
        "priority": 2,
    }
    values.update(changes)
    return engine.work.create(**values)


def test_lifecycle_reserves_without_deducting_and_releases_in_event_order() -> None:
    engine, settlement_id, npc_id = _engine()
    definition = _create(engine, settlement_id)
    with pytest.raises(FrozenInstanceError):
        definition.priority = 4  # type: ignore[misc]
    engine.work.mark_ready(definition.id)
    before = dict(engine.state.entities[settlement_id].attributes["resources"])
    assigned = engine.work.assign_and_reserve(definition.id, (npc_id,))
    assert assigned.status is WorkStatus.ASSIGNED
    assert engine.state.entities[settlement_id].attributes["resources"] == before
    engine.work.activate(definition.id)
    engine.work.record_progress(definition.id, 3)
    engine.work.complete(definition.id)
    kinds = [event.kind for event in engine.state.events.values()]
    assert kinds[-2:] == ["work_reservation_released", "work_order_completed"]
    assert engine.work.active_reservations() == ()


def test_labor_and_aggregate_inputs_cannot_be_double_reserved() -> None:
    engine, settlement_id, npc_id = _engine()
    first = _create(engine, settlement_id)
    second = _create(engine, settlement_id, public_label="Plant another crop")
    for item in (first, second):
        engine.work.mark_ready(item.id)
    engine.work.assign_and_reserve(first.id, (npc_id,))
    with pytest.raises(ValueError, match="laborer"):
        engine.work.assign_and_reserve(second.id, (npc_id,))
    engine.work.block(first.id, "Waiting for another worker.")
    engine.state.entities[settlement_id].attributes["resources"]["seed"] = 1
    with pytest.raises(ValueError, match="Insufficient"):
        engine.work.assign_and_reserve(second.id, (npc_id,))


def test_block_releases_and_reassignment_creates_history() -> None:
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    engine.work.activate(work.id)
    engine.work.record_progress(work.id, 1)
    engine.work.block(work.id, "Rain stopped the work.")
    release, blocked = tuple(engine.state.events.values())[-2:]
    assert dict(release.attributes) == {"work_id": work.id, "release_status": "blocked"}
    assert dict(blocked.attributes) == {
        "previous_status": "active",
        "current_status": "blocked",
        "reason": "Rain stopped the work.",
    }
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    assert len(engine.work.reservations_for(work.id)) == 2
    assert engine.state.work_states[work.id].progress == 1


def test_creation_reference_and_target_validation_is_atomic() -> None:
    engine, settlement_id, _ = _engine()
    with pytest.raises(ValueError, match="target"):
        _create(
            engine,
            settlement_id,
            category=WorkCategory.GATHER_WATER,
            target=ResourceWorkTarget("food", 1),
        )
    assert engine.state.work_definitions == {}


def test_safe_interpretation_hides_authoritative_work_details() -> None:
    engine, settlement_id, _ = _engine()
    work = _create(engine, settlement_id)
    result = engine.work.npc_interpretation(work.id)
    assert result.label == "Plant the first crop"
    assert result.description == "This work is being considered."
    assert not hasattr(result, "id") and not hasattr(result, "progress")


def test_priority_query_order_is_deterministic() -> None:
    engine, settlement_id, _ = _engine()
    low = _create(engine, settlement_id, priority=1)
    high = _create(engine, settlement_id, public_label="Urgent planting", priority=9)
    assert [x.id for x in engine.work.all()] == [high.id, low.id]


def test_schema_nine_round_trip_preserves_work_and_reservations(tmp_path) -> None:
    repository = SQLiteRepository(str(tmp_path / "work.sqlite3"))
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    repository.save_world(engine.state)
    loaded = repository.load_world()
    assert loaded.work_definitions == engine.state.work_definitions
    assert loaded.work_states == engine.state.work_states
    assert loaded.work_reservations == engine.state.work_reservations


@pytest.mark.parametrize(
    "state",
    (
        WorkState("work_000001", progress=1),
        WorkState(
            "work_000001", WorkStatus.ACTIVE, reservation_id="work_reservation_000001"
        ),
        WorkState("work_000001", WorkStatus.COMPLETED, progress=3, resolution_tick=0),
        WorkState("work_000001", WorkStatus.BLOCKED),
    ),
)
def test_loaded_state_rejects_invalid_status_tick_matrix(state: WorkState) -> None:
    engine, settlement_id, _ = _engine()
    work = _create(engine, settlement_id)
    engine.state.work_states[work.id] = state
    with pytest.raises((TypeError, ValueError)):
        engine.work.validate_loaded_state()


def test_loaded_state_rejects_noncanonical_keys_and_reservation_graph() -> None:
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    reservation = next(iter(engine.state.work_reservations.values()))
    engine.state.work_reservations["bad"] = replace(
        reservation, id="work_reservation_000002"
    )
    with pytest.raises(ValueError, match="canonical IDs"):
        engine.work.validate_loaded_state()


def test_release_then_transition_event_failure_rolls_back(monkeypatch) -> None:
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    before_state = engine.state.work_states[work.id]
    before_reservation = next(iter(engine.state.work_reservations.values()))
    original = engine.events.record
    calls = 0

    def fail_second(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("event failure")
        return original(**kwargs)

    monkeypatch.setattr(engine.events, "record", fail_second)
    with pytest.raises(RuntimeError, match="event failure"):
        engine.work.block(work.id, "Waiting.")
    assert engine.state.work_states[work.id] == before_state
    assert next(iter(engine.state.work_reservations.values())) == before_reservation


def test_spatial_ancestor_cannot_move_while_descendant_labor_is_reserved() -> None:
    engine, settlement_id, npc_id = _engine()
    engine.definitions.register(Definition("district"))
    district = engine.entities.create(definition_key="district", name="Fields")
    engine.spatial.place(
        entity_id=district.id,
        geometry=Bounds(0, 0, 5, 5),
        containing_entity_id=settlement_id,
        bounds_kind=BoundsKind.AREA,
    )
    engine.spatial.replace(
        entity_id=npc_id, geometry=Point(1, 1), containing_entity_id=district.id
    )
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    with pytest.raises(ValueError, match="required by nonterminal work"):
        engine.spatial.replace(
            entity_id=district.id,
            geometry=Bounds(1, 1, 5, 5),
            containing_entity_id=settlement_id,
            bounds_kind=BoundsKind.AREA,
        )


@pytest.mark.parametrize(
    "corruption", ("terminal_then_later", "overlap", "mismatch", "nonterminal_terminal")
)
def test_loaded_reservation_history_rejects_invalid_chronology(corruption: str) -> None:
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    engine.work.activate(work.id)
    engine.work.record_progress(work.id, 1)
    engine.work.block(work.id, "Paused.")
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    history = engine.work.reservations_for(work.id)
    first, second = history
    if corruption == "terminal_then_later":
        engine.state.work_reservations[first.id] = replace(
            first, release_status=WorkStatus.CANCELLED
        )
    elif corruption == "overlap":
        engine.state.work_reservations[first.id] = replace(first, released_tick=1)
    elif corruption == "mismatch":
        engine.state.work_reservations[second.id] = replace(
            second, released_tick=0, release_status=WorkStatus.FAILED
        )
        engine.state.work_states[work.id] = replace(
            engine.state.work_states[work.id],
            status=WorkStatus.CANCELLED,
            reservation_id=None,
            status_reason="Stopped.",
            resolution_tick=0,
        )
    else:
        engine.state.work_reservations[second.id] = replace(
            second, released_tick=0, release_status=WorkStatus.CANCELLED
        )
        engine.state.work_states[work.id] = replace(
            engine.state.work_states[work.id],
            status=WorkStatus.READY,
            reservation_id=None,
        )
    with pytest.raises(ValueError):
        engine.work.validate_loaded_state()


def test_same_tick_block_and_reassignment_is_valid_loaded_history() -> None:
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    engine.work.block(work.id, "Paused.")
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    engine.work.validate_loaded_state()


@pytest.mark.parametrize("terminal", (WorkStatus.CANCELLED, WorkStatus.FAILED))
def test_terminal_release_paths_and_exact_event_payloads(terminal: WorkStatus) -> None:
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    created = tuple(engine.state.events.values())[-1]
    assert set(created.attributes) == {
        "category",
        "target",
        "public_label",
        "settlement_id",
        "objective_id",
        "location_id",
        "prerequisite_work_ids",
        "labor_required",
        "tools",
        "resources",
        "required_progress",
        "priority",
        "deadline_tick",
    }
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    if terminal is WorkStatus.CANCELLED:
        engine.work.cancel(work.id, "Stopped.")
    else:
        engine.work.fail(work.id, "Failed.")
    release, transition = tuple(engine.state.events.values())[-2:]
    assert release.kind == "work_reservation_released"
    assert dict(release.attributes) == {
        "work_id": work.id,
        "release_status": terminal.value,
    }
    assert transition.kind == f"work_order_{terminal.value}"
    reason = "Stopped." if terminal is WorkStatus.CANCELLED else "Failed."
    assert dict(transition.attributes) == {
        "previous_status": "assigned",
        "current_status": terminal.value,
        "reason": reason,
    }
    engine.work.validate_loaded_state()


def test_cancel_before_assignment_has_no_terminal_reservation() -> None:
    engine, settlement_id, _ = _engine()
    work = _create(engine, settlement_id)
    engine.work.cancel(work.id, "Withdrawn.")
    assert engine.work.reservations_for(work.id) == ()
    engine.work.validate_loaded_state()


def test_prerequisites_require_strict_completed_same_settlement_history() -> None:
    engine, settlement_id, _ = _engine()
    prerequisite = _create(
        engine,
        settlement_id,
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=1,
    )
    dependent = _create(
        engine,
        settlement_id,
        public_label="Dependent crop",
        prerequisite_work_ids=(prerequisite.id,),
    )
    with pytest.raises(ValueError, match="prerequisite"):
        engine.work.mark_ready(dependent.id)
    engine.work.mark_ready(prerequisite.id)
    engine.work.assign_and_reserve(prerequisite.id, ())
    engine.work.activate(prerequisite.id)
    engine.work.record_progress(prerequisite.id, 1)
    engine.work.complete(prerequisite.id)
    assert engine.work.mark_ready(dependent.id).status is WorkStatus.READY
    engine.state.work_definitions[dependent.id] = replace(
        dependent, prerequisite_work_ids=(dependent.id,)
    )
    with pytest.raises(ValueError, match="prerequisite"):
        engine.work.validate_loaded_state()


def test_cross_kind_locks_share_one_settlement_pool() -> None:
    engine, settlement_id, npc_id = _engine()
    first = _create(
        engine, settlement_id, tools=(ToolRequirement("basket", 2),), resources=()
    )
    second = _create(
        engine,
        settlement_id,
        public_label="Use baskets as inputs",
        tools=(),
        resources=(ResourceRequirement("basket", 1),),
        labor_required=0,
    )
    for work in (first, second):
        engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(first.id, (npc_id,))
    with pytest.raises(ValueError, match="Insufficient unreserved"):
        engine.work.assign_and_reserve(second.id, ())


def test_progress_priority_bounds_and_terminal_immutability() -> None:
    engine, settlement_id, _ = _engine()
    work = _create(
        engine,
        settlement_id,
        labor_required=0,
        tools=(),
        resources=(),
        required_progress=2,
    )
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, ())
    engine.work.activate(work.id)
    with pytest.raises(ValueError):
        engine.work.record_progress(work.id, 3)
    engine.work.record_progress(work.id, 2)
    engine.work.complete(work.id)
    for operation in (
        lambda: engine.work.set_priority(work.id, 9),
        lambda: engine.work.cancel(work.id, "No."),
        lambda: engine.work.fail(work.id, "No."),
        lambda: engine.work.mark_ready(work.id),
    ):
        with pytest.raises(ValueError):
            operation()


@pytest.mark.parametrize("operation", ("create", "assign", "progress", "priority"))
def test_event_failure_rolls_back_mutation_and_allocators(
    monkeypatch, operation: str
) -> None:
    engine, settlement_id, npc_id = _engine()
    work = None
    if operation != "create":
        work = _create(engine, settlement_id)
        engine.work.mark_ready(work.id)
    if operation in {"progress"}:
        engine.work.assign_and_reserve(work.id, (npc_id,))
        engine.work.activate(work.id)
    before = (
        dict(engine.state.work_definitions),
        dict(engine.state.work_states),
        dict(engine.state.work_reservations),
    )
    monkeypatch.setattr(
        engine.events,
        "record",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("event failure")),
    )
    with pytest.raises(RuntimeError, match="event failure"):
        if operation == "create":
            _create(engine, settlement_id)
        elif operation == "assign":
            engine.work.assign_and_reserve(work.id, (npc_id,))
        elif operation == "progress":
            engine.work.record_progress(work.id, 1)
        else:
            engine.work.set_priority(work.id, 7)
    assert (
        engine.state.work_definitions,
        engine.state.work_states,
        engine.state.work_reservations,
    ) == before


def test_undercollateralized_lock_round_trips_and_next_ids_resume(tmp_path) -> None:
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    engine.state.entities[settlement_id].attributes["resources"]["seed"] = 0
    repository = SQLiteRepository(str(tmp_path / "under.sqlite3"))
    repository.save_world(engine.state)
    loaded_engine = SimulationEngine(repository)
    assert (
        loaded_engine.state.entities[settlement_id].attributes["resources"]["seed"] == 0
    )
    assert loaded_engine.work.active_reservations()[0].resources == (
        ResourceRequirement("seed", 2),
    )
    loaded_engine.work.block(work.id, "Inputs depleted.")
    loaded_engine.work.mark_ready(work.id)
    loaded_engine.state.entities[settlement_id].attributes["resources"]["seed"] = 2
    reassigned = loaded_engine.work.assign_and_reserve(work.id, (npc_id,))
    assert reassigned.reservation_id == "work_reservation_000002"
    next_work = _create(
        loaded_engine,
        settlement_id,
        public_label="Next crop",
        tools=(),
        resources=(),
        labor_required=0,
    )
    assert next_work.id == "work_000002"


def _all_targets(engine: SimulationEngine, settlement_id: str):
    capability = engine.entities.create(
        definition_key="npc", name="Mill", attributes={"is_constructed": True}
    )
    policy = MaintenancePolicy(
        "maintenance_mill",
        settlement_id,
        capability.id,
        "Mill",
        (MaintenanceRequirement("wood", 1),),
        2,
        3,
        1,
        1,
    )
    engine.state.maintenance_policies[policy.id] = policy
    engine.state.maintenance_states[policy.id] = MaintenanceState(policy.id, 2)
    reference = engine.external_world_references.create(
        name="River Guild",
        role="trader",
        capacity=5,
        delay_ticks=1,
        cost_per_unit=0,
        reliability=1.0,
        contact_state=ContactState.CONTACTABLE,
    )
    return {
        WorkCategory.GATHER_WATER: ResourceWorkTarget("water", 1),
        WorkCategory.PRODUCE_FOOD: ResourceWorkTarget("food", 1),
        WorkCategory.BUILD_SHELTER: CapabilityWorkTarget("shelter", 1),
        WorkCategory.BUILD_STORAGE: CapabilityWorkTarget("storage", 1),
        WorkCategory.MAINTAIN_CAPABILITY: MaintenanceWorkTarget(policy.id),
        WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION: ExternalConnectionWorkTarget(
            reference.id
        ),
    }


@pytest.mark.parametrize("category", tuple(WorkCategory))
def test_all_six_categories_construct_with_exact_target_family(
    category: WorkCategory,
) -> None:
    engine, settlement_id, _ = _engine()
    targets = _all_targets(engine, settlement_id)
    work = _create(
        engine,
        settlement_id,
        category=category,
        target=targets[category],
        public_label=f"Public {category.value.replace('_', ' ')}",
    )
    assert work.category is category
    assert type(work.target) is type(targets[category])


@pytest.mark.parametrize("category", tuple(WorkCategory))
@pytest.mark.parametrize("target_key", tuple(WorkCategory))
def test_every_invalid_category_target_pairing_is_rejected(
    category: WorkCategory, target_key: WorkCategory
) -> None:
    expected_family = {
        WorkCategory.GATHER_WATER: ResourceWorkTarget,
        WorkCategory.PRODUCE_FOOD: ResourceWorkTarget,
        WorkCategory.BUILD_SHELTER: CapabilityWorkTarget,
        WorkCategory.BUILD_STORAGE: CapabilityWorkTarget,
        WorkCategory.MAINTAIN_CAPABILITY: MaintenanceWorkTarget,
        WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION: ExternalConnectionWorkTarget,
    }
    engine, settlement_id, _ = _engine()
    targets = _all_targets(engine, settlement_id)
    target = targets[target_key]
    if type(target) is expected_family[category]:
        pytest.skip("This combination has the valid target family.")
    with pytest.raises(ValueError, match="target type"):
        _create(
            engine,
            settlement_id,
            category=category,
            target=target,
            public_label="Invalid pairing",
        )


@pytest.mark.parametrize(
    "category,resource",
    ((WorkCategory.GATHER_WATER, "food"), (WorkCategory.PRODUCE_FOOD, "water")),
)
def test_resource_category_requires_exact_resource_name(
    category: WorkCategory, resource: str
) -> None:
    engine, settlement_id, _ = _engine()
    with pytest.raises(ValueError, match="does not match"):
        _create(
            engine,
            settlement_id,
            category=category,
            target=ResourceWorkTarget(resource, 1),
        )


def test_maintenance_creation_requires_live_positive_but_loaded_history_allows_loss() -> (
    None
):
    engine, settlement_id, _ = _engine()
    target = _all_targets(engine, settlement_id)[WorkCategory.MAINTAIN_CAPABILITY]
    _create(
        engine, settlement_id, category=WorkCategory.MAINTAIN_CAPABILITY, target=target
    )
    policy = engine.state.maintenance_policies[target.policy_id]
    engine.state.maintenance_states[target.policy_id] = replace(
        engine.state.maintenance_states[target.policy_id], condition=0
    )
    engine.state.entities[policy.capability_id].destroyed_tick = 0
    engine.work.validate_loaded_state()
    with pytest.raises(ValueError, match="live positive-condition"):
        _create(
            engine,
            settlement_id,
            category=WorkCategory.MAINTAIN_CAPABILITY,
            target=target,
            public_label="Another maintenance",
        )


def test_exact_full_payloads_for_nonterminal_and_completion_event_kinds() -> None:
    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.set_priority(work.id, 5)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    engine.work.activate(work.id)
    engine.work.record_progress(work.id, 3)
    engine.work.complete(work.id)
    events = {
        event.kind: event
        for event in engine.state.events.values()
        if event.subject_id in {work.id, "work_reservation_000001"}
    }
    assert dict(events["work_order_created"].attributes) == {
        "category": "produce_food",
        "target": {"kind": "resource", "resource": "food", "quantity": 5},
        "public_label": "Plant the first crop",
        "settlement_id": settlement_id,
        "objective_id": "objective_food",
        "location_id": settlement_id,
        "prerequisite_work_ids": (),
        "labor_required": 1,
        "tools": ({"tool": "basket", "quantity": 1},),
        "resources": ({"resource": "seed", "quantity": 2},),
        "required_progress": 3,
        "priority": 2,
        "deadline_tick": None,
    }
    assert dict(events["work_order_priority_changed"].attributes) == {
        "previous_priority": 2,
        "current_priority": 5,
    }
    assert dict(events["work_order_ready"].attributes) == {
        "previous_status": "proposed",
        "current_status": "ready",
    }
    assert dict(events["work_reservation_created"].attributes) == {
        "work_id": work.id,
        "labor_entity_ids": (npc_id,),
        "tools": ({"tool": "basket", "quantity": 1},),
        "resources": ({"resource": "seed", "quantity": 2},),
    }
    assert dict(events["work_order_assigned"].attributes) == {
        "previous_status": "ready",
        "current_status": "assigned",
        "reservation_id": "work_reservation_000001",
    }
    assert dict(events["work_order_activated"].attributes) == {
        "previous_status": "assigned",
        "current_status": "active",
    }
    assert dict(events["work_order_progressed"].attributes) == {
        "previous_progress": 0,
        "current_progress": 3,
    }
    assert dict(events["work_reservation_released"].attributes) == {
        "work_id": work.id,
        "release_status": "completed",
    }
    assert dict(events["work_order_completed"].attributes) == {
        "previous_status": "active",
        "current_status": "completed",
    }
    kinds = [event.kind for event in engine.state.events.values()]
    assert kinds.index("work_reservation_created") < kinds.index("work_order_assigned")
    assert kinds.index("work_reservation_released") < kinds.index(
        "work_order_completed"
    )
