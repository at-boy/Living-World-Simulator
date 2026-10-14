from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import cast

import pytest

from living_world.core.definition import Definition
from living_world.goals import (
    CapacityCriterion,
    CriterionDisposition,
    GoalCriterion,
    GoalDefinition,
    GoalOwnerKind,
    GoalStatus,
    ObjectiveDefinition,
    PopulationMinimumCriterion,
)
from living_world.needs import MaintenancePolicy
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.stages import (
    SettlementStage,
    SettlementStageDefinition,
    SettlementStageEvaluationSystem,
    SettlementStageProgram,
    SettlementStageState,
    StageObjectiveRequirement,
    StageRequirementEvidence,
    StageRequirementKind,
)
from living_world.state.world_state import WorldState


def configured() -> tuple[SimulationEngine, str, SettlementStageProgram]:
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    owner = engine.entities.create(
        definition_key="settlement",
        name="Camp",
        attributes={"population": 4, "housing_capacity": 4},
    )
    objective = ObjectiveDefinition(
        "objective_housing",
        "Housing",
        "Provide homes",
        "Build homes.",
        (CapacityCriterion("housing", 1),),
        authorized_action_categories=("work",),
    )
    engine.goals.create(
        GoalDefinition(
            "goal_housing",
            GoalOwnerKind.SETTLEMENT,
            owner.id,
            "Homes",
            "Provide homes",
            "Build homes.",
            (objective.id,),
            authorized_action_categories=("work",),
        ),
        (objective,),
    )
    requirement = StageObjectiveRequirement(
        StageRequirementKind.CAPABILITY, objective.id
    )
    program = SettlementStageProgram(
        owner.id,
        (
            SettlementStageDefinition(SettlementStage.FOUNDING_CAMP, ()),
            SettlementStageDefinition(SettlementStage.SETTLEMENT, (requirement,)),
            SettlementStageDefinition(SettlementStage.TOWN, (requirement,)),
        ),
    )
    engine.settlement_stages.configure(program)
    return engine, owner.id, program


def test_adjacent_promotions_and_same_tick_idempotence() -> None:
    engine, owner, _ = configured()
    engine.step()
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.FOUNDING_CAMP
    )
    engine.step()
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.SETTLEMENT
    )
    system = SettlementStageEvaluationSystem(engine.settlement_stages)
    engine.state.tick -= 1
    system.step(engine.state)
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.SETTLEMENT
    )
    engine.state.tick += 1
    system.step(engine.state)
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.TOWN
    )
    system.step(engine.state)
    events = [
        e
        for e in engine.state.events.values()
        if e.kind == "settlement_stage_transitioned"
    ]
    assert len(events) == 2
    assert set(events[0].attributes) == {
        "previous_stage",
        "current_stage",
        "requirements",
    }
    requirements = cast(
        tuple[Mapping[str, object], ...], events[0].attributes["requirements"]
    )
    assert requirements[0]["source_event_ids"]


def test_frozen_and_duplicate_configuration() -> None:
    engine, owner, program = configured()
    with pytest.raises(FrozenInstanceError):
        program.settlement_id = "other"
    with pytest.raises(ValueError):
        engine.settlement_stages.configure(program)
    with pytest.raises(ValueError):
        engine.entities.remove(owner)
    with pytest.raises(ValueError):
        engine.entities.mark_destroyed(owner, engine.state.tick)


def test_population_criterion_registered() -> None:
    from living_world.goals import CriterionDisposition, CriterionEvaluatorRegistry

    engine, owner, _ = configured()
    result = CriterionEvaluatorRegistry().evaluate(
        PopulationMinimumCriterion(4), owner_id=owner, state=engine.state
    )
    assert result.disposition is CriterionDisposition.SATISFIED


def bare(
    criterion: GoalCriterion | None = None,
    kind: StageRequirementKind = StageRequirementKind.CAPABILITY,
) -> tuple[SimulationEngine, str, SettlementStageProgram]:
    engine, owner, program = configured()
    engine.state.settlement_stage_programs.clear()
    engine.state.settlement_stage_states.clear()
    objective = engine.state.objective_definitions["objective_housing"]
    if criterion is not None:
        engine.state.objective_definitions[objective.id] = replace(
            objective, completion_criteria=(criterion,)
        )
    requirement = replace(program.stages[1].requirements[0], kind=kind)
    program = replace(
        program,
        stages=(
            program.stages[0],
            replace(program.stages[1], requirements=(requirement,)),
            replace(program.stages[2], requirements=(requirement,)),
        ),
    )
    return engine, owner, program


