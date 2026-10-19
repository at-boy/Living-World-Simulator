from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from living_world.goals.model import (
    CapacityCriterion,
    ConstructedCapabilityCriterion,
    ExternalConnectionCriterion,
    GoalOwnerKind,
    GoalStatus,
    MaintainedCapabilityCriterion,
    PopulationMinimumCriterion,
    ProgressEvidence,
    SustainedNeedCriterion,
)
from living_world.needs.model import NeedKind
from living_world.stages.model import (
    NPCSettlementStageInterpretation,
    SettlementStage,
    SettlementStageProgram,
    SettlementStageState,
    StageRequirementEvidence,
    StageRequirementKind,
)

if TYPE_CHECKING:
    from living_world.managers.event_manager import EventManager
    from living_world.state.world_state import WorldState


class SettlementStageManager:
    """Exclusive mutation boundary for explicitly configured settlement stages."""

    def __init__(self, state: WorldState, events: EventManager) -> None:
        self._state = state
        self._events = events

    def get(self, settlement_id: str) -> SettlementStageProgram | None:
        return self._state.settlement_stage_programs.get(settlement_id)

    def state_for(self, settlement_id: str) -> SettlementStageState | None:
        return self._state.settlement_stage_states.get(settlement_id)

    def all(self) -> tuple[SettlementStageProgram, ...]:
        return tuple(
            self._state.settlement_stage_programs[key]
            for key in sorted(self._state.settlement_stage_programs)
        )

    def _validate_program(self, program: SettlementStageProgram) -> None:
        if not isinstance(program, SettlementStageProgram):
            raise TypeError("program must be a SettlementStageProgram.")
        program.__post_init__()
        for definition in program.stages:
            definition.__post_init__()
            for requirement in definition.requirements:
                requirement.__post_init__()
        owner = self._state.entities.get(program.settlement_id)
        if owner is None or owner.destroyed_tick is not None:
            raise ValueError("Stage owner must be a live settlement entity.")
        if tuple(item.stage for item in program.stages) != tuple(SettlementStage):
            raise ValueError("Programs require exactly the canonical stages in order.")
        for definition in program.stages:
            if definition.stage is SettlementStage.FOUNDING_CAMP:
                if definition.requirements:
                    raise ValueError("Founding camp must have no requirements.")
                continue
            if not definition.requirements:
                raise ValueError("Promotion stages must have requirements.")
            if all(
                item.kind is StageRequirementKind.POPULATION
                for item in definition.requirements
            ):
                raise ValueError("Population alone cannot promote a settlement.")
            ids = [item.objective_id for item in definition.requirements]
            if len(ids) != len(set(ids)):
                raise ValueError("Objective references within a stage must be unique.")
            for requirement in definition.requirements:
                owners = [
                    goal
                    for goal in self._state.goal_definitions.values()
                    if requirement.objective_id in goal.objective_ids
                ]
                if (
                    len(owners) != 1
                    or owners[0].owner_kind is not GoalOwnerKind.SETTLEMENT
                    or owners[0].owner_id != program.settlement_id
                ):
                    raise ValueError(
                        "Stage objective must belong to exactly one settlement goal for its owner."
                    )
                objective = self._state.objective_definitions.get(
                    requirement.objective_id
                )
                if (
                    objective is None
                    or requirement.objective_id not in self._state.objective_states
                ):
                    raise ValueError("Stage objective definition and state must exist.")
                if (
                    objective.id != requirement.objective_id
                    or self._state.objective_states[
                        requirement.objective_id
                    ].objective_id
                    != requirement.objective_id
                ):
                    raise ValueError("Objective keys must match their identifiers.")
                criteria = objective.completion_criteria
                kind = requirement.kind
                if kind in {
                    StageRequirementKind.WATER,
                    StageRequirementKind.FOOD,
                    StageRequirementKind.SHELTER,
                    StageRequirementKind.STORAGE,
                }:
                    matches = [
                        item
                        for item in criteria
                        if isinstance(item, SustainedNeedCriterion)
                        and item.need == kind.value
                    ]
                    needs = [
                        item
                        for item in self._state.need_definitions.values()
                        if item.owner_id == program.settlement_id
                        and item.kind is NeedKind(kind.value)
                    ]
                    if (
                        not matches
                        or len(needs) != 1
                        or any(
                            item.duration_ticks > needs[0].assessment_window_ticks
                            for item in matches
                        )
                    ):
                        raise ValueError(
                            "Sustained stage requirement needs a unique matching need and sufficient window."
                        )
                else:
                    types = {
                        StageRequirementKind.MAINTENANCE: (
                            MaintainedCapabilityCriterion,
                        ),
                        StageRequirementKind.EXTERNAL_CONNECTION: (
                            ExternalConnectionCriterion,
                        ),
                        StageRequirementKind.POPULATION: (PopulationMinimumCriterion,),
                        StageRequirementKind.CAPABILITY: (
                            ConstructedCapabilityCriterion,
                            CapacityCriterion,
                        ),
                    }[kind]
                    if not any(isinstance(item, types) for item in criteria):
                        raise ValueError(
                            "Stage requirement kind does not match objective criteria."
                        )

    def configure(self, program: SettlementStageProgram) -> SettlementStageProgram:
        self._validate_program(program)
        program = replace(
            program,
            stages=tuple(
                replace(
                    definition,
                    requirements=tuple(
                        sorted(
                            definition.requirements,
                            key=lambda item: (item.kind.value, item.objective_id),
                        )
                    ),
                )
                for definition in program.stages
            ),
        )
        key = program.settlement_id
        if (
            key in self._state.settlement_stage_programs
            or key in self._state.settlement_stage_states
        ):
            raise ValueError("Settlement already has a stage program or state.")
        event_ids = frozenset(self._state.events)
        try:
            self._state.settlement_stage_programs[key] = program
            self._state.settlement_stage_states[key] = SettlementStageState(
                key, SettlementStage.FOUNDING_CAMP, self._state.tick
            )
            self._events.record(
                kind="settlement_stage_program_configured",
                subject_id=key,
                attributes={},
            )
        except Exception:
            self._state.settlement_stage_programs.pop(key, None)
            self._state.settlement_stage_states.pop(key, None)
            self._remove_events(event_ids)
            raise
        return program

    def requirement_evidence(
        self, settlement_id: str
    ) -> tuple[StageRequirementEvidence, ...]:
        """Normalize authoritative objective evidence for the next adjacent stage."""
        program = self._state.settlement_stage_programs[settlement_id]
        current = self._state.settlement_stage_states[settlement_id]
        index = tuple(SettlementStage).index(current.current_stage) + 1
        if index == len(program.stages):
            return ()
        for requirement in program.stages[index].requirements:
            for evidence in self._state.objective_states[
                requirement.objective_id
            ].evidence:
                if not isinstance(evidence, ProgressEvidence):
                    raise TypeError("Objective evidence must be typed records.")
                if (
                    not isinstance(evidence.tick, int)
                    or isinstance(evidence.tick, bool)
                    or not 0 <= evidence.tick <= self._state.tick
                ):
                    raise ValueError(
                        "Objective evidence ticks must be current or historical."
                    )
                if not isinstance(evidence.source_event_ids, tuple):
                    raise TypeError("Objective evidence sources must be a tuple.")
                StageRequirementEvidence(
                    requirement.kind,
                    requirement.objective_id,
                    tuple(sorted(evidence.source_event_ids)),
                )
                if any(
                    source not in self._state.events
                    for source in evidence.source_event_ids
                ):
                    raise ValueError(
                        "Objective evidence must reference existing events."
                    )
        return tuple(
            StageRequirementEvidence(
                item.kind,
                item.objective_id,
                tuple(
                    sorted(
                        {
                            source
                            for evidence in self._state.objective_states[
                                item.objective_id
                            ].evidence
                            for source in evidence.source_event_ids
                        }
                        | {
                            event.id
                            for event in self._state.events.values()
                            if event.subject_id == item.objective_id
                            and event.kind
                            in {
                                "objective_active",
                                "objective_blocked",
                                "objective_completed",
                                "objective_failed",
                            }
                        }
                    )
                ),
            )
            for item in sorted(
                program.stages[index].requirements,
                key=lambda item: (item.kind.value, item.objective_id),
            )
        )

    def transition_to_next(
        self, settlement_id: str, evidence: tuple[StageRequirementEvidence, ...]
    ) -> SettlementStageState:
        self.validate_loaded_state()
        current = self.state_for(settlement_id)
        if current is None:
            raise ValueError("Settlement has no stage program.")
        if (
            current.current_stage is SettlementStage.TOWN
            or current.last_transition_tick == self._state.tick
        ):
            raise ValueError("No adjacent transition is available this tick.")
        expected = self.requirement_evidence(settlement_id)
        if not isinstance(evidence, tuple) or any(
            not isinstance(item, StageRequirementEvidence) for item in evidence
        ):
            raise TypeError("evidence must contain stage evidence records.")
        if evidence != expected:
            raise ValueError(
                "Transition evidence must exactly match authoritative objective evidence."
            )
        if any(
            self._state.objective_states[item.objective_id].status
            is not GoalStatus.COMPLETED
            for item in evidence
        ):
            raise ValueError("All promotion objectives must be completed.")
        updated = SettlementStageState(
            settlement_id,
            tuple(SettlementStage)[
                tuple(SettlementStage).index(current.current_stage) + 1
            ],
            self._state.tick,
            self._state.tick,
        )
        event_ids = frozenset(self._state.events)
        try:
            self._state.settlement_stage_states[settlement_id] = updated
            self._events.record(
                kind="settlement_stage_transitioned",
                subject_id=settlement_id,
                attributes={
                    "previous_stage": current.current_stage.value,
                    "current_stage": updated.current_stage.value,
                    "requirements": tuple(
                        {
                            "kind": item.kind.value,
                            "objective_id": item.objective_id,
                            "source_event_ids": item.source_event_ids,
                        }
                        for item in evidence
                    ),
                },
            )
        except Exception:
            self._state.settlement_stage_states[settlement_id] = current
            self._remove_events(event_ids)
            raise
        return updated

    def _remove_events(self, original: frozenset[str]) -> None:
        for event_id in set(self._state.events) - original:
            self._state.events.pop(event_id, None)

    def npc_interpretation(
        self, settlement_id: str
    ) -> NPCSettlementStageInterpretation:
        current = self.state_for(settlement_id)
        if current is None:
            raise ValueError("Settlement has no stage program.")
        prose = {
            SettlementStage.FOUNDING_CAMP: (
                "New community",
                "A newly established community is finding its footing.",
            ),
            SettlementStage.SETTLEMENT: (
                "Established settlement",
                "An established settlement offers a lasting home.",
            ),
            SettlementStage.TOWN: (
                "Developed town",
                "A developed town supports a thriving community.",
            ),
        }
        return NPCSettlementStageInterpretation(*prose[current.current_stage])

    def validate_loaded_state(self) -> None:
        if set(self._state.settlement_stage_programs) != set(
            self._state.settlement_stage_states
        ):
            raise ValueError("Stage programs and states must correspond.")
        for key, program in self._state.settlement_stage_programs.items():
            self._validate_program(program)
            current = self._state.settlement_stage_states[key]
            if not isinstance(current, SettlementStageState):
                raise TypeError("Stage state must be a SettlementStageState.")
            current.__post_init__()
            if program.settlement_id != key or current.settlement_id != key:
                raise ValueError("Stage keys must match owner IDs.")
            if current.entered_tick > self._state.tick or (
                current.last_transition_tick is not None
                and current.last_transition_tick > self._state.tick
            ):
                raise ValueError("Stage ticks cannot be in the future.")
            if (current.current_stage is SettlementStage.FOUNDING_CAMP) != (
                current.last_transition_tick is None
            ):
                raise ValueError("Initial and promoted stage ticks are inconsistent.")

    def validate_entity_removal(self, entity_id: str) -> None:
        if (
            entity_id in self._state.settlement_stage_programs
            or entity_id in self._state.settlement_stage_states
        ):
            raise ValueError("Entity owns a settlement stage program or state.")

    def validate_entity_destruction(self, entity_id: str) -> None:
        self.validate_entity_removal(entity_id)
