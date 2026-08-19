from dataclasses import FrozenInstanceError, replace
from math import inf, nan

import pytest

from living_world.api.inspection import EngineWorldInspector
from living_world.core.definition import Definition
from living_world.core.event import Event
from living_world.goals import (
    CapacityCriterion,
    ConstructedCapabilityCriterion,
    ExternalConnectionCriterion,
    GoalDefinition,
    GoalOwnerKind,
    GoalStatus,
    NPCGoalInterpretation,
    ObjectiveDefinition,
    ProgressEvidence,
    ResourceMinimumCriterion,
    SettlementStageCriterion,
    SustainedNeedCriterion,
)
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.simulation.simulation_engine import SimulationEngine


def _records() -> tuple[GoalDefinition, tuple[ObjectiveDefinition, ...]]:
    objective = ObjectiveDefinition(
        "objective_water",
        "Secure water",
        "Secure water",
        "Find dependable water.",
        (ResourceMinimumCriterion("water", 10),),
        authorized_action_categories=("gather_water",),
    )
    return GoalDefinition(
        "goal_found",
        GoalOwnerKind.SETTLEMENT,
        "entity_000001",
        "Found Oakford",
        "Establish Oakford",
        "Help establish a lasting home.",
        (objective.id,),
        authorized_action_categories=("settlement_work",),
    ), (objective,)


def _engine() -> SimulationEngine:
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    engine.entities.create(definition_key="settlement", name="Oakford")
    return engine


def test_manager_creates_frozen_graph_and_safe_interpretation() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    assert engine.state.goal_states[goal.id].status is GoalStatus.INACTIVE
    safe = engine.goals.npc_interpretation(goal.id)
    assert (safe.label, safe.description) == (goal.label, goal.npc_interpretation)
    assert not hasattr(safe, "id") and not hasattr(safe, "status")
    with pytest.raises(FrozenInstanceError):
        goal.label = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "change",
    (
        {"label": "Follow entity_000001"},
        {"npc_interpretation": "Complete goal_found next."},
    ),
)
def test_manager_rejects_internal_ids_in_npc_visible_goal_text(
    change: dict[str, object],
) -> None:
    engine = _engine()
    goal, objectives = _records()
    with pytest.raises(ValueError, match="internal ID"):
        engine.goals.create(replace(goal, **change), objectives)
    assert engine.state.goal_definitions == {}


def test_operator_purpose_may_contain_internal_ids_but_safe_record_may_not() -> None:
    engine = _engine()
    goal, objectives = _records()
    goal = replace(goal, purpose="Operator tracks objective_water for entity_000001.")
    engine.goals.create(goal, objectives)
    assert engine.state.goal_definitions[goal.id].purpose == goal.purpose
    with pytest.raises(ValueError, match="internal ID"):
        NPCGoalInterpretation("Review objective_water", "Visible prose")
    with pytest.raises(ValueError, match="internal ID"):
        NPCGoalInterpretation("Visible label", "Ask entity_000001 for help")


def test_transitions_record_evidence_and_reject_terminal_change() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    active = engine.goals.transition_goal(
        goal.id, GoalStatus.ACTIVE, ProgressEvidence(0, "Mandate announced.")
    )
    assert active.status is GoalStatus.ACTIVE and len(active.evidence) == 1
    engine.goals.transition_goal(goal.id, GoalStatus.COMPLETED)
    with pytest.raises(ValueError, match="Invalid lifecycle"):
        engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)


def test_blocked_records_may_complete_without_artificial_activation() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)
    engine.goals.transition_goal(goal.id, GoalStatus.BLOCKED)
    completed = engine.goals.transition_goal(goal.id, GoalStatus.COMPLETED)
    assert completed.status is GoalStatus.COMPLETED


def test_manager_records_progress_evidence_without_an_event_and_deduplicates() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)
    event_count = len(engine.state.events)
    evidence = ProgressEvidence(0, "Water reserve: 1 of 10 required.")
    updated = engine.goals.record_goal_evidence(goal.id, evidence)
    duplicate = engine.goals.record_goal_evidence(
        goal.id, ProgressEvidence(0, evidence.description)
    )
    assert updated == duplicate
    assert updated.evidence == (evidence,)
    assert len(engine.state.events) == event_count