@pytest.mark.parametrize(
    "case",
    [
        "order",
        "missing_stage",
        "duplicate_stage",
        "founding_requirements",
        "empty_settlement",
        "empty_town",
        "duplicate_objective",
        "unknown_owner",
        "destroyed_owner",
        "missing_objective",
        "wrong_owner_kind",
        "wrong_owner",
        "ambiguous_goal",
        "mismatched_kind",
        "population_only",
    ],
)
def test_configuration_rejects_invalid_programs_atomically(case: str) -> None:
    engine, owner, program = bare()
    stages = list(program.stages)
    goal = engine.state.goal_definitions["goal_housing"]
    if case == "order":
        stages.reverse()
    elif case == "missing_stage":
        stages.pop()
    elif case == "duplicate_stage":
        stages[2] = stages[1]
    elif case == "founding_requirements":
        stages[0] = replace(stages[0], requirements=stages[1].requirements)
    elif case in {"empty_settlement", "empty_town"}:
        index = 1 if case == "empty_settlement" else 2
        stages[index] = replace(stages[index], requirements=())
    elif case == "duplicate_objective":
        stages[1] = replace(stages[1], requirements=stages[1].requirements * 2)
    elif case == "unknown_owner":
        program = replace(program, settlement_id="entity_missing")
    elif case == "destroyed_owner":
        engine.state.entities[owner].destroyed_tick = 0
    elif case == "missing_objective":
        engine.state.objective_definitions.clear()
    elif case == "wrong_owner_kind":
        engine.state.goal_definitions[goal.id] = replace(
            goal, owner_kind=GoalOwnerKind.NPC
        )
    elif case == "wrong_owner":
        engine.state.goal_definitions[goal.id] = replace(goal, owner_id="entity_other")
    elif case == "ambiguous_goal":
        engine.state.goal_definitions["goal_other"] = replace(goal, id="goal_other")
    elif case in {"mismatched_kind", "population_only"}:
        kind = (
            StageRequirementKind.MAINTENANCE
            if case == "mismatched_kind"
            else StageRequirementKind.POPULATION
        )
        if case == "population_only":
            objective = engine.state.objective_definitions["objective_housing"]
            engine.state.objective_definitions[objective.id] = replace(
                objective, completion_criteria=(PopulationMinimumCriterion(1),)
            )
        stages[1] = replace(
            stages[1], requirements=(replace(stages[1].requirements[0], kind=kind),)
        )
    program = replace(program, stages=tuple(stages))
    before = dict(engine.state.events)
    with pytest.raises(ValueError):
        engine.settlement_stages.configure(program)
    assert not engine.state.settlement_stage_programs
    assert not engine.state.settlement_stage_states
    assert engine.state.events == before


@pytest.mark.parametrize(
    "kind",
    [
        StageRequirementKind.WATER,
        StageRequirementKind.FOOD,
        StageRequirementKind.SHELTER,
        StageRequirementKind.STORAGE,
    ],
)
@pytest.mark.parametrize("case", ["missing", "ambiguous", "short", "valid"])
def test_sustained_requirement_configuration(
    kind: StageRequirementKind, case: str
) -> None:
    from living_world.goals import SustainedNeedCriterion
    from living_world.needs import NeedDefinition, NeedKind

    engine, owner, program = bare(SustainedNeedCriterion(kind.value, 0.2, 2), kind)
    if case != "missing":
        definition = NeedDefinition(
            "need_supply",
            owner,
            NeedKind(kind.value),
            1,
            0.2,
            0.5,
            1 if case == "short" else 2,
        )
        engine.needs.create(definition)
        if case == "ambiguous":
            engine.state.need_definitions["need_duplicate"] = replace(
                definition, id="need_duplicate"
            )
    if case == "valid":
        engine.settlement_stages.configure(program)
        engine.step()
        assert (
            cast(
                SettlementStageState, engine.settlement_stages.state_for(owner)
            ).current_stage
            is SettlementStage.FOUNDING_CAMP
        )
    else:
        with pytest.raises(ValueError):
            engine.settlement_stages.configure(program)


@pytest.mark.parametrize("kind", list(StageRequirementKind))
@pytest.mark.parametrize(
    "status",
    [GoalStatus.INACTIVE, GoalStatus.ACTIVE, GoalStatus.BLOCKED, GoalStatus.FAILED],
)
def test_every_role_blocks_while_incomplete(
    kind: StageRequirementKind, status: GoalStatus
) -> None:
    from living_world.goals import (
        ExternalConnectionCriterion,
        MaintainedCapabilityCriterion,
        SustainedNeedCriterion,
    )
    from living_world.goals.model import ObjectiveState
    from living_world.needs import NeedDefinition, NeedKind

    criteria = {
        StageRequirementKind.MAINTENANCE: MaintainedCapabilityCriterion("well", 1, 1),
        StageRequirementKind.EXTERNAL_CONNECTION: ExternalConnectionCriterion(
            "trade", "connected"
        ),
        StageRequirementKind.POPULATION: PopulationMinimumCriterion(1),
        StageRequirementKind.CAPABILITY: CapacityCriterion("housing", 1),
    }
    criterion = criteria.get(kind, SustainedNeedCriterion(kind.value, 0.2, 1))
    engine, owner, program = bare(criterion, kind)
    if kind.value in {"water", "food", "shelter", "storage"}:
        engine.needs.create(
            NeedDefinition("need_supply", owner, NeedKind(kind.value), 1, 0.2, 0.5, 1)
        )
    if kind is StageRequirementKind.POPULATION:
        other = ObjectiveDefinition(
            "objective_other",
            "Other",
            "Homes",
            "Build homes.",
            (CapacityCriterion("housing", 1),),
            authorized_action_categories=("work",),
        )
        engine.state.objective_definitions[other.id] = other
        engine.state.objective_states[other.id] = ObjectiveState(
            other.id, GoalStatus.COMPLETED
        )
        goal = engine.state.goal_definitions["goal_housing"]
        engine.state.goal_definitions[goal.id] = replace(
            goal, objective_ids=goal.objective_ids + (other.id,)
        )
        program = replace(
            program,
            stages=tuple(
                (
                    replace(
                        definition,
                        requirements=definition.requirements
                        + (
                            StageObjectiveRequirement(
                                StageRequirementKind.CAPABILITY, other.id
                            ),
                        ),
                    )
                    if definition.requirements
                    else definition
                )
                for definition in program.stages
            ),
        )
    engine.settlement_stages.configure(program)
    engine.state.objective_states["objective_housing"] = ObjectiveState(
        "objective_housing", status
    )
    before = dict(engine.state.events)
    SettlementStageEvaluationSystem(engine.settlement_stages).step(engine.state)
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.FOUNDING_CAMP
    )
    assert engine.state.events == before


