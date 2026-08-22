import pytest

from living_world.api.inspection import EngineWorldInspector
from living_world.core.definition import Definition
from living_world.external_world import ContactState
from living_world.goals import (
    CapacityCriterion,
    ConstructedCapabilityCriterion,
    CriterionDisposition,
    CriterionEvaluation,
    CriterionEvaluatorRegistry,
    ExternalConnectionCriterion,
    GoalDefinition,
    GoalEvaluationSystem,
    GoalOwnerKind,
    GoalStatus,
    ObjectiveDefinition,
    ResourceMinimumCriterion,
    SettlementStageCriterion,
    SustainedNeedCriterion,
    default_criterion_evaluators,
)
from living_world.needs import (
    NeedAssessment,
    NeedDefinition,
    NeedKind,
    NeedLevel,
    NeedState,
)
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.simulation.simulation_engine import SimulationEngine


def _engine() -> tuple[SimulationEngine, str]:
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    owner = engine.entities.create(definition_key="settlement", name="Oakford")
    return engine, owner.id


def _create(
    engine: SimulationEngine,
    owner_id: str,
    objectives: tuple[ObjectiveDefinition, ...],
    *,
    completion_criteria: tuple[object, ...] = (),
    failure_criteria: tuple[object, ...] = (),
    deadline_tick: int | None = None,
) -> GoalDefinition:
    goal = GoalDefinition(
        "goal_found",
        GoalOwnerKind.SETTLEMENT,
        owner_id,
        "Found Oakford",
        "Establish Oakford",
        "Help establish a lasting home.",
        tuple(item.id for item in objectives),
        deadline_tick=deadline_tick,
        authorized_action_categories=("settlement_work",),
        completion_criteria=completion_criteria,  # type: ignore[arg-type]
        failure_criteria=failure_criteria,  # type: ignore[arg-type]
    )
    engine.goals.create(goal, objectives)
    return goal


def _objective(
    objective_id: str,
    criterion: object,
    *,
    dependencies: tuple[str, ...] = (),
    alternatives: tuple[str, ...] = (),
    failure_criteria: tuple[object, ...] = (),
    deadline_tick: int | None = None,
) -> ObjectiveDefinition:
    return ObjectiveDefinition(
        objective_id,
        objective_id.replace("_", " ").title(),
        "Operator purpose",
        "Make visible progress.",
        (criterion,),  # type: ignore[arg-type]
        failure_criteria=failure_criteria,  # type: ignore[arg-type]
        dependencies=dependencies,
        alternatives=alternatives,
        deadline_tick=deadline_tick,
        authorized_action_categories=("settlement_work",),
    )


def test_resource_evaluation_transitions_once_and_is_idempotent() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes["resources"] = {"water": 10}
    objective = _objective("water", ResourceMinimumCriterion("water", 10))
    goal = _create(engine, owner_id, (objective,))

    engine.step()
    assert engine.state.objective_states[objective.id].status is GoalStatus.ACTIVE
    assert engine.state.goal_states[goal.id].status is GoalStatus.ACTIVE
    engine.step()
    assert engine.state.objective_states[objective.id].status is GoalStatus.COMPLETED
    assert engine.state.goal_states[goal.id].status is GoalStatus.COMPLETED
    event_count = len(engine.state.events)
    evidence_count = len(engine.state.objective_states[objective.id].evidence)
    engine.step()
    assert len(engine.state.events) == event_count
    assert len(engine.state.objective_states[objective.id].evidence) == evidence_count


def test_active_resource_progress_records_only_material_changes() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes["resources"] = {"water": 1}
    objective = _objective("water", ResourceMinimumCriterion("water", 10))
    _create(engine, owner_id, (objective,))
    engine.step()
    initial = engine.state.objective_states[objective.id]
    event_count = len(engine.state.events)
    assert "1 of 10" in initial.evidence[-1].description

    engine.state.entities[owner_id].attributes["resources"]["water"] = 4  # type: ignore[index]
    engine.step()
    progressed = engine.state.objective_states[objective.id]
    assert progressed.status is GoalStatus.ACTIVE
    assert len(progressed.evidence) == len(initial.evidence) + 1
    assert "4 of 10" in progressed.evidence[-1].description
    assert len(engine.state.events) == event_count

    engine.step()
    assert engine.state.objective_states[objective.id].evidence == progressed.evidence
    assert len(engine.state.events) == event_count