def test_manager_rejects_invalid_progress_evidence_atomically() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    engine.goals.transition_objective(objectives[0].id, GoalStatus.ACTIVE)
    before = engine.state.objective_states[objectives[0].id]
    event_count = len(engine.state.events)
    with pytest.raises(ValueError, match="future tick"):
        engine.goals.record_objective_evidence(
            objectives[0].id, ProgressEvidence(1, "Future progress.")
        )
    assert engine.state.objective_states[objectives[0].id] == before
    assert len(engine.state.events) == event_count


def test_graph_creation_is_atomic_on_invalid_reference_or_cycle() -> None:
    engine = _engine()
    goal, (objective,) = _records()
    bad = ObjectiveDefinition(
        objective.id,
        objective.label,
        objective.purpose,
        objective.npc_interpretation,
        objective.completion_criteria,
        dependencies=("missing",),
        authorized_action_categories=objective.authorized_action_categories,
    )
    with pytest.raises(ValueError, match="references"):
        engine.goals.create(goal, (bad,))
    assert not engine.state.goal_definitions and not engine.state.objective_definitions


def test_duplicate_labels_deadlines_and_missing_owners_are_rejected() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    with pytest.raises(ValueError, match="unique per owner"):
        engine.goals.create(
            GoalDefinition(
                "other",
                goal.owner_kind,
                goal.owner_id,
                " found oakford ",
                "x",
                "x",
                ("other_o",),
                authorized_action_categories=("x",),
            ),
            (
                ObjectiveDefinition(
                    "other_o",
                    "x",
                    "x",
                    "x",
                    (ResourceMinimumCriterion("x", 1),),
                    authorized_action_categories=("x",),
                ),
            ),
        )


def test_all_closed_criterion_variants_round_trip_and_inspection_is_detached(
    tmp_path: object,
) -> None:
    from pathlib import Path

    database = Path(str(tmp_path)) / "goals.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    engine.definitions.register(Definition("settlement"))
    owner = engine.entities.create(definition_key="settlement", name="Oakford")
    criteria = (
        ResourceMinimumCriterion("water", 10),
        ConstructedCapabilityCriterion("shelter", 2),
        CapacityCriterion("storage", 20),
        ExternalConnectionCriterion("homeland", "contactable"),
        SustainedNeedCriterion("hunger", 0.25, 4),
        SettlementStageCriterion("settlement"),
    )
    objective = ObjectiveDefinition(
        "objective_all",
        "Founding conditions",
        "Meet conditions",
        "Build a secure home.",
        criteria,
        authorized_action_categories=("founding_work",),
    )
    goal = GoalDefinition(
        "goal_all",
        GoalOwnerKind.SETTLEMENT,
        owner.id,
        "Establish Oakford",
        "Establish Oakford",
        "Help establish Oakford.",
        (objective.id,),
        authorized_action_categories=("founding_work",),
    )
    engine.goals.create(goal, (objective,))
    engine.save_world()
    loaded = repository.load_world()
    assert loaded.objective_definitions[objective.id].completion_criteria == criteria
    snapshot = EngineWorldInspector(engine).goals()
    snapshot[0]["definition"]["label"] = "changed"  # type: ignore[index]
    assert engine.state.goal_definitions[goal.id].label == "Establish Oakford"


def test_cycle_is_rejected_without_partial_mutation() -> None:
    engine = _engine()
    first = ObjectiveDefinition(
        "a",
        "A",
        "A",
        "A",
        (ResourceMinimumCriterion("x", 1),),
        dependencies=("b",),
        authorized_action_categories=("x",),
    )
    second = ObjectiveDefinition(
        "b",
        "B",
        "B",
        "B",
        (ResourceMinimumCriterion("x", 1),),
        dependencies=("a",),
        authorized_action_categories=("x",),
    )
    goal = GoalDefinition(
        "cycle",
        GoalOwnerKind.SETTLEMENT,
        "entity_000001",
        "Cycle",
        "Cycle",
        "Cycle",
        ("a", "b"),
        authorized_action_categories=("x",),
    )
    with pytest.raises(ValueError, match="acyclic"):
        engine.goals.create(goal, (first, second))
    assert engine.state.goal_definitions == {}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (("objective_ids", ("objective_water", "objective_water"), "unique"),),
)
def test_duplicate_goal_graph_ids_are_rejected_atomically(
    field: str, value: object, message: str
) -> None:
    engine = _engine()
    goal, objectives = _records()
    with pytest.raises(ValueError, match=message):
        engine.goals.create(replace(goal, **{field: value}), objectives)
    assert engine.state.goal_definitions == {}
    assert engine.state.objective_definitions == {}
    assert engine.state.events == {}