@pytest.mark.parametrize(
    "case",
    [
        "type",
        "owner",
        "future",
        "missing",
        "initial_transition",
        "promoted_without_transition",
    ],
)
def test_loaded_state_validation(case: str) -> None:
    from living_world.stages import SettlementStageState

    engine, owner, _ = configured()
    current = cast(SettlementStageState, engine.settlement_stages.state_for(owner))
    if case == "type":
        engine.state.settlement_stage_states[owner] = cast(SettlementStageState, {})
    elif case == "owner":
        engine.state.settlement_stage_states[owner] = replace(
            current, settlement_id="other"
        )
    elif case == "future":
        engine.state.settlement_stage_states[owner] = replace(current, entered_tick=1)
    elif case == "missing":
        engine.state.settlement_stage_states.clear()
    elif case == "initial_transition":
        engine.state.settlement_stage_states[owner] = replace(
            current, last_transition_tick=0
        )
    else:
        engine.state.settlement_stage_states[owner] = SettlementStageState(
            owner, SettlementStage.SETTLEMENT, 0
        )
    with pytest.raises((TypeError, ValueError)):
        engine.settlement_stages.validate_loaded_state()


def test_manager_rejects_forged_or_incomplete_evidence() -> None:
    from living_world.stages import StageRequirementEvidence

    engine, owner, _ = configured()
    evidence = engine.settlement_stages.requirement_evidence(owner)
    with pytest.raises(ValueError):
        engine.settlement_stages.transition_to_next(owner, evidence)
    engine.run(2)
    evidence = engine.settlement_stages.requirement_evidence(owner)
    with pytest.raises(ValueError):
        engine.settlement_stages.transition_to_next(
            owner, (replace(evidence[0], source_event_ids=()),)
        )
    with pytest.raises(TypeError):
        engine.settlement_stages.transition_to_next(
            owner, cast(tuple[StageRequirementEvidence, ...], [evidence[0]])
        )
    with pytest.raises(ValueError):
        StageRequirementEvidence(
            StageRequirementKind.CAPABILITY, "objective_x", ("z", "a")
        )


def test_manager_configuration_and_transition_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, owner, program = bare()
    original = engine.events.record

    def failing(
        *,
        kind: str,
        subject_id: str | None = None,
        attributes: dict[str, object] | None = None,
    ) -> None:
        original(kind=kind, subject_id=subject_id, attributes=attributes)
        raise RuntimeError("event failure")

    before = dict(engine.state.events)
    monkeypatch.setattr(engine.events, "record", failing)
    with pytest.raises(RuntimeError):
        engine.settlement_stages.configure(program)
    assert not engine.state.settlement_stage_programs
    assert not engine.state.settlement_stage_states
    assert engine.state.events == before
    monkeypatch.setattr(engine.events, "record", original)
    engine.settlement_stages.configure(program)
    engine.goals.transition_objective("objective_housing", GoalStatus.ACTIVE)
    engine.goals.transition_objective("objective_housing", GoalStatus.COMPLETED)
    before = dict(engine.state.events)
    current = cast(SettlementStageState, engine.settlement_stages.state_for(owner))
    monkeypatch.setattr(engine.events, "record", failing)
    with pytest.raises(RuntimeError):
        engine.settlement_stages.transition_to_next(
            owner, engine.settlement_stages.requirement_evidence(owner)
        )
    assert (
        cast(SettlementStageState, engine.settlement_stages.state_for(owner)) == current
    )
    assert engine.state.events == before


def test_phase_rollback_preserves_earlier_phase_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, _owner, program = configured()
    second = engine.entities.create(definition_key="settlement", name="Second")
    objective = replace(
        engine.state.objective_definitions["objective_housing"],
        id="objective_second",
        label="Second homes",
    )
    engine.goals.create(
        GoalDefinition(
            "goal_second",
            GoalOwnerKind.SETTLEMENT,
            second.id,
            "Second",
            "Homes",
            "Build homes.",
            (objective.id,),
            authorized_action_categories=("work",),
        ),
        (objective,),
    )
    second_program = replace(
        program,
        settlement_id=second.id,
        stages=tuple(
            replace(
                definition,
                requirements=tuple(
                    replace(item, objective_id=objective.id)
                    for item in definition.requirements
                ),
            )
            for definition in program.stages
        ),
    )
    engine.settlement_stages.configure(second_program)
    for objective_id in ("objective_housing", "objective_second"):
        engine.goals.transition_objective(objective_id, GoalStatus.ACTIVE)
        engine.goals.transition_objective(objective_id, GoalStatus.COMPLETED)
    before = dict(engine.state.events)
    states = dict(engine.state.settlement_stage_states)
    original = engine.settlement_stages.transition_to_next

    def failing(
        settlement_id: str, evidence: tuple[StageRequirementEvidence, ...]
    ) -> SettlementStageState:
        result = original(settlement_id, evidence)
        if settlement_id == second.id:
            raise RuntimeError("second settlement failure")
        return result

    monkeypatch.setattr(engine.settlement_stages, "transition_to_next", failing)
    with pytest.raises(RuntimeError):
        SettlementStageEvaluationSystem(engine.settlement_stages).step(engine.state)
    assert engine.state.settlement_stage_states == states
    assert engine.state.events == before


