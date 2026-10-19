from dataclasses import FrozenInstanceError, replace

import pytest

from living_world.cognition import ActionRequest, NPCActionResolver
from living_world.core.definition import Definition
from living_world.goals import (
    GoalDefinition,
    GoalOwnerKind,
    GoalStatus,
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
from living_world.spatial import Bounds, BoundsKind, Placement, Point
from living_world.work import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    MaintenanceWorkTarget,
    ResourceRequirement,
    ResourceWorkTarget,
    ToolRequirement,
    WorkActionHandler,
    WorkAssignmentOffer,
    WorkCategory,
    WorkCreationOffer,
    WorkPriorityOffer,
    WorkStatus,
)


def _engine() -> tuple[SimulationEngine, str, str]:
    engine = SimulationEngine()
    for key in ("settlement", "npc", "shelter", "storage"):
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
        entity_id=npc.id,
        geometry=Point(1, 1),
        containing_entity_id=settlement.id,
    )
    objective = ObjectiveDefinition(
        "objective_food",
        "Secure food",
        "Secure food",
        "Help establish a dependable food supply.",
        (ResourceMinimumCriterion("food", 5),),
        authorized_action_categories=tuple(category.value for category in WorkCategory),
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
    engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)
    engine.goals.transition_objective(objective.id, GoalStatus.ACTIVE)
    return engine, settlement.id, npc.id