@pytest.mark.parametrize("reference_field", ("dependencies", "alternatives"))
def test_duplicate_objective_references_are_rejected_atomically(
    reference_field: str,
) -> None:
    engine = _engine()
    goal, (objective,) = _records()
    duplicate = replace(objective, **{reference_field: (objective.id, objective.id)})
    with pytest.raises(ValueError, match="unique"):
        engine.goals.create(goal, (duplicate,))
    assert engine.state.goal_definitions == {}
    assert engine.state.objective_definitions == {}
    assert engine.state.events == {}


def test_duplicate_supplied_objective_ids_are_rejected_atomically() -> None:
    engine = _engine()
    goal, (objective,) = _records()
    with pytest.raises(ValueError, match="exactly once"):
        engine.goals.create(goal, (objective, objective))
    assert engine.state.goal_definitions == {}
    assert engine.state.objective_definitions == {}
    assert engine.state.events == {}


@pytest.mark.parametrize(
    "goal_change",
    (
        {"owner_kind": "settlement"},
        {"objective_ids": ["objective_water"]},
        {"deadline_tick": 1.5},
        {"deadline_tick": True},
        {"priority": 1.5},
        {"priority": True},
        {"authorized_action_categories": ["work"]},
        {"completion_criteria": []},
    ),
)
def test_goal_runtime_types_are_validated_predictably(
    goal_change: dict[str, object],
) -> None:
    engine = _engine()
    goal, objectives = _records()
    with pytest.raises(TypeError):
        engine.goals.create(replace(goal, **goal_change), objectives)
    assert engine.state.goal_definitions == {}


@pytest.mark.parametrize(
    "objective_change",
    (
        {"dependencies": ["objective_water"]},
        {"alternatives": ["objective_water"]},
        {"completion_criteria": []},
        {"failure_criteria": []},
        {"deadline_tick": False},
        {"priority": False},
        {"authorized_action_categories": ["work"]},
    ),
)
def test_objective_runtime_types_are_validated_predictably(
    objective_change: dict[str, object],
) -> None:
    engine = _engine()
    goal, (objective,) = _records()
    with pytest.raises(TypeError):
        engine.goals.create(goal, (replace(objective, **objective_change),))
    assert engine.state.objective_definitions == {}


@pytest.mark.parametrize(
    "criterion",
    (
        ResourceMinimumCriterion("water", True),
        ConstructedCapabilityCriterion("well", 1.5),
        CapacityCriterion("storage", False),
        SustainedNeedCriterion("hunger", True, 2),
        SustainedNeedCriterion("hunger", 0.2, False),
    ),
)
def test_criterion_numeric_types_reject_bool_and_wrong_types(
    criterion: object,
) -> None:
    engine = _engine()
    goal, (objective,) = _records()
    with pytest.raises(TypeError):
        engine.goals.create(
            goal, (replace(objective, completion_criteria=(criterion,)),)
        )


@pytest.mark.parametrize("maximum", (-1.0, nan, inf, -inf))
def test_sustained_need_maximum_must_be_finite_and_nonnegative(
    maximum: float,
) -> None:
    engine = _engine()
    goal, (objective,) = _records()
    criterion = SustainedNeedCriterion("hunger", maximum, 2)
    with pytest.raises(ValueError, match="finite and non-negative"):
        engine.goals.create(
            goal, (replace(objective, completion_criteria=(criterion,)),)
        )


def test_progress_evidence_sources_must_be_unique_nonempty_and_existing() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    engine.events.add(Event("source", 0, "observed"))
    for source_ids, message in (
        (("source", "source"), "unique"),
        (("",), "cannot be empty"),
        (("missing",), "existing events"),
    ):
        with pytest.raises(ValueError, match=message):
            engine.goals.transition_goal(
                goal.id,
                GoalStatus.ACTIVE,
                ProgressEvidence(0, "Evidence", source_ids),
            )
        assert engine.state.goal_states[goal.id].status is GoalStatus.INACTIVE