def test_stage_criterion_all_dispositions_and_next_tick_visibility() -> None:
    from living_world.goals import (
        CriterionDisposition,
        CriterionEvaluatorRegistry,
        SettlementStageCriterion,
    )

    engine, owner, _ = configured()
    registry = CriterionEvaluatorRegistry()

    def evaluate(stage: str, owner_id: str = owner) -> CriterionDisposition:
        return registry.evaluate(
            SettlementStageCriterion(stage), owner_id=owner_id, state=engine.state
        ).disposition

    assert evaluate("founding_camp") is CriterionDisposition.SATISFIED
    assert evaluate("town") is CriterionDisposition.UNSATISFIED
    assert evaluate("legacy") is CriterionDisposition.UNAVAILABLE
    assert evaluate("town", "unknown") is CriterionDisposition.UNAVAILABLE
    objective = ObjectiveDefinition(
        "objective_stage",
        "Established",
        "Become established",
        "Establish a home.",
        (SettlementStageCriterion("settlement"),),
        authorized_action_categories=("work",),
    )
    engine.goals.create(
        GoalDefinition(
            "goal_stage",
            GoalOwnerKind.SETTLEMENT,
            owner,
            "Established",
            "Become established",
            "Establish a home.",
            (objective.id,),
            authorized_action_categories=("work",),
        ),
        (objective,),
    )
    engine.run(2)
    assert engine.state.objective_states[objective.id].status is GoalStatus.ACTIVE
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.SETTLEMENT
    )
    engine.step()
    assert engine.state.objective_states[objective.id].status is GoalStatus.COMPLETED
    assert evaluate("settlement") is CriterionDisposition.SATISFIED


def test_scheduler_stage_is_last_after_later_registration() -> None:
    engine, _, _ = configured()

    class Ordinary:
        def step(self, state: WorldState) -> None:
            pass

    engine.register_system(Ordinary())
    systems = engine._scheduler._systems
    assert [type(system).__name__ for system in systems[-5:]] == [
        "WorkExecutionSystem",
        "ConsequenceSystem",
        "NeedAssessmentSystem",
        "GoalEvaluationSystem",
        "SettlementStageEvaluationSystem",
    ]
    assert isinstance(systems[-6], Ordinary)


@pytest.mark.parametrize("value", [True, "4", 2.0, -1])
def test_invalid_population_fails_loudly(value: object) -> None:
    from living_world.goals import CriterionEvaluatorRegistry

    engine, owner, _ = configured()
    engine.entities.set_attribute(entity_id=owner, key="population", value=value)
    with pytest.raises((TypeError, ValueError)):
        CriterionEvaluatorRegistry().evaluate(
            PopulationMinimumCriterion(1), owner_id=owner, state=engine.state
        )


def test_population_missing_and_below_threshold() -> None:
    from living_world.goals import CriterionDisposition, CriterionEvaluatorRegistry

    engine, owner, _ = configured()
    registry = CriterionEvaluatorRegistry()
    assert (
        registry.evaluate(
            PopulationMinimumCriterion(5), owner_id=owner, state=engine.state
        ).disposition
        is CriterionDisposition.UNSATISFIED
    )
    del engine.state.entities[owner].attributes["population"]
    assert (
        registry.evaluate(
            PopulationMinimumCriterion(1), owner_id=owner, state=engine.state
        ).disposition
        is CriterionDisposition.UNAVAILABLE
    )
    engine.state.entities[owner].destroyed_tick = 0
    with pytest.raises(ValueError):
        registry.evaluate(
            PopulationMinimumCriterion(1), owner_id=owner, state=engine.state
        )


def maintained() -> tuple[SimulationEngine, str, str, MaintenancePolicy]:
    from living_world.needs import MaintenancePolicy, MaintenanceRequirement

    engine, owner, _ = configured()
    engine.definitions.register(Definition("well"))
    capability = engine.entities.create(
        definition_key="well", name="Well", attributes={"is_constructed": True}
    )
    engine.relationships.create(kind="owns", source_id=owner, target_id=capability.id)
    policy = MaintenancePolicy(
        "maintenance_well",
        owner,
        capability.id,
        "Well upkeep",
        (MaintenanceRequirement("wood", 1),),
        10,
        10,
        1,
        1,
    )
    engine.consequences.create_maintenance(policy)
    return engine, owner, capability.id, policy