def test_goal_level_criterion_progress_is_recorded_without_npc_exposure() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes["resources"] = {
        "water": 1,
        "stone": 0,
    }
    objective = _objective("stone", ResourceMinimumCriterion("stone", 1))
    goal = _create(
        engine,
        owner_id,
        (objective,),
        completion_criteria=(ResourceMinimumCriterion("water", 10),),
    )
    engine.step()
    initial_count = len(engine.state.goal_states[goal.id].evidence)
    event_count = len(engine.state.events)
    engine.state.entities[owner_id].attributes["resources"]["water"] = 4  # type: ignore[index]
    engine.step()
    goal_state = engine.state.goal_states[goal.id]
    assert len(goal_state.evidence) == initial_count + 1
    assert "4 of 10" in goal_state.evidence[-1].description
    assert len(engine.state.events) == event_count
    safe = engine.goals.npc_interpretation(goal.id)
    assert not hasattr(safe, "evidence") and not hasattr(safe, "status")
    privileged = EngineWorldInspector(engine).goals()[0]
    assert privileged["state"]["evidence"][-1]["description"] == (
        goal_state.evidence[-1].description
    )


def test_construction_and_capacity_use_only_live_directly_owned_entities() -> None:
    engine, owner_id = _engine()
    engine.definitions.register(Definition("shelter"))
    direct = engine.entities.create(
        definition_key="shelter",
        name="Direct shelter",
        attributes={"is_constructed": True, "beds_capacity": 4},
    )
    nested = engine.entities.create(
        definition_key="shelter",
        name="Nested shelter",
        attributes={"is_constructed": True, "beds_capacity": 100},
    )
    intermediary = engine.entities.create(definition_key="settlement", name="Ward")
    engine.relationships.create(kind="owns", source_id=owner_id, target_id=direct.id)
    engine.relationships.create(
        kind="owns", source_id=owner_id, target_id=intermediary.id
    )
    engine.relationships.create(
        kind="owns", source_id=intermediary.id, target_id=nested.id
    )
    objectives = (
        _objective("shelter", ConstructedCapabilityCriterion("shelter", 1)),
        _objective("beds", CapacityCriterion("beds", 5)),
    )
    _create(engine, owner_id, objectives)
    engine.run(2)
    assert engine.state.objective_states["shelter"].status is GoalStatus.COMPLETED
    assert engine.state.objective_states["beds"].status is GoalStatus.ACTIVE


def test_missing_capacity_and_deferred_criteria_block_deterministically() -> None:
    engine, owner_id = _engine()
    objectives = (
        _objective("capacity", CapacityCriterion("beds", 1)),
        _objective("need", SustainedNeedCriterion("hunger", 0.2, 3)),
        _objective("stage", SettlementStageCriterion("settlement")),
    )
    _create(engine, owner_id, objectives)
    engine.run(2)
    assert {engine.state.objective_states[item.id].status for item in objectives} == {
        GoalStatus.BLOCKED
    }
    counts = {
        item.id: len(engine.state.objective_states[item.id].evidence)
        for item in objectives
    }
    engine.step()
    assert counts == {
        item.id: len(engine.state.objective_states[item.id].evidence)
        for item in objectives
    }


def test_external_connection_matches_exact_role_and_contact_state() -> None:
    engine, owner_id = _engine()
    engine.external_world_references.create(
        name="Homeland",
        role="homeland",
        capacity=10,
        delay_ticks=1,
        cost_per_unit=1,
        reliability=1.0,
        contact_state=ContactState.CONTACTABLE,
    )
    objective = _objective(
        "connection", ExternalConnectionCriterion("homeland", "contactable")
    )
    _create(engine, owner_id, (objective,))
    engine.run(2)
    state = engine.state.objective_states[objective.id]
    assert state.status is GoalStatus.COMPLETED
    assert state.evidence[-1].source_event_ids == ("event_000001",)