def _creation(settlement_id: str, **changes: object) -> WorkCreationOffer:
    values: dict[str, object] = {
        "label": "Plant the first crop",
        "category": WorkCategory.PRODUCE_FOOD,
        "target": ResourceWorkTarget("food", 5),
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
    return WorkCreationOffer(**values)  # type: ignore[arg-type]


def _handler(
    engine: SimulationEngine,
    settlement_id: str,
    npc_id: str,
    *,
    creation_offers: tuple[WorkCreationOffer, ...] = (),
    priority_offers: tuple[WorkPriorityOffer, ...] = (),
    assignment_offers: tuple[WorkAssignmentOffer, ...] = (),
) -> WorkActionHandler:
    return WorkActionHandler(
        engine.state,
        engine.definitions,
        engine.work,
        npc_id,
        creation_offers,
        priority_offers,
        assignment_offers,
    )


def _request(key: str, label: str, **changes: object) -> ActionRequest:
    values: dict[str, object] = {
        "action_key": key,
        "target_label": label,
        "rationale": "This could help the settlement.",
    }
    values.update(changes)
    return ActionRequest(**values)  # type: ignore[arg-type]


def test_creation_offer_is_strict_frozen_and_canonical() -> None:
    _, settlement_id, _ = _engine()
    offer = _creation(settlement_id)
    with pytest.raises(FrozenInstanceError):
        offer.priority = 8  # type: ignore[misc]
    with pytest.raises(TypeError, match="tuple"):
        _creation(settlement_id, tools=[ToolRequirement("basket", 1)])
    with pytest.raises(ValueError, match="sorted"):
        _creation(
            settlement_id,
            prerequisite_work_ids=("work_000002", "work_000001"),
        )


@pytest.mark.parametrize(
    ("category", "target"),
    (
        (WorkCategory.GATHER_WATER, ResourceWorkTarget("water", 1)),
        (WorkCategory.PRODUCE_FOOD, ResourceWorkTarget("food", 1)),
        (WorkCategory.BUILD_SHELTER, CapabilityWorkTarget("shelter", 1)),
        (WorkCategory.BUILD_STORAGE, CapabilityWorkTarget("storage", 1)),
        (WorkCategory.MAINTAIN_CAPABILITY, MaintenanceWorkTarget("maintenance_1")),
        (
            WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION,
            ExternalConnectionWorkTarget("external_reference_1"),
        ),
    ),
)
def test_offer_construction_covers_all_six_category_target_families(
    category: WorkCategory, target: object
) -> None:
    _, settlement_id, _ = _engine()
    assert (
        _creation(settlement_id, category=category, target=target).category is category
    )


@pytest.mark.parametrize(
    ("category", "target"),
    (
        (WorkCategory.GATHER_WATER, ResourceWorkTarget("food", 1)),
        (WorkCategory.PRODUCE_FOOD, ResourceWorkTarget("water", 1)),
        (WorkCategory.BUILD_SHELTER, ResourceWorkTarget("food", 1)),
        (WorkCategory.MAINTAIN_CAPABILITY, CapabilityWorkTarget("shelter", 1)),
    ),
)
def test_offer_constructor_rejects_invalid_category_target_policy(
    category: WorkCategory, target: object
) -> None:
    _, settlement_id, _ = _engine()
    with pytest.raises(ValueError, match="target"):
        _creation(settlement_id, category=category, target=target)
    with pytest.raises(ValueError, match="overlap"):
        _creation(
            settlement_id,
            tools=(ToolRequirement("seed", 1),),
            resources=(ResourceRequirement("seed", 1),),
        )


def test_creation_uses_only_offered_label_and_exact_manager_event() -> None:
    engine, settlement_id, npc_id = _engine()
    before_resources = dict(
        engine.state.entities[settlement_id].attributes["resources"]
    )
    before_events = tuple(engine.state.events)
    handler = _handler(
        engine, settlement_id, npc_id, creation_offers=(_creation(settlement_id),)
    )
    assert handler.action_options == (handler.action_options[0],)
    option = handler.action_options[0]
    assert option.key == "produce_food"
    assert option.description == "Propose producing food for the settlement."
    assert option.target_labels == ("Plant the first crop",)
    assert "work_" not in repr(option)
    resolver = NPCActionResolver(handler.action_options, (handler,))
    result = resolver.resolve(
        actor_id=npc_id,
        request=_request("produce_food", "Plant the first crop"),
    )
    assert result.accepted is True
    assert result.reason == "The work proposal was accepted."
    work = handler.last_created
    assert work is not None and work.public_label == "Plant the first crop"
    assert engine.state.work_states[work.id].status is WorkStatus.PROPOSED
    assert engine.state.work_reservations == {}
    assert (
        engine.state.entities[settlement_id].attributes["resources"] == before_resources
    )
    new_events = tuple(
        engine.state.events[key]
        for key in tuple(engine.state.events)[len(before_events) :]
    )
    assert [event.kind for event in new_events] == ["work_order_created"]


def test_closed_key_order_and_normalized_label_order() -> None:
    engine, settlement_id, npc_id = _engine()
    offers = (
        _creation(
            settlement_id,
            label="Zulu shelter",
            category=WorkCategory.BUILD_SHELTER,
            target=CapabilityWorkTarget("shelter", 1),
            tools=(),
            resources=(),
        ),
        _creation(settlement_id, label=" berry crop"),
        _creation(settlement_id, label="Apple crop", location_id=npc_id),
    )
    handler = _handler(engine, settlement_id, npc_id, creation_offers=offers)
    assert tuple(option.key for option in handler.action_options) == (
        "produce_food",
        "build_shelter",
    )
    assert handler.action_options[0].target_labels == ("Apple crop", " berry crop")
    with pytest.raises(ValueError, match="unambiguous"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            creation_offers=(
                _creation(settlement_id, label=" One crop"),
                _creation(settlement_id, label="one CROP", location_id=npc_id),
            ),
        )


def test_handler_preflights_all_six_families_and_orders_all_eight_keys() -> None:
    engine, settlement_id, npc_id = _engine()
    engine.definitions.register(Definition("well"))
    well = engine.entities.create(
        definition_key="well",
        name="Village well",
        attributes={"is_constructed": True},
    )
    engine.spatial.place(
        entity_id=well.id,
        geometry=Point(3, 3),
        containing_entity_id=settlement_id,
    )
    engine.relationships.create(kind="owns", source_id=settlement_id, target_id=well.id)
    engine.consequences.create_maintenance(
        MaintenancePolicy(
            "maintenance_well",
            settlement_id,
            well.id,
            "Village well",
            (MaintenanceRequirement("seed", 1),),
            2,
            3,
            1,
            1,
        )
    )
    reference = engine.external_world_references.create(
        name="River Guild",
        role="regional supplier",
        capacity=10,
        delay_ticks=1,
        cost_per_unit=1,
        reliability=1.0,
    )
    offers = (
        _creation(
            settlement_id,
            label="Gather stream water",
            category=WorkCategory.GATHER_WATER,
            target=ResourceWorkTarget("water", 1),
            tools=(),
            resources=(),
        ),
        _creation(settlement_id),
        _creation(
            settlement_id,
            label="Raise a shelter",
            category=WorkCategory.BUILD_SHELTER,
            target=CapabilityWorkTarget("shelter", 1),
            tools=(),
            resources=(),
        ),
        _creation(
            settlement_id,
            label="Raise a storehouse",
            category=WorkCategory.BUILD_STORAGE,
            target=CapabilityWorkTarget("storage", 1),
            tools=(),
            resources=(),
        ),
        _creation(
            settlement_id,
            label="Care for the village well",
            category=WorkCategory.MAINTAIN_CAPABILITY,
            target=MaintenanceWorkTarget("maintenance_well"),
            tools=(),
            resources=(),
        ),
        _creation(
            settlement_id,
            label="Open trade with the river guild",
            category=WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION,
            target=ExternalConnectionWorkTarget(reference.id),
            tools=(),
            resources=(),
        ),
    )
    priority_work = engine.work.create(
        category=WorkCategory.PRODUCE_FOOD,
        target=ResourceWorkTarget("food", 2),
        public_label="Existing orchard plan",
        settlement_id=settlement_id,
        objective_id="objective_food",
        location_id=well.id,
    )
    assignment_work = engine.work.create(
        category=WorkCategory.PRODUCE_FOOD,
        target=ResourceWorkTarget("food", 3),
        public_label="Existing garden plan",
        settlement_id=settlement_id,
        objective_id="objective_food",
        location_id=npc_id,
        labor_required=1,
    )
    engine.work.mark_ready(assignment_work.id)
    handler = _handler(
        engine,
        settlement_id,
        npc_id,
        creation_offers=offers,
        priority_offers=(
            WorkPriorityOffer("Raise the orchard priority", priority_work.id, 4),
        ),
        assignment_offers=(
            WorkAssignmentOffer("Volunteer for the garden", assignment_work.id),
        ),
    )
    assert tuple(option.key for option in handler.action_options) == tuple(
        category.value for category in WorkCategory
    ) + ("prioritize_work", "volunteer_for_work")


def test_validation_rejections_are_safe_and_mutation_free() -> None:
    engine, settlement_id, npc_id = _engine()
    handler = _handler(
        engine, settlement_id, npc_id, creation_offers=(_creation(settlement_id),)
    )
    before = (
        dict(engine.state.work_definitions),
        dict(engine.state.work_states),
        dict(engine.state.work_reservations),
        dict(engine.state.events),
    )
    result = handler.validate(
        actor_id=npc_id,
        request=_request(
            "produce_food",
            "Plant the first crop",
            arguments={"priority": "999"},
        ),
    )
    assert result.reason == "Work proposals cannot set engine policy."
    wrong_actor = handler.validate(
        actor_id=settlement_id,
        request=_request("produce_food", "Plant the first crop"),
    )
    assert wrong_actor.reason == "That work proposal is not currently available."
    assert before == (
        engine.state.work_definitions,
        engine.state.work_states,
        engine.state.work_reservations,
        engine.state.events,
    )


def test_handler_isolated_to_bound_actor_and_live_placement() -> None:
    engine, settlement_id, npc_id = _engine()
    other = engine.entities.create(
        definition_key="npc",
        name="Other",
        attributes={
            "npc_identity": {
                "name": "Other",
                "description": "Another settler.",
                "capability_descriptions": [],
            }
        },
    )
    engine.spatial.place(
        entity_id=other.id,
        geometry=Point(2, 2),
        containing_entity_id=settlement_id,
    )
    handler = _handler(
        engine, settlement_id, npc_id, creation_offers=(_creation(settlement_id),)
    )
    request = _request("produce_food", "Plant the first crop")
    assert handler.validate(actor_id=other.id, request=request).accepted is False
    engine.state.placements.pop(npc_id)
    assert handler.validate(actor_id=npc_id, request=request).accepted is False


def test_construction_rejects_unknown_destroyed_non_npc_and_foreign_actor() -> None:
    engine, settlement_id, _ = _engine()
    with pytest.raises(ValueError, match="live"):
        _handler(
            engine,
            settlement_id,
            "entity_999999",
            creation_offers=(_creation(settlement_id),),
        )

    engine, settlement_id, npc_id = _engine()
    engine.state.entities[npc_id].destroyed_tick = 0
    with pytest.raises(ValueError, match="live"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            creation_offers=(_creation(settlement_id),),
        )

    engine, settlement_id, _ = _engine()
    with pytest.raises(TypeError, match="NPC identity"):
        _handler(
            engine,
            settlement_id,
            settlement_id,
            creation_offers=(_creation(settlement_id),),
        )

    engine, settlement_id, npc_id = _engine()
    other = engine.entities.create(definition_key="settlement", name="Elsewhere")
    engine.spatial.place(
        entity_id=other.id,
        geometry=Bounds(20, 20, 5, 5),
        bounds_kind=BoundsKind.AREA,
    )
    engine.spatial.replace(
        entity_id=npc_id, geometry=Point(21, 21), containing_entity_id=other.id
    )
    with pytest.raises(ValueError, match="within"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            creation_offers=(_creation(settlement_id),),
        )

    engine, settlement_id, npc_id = _engine()
    engine.state.maintenance_policies["maintenance_actor"] = MaintenancePolicy(
        "maintenance_actor",
        settlement_id,
        npc_id,
        "Maintained actor",
        (MaintenanceRequirement("seed", 1),),
        1,
        1,
        1,
        1,
    )
    with pytest.raises(ValueError, match="Maintenance"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            creation_offers=(_creation(settlement_id),),
        )


@pytest.mark.parametrize(
    "status",
    (GoalStatus.INACTIVE, GoalStatus.BLOCKED, GoalStatus.COMPLETED, GoalStatus.FAILED),
)
def test_exact_active_goal_and_objective_authorization(status: GoalStatus) -> None:
    engine, settlement_id, npc_id = _engine()
    engine.state.objective_states["objective_food"] = engine.state.objective_states[
        "objective_food"
    ].__class__("objective_food", status)
    with pytest.raises(ValueError, match="authorized"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            creation_offers=(_creation(settlement_id),),
        )


@pytest.mark.parametrize(
    "status",
    (GoalStatus.INACTIVE, GoalStatus.BLOCKED, GoalStatus.COMPLETED, GoalStatus.FAILED),
)
def test_goal_itself_must_be_exactly_active(status: GoalStatus) -> None:
    engine, settlement_id, npc_id = _engine()
    engine.state.goal_states["goal_home"] = replace(
        engine.state.goal_states["goal_home"], status=status
    )
    with pytest.raises(ValueError, match="authorized"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            creation_offers=(_creation(settlement_id),),
        )


@pytest.mark.parametrize("scope", ("goal", "objective"))
def test_exact_umbrella_and_category_authorization(scope: str) -> None:
    engine, settlement_id, npc_id = _engine()
    if scope == "goal":
        engine.state.goal_definitions["goal_home"] = replace(
            engine.state.goal_definitions["goal_home"],
            authorized_action_categories=(),
        )
    else:
        engine.state.objective_definitions["objective_food"] = replace(
            engine.state.objective_definitions["objective_food"],
            authorized_action_categories=(),
        )
    with pytest.raises(ValueError, match="authorized"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            creation_offers=(_creation(settlement_id),),
        )


def test_creation_admission_rejects_duplicate_and_unavailable_inputs() -> None:
    engine, settlement_id, npc_id = _engine()
    offer = _creation(settlement_id)
    engine.work.create(
        category=offer.category,
        target=offer.target,
        public_label="Existing crop",
        settlement_id=offer.settlement_id,
        objective_id=offer.objective_id,
        location_id=offer.location_id,
        labor_required=offer.labor_required,
        tools=offer.tools,
        resources=offer.resources,
        required_progress=offer.required_progress,
        priority=offer.priority,
    )
    with pytest.raises(ValueError, match="Duplicate"):
        _handler(engine, settlement_id, npc_id, creation_offers=(offer,))
    engine.state.work_definitions.clear()
    engine.state.work_states.clear()
    engine.state.entities[settlement_id].attributes["resources"]["seed"] = 1
    with pytest.raises(ValueError, match="Insufficient"):
        _handler(engine, settlement_id, npc_id, creation_offers=(offer,))


@pytest.mark.parametrize(
    "status",
    (
        WorkStatus.PROPOSED,
        WorkStatus.READY,
        WorkStatus.ASSIGNED,
        WorkStatus.ACTIVE,
        WorkStatus.BLOCKED,
    ),
)
def test_duplicate_identity_rejects_every_nonterminal_status(
    status: WorkStatus,
) -> None:
    engine, settlement_id, npc_id = _engine()
    offer = _creation(settlement_id)
    work = engine.work.create(
        category=offer.category,
        target=offer.target,
        public_label="Existing crop",
        settlement_id=offer.settlement_id,
        objective_id=offer.objective_id,
        location_id=offer.location_id,
    )
    engine.state.work_states[work.id] = replace(
        engine.state.work_states[work.id], status=status
    )
    with pytest.raises(ValueError, match="Duplicate"):
        _handler(engine, settlement_id, npc_id, creation_offers=(offer,))


@pytest.mark.parametrize(
    "status", (WorkStatus.COMPLETED, WorkStatus.CANCELLED, WorkStatus.FAILED)
)
def test_terminal_history_allows_same_creation_identity(status: WorkStatus) -> None:
    engine, settlement_id, npc_id = _engine()
    offer = _creation(settlement_id)
    work = engine.work.create(
        category=offer.category,
        target=offer.target,
        public_label="Historical crop",
        settlement_id=offer.settlement_id,
        objective_id=offer.objective_id,
        location_id=offer.location_id,
    )
    engine.state.work_states[work.id] = replace(
        engine.state.work_states[work.id], status=status
    )
    assert _handler(
        engine, settlement_id, npc_id, creation_offers=(offer,)
    ).action_options


def test_priority_and_self_assignment_use_manager_paths_and_event_order() -> None:
    engine, settlement_id, npc_id = _engine()
    offer = _creation(settlement_id)
    work = engine.work.create(
        category=offer.category,
        target=offer.target,
        public_label=offer.label,
        settlement_id=offer.settlement_id,
        objective_id=offer.objective_id,
        location_id=offer.location_id,
        labor_required=1,
        tools=offer.tools,
        resources=offer.resources,
        required_progress=offer.required_progress,
        priority=offer.priority,
    )
    engine.work.mark_ready(work.id)
    handler = _handler(
        engine,
        settlement_id,
        npc_id,
        priority_offers=(WorkPriorityOffer("Make planting urgent", work.id, 8),),
        assignment_offers=(WorkAssignmentOffer("I will plant the crop", work.id),),
    )
    resolver = NPCActionResolver(handler.action_options, (handler,))
    priority = resolver.resolve(
        actor_id=npc_id,
        request=_request("prioritize_work", "Make planting urgent"),
    )
    assert priority.reason == "The work priority proposal was accepted."
    assert engine.state.work_definitions[work.id].priority == 8
    assigned = resolver.resolve(
        actor_id=npc_id,
        request=_request("volunteer_for_work", "I will plant the crop"),
    )
    assert assigned.reason == "The volunteer proposal was accepted."
    assert engine.state.work_reservations[
        engine.state.work_states[work.id].reservation_id  # type: ignore[index]
    ].labor_entity_ids == (npc_id,)
    assert [event.kind for event in tuple(engine.state.events.values())[-2:]] == [
        "work_reservation_created",
        "work_order_assigned",
    ]


def test_priority_noop_and_every_terminal_status_reject_safely() -> None:
    engine, settlement_id, npc_id = _engine()
    offer = _creation(settlement_id)
    work = engine.work.create(
        category=offer.category,
        target=offer.target,
        public_label=offer.label,
        settlement_id=offer.settlement_id,
        objective_id=offer.objective_id,
        location_id=offer.location_id,
        priority=1,
    )
    request = _request("prioritize_work", "Raise crop priority")
    handler = _handler(
        engine,
        settlement_id,
        npc_id,
        priority_offers=(WorkPriorityOffer("Raise crop priority", work.id, 4),),
    )
    engine.work.set_priority(work.id, 4)
    before = (dict(engine.state.work_definitions), dict(engine.state.events))
    result = handler.validate(actor_id=npc_id, request=request)
    assert result.reason == "That priority proposal is not currently available."
    assert before == (engine.state.work_definitions, engine.state.events)
    next_work = engine.work.create(
        category=offer.category,
        target=ResourceWorkTarget("food", 2),
        public_label="Another crop",
        settlement_id=settlement_id,
        objective_id=offer.objective_id,
        location_id=npc_id,
    )
    assert next_work.id == "work_000002"

    for status in (WorkStatus.COMPLETED, WorkStatus.CANCELLED, WorkStatus.FAILED):
        terminal_engine, terminal_settlement, terminal_npc = _engine()
        terminal_offer = _creation(terminal_settlement)
        terminal_work = terminal_engine.work.create(
            category=terminal_offer.category,
            target=terminal_offer.target,
            public_label=terminal_offer.label,
            settlement_id=terminal_offer.settlement_id,
            objective_id=terminal_offer.objective_id,
            location_id=terminal_offer.location_id,
        )
        terminal_handler = _handler(
            terminal_engine,
            terminal_settlement,
            terminal_npc,
            priority_offers=(
                WorkPriorityOffer("Raise crop priority", terminal_work.id, 4),
            ),
        )
        terminal_engine.state.work_states[terminal_work.id] = replace(
            terminal_engine.state.work_states[terminal_work.id], status=status
        )
        events = dict(terminal_engine.state.events)
        terminal_result = terminal_handler.validate(
            actor_id=terminal_npc, request=request
        )
        assert (
            terminal_result.reason
            == "That priority proposal is not currently available."
        )
        assert terminal_engine.state.events == events


def test_volunteer_rechecks_double_booking_and_stale_input_availability() -> None:
    engine, settlement_id, npc_id = _engine()
    first_offer = _creation(settlement_id)
    first = engine.work.create(
        category=first_offer.category,
        target=ResourceWorkTarget("food", 2),
        public_label="First planting",
        settlement_id=settlement_id,
        objective_id="objective_food",
        location_id=settlement_id,
        labor_required=1,
    )
    second = engine.work.create(
        category=first_offer.category,
        target=ResourceWorkTarget("food", 3),
        public_label="Second planting",
        settlement_id=settlement_id,
        objective_id="objective_food",
        location_id=npc_id,
        labor_required=1,
        tools=(ToolRequirement("basket", 2),),
    )
    engine.work.mark_ready(first.id)
    engine.work.mark_ready(second.id)
    handler = _handler(
        engine,
        settlement_id,
        npc_id,
        assignment_offers=(WorkAssignmentOffer("Volunteer for second", second.id),),
    )
    engine.work.assign_and_reserve(first.id, (npc_id,))
    before = (dict(engine.state.work_reservations), dict(engine.state.events))
    result = handler.validate(
        actor_id=npc_id,
        request=_request("volunteer_for_work", "Volunteer for second"),
    )
    assert result.reason == "That volunteer proposal is not currently available."
    assert before == (engine.state.work_reservations, engine.state.events)
    engine.work.block(first.id, "The first planting is waiting.")
    assert handler.apply(
        actor_id=npc_id,
        request=_request("volunteer_for_work", "Volunteer for second"),
    ).accepted
    assert engine.state.work_states[second.id].reservation_id == (
        "work_reservation_000002"
    )

    unavailable_engine, unavailable_settlement, unavailable_npc = _engine()
    unavailable_offer = _creation(unavailable_settlement)
    unavailable_work = unavailable_engine.work.create(
        category=unavailable_offer.category,
        target=unavailable_offer.target,
        public_label=unavailable_offer.label,
        settlement_id=unavailable_settlement,
        objective_id=unavailable_offer.objective_id,
        location_id=unavailable_settlement,
        labor_required=1,
        tools=(ToolRequirement("basket", 2),),
    )
    unavailable_engine.work.mark_ready(unavailable_work.id)
    unavailable_handler = _handler(
        unavailable_engine,
        unavailable_settlement,
        unavailable_npc,
        assignment_offers=(
            WorkAssignmentOffer("Volunteer for planting", unavailable_work.id),
        ),
    )
    unavailable_engine.state.entities[unavailable_settlement].attributes["resources"][
        "basket"
    ] = 1
    unavailable_before = (
        dict(unavailable_engine.state.work_reservations),
        dict(unavailable_engine.state.events),
    )
    unavailable_result = unavailable_handler.validate(
        actor_id=unavailable_npc,
        request=_request("volunteer_for_work", "Volunteer for planting"),
    )
    assert (
        unavailable_result.reason
        == "That volunteer proposal is not currently available."
    )
    assert unavailable_before == (
        unavailable_engine.state.work_reservations,
        unavailable_engine.state.events,
    )
    unavailable_engine.state.entities[unavailable_settlement].attributes["resources"][
        "basket"
    ] = 2
    assert unavailable_handler.apply(
        actor_id=unavailable_npc,
        request=_request("volunteer_for_work", "Volunteer for planting"),
    ).accepted
    assert (
        unavailable_engine.state.work_states[unavailable_work.id].reservation_id
        == "work_reservation_000001"
    )

    cross_engine, cross_settlement, cross_npc = _engine()
    other = cross_engine.entities.create(
        definition_key="npc",
        name="Other",
        attributes={
            "npc_identity": {
                "name": "Other",
                "description": "Another worker.",
                "capability_descriptions": [],
            }
        },
    )
    cross_engine.spatial.place(
        entity_id=other.id,
        geometry=Point(2, 2),
        containing_entity_id=cross_settlement,
    )
    resource_lock = cross_engine.work.create(
        category=WorkCategory.PRODUCE_FOOD,
        target=ResourceWorkTarget("food", 2),
        public_label="Reserve baskets as materials",
        settlement_id=cross_settlement,
        objective_id="objective_food",
        location_id=cross_settlement,
        labor_required=1,
        resources=(ResourceRequirement("basket", 1),),
    )
    tool_work = cross_engine.work.create(
        category=WorkCategory.PRODUCE_FOOD,
        target=ResourceWorkTarget("food", 3),
        public_label="Use baskets as tools",
        settlement_id=cross_settlement,
        objective_id="objective_food",
        location_id=cross_npc,
        labor_required=1,
        tools=(ToolRequirement("basket", 2),),
    )
    cross_engine.work.mark_ready(resource_lock.id)
    cross_engine.work.mark_ready(tool_work.id)
    cross_handler = _handler(
        cross_engine,
        cross_settlement,
        cross_npc,
        assignment_offers=(WorkAssignmentOffer("Volunteer with tools", tool_work.id),),
    )
    cross_engine.work.assign_and_reserve(resource_lock.id, (other.id,))
    cross_result = cross_handler.validate(
        actor_id=cross_npc,
        request=_request("volunteer_for_work", "Volunteer with tools"),
    )
    assert cross_result.reason == "That volunteer proposal is not currently available."


def test_multi_person_volunteer_and_stale_apply_are_rejected_or_propagate() -> None:
    engine, settlement_id, npc_id = _engine()
    offer = _creation(settlement_id, labor_required=2)
    work = engine.work.create(
        category=offer.category,
        target=offer.target,
        public_label=offer.label,
        settlement_id=offer.settlement_id,
        objective_id=offer.objective_id,
        location_id=offer.location_id,
        labor_required=2,
        required_progress=1,
    )
    engine.work.mark_ready(work.id)
    with pytest.raises(ValueError, match="one laborer"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            assignment_offers=(WorkAssignmentOffer("I will help", work.id),),
        )

    handler = _handler(
        engine,
        settlement_id,
        npc_id,
        creation_offers=(
            _creation(settlement_id, label="A later crop", location_id=npc_id),
        ),
    )
    request = _request("produce_food", "A later crop")
    assert handler.validate(actor_id=npc_id, request=request).accepted
    engine.goals.transition_objective("objective_food", GoalStatus.BLOCKED)
    with pytest.raises(ValueError, match="authorized"):
        handler.apply(actor_id=npc_id, request=request)


@pytest.mark.parametrize("stale_kind", ("destroyed", "moved", "missing"))
def test_stale_creation_location_rejects_safely_without_advancing_id(
    stale_kind: str,
) -> None:
    engine, settlement_id, npc_id = _engine()
    engine.definitions.register(Definition("site"))
    site = engine.entities.create(definition_key="site", name="Field site")
    engine.spatial.place(
        entity_id=site.id,
        geometry=Point(3, 3),
        containing_entity_id=settlement_id,
    )
    offer = _creation(settlement_id, location_id=site.id)
    handler = _handler(engine, settlement_id, npc_id, creation_offers=(offer,))
    saved_entity = engine.state.entities[site.id]
    saved_placement = engine.state.placements[site.id]
    if stale_kind == "destroyed":
        saved_entity.destroyed_tick = 0
    elif stale_kind == "moved":
        engine.state.placements[site.id] = Placement(site.id, Point(20, 20))
    else:
        engine.state.entities.pop(site.id)
    before = (dict(engine.state.work_definitions), dict(engine.state.events))
    result = handler.validate(
        actor_id=npc_id,
        request=_request("produce_food", "Plant the first crop"),
    )
    assert result.reason == "That work proposal is not currently available."
    assert before == (engine.state.work_definitions, engine.state.events)

    saved_entity.destroyed_tick = None
    engine.state.entities[site.id] = saved_entity
    engine.state.placements[site.id] = saved_placement
    assert handler.apply(
        actor_id=npc_id,
        request=_request("produce_food", "Plant the first crop"),
    ).accepted
    assert handler.last_created is not None
    assert handler.last_created.id == "work_000001"


def test_stale_missing_prerequisite_rejects_but_incomplete_valid_prerequisite_waits() -> (
    None
):
    engine, settlement_id, npc_id = _engine()
    prerequisite = engine.work.create(
        category=WorkCategory.PRODUCE_FOOD,
        target=ResourceWorkTarget("food", 2),
        public_label="Prepare the field",
        settlement_id=settlement_id,
        objective_id="objective_food",
        location_id=settlement_id,
    )
    offer = _creation(
        settlement_id,
        location_id=npc_id,
        prerequisite_work_ids=(prerequisite.id,),
    )
    handler = _handler(engine, settlement_id, npc_id, creation_offers=(offer,))
    saved_definition = engine.state.work_definitions.pop(prerequisite.id)
    saved_state = engine.state.work_states.pop(prerequisite.id)
    before = (dict(engine.state.work_definitions), dict(engine.state.events))
    rejected = handler.validate(
        actor_id=npc_id,
        request=_request("produce_food", "Plant the first crop"),
    )
    assert rejected.reason == "That work proposal is not currently available."
    assert before == (engine.state.work_definitions, engine.state.events)

    engine.state.work_definitions[prerequisite.id] = saved_definition
    engine.state.work_states[prerequisite.id] = saved_state
    engine.state.work_definitions[prerequisite.id] = replace(
        saved_definition, settlement_id="another_settlement"
    )
    cross_settlement = handler.validate(
        actor_id=npc_id,
        request=_request("produce_food", "Plant the first crop"),
    )
    assert cross_settlement.reason == "That work proposal is not currently available."
    assert set(engine.state.work_definitions) == {prerequisite.id}
    engine.state.work_definitions[prerequisite.id] = saved_definition
    accepted = handler.apply(
        actor_id=npc_id,
        request=_request("produce_food", "Plant the first crop"),
    )
    assert accepted.accepted
    assert handler.last_created is not None
    assert handler.last_created.id == "work_000002"
    with pytest.raises(ValueError, match="prerequisite"):
        engine.work.mark_ready(handler.last_created.id)


def test_stale_creation_targets_capability_registry_and_deadline_reject_safely() -> (
    None
):
    capability_engine, capability_settlement, capability_npc = _engine()
    capability_offer = _creation(
        capability_settlement,
        category=WorkCategory.BUILD_SHELTER,
        target=CapabilityWorkTarget("shelter", 1),
        tools=(),
        resources=(),
    )
    capability_handler = _handler(
        capability_engine,
        capability_settlement,
        capability_npc,
        creation_offers=(capability_offer,),
    )
    capability_engine.definitions._definitions.pop("shelter")  # type: ignore[attr-defined]
    assert (
        capability_handler.validate(
            actor_id=capability_npc,
            request=_request("build_shelter", capability_offer.label),
        ).reason
        == "That work proposal is not currently available."
    )
    assert capability_engine.state.work_definitions == {}

    external_engine, external_settlement, external_npc = _engine()
    reference = external_engine.external_world_references.create(
        name="River Guild",
        role="regional supplier",
        capacity=10,
        delay_ticks=1,
        cost_per_unit=1,
        reliability=1.0,
    )
    external_offer = _creation(
        external_settlement,
        category=WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION,
        target=ExternalConnectionWorkTarget(reference.id),
        tools=(),
        resources=(),
    )
    external_handler = _handler(
        external_engine,
        external_settlement,
        external_npc,
        creation_offers=(external_offer,),
    )
    external_engine.state.external_world_references.pop(reference.id)
    assert (
        external_handler.validate(
            actor_id=external_npc,
            request=_request(
                WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION.value,
                external_offer.label,
            ),
        ).reason
        == "That work proposal is not currently available."
    )
    assert external_engine.state.work_definitions == {}

    deadline_engine, deadline_settlement, deadline_npc = _engine()
    deadline_offer = _creation(deadline_settlement, deadline_tick=1)
    deadline_handler = _handler(
        deadline_engine,
        deadline_settlement,
        deadline_npc,
        creation_offers=(deadline_offer,),
    )
    deadline_engine.state.tick = 1
    assert (
        deadline_handler.validate(
            actor_id=deadline_npc,
            request=_request("produce_food", deadline_offer.label),
        ).reason
        == "That work proposal is not currently available."
    )
    assert deadline_engine.state.work_definitions == {}


def test_stale_missing_maintenance_target_rejects_without_mutation() -> None:
    engine, settlement_id, npc_id = _engine()
    engine.definitions.register(Definition("well"))
    well = engine.entities.create(
        definition_key="well",
        name="Village well",
        attributes={"is_constructed": True},
    )
    engine.spatial.place(
        entity_id=well.id,
        geometry=Point(3, 3),
        containing_entity_id=settlement_id,
    )
    policy = MaintenancePolicy(
        "maintenance_well",
        settlement_id,
        well.id,
        "Village well",
        (MaintenanceRequirement("seed", 1),),
        2,
        3,
        1,
        1,
    )
    engine.state.maintenance_policies[policy.id] = policy
    engine.state.maintenance_states[policy.id] = MaintenanceState(policy.id, 2)
    offer = _creation(
        settlement_id,
        category=WorkCategory.MAINTAIN_CAPABILITY,
        target=MaintenanceWorkTarget(policy.id),
        tools=(),
        resources=(),
    )
    handler = _handler(engine, settlement_id, npc_id, creation_offers=(offer,))
    engine.state.maintenance_policies.pop(policy.id)
    engine.state.maintenance_states.pop(policy.id)
    before = (dict(engine.state.work_definitions), dict(engine.state.events))
    result = handler.validate(
        actor_id=npc_id,
        request=_request(WorkCategory.MAINTAIN_CAPABILITY.value, offer.label),
    )
    assert result.reason == "That work proposal is not currently available."
    assert before == (engine.state.work_definitions, engine.state.events)


def test_manager_preflights_do_not_mutate_or_advance_allocators() -> None:
    engine, settlement_id, _ = _engine()
    offer = _creation(settlement_id)
    before = (
        dict(engine.state.work_definitions),
        dict(engine.state.work_states),
        dict(engine.state.work_reservations),
        dict(engine.state.events),
    )
    engine.work.validate_create(
        category=offer.category,
        target=offer.target,
        public_label=offer.label,
        settlement_id=offer.settlement_id,
        objective_id=offer.objective_id,
        location_id=offer.location_id,
        labor_required=offer.labor_required,
        tools=offer.tools,
        resources=offer.resources,
        required_progress=offer.required_progress,
        priority=offer.priority,
        require_available_inputs=True,
        reject_nonterminal_duplicate=True,
    )
    assert before == (
        engine.state.work_definitions,
        engine.state.work_states,
        engine.state.work_reservations,
        engine.state.events,
    )
    assert (
        engine.work.create(
            category=offer.category,
            target=offer.target,
            public_label=offer.label,
            settlement_id=offer.settlement_id,
            objective_id=offer.objective_id,
            location_id=offer.location_id,
        ).id
        == "work_000001"
    )


def test_capability_offer_requires_authoritative_definition() -> None:
    engine, settlement_id, npc_id = _engine()
    with pytest.raises(ValueError, match="definition"):
        _handler(
            engine,
            settlement_id,
            npc_id,
            creation_offers=(
                _creation(
                    settlement_id,
                    category=WorkCategory.BUILD_SHELTER,
                    target=CapabilityWorkTarget("unknown_shelter", 1),
                    tools=(),
                    resources=(),
                ),
            ),
        )


def test_apply_time_event_failure_restores_state_and_next_work_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, settlement_id, npc_id = _engine()
    handler = _handler(
        engine, settlement_id, npc_id, creation_offers=(_creation(settlement_id),)
    )
    request = _request("produce_food", "Plant the first crop")
    original = engine.events.record

    def fail_after_record(**arguments: object) -> object:
        original(**arguments)  # type: ignore[arg-type]
        raise RuntimeError("event failure")

    monkeypatch.setattr(engine.events, "record", fail_after_record)
    with pytest.raises(RuntimeError, match="event failure"):
        handler.apply(actor_id=npc_id, request=request)
    assert engine.state.work_definitions == {}
    assert engine.state.work_states == {}
    assert engine.state.work_reservations == {}
    assert handler.last_created is None
    monkeypatch.setattr(engine.events, "record", original)
    assert handler.apply(actor_id=npc_id, request=request).accepted
    assert handler.last_created is not None
    assert handler.last_created.id == "work_000001"


def test_priority_and_assignment_event_failures_restore_manager_state_and_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, settlement_id, npc_id = _engine()
    offer = _creation(settlement_id)
    work = engine.work.create(
        category=offer.category,
        target=offer.target,
        public_label=offer.label,
        settlement_id=offer.settlement_id,
        objective_id=offer.objective_id,
        location_id=offer.location_id,
        labor_required=1,
    )
    engine.work.mark_ready(work.id)
    priority_handler = _handler(
        engine,
        settlement_id,
        npc_id,
        priority_offers=(WorkPriorityOffer("Raise the crop priority", work.id, 7),),
    )
    original = engine.events.record

    def fail_after_record(**arguments: object) -> object:
        original(**arguments)  # type: ignore[arg-type]
        raise RuntimeError("event failure")

    monkeypatch.setattr(engine.events, "record", fail_after_record)
    with pytest.raises(RuntimeError, match="event failure"):
        priority_handler.apply(
            actor_id=npc_id,
            request=_request("prioritize_work", "Raise the crop priority"),
        )
    assert engine.state.work_definitions[work.id].priority == work.priority

    monkeypatch.setattr(engine.events, "record", original)
    assignment_handler = _handler(
        engine,
        settlement_id,
        npc_id,
        assignment_offers=(WorkAssignmentOffer("I will plant", work.id),),
    )
    calls = 0

    def fail_second(**arguments: object) -> object:
        nonlocal calls
        calls += 1
        result = original(**arguments)  # type: ignore[arg-type]
        if calls == 2:
            raise RuntimeError("assignment event failure")
        return result

    monkeypatch.setattr(engine.events, "record", fail_second)
    with pytest.raises(RuntimeError, match="assignment event failure"):
        assignment_handler.apply(
            actor_id=npc_id,
            request=_request("volunteer_for_work", "I will plant"),
        )
    assert engine.state.work_states[work.id].status is WorkStatus.READY
    assert engine.state.work_reservations == {}
    monkeypatch.setattr(engine.events, "record", original)
    assert assignment_handler.apply(
        actor_id=npc_id,
        request=_request("volunteer_for_work", "I will plant"),
    ).accepted
    reservation_id = engine.state.work_states[work.id].reservation_id
    assert reservation_id == "work_reservation_000001"


def test_schema_nine_round_trip_reconstructs_equivalent_offer_and_next_id(
    tmp_path,
) -> None:
    repository = SQLiteRepository(str(tmp_path / "work-action.sqlite3"))
    engine, settlement_id, npc_id = _engine()
    first_handler = _handler(
        engine, settlement_id, npc_id, creation_offers=(_creation(settlement_id),)
    )
    first_handler.apply(
        actor_id=npc_id,
        request=_request("produce_food", "Plant the first crop"),
    )
    assert first_handler.last_created is not None
    engine.work.cancel(first_handler.last_created.id, "A different plan was chosen.")
    repository.save_world(engine.state)

    resumed = SimulationEngine(repository)
    resumed_handler = _handler(
        resumed,
        settlement_id,
        npc_id,
        creation_offers=(_creation(settlement_id),),
    )
    resumed_result = resumed_handler.apply(
        actor_id=npc_id,
        request=_request("produce_food", "Plant the first crop"),
    )
    assert resumed_result.reason == "The work proposal was accepted."
    assert resumed_handler.last_created is not None
    assert resumed_handler.last_created.id == "work_000002"