@pytest.mark.parametrize(
    "case",
    [
        "enough",
        "low",
        "missing_state",
        "missing_policy",
        "unconstructed",
        "destroyed",
        "wrong_definition",
        "wrong_owner",
        "duplicate_policy",
        "state_mismatch",
        "condition_bool",
        "condition_zero",
        "condition_high",
        "future",
        "malformed_policy",
    ],
)
def test_maintenance_evaluator_contract(case: str) -> None:
    from living_world.goals import (
        CriterionDisposition,
        CriterionEvaluatorRegistry,
        MaintainedCapabilityCriterion,
    )

    engine, owner, capability, policy = maintained()
    state = engine.state.maintenance_states[policy.id]
    error = case in {
        "wrong_owner",
        "duplicate_policy",
        "state_mismatch",
        "condition_bool",
        "condition_zero",
        "condition_high",
        "future",
        "malformed_policy",
    }
    if case == "low":
        engine.state.maintenance_states[policy.id] = replace(
            state, condition=1, last_processed_tick=0
        )
    elif case == "missing_state":
        engine.state.maintenance_states.clear()
    elif case == "missing_policy":
        engine.state.maintenance_policies.clear()
    elif case == "unconstructed":
        engine.state.entities[capability].attributes["is_constructed"] = False
    elif case == "destroyed":
        engine.state.entities[capability].destroyed_tick = 0
    elif case == "wrong_definition":
        engine.state.entities[capability].definition_key = "other"
    elif case == "wrong_owner":
        engine.state.maintenance_policies[policy.id] = replace(policy, owner_id="other")
    elif case == "duplicate_policy":
        engine.state.maintenance_policies["maintenance_other"] = replace(
            policy, id="maintenance_other"
        )
    elif case == "state_mismatch":
        engine.state.maintenance_states[policy.id] = replace(
            state, policy_id="maintenance_other"
        )
    elif case in {"condition_bool", "condition_zero", "condition_high"}:
        # Bypass record construction to prove runtime corruption fails loudly.
        altered = replace(state)
        object.__setattr__(
            altered,
            "condition",
            {"condition_bool": True, "condition_zero": 0, "condition_high": 11}[case],
        )
        engine.state.maintenance_states[policy.id] = altered
    elif case == "future":
        engine.state.maintenance_states[policy.id] = replace(
            state, last_processed_tick=1
        )
    elif case == "malformed_policy":
        altered = replace(policy)
        object.__setattr__(altered, "maximum_condition", True)
        engine.state.maintenance_policies[policy.id] = altered
    registry = CriterionEvaluatorRegistry()
    if error:
        with pytest.raises((TypeError, ValueError)):
            registry.evaluate(
                MaintainedCapabilityCriterion("well", 1, 5),
                owner_id=owner,
                state=engine.state,
            )
    else:
        result = registry.evaluate(
            MaintainedCapabilityCriterion("well", 1, 5),
            owner_id=owner,
            state=engine.state,
        )
        assert result.disposition is (
            CriterionDisposition.SATISFIED
            if case == "enough"
            else CriterionDisposition.UNSATISFIED
        )
        assert result.source_event_ids == tuple(sorted(set(result.source_event_ids)))
        assert "minimum condition 5" in result.description


@pytest.mark.parametrize(
    "value", [PopulationMinimumCriterion(0), PopulationMinimumCriterion(True)]
)
def test_goal_manager_validates_new_thresholds(
    value: PopulationMinimumCriterion,
) -> None:
    from living_world.goals import GoalManager

    with pytest.raises((TypeError, ValueError)):
        GoalManager._criterion(value)


@pytest.mark.parametrize(
    "prose",
    [
        "entity_001",
        "goal_private",
        "objective_hidden",
        "need_supply",
        "maintenance_well",
        "work_order",
        "settlement_stage_programs",
        "entered_tick 0",
        "founding_camp",
    ],
)
def test_stage_boundary_rejects_hidden_prose(prose: str) -> None:
    from living_world.cognition.information_boundary import NPCInformationBoundary

    engine, _, _ = configured()
    with pytest.raises(ValueError):
        NPCInformationBoundary(engine.state).validate_conversation_prose(prose)


def test_safe_interpretation_and_no_automatic_injection() -> None:
    from living_world.cognition.information_boundary import NPCInformationBoundary
    from living_world.cognition.npc_context import NPCContextAssembler
    from living_world.stages import NPCSettlementStageInterpretation

    engine, owner, _ = configured()
    engine.definitions.register(Definition("npc"))
    npc = engine.entities.create(definition_key="npc", name="Ada")
    projection = engine.settlement_stages.npc_interpretation(owner)
    boundary = NPCInformationBoundary(engine.state)
    assert (
        boundary.validate_conversation_prose(projection.description)
        == projection.description
    )
    context = NPCContextAssembler(engine.state).assemble(holder_id=npc.id)
    assert projection.description not in repr(context)
    assert owner not in repr(context)
    with pytest.raises(TypeError):
        boundary.validate_conversation_prose(engine.state.settlement_stage_programs)
    with pytest.raises(TypeError):
        boundary.validate_conversation_prose(
            cast(SettlementStageState, engine.settlement_stages.state_for(owner))
        )
    for label in ("", "objective_private", "work_private"):
        with pytest.raises(ValueError):
            NPCSettlementStageInterpretation(label, "Visible prose")
    with pytest.raises(FrozenInstanceError):
        projection.description = "Become a town now"
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.FOUNDING_CAMP
    )