def test_dependency_and_alternative_graph_order() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes["resources"] = {"wood": 1}
    alternative = _objective("alternative", ResourceMinimumCriterion("wood", 1))
    parent = _objective(
        "parent",
        ResourceMinimumCriterion("stone", 1),
        alternatives=(alternative.id,),
    )
    dependent = _objective(
        "dependent",
        ResourceMinimumCriterion("wood", 1),
        dependencies=(parent.id,),
    )
    goal = _create(engine, owner_id, (dependent, parent, alternative))
    engine.run(2)
    assert engine.state.objective_states[alternative.id].status is GoalStatus.COMPLETED
    assert engine.state.objective_states[parent.id].status is GoalStatus.COMPLETED
    assert engine.state.objective_states[dependent.id].status is GoalStatus.ACTIVE
    engine.step()
    assert engine.state.objective_states[dependent.id].status is GoalStatus.COMPLETED
    assert engine.state.goal_states[goal.id].status is GoalStatus.COMPLETED


def test_deadlines_and_failure_criteria_take_precedence() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes["resources"] = {"water": 10}
    objective = _objective(
        "water",
        ResourceMinimumCriterion("water", 10),
        failure_criteria=(ResourceMinimumCriterion("water", 5),),
        deadline_tick=1,
    )
    goal = _create(engine, owner_id, (objective,), deadline_tick=1)
    engine.step()
    assert engine.state.objective_states[objective.id].status is GoalStatus.FAILED
    assert engine.state.goal_states[goal.id].status is GoalStatus.FAILED
    assert (
        "failure criteria"
        in engine.state.objective_states[objective.id].evidence[-1].description
    )


def test_any_satisfied_failure_criterion_is_sufficient() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes["resources"] = {"water": 10}
    objective = _objective(
        "water",
        ResourceMinimumCriterion("stone", 1),
        failure_criteria=(
            ResourceMinimumCriterion("wood", 10),
            ResourceMinimumCriterion("water", 5),
        ),
    )
    _create(engine, owner_id, (objective,))
    engine.step()
    assert engine.state.objective_states[objective.id].status is GoalStatus.FAILED


def test_deadline_fails_at_the_configured_current_tick() -> None:
    engine, owner_id = _engine()
    objective = _objective(
        "water", ResourceMinimumCriterion("water", 1), deadline_tick=1
    )
    goal = _create(engine, owner_id, (objective,), deadline_tick=1)
    engine.step()
    assert engine.state.tick == 1
    assert engine.state.objective_states[objective.id].status is GoalStatus.ACTIVE
    engine.step()
    assert engine.state.objective_states[objective.id].status is GoalStatus.FAILED
    assert engine.state.goal_states[goal.id].status is GoalStatus.FAILED
    assert engine.state.objective_states[objective.id].evidence[-1].tick == 1


def test_blocked_objective_can_complete_directly() -> None:
    engine, owner_id = _engine()
    objective = _objective("water", ResourceMinimumCriterion("water", 1))
    _create(engine, owner_id, (objective,))
    engine.run(2)
    engine.state.entities[owner_id].attributes["resources"] = {"water": 1}
    event_count = len(engine.state.events)
    engine.step()
    assert engine.state.objective_states[objective.id].status is GoalStatus.COMPLETED
    assert len(engine.state.events) == event_count + 2  # objective and goal
    assert (
        engine.state.objective_states[objective.id]
        .evidence[-1]
        .description.startswith("Objective completion")
    )


def test_registry_rejects_missing_and_unknown_types() -> None:
    with pytest.raises(ValueError, match="Missing criterion evaluators"):
        CriterionEvaluatorRegistry({})
    evaluators = default_criterion_evaluators()
    evaluators.pop(ResourceMinimumCriterion)
    with pytest.raises(ValueError, match="Missing criterion evaluators"):
        CriterionEvaluatorRegistry(evaluators)
    evaluators = default_criterion_evaluators()
    evaluators[str] = evaluators[ResourceMinimumCriterion]
    with pytest.raises(TypeError, match="Unregistered criterion types"):
        CriterionEvaluatorRegistry(evaluators)