def test_goal_and_objective_blocked_lifecycle() -> None:
    engine = _engine()
    goal, (objective,) = _records()
    engine.goals.create(goal, (objective,))
    engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)
    engine.goals.transition_goal(goal.id, GoalStatus.BLOCKED)
    assert (
        engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE).status
        is GoalStatus.ACTIVE
    )
    engine.goals.transition_objective(objective.id, GoalStatus.ACTIVE)
    blocked = engine.goals.transition_objective(objective.id, GoalStatus.BLOCKED)
    assert blocked.status is GoalStatus.BLOCKED
    assert (
        engine.goals.transition_objective(objective.id, GoalStatus.ACTIVE).status
        is GoalStatus.ACTIVE
    )
    with pytest.raises(ValueError, match="Invalid lifecycle"):
        engine.goals.transition_objective(objective.id, GoalStatus.INACTIVE)


def test_create_rolls_back_state_and_partially_recorded_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _engine()
    goal, objectives = _records()

    def fail_record(**_: object) -> None:
        engine.state.events["partial"] = Event("partial", 0, "goal_created")
        raise RuntimeError("event failure")

    monkeypatch.setattr(engine.events, "record", fail_record)
    with pytest.raises(RuntimeError, match="event failure"):
        engine.goals.create(goal, objectives)
    assert engine.state.goal_definitions == {}
    assert engine.state.goal_states == {}
    assert engine.state.objective_definitions == {}
    assert engine.state.objective_states == {}
    assert engine.state.events == {}


def test_transition_rolls_back_state_and_partially_recorded_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    original_events = dict(engine.state.events)

    def fail_record(**_: object) -> None:
        engine.state.events["partial"] = Event("partial", 0, "goal_active")
        raise RuntimeError("event failure")

    monkeypatch.setattr(engine.events, "record", fail_record)
    with pytest.raises(RuntimeError, match="event failure"):
        engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)
    assert engine.state.goal_states[goal.id].status is GoalStatus.INACTIVE
    assert engine.state.events == original_events


def test_transition_rejects_non_enum_status_and_non_tuple_evidence_sources() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    with pytest.raises(TypeError, match="GoalStatus"):
        engine.goals.transition_goal(goal.id, "active")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be a tuple"):
        engine.goals.transition_goal(
            goal.id,
            GoalStatus.ACTIVE,
            ProgressEvidence(0, "Evidence", ["event_000001"]),  # type: ignore[arg-type]
        )


def test_loaded_state_rejects_non_enum_status_and_non_tuple_evidence() -> None:
    engine = _engine()
    goal, objectives = _records()
    engine.goals.create(goal, objectives)
    current = engine.state.goal_states[goal.id]
    engine.state.goal_states[goal.id] = replace(
        current, status="active"  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="GoalStatus"):
        engine.goals.validate_loaded_state()
    engine.state.goal_states[goal.id] = replace(
        current, evidence=[]  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="must be a tuple"):
        engine.goals.validate_loaded_state()


@pytest.mark.parametrize("owner_kind", tuple(GoalOwnerKind))
def test_all_owner_scopes_are_supported_and_owner_removal_is_guarded(
    owner_kind: GoalOwnerKind,
) -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(owner_kind.value))
    owner = engine.entities.create(
        definition_key=owner_kind.value, name=owner_kind.value.title()
    )
    objective = ObjectiveDefinition(
        "objective",
        "Objective",
        "Purpose",
        "Visible purpose.",
        (ResourceMinimumCriterion("water", 1),),
        authorized_action_categories=("work",),
    )
    goal = GoalDefinition(
        "goal",
        owner_kind,
        owner.id,
        "Goal",
        "Purpose",
        "Visible purpose.",
        (objective.id,),
        authorized_action_categories=("work",),
    )
    engine.goals.create(goal, (objective,))
    with pytest.raises(ValueError, match="goal refers"):
        engine.entities.remove(owner.id)
    missing = GoalDefinition(
        "missing",
        GoalOwnerKind.NPC,
        "none",
        "Personal",
        "x",
        "x",
        ("mo",),
        authorized_action_categories=("x",),
    )
    with pytest.raises(ValueError, match="live entity"):
        engine.goals.create(
            missing,
            (
                ObjectiveDefinition(
                    "mo",
                    "x",
                    "x",
                    "x",
                    (ResourceMinimumCriterion("x", 1),),
                    authorized_action_categories=("x",),
                ),
            ),
        )