def test_schema_eleven_roundtrip_resume_and_failed_save(tmp_path: Path) -> None:
    import sqlite3

    from living_world.api.inspection import EngineWorldInspector
    from living_world.repositories.sqlite_repository import (
        RepositorySaveError,
        SQLiteRepository,
    )

    engine, owner, program = configured()
    engine.run(2)
    repository = SQLiteRepository(str(tmp_path / "stages.sqlite3"))
    repository.save_world(engine.state)
    with sqlite3.connect(tmp_path / "stages.sqlite3") as connection:
        assert (
            connection.execute("SELECT schema_version FROM world_snapshots").fetchone()[
                0
            ]
            == 12
        )
    resumed = SimulationEngine(repository)
    resumed.definitions.register(Definition("settlement"))
    assert resumed.settlement_stages.get(owner) == program
    assert resumed.settlement_stages.state_for(owner) == cast(
        SettlementStageState, engine.settlement_stages.state_for(owner)
    )
    engine.step()
    resumed.step()
    assert (
        EngineWorldInspector(engine).settlement_stages()
        == EngineWorldInspector(resumed).settlement_stages()
    )
    assert engine.state.tick == resumed.state.tick
    assert tuple(engine.state.events.values()) == tuple(resumed.state.events.values())
    previous = repository.load_world()
    engine.state.settlement_stage_states[owner] = replace(
        cast(SettlementStageState, engine.settlement_stages.state_for(owner)),
        entered_tick=99,
        last_transition_tick=99,
    )
    with pytest.raises(RepositorySaveError):
        repository.save_world(engine.state)
    assert repository.load_world() == previous


@pytest.mark.parametrize("version", range(1, 11))
def test_legacy_schemas_default_empty_and_write_forward(
    tmp_path: Path, version: int
) -> None:
    import sqlite3

    from living_world.repositories.sqlite_repository import SQLiteRepository

    engine, _, _ = configured()
    database = tmp_path / "legacy.sqlite3"
    repository = SQLiteRepository(str(database))
    repository.save_world(engine.state)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE world_snapshots SET schema_version = ?", (version,))
    loaded = repository.load_world()
    assert loaded.settlement_stage_programs == {}
    assert loaded.settlement_stage_states == {}
    repository.save_world(loaded)
    with sqlite3.connect(database) as connection:
        assert (
            connection.execute("SELECT schema_version FROM world_snapshots").fetchone()[
                0
            ]
            == 12
        )


@pytest.mark.parametrize(
    "case",
    [
        "missing_collection",
        "extra_program",
        "missing_program_field",
        "extra_stage",
        "extra_requirement",
        "invalid_kind",
        "wrong_stage_order",
        "duplicate_program",
        "duplicate_requirement",
        "empty_town",
        "missing_state",
        "extra_state",
        "invalid_stage",
        "future_tick",
        "negative_tick",
        "bool_tick",
        "transition_mismatch",
        "owner_mismatch",
        "unknown_objective",
        "destroyed_owner",
        "population_only",
    ],
)
def test_schema_eleven_rejects_malformed_stage_records(
    tmp_path: Path, case: str
) -> None:
    import json
    import sqlite3

    from living_world.repositories.sqlite_repository import (
        RepositoryLoadError,
        SQLiteRepository,
    )

    engine, _, _ = configured()
    database = tmp_path / "malformed.sqlite3"
    repository = SQLiteRepository(str(database))
    repository.save_world(engine.state)
    with sqlite3.connect(database) as connection:
        payload = cast(
            dict[str, object],
            json.loads(
                connection.execute("SELECT payload FROM world_snapshots").fetchone()[0]
            ),
        )
        programs = cast(list[dict[str, object]], payload["settlement_stage_programs"])
        program = programs[0]
        current = cast(list[dict[str, object]], payload["settlement_stage_states"])[0]
        stages = cast(list[dict[str, object]], program["stages"])
        promotion_requirements = cast(
            list[dict[str, object]], stages[1]["requirements"]
        )
        if case == "missing_collection":
            del payload["settlement_stage_programs"]
        elif case == "extra_program":
            program["extra"] = True
        elif case == "missing_program_field":
            del program["settlement_id"]
        elif case == "extra_stage":
            stages[0]["extra"] = True
        elif case == "extra_requirement":
            promotion_requirements[0]["extra"] = True
        elif case == "invalid_kind":
            promotion_requirements[0]["kind"] = "magic"
        elif case == "wrong_stage_order":
            stages.reverse()
        elif case == "duplicate_program":
            programs.append(program)
        elif case == "duplicate_requirement":
            stages[1]["requirements"] = promotion_requirements * 2
        elif case == "empty_town":
            stages[2]["requirements"] = []
        elif case == "missing_state":
            payload["settlement_stage_states"] = []
        elif case == "extra_state":
            current["extra"] = True
        elif case == "invalid_stage":
            current["current_stage"] = "city"
        elif case in {"future_tick", "negative_tick", "bool_tick"}:
            current["entered_tick"] = {
                "future_tick": 99,
                "negative_tick": -1,
                "bool_tick": True,
            }[case]
        elif case == "transition_mismatch":
            current["last_transition_tick"] = 1
        elif case == "owner_mismatch":
            current["settlement_id"] = "other"
        elif case == "unknown_objective":
            promotion_requirements[0]["objective_id"] = "objective_unknown"
        elif case == "destroyed_owner":
            cast(list[dict[str, object]], payload["entities"])[0]["destroyed_tick"] = 0
        elif case == "population_only":
            promotion_requirements[0]["kind"] = "population"
        connection.execute(
            "UPDATE world_snapshots SET payload = ?", (json.dumps(payload),)
        )
    with pytest.raises(RepositoryLoadError):
        repository.load_world()