def test_custom_registered_evaluator_result_is_frozen_and_normalized() -> None:
    class AvailableStage:
        def evaluate(
            self, criterion: object, *, owner_id: str, state: object
        ) -> CriterionEvaluation:
            del criterion, owner_id, state
            return CriterionEvaluation(CriterionDisposition.SATISFIED, "Stage reached.")

    engine, owner_id = _engine()
    evaluators = default_criterion_evaluators()
    evaluators[SettlementStageCriterion] = AvailableStage()
    objective = _objective("stage", SettlementStageCriterion("settlement"))
    _create(engine, owner_id, (objective,))
    system = GoalEvaluationSystem(engine.goals, CriterionEvaluatorRegistry(evaluators))
    system.step(engine.state)
    system.step(engine.state)
    assert engine.state.objective_states[objective.id].status is GoalStatus.COMPLETED


def test_evaluation_rolls_back_all_transitions_when_event_recording_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, owner_id = _engine()
    objective = _objective("water", ResourceMinimumCriterion("water", 1))
    _create(engine, owner_id, (objective,))
    before_events = dict(engine.state.events)
    calls = 0
    original = engine.events.record

    def fail_second(**kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("event failure")
        return original(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(engine.events, "record", fail_second)
    with pytest.raises(RuntimeError, match="event failure"):
        GoalEvaluationSystem(engine.goals).step(engine.state)
    assert engine.state.objective_states[objective.id].status is GoalStatus.INACTIVE
    assert engine.state.goal_states["goal_found"].status is GoalStatus.INACTIVE
    assert engine.state.events == before_events


def test_goal_completion_criteria_are_evaluated_after_required_objectives() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes["resources"] = {"water": 1}
    objective = _objective("water", ResourceMinimumCriterion("water", 1))
    goal = _create(
        engine,
        owner_id,
        (objective,),
        completion_criteria=(ResourceMinimumCriterion("stone", 1),),
    )
    engine.run(2)
    assert engine.state.objective_states[objective.id].status is GoalStatus.COMPLETED
    assert engine.state.goal_states[goal.id].status is GoalStatus.ACTIVE
    engine.state.entities[owner_id].attributes["resources"]["stone"] = 1  # type: ignore[index]
    engine.step()
    assert engine.state.goal_states[goal.id].status is GoalStatus.COMPLETED


def test_invalid_authoritative_field_types_fail_loudly() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes["resources"] = {"water": True}
    objective = _objective("water", ResourceMinimumCriterion("water", 1))
    _create(engine, owner_id, (objective,))
    with pytest.raises(TypeError, match="must be an integer"):
        engine.step()


def test_later_registered_domain_system_still_runs_before_goal_evaluation() -> None:
    engine, owner_id = _engine()
    objective = _objective("water", ResourceMinimumCriterion("water", 1))
    _create(engine, owner_id, (objective,))
    engine.goals.transition_objective(objective.id, GoalStatus.ACTIVE)

    class SupplyWater:
        def step(self, state: object) -> None:
            del state
            engine.state.entities[owner_id].attributes["resources"] = {"water": 1}

    engine.register_system(SupplyWater())
    engine.step()
    assert engine.state.objective_states[objective.id].status is GoalStatus.COMPLETED


def test_save_resume_matches_uninterrupted_evaluation(tmp_path: object) -> None:
    from pathlib import Path

    repository = SQLiteRepository(str(Path(str(tmp_path)) / "goals.sqlite3"))
    resumed = SimulationEngine(repository)
    resumed.definitions.register(Definition("settlement"))
    owner = resumed.entities.create(definition_key="settlement", name="Oakford")
    owner.attributes["resources"] = {"water": 1}
    objective = _objective("water", ResourceMinimumCriterion("water", 1))
    goal = _create(resumed, owner.id, (objective,))
    resumed.step()
    resumed.save_world()
    resumed = SimulationEngine(repository)
    resumed.definitions.register(Definition("settlement"))
    resumed.step()

    uninterrupted, owner_id = _engine()
    uninterrupted.state.entities[owner_id].attributes["resources"] = {"water": 1}
    same_objective = _objective("water", ResourceMinimumCriterion("water", 1))
    same_goal = _create(uninterrupted, owner_id, (same_objective,))
    uninterrupted.run(2)

    assert (
        resumed.state.goal_states[goal.id]
        == uninterrupted.state.goal_states[same_goal.id]
    )
    assert resumed.state.objective_states[objective.id] == (
        uninterrupted.state.objective_states[same_objective.id]
    )
    assert tuple(
        (event.tick, event.kind, event.subject_id)
        for event in resumed.state.events.values()
    ) == tuple(
        (event.tick, event.kind, event.subject_id)
        for event in uninterrupted.state.events.values()
    )


def test_progress_evidence_persists_across_save_and_resume(tmp_path: object) -> None:
    from pathlib import Path

    repository = SQLiteRepository(str(Path(str(tmp_path)) / "progress.sqlite3"))
    engine = SimulationEngine(repository)
    engine.definitions.register(Definition("settlement"))
    owner = engine.entities.create(definition_key="settlement", name="Oakford")
    owner.attributes["resources"] = {"water": 1}
    objective = _objective("water", ResourceMinimumCriterion("water", 10))
    _create(engine, owner.id, (objective,))
    engine.step()
    owner.attributes["resources"]["water"] = 4  # type: ignore[index]
    engine.step()
    expected = engine.state.objective_states[objective.id].evidence
    engine.save_world()

    loaded = SimulationEngine(repository)
    assert loaded.state.objective_states[objective.id].evidence == expected
    assert "4 of 10" in expected[-1].description


def test_sustained_need_evaluator_requires_consecutive_current_history() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes.update(
        {"population": 10, "resources": {"water": 9}}
    )
    engine.needs.create(
        NeedDefinition("need_water", owner_id, NeedKind.WATER, 1, 0.2, 0.5, 3)
    )
    evaluator = default_criterion_evaluators()[SustainedNeedCriterion]
    criterion = SustainedNeedCriterion("water", 0.2, 2)

    first = evaluator.evaluate(criterion, owner_id=owner_id, state=engine.state)
    assert first.disposition is CriterionDisposition.UNAVAILABLE
    engine.run(2)
    result = evaluator.evaluate(criterion, owner_id=owner_id, state=engine.state)
    # The scheduler has advanced beyond the final recorded tick until the next pass.
    assert result.disposition is CriterionDisposition.UNAVAILABLE
    engine.state.tick -= 1
    result = evaluator.evaluate(criterion, owner_id=owner_id, state=engine.state)
    assert result.disposition is CriterionDisposition.SATISFIED
    assert "ordered pressures [0.1, 0.1]" in result.description
    assert result.source_event_ids == tuple(sorted(result.source_event_ids))


def test_sustained_need_pressure_change_appends_evidence_then_is_idempotent() -> None:
    engine, owner_id = _engine()
    owner = engine.state.entities[owner_id]
    owner.attributes.update({"population": 10, "resources": {"food": 8}})
    engine.needs.create(
        NeedDefinition("need_food", owner_id, NeedKind.FOOD, 1, 0.5, 0.8, 2)
    )
    objective = _objective("food", SustainedNeedCriterion("food", 0.1, 2))
    _create(engine, owner_id, (objective,))

    engine.step()
    owner.attributes["resources"] = {"food": 7}
    engine.step()
    before = len(engine.state.objective_states[objective.id].evidence)
    owner.attributes["resources"] = {"food": 6}
    engine.step()
    changed = len(engine.state.objective_states[objective.id].evidence)
    assert changed == before + 1
    assert "ordered pressures [0.3, 0.4]" in (
        engine.state.objective_states[objective.id].evidence[-1].description
    )
    assert engine.state.need_states["need_food"].current.level is NeedLevel.SECURE

    engine.step()
    stable_sequence = len(engine.state.objective_states[objective.id].evidence)
    engine.step()
    assert len(engine.state.objective_states[objective.id].evidence) == stable_sequence


def test_sustained_need_maximum_above_one_passes() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes.update(
        {"population": 10, "resources": {"food": 0}}
    )
    engine.needs.create(
        NeedDefinition("need_food", owner_id, NeedKind.FOOD, 1, 0.2, 0.5, 2)
    )
    engine.run(2)
    engine.state.tick = 1
    evaluator = default_criterion_evaluators()[SustainedNeedCriterion]
    result = evaluator.evaluate(
        SustainedNeedCriterion("food", 1.5, 2),
        owner_id=owner_id,
        state=engine.state,
    )
    assert result.disposition is CriterionDisposition.SATISFIED


@pytest.mark.parametrize(
    ("mode", "reason"),
    (
        ("missing", "unique need definition"),
        ("short", "assessment window is too short"),
        ("incomplete", "assessment history is incomplete"),
        ("nonconsecutive", "assessment history is not consecutive"),
        ("unavailable", "an assessment is unavailable"),
    ),
)
def test_sustained_need_unavailable_reasons_are_stable(mode: str, reason: str) -> None:
    engine, owner_id = _engine()
    evaluator = default_criterion_evaluators()[SustainedNeedCriterion]
    if mode != "missing":
        window = 1 if mode == "short" else 3
        definition = engine.needs.create(
            NeedDefinition("need_food", owner_id, NeedKind.FOOD, 1, 0.2, 0.5, window)
        )
        if mode == "nonconsecutive":
            first = NeedAssessment(0, NeedLevel.SECURE, 1, 1, 0, 0.0)
            last = NeedAssessment(2, NeedLevel.SECURE, 1, 1, 0, 0.0)
            engine.state.tick = 2
            engine.state.need_states[definition.id] = NeedState(
                definition.id, last, (first, last)
            )
        elif mode == "unavailable":
            first = NeedAssessment(0, NeedLevel.SECURE, 1, 1, 0, 0.0)
            last = NeedAssessment(1, NeedLevel.UNAVAILABLE, None, None, None, None)
            engine.state.tick = 1
            engine.state.need_states[definition.id] = NeedState(
                definition.id, last, (first, last)
            )
    result = evaluator.evaluate(
        SustainedNeedCriterion("food", 0.5, 2),
        owner_id=owner_id,
        state=engine.state,
    )
    assert result.disposition is CriterionDisposition.UNAVAILABLE
    assert reason in result.description


def test_sustained_need_sources_exclude_unrelated_same_subject_events() -> None:
    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes.update(
        {"population": 1, "resources": {"food": 1}}
    )
    definition = engine.needs.create(
        NeedDefinition("need_food", owner_id, NeedKind.FOOD, 1, 0.2, 0.5, 2)
    )
    unrelated = engine.events.record(kind="unrelated", subject_id=definition.id)
    engine.run(2)
    engine.state.tick = 1
    result = default_criterion_evaluators()[SustainedNeedCriterion].evaluate(
        SustainedNeedCriterion("food", 0.5, 2),
        owner_id=owner_id,
        state=engine.state,
    )
    assert unrelated.id not in result.source_event_ids
    assert all(
        engine.state.events[event_id].kind in {"need_created", "need_level_changed"}
        for event_id in result.source_event_ids
    )


def test_consequence_need_sustained_goal_evidence_flow() -> None:
    from living_world.needs import ConsumptionPolicy

    engine, owner_id = _engine()
    engine.state.entities[owner_id].attributes.update(
        {"population": 1, "resources": {"food": 1}}
    )
    engine.needs.create(
        NeedDefinition("need_food", owner_id, NeedKind.FOOD, 1, 0.2, 0.5, 2)
    )
    objective = _objective("food", SustainedNeedCriterion("food", 1.0, 2))
    _create(engine, owner_id, (objective,))
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner_id, 1, 1)
    )
    engine.run(2)
    assert engine.state.need_states["need_food"].current.available == 0
    evidence = engine.state.objective_states[objective.id].evidence
    assert evidence
    assert "ordered pressures [1.0, 1.0]" in evidence[-1].description
    assert all(
        engine.state.events[event_id].kind in {"need_created", "need_level_changed"}
        for event_id in evidence[-1].source_event_ids
    )