def test_new_goal_criteria_strict_roundtrip(tmp_path: Path) -> None:
    import json
    import sqlite3

    from living_world.goals import MaintainedCapabilityCriterion
    from living_world.repositories.sqlite_repository import (
        RepositoryLoadError,
        SQLiteRepository,
    )

    engine, _, _ = configured()
    objective = engine.state.objective_definitions["objective_housing"]
    engine.state.objective_definitions[objective.id] = replace(
        objective,
        completion_criteria=objective.completion_criteria
        + (PopulationMinimumCriterion(1), MaintainedCapabilityCriterion("well", 1, 3)),
    )
    database = tmp_path / "criteria.sqlite3"
    repository = SQLiteRepository(str(database))
    repository.save_world(engine.state)
    assert (
        repository.load_world().objective_definitions
        == engine.state.objective_definitions
    )
    with sqlite3.connect(database) as connection:
        payload = cast(
            dict[str, object],
            json.loads(
                connection.execute("SELECT payload FROM world_snapshots").fetchone()[0]
            ),
        )
        objectives = cast(list[dict[str, object]], payload["objective_definitions"])
        criteria = cast(list[dict[str, object]], objectives[0]["completion_criteria"])
        criteria[1]["extra"] = 1
        connection.execute(
            "UPDATE world_snapshots SET payload = ?", (json.dumps(payload),)
        )
    with pytest.raises(RepositoryLoadError):
        repository.load_world()


def test_privileged_inspection_detachment_and_get_only_api() -> None:
    from test_inspection_api import ASGIClient

    from living_world.api.inspection import EngineWorldInspector
    from living_world.api.server import create_app

    empty = EngineWorldInspector(SimulationEngine())
    assert empty.settlement_stages() == ()
    assert empty.world_summary()["settlement_stage_program_count"] == 0
    engine, owner, program = configured()
    inspector = EngineWorldInspector(engine)
    snapshot = inspector.settlement_stages()
    snapshot_program = cast(dict[str, object], snapshot[0]["program"])
    assert snapshot_program["settlement_id"] == owner
    snapshot_stages = cast(list[dict[str, object]], snapshot_program["stages"])
    snapshot_requirements = cast(
        list[dict[str, object]], snapshot_stages[1]["requirements"]
    )
    snapshot_requirements[0]["objective_id"] = "changed"
    assert engine.settlement_stages.get(owner) == program
    assert inspector.world_summary()["settlement_stage_program_count"] == 1
    client = ASGIClient(create_app(engine))
    assert client.get("/world/settlement-stages").json() == list(
        inspector.settlement_stages()
    )
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        assert client.request(method, "/world/settlement-stages").status_code == 405


@pytest.mark.parametrize(
    "factory",
    [
        lambda: StageObjectiveRequirement(
            cast(StageRequirementKind, "water"), "objective_x"
        ),
        lambda: SettlementStageDefinition(cast(SettlementStage, "town"), ()),
        lambda: SettlementStageProgram("", ()),
        lambda: SettlementStageProgram(
            "owner", cast(tuple[SettlementStageDefinition, ...], [])
        ),
        lambda: StageObjectiveRequirement(StageRequirementKind.WATER, ""),
    ],
)
def test_strict_stage_record_types(factory: Callable[[], object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_sustained_water_only_promotes_after_complete_history() -> None:
    from living_world.goals import SustainedNeedCriterion
    from living_world.needs import NeedDefinition, NeedKind

    engine, owner, program = bare(
        SustainedNeedCriterion("water", 0.2, 3), StageRequirementKind.WATER
    )
    engine.needs.create(
        NeedDefinition("need_water", owner, NeedKind.WATER, 1, 0.2, 0.5, 3)
    )
    engine.entities.set_attribute(entity_id=owner, key="resources", value={"water": 4})
    engine.settlement_stages.configure(program)
    engine.run(2)
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.FOUNDING_CAMP
    )
    engine.step()
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.SETTLEMENT
    )


def test_canonical_requirements_and_exact_immutable_sources(tmp_path: Path) -> None:
    from living_world.goals import ProgressEvidence
    from living_world.repositories.sqlite_repository import SQLiteRepository

    engine, owner, program = bare()
    objective = ObjectiveDefinition(
        "objective_population",
        "Population",
        "Support inhabitants",
        "Support the community.",
        (PopulationMinimumCriterion(4),),
        authorized_action_categories=("work",),
    )
    engine.goals.create(
        GoalDefinition(
            "goal_population",
            GoalOwnerKind.SETTLEMENT,
            owner,
            "Population",
            "Support inhabitants",
            "Support the community.",
            (objective.id,),
            authorized_action_categories=("work",),
        ),
        (objective,),
    )
    population = StageObjectiveRequirement(
        StageRequirementKind.POPULATION, objective.id
    )
    program = replace(
        program,
        stages=tuple(
            (
                replace(
                    definition, requirements=(population,) + definition.requirements
                )
                if definition.requirements
                else definition
            )
            for definition in program.stages
        ),
    )
    normalized = engine.settlement_stages.configure(program)
    assert normalized.stages[1].requirements[0].kind is StageRequirementKind.CAPABILITY
    source_b = engine.events.record(kind="domain_effect", subject_id=owner)
    source_a = engine.events.record(kind="domain_effect", subject_id=owner)
    for objective_id in ("objective_housing", objective.id):
        engine.goals.transition_objective(objective_id, GoalStatus.ACTIVE)
        engine.goals.transition_objective(
            objective_id,
            GoalStatus.COMPLETED,
            ProgressEvidence(0, "Completed", (source_a.id, source_b.id)),
        )
    irrelevant = engine.events.record(kind="arbitrary_note", subject_id=objective.id)
    expected = engine.settlement_stages.requirement_evidence(owner)
    assert irrelevant.id not in expected[1].source_event_ids
    SettlementStageEvaluationSystem(engine.settlement_stages).step(engine.state)
    event = next(
        e
        for e in engine.state.events.values()
        if e.kind == "settlement_stage_transitioned"
    )
    event_requirements = cast(
        tuple[Mapping[str, object], ...], event.attributes["requirements"]
    )
    assert tuple(item["kind"] for item in event_requirements) == (
        "capability",
        "population",
    )
    assert event_requirements[1]["source_event_ids"] == expected[1].source_event_ids
    with pytest.raises(TypeError):
        cast(dict[str, object], event_requirements[0])["kind"] = "water"
    repository = SQLiteRepository(str(tmp_path / "ordering.sqlite3"))
    repository.save_world(engine.state)
    assert repository.load_world().settlement_stage_programs[owner] == normalized


def test_high_population_and_prose_do_not_promote_without_objectives() -> None:
    engine, owner, _ = configured()
    engine.entities.set_attribute(entity_id=owner, key="population", value=9999)
    engine.entities.set_attribute(entity_id=owner, key="stage", value="town")
    engine.entities.set_attribute(
        entity_id=owner, key="llm_assertion", value="This settlement is a town now."
    )
    SettlementStageEvaluationSystem(engine.settlement_stages).step(engine.state)
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.FOUNDING_CAMP
    )


@pytest.mark.parametrize(
    "case", ["negative", "bool", "minimum_zero", "minimum_bool", "empty_capability"]
)
def test_maintained_criterion_manager_validation(case: str) -> None:
    from living_world.goals import GoalManager, MaintainedCapabilityCriterion

    criterion = MaintainedCapabilityCriterion(
        "" if case == "empty_capability" else "well",
        -1 if case == "negative" else True if case == "bool" else 1,
        0 if case == "minimum_zero" else True if case == "minimum_bool" else 1,
    )
    with pytest.raises((TypeError, ValueError)):
        GoalManager._criterion(criterion)


def test_stage_ticks_reject_negative_noninteger_and_mismatched_values() -> None:
    from living_world.stages import SettlementStageState

    for tick in (-1, True, "0"):
        with pytest.raises((TypeError, ValueError)):
            SettlementStageState(
                "owner", SettlementStage.FOUNDING_CAMP, cast(int, tick)
            )
    with pytest.raises(ValueError):
        SettlementStageState("owner", SettlementStage.SETTLEMENT, 2, 1)


def test_nonrecord_configuration_and_corrupt_evidence_are_rejected() -> None:
    from living_world.goals import ProgressEvidence

    engine, owner, _ = configured()
    with pytest.raises(TypeError):
        engine.settlement_stages.configure(cast(SettlementStageProgram, {}))
    engine.goals.transition_objective("objective_housing", GoalStatus.ACTIVE)
    engine.goals.transition_objective("objective_housing", GoalStatus.COMPLETED)
    current = engine.state.objective_states["objective_housing"]
    engine.state.objective_states[current.id] = replace(
        current, evidence=(ProgressEvidence(0, "Corrupt evidence", ("event_missing",)),)
    )
    before = dict(engine.state.events)
    with pytest.raises(ValueError):
        SettlementStageEvaluationSystem(engine.settlement_stages).step(engine.state)
    assert engine.state.events == before
    assert (
        cast(
            SettlementStageState, engine.settlement_stages.state_for(owner)
        ).current_stage
        is SettlementStage.FOUNDING_CAMP
    )


def test_stage_boundary_rejects_ticks_and_referenced_thresholds() -> None:
    from living_world.cognition.information_boundary import NPCInformationBoundary

    engine, _, program = bare()
    engine.state.tick = 17
    engine.settlement_stages.configure(program)
    boundary = NPCInformationBoundary(engine.state)
    for text in ("It takes 17 steps.", "Capacity is 1."):
        with pytest.raises(ValueError):
            boundary.validate_conversation_prose(text)
