from __future__ import annotations

from dataclasses import replace
from math import isfinite
from typing import TYPE_CHECKING

from living_world.goals.model import (
    CapacityCriterion,
    ConstructedCapabilityCriterion,
    ExternalConnectionCriterion,
    GoalDefinition,
    GoalOwnerKind,
    GoalState,
    GoalStatus,
    NPCGoalInterpretation,
    ObjectiveDefinition,
    ObjectiveState,
    ProgressEvidence,
    ResourceMinimumCriterion,
    SettlementStageCriterion,
    SustainedNeedCriterion,
    _visible_text,
)

if TYPE_CHECKING:
    from living_world.managers.event_manager import EventManager
    from living_world.state.world_state import WorldState

_TERMINAL = frozenset({GoalStatus.COMPLETED, GoalStatus.FAILED})
_TRANSITIONS = {
    GoalStatus.INACTIVE: frozenset({GoalStatus.ACTIVE, GoalStatus.FAILED}),
    GoalStatus.ACTIVE: frozenset(
        {GoalStatus.BLOCKED, GoalStatus.COMPLETED, GoalStatus.FAILED}
    ),
    GoalStatus.BLOCKED: frozenset({GoalStatus.ACTIVE, GoalStatus.FAILED}),
}


class GoalManager:
    """Exclusive mutation boundary for durable goal and objective records."""

    def __init__(self, state: WorldState, events: EventManager) -> None:
        self._state = state
        self._events = events

    def create(
        self, goal: GoalDefinition, objectives: tuple[ObjectiveDefinition, ...]
    ) -> GoalDefinition:
        if not isinstance(goal, GoalDefinition):
            raise TypeError("goal must be a GoalDefinition.")
        self._tuple(objectives, "objectives")
        if any(not isinstance(item, ObjectiveDefinition) for item in objectives):
            raise TypeError("objectives must contain ObjectiveDefinition records.")
        self._validate_new(goal, objectives)
        event_ids = frozenset(self._state.events)
        try:
            self._state.goal_definitions[goal.id] = goal
            self._state.goal_states[goal.id] = GoalState(goal.id)
            for objective in objectives:
                self._state.objective_definitions[objective.id] = objective
                self._state.objective_states[objective.id] = ObjectiveState(
                    objective.id
                )
            self._events.record(
                kind="goal_created",
                subject_id=goal.id,
                attributes={"owner_kind": goal.owner_kind.value},
            )
        except Exception:
            self._state.goal_definitions.pop(goal.id, None)
            self._state.goal_states.pop(goal.id, None)
            for objective in objectives:
                self._state.objective_definitions.pop(objective.id, None)
                self._state.objective_states.pop(objective.id, None)
            for event_id in set(self._state.events) - event_ids:
                self._state.events.pop(event_id, None)
            raise
        return goal

    def transition_goal(
        self, goal_id: str, status: GoalStatus, evidence: ProgressEvidence | None = None
    ) -> GoalState:
        return self._transition(goal_id, status, evidence, objective=False)

    def transition_objective(
        self,
        objective_id: str,
        status: GoalStatus,
        evidence: ProgressEvidence | None = None,
    ) -> ObjectiveState:
        return self._transition(objective_id, status, evidence, objective=True)

    def all(self) -> tuple[GoalDefinition, ...]:
        return tuple(
            self._state.goal_definitions[key]
            for key in sorted(self._state.goal_definitions)
        )

    def npc_interpretation(self, goal_id: str) -> NPCGoalInterpretation:
        goal = self._state.goal_definitions.get(goal_id)
        if goal is None:
            raise ValueError(f"Unknown goal '{goal_id}'.")
        return NPCGoalInterpretation(goal.label, goal.npc_interpretation)

    def npc_interpretations(self) -> tuple[NPCGoalInterpretation, ...]:
        return tuple(self.npc_interpretation(goal.id) for goal in self.all())

    def validate_loaded_state(self) -> None:
        goal_ids = set(self._state.goal_definitions)
        if goal_ids != set(self._state.goal_states):
            raise ValueError("Persisted goals and goal states must correspond.")
        objective_ids = set(self._state.objective_definitions)
        if objective_ids != set(self._state.objective_states):
            raise ValueError(
                "Persisted objectives and objective states must correspond."
            )
        owned: set[str] = set()
        labels: set[tuple[str, str]] = set()
        for goal in self._state.goal_definitions.values():
            if not isinstance(goal, GoalDefinition):
                raise TypeError(
                    "Persisted goal definitions must be GoalDefinition records."
                )
            label_key = (goal.owner_id, goal.label.strip().casefold())
            if label_key in labels:
                raise ValueError("Goal labels must be unique per owner.")
            labels.add(label_key)
            objectives = tuple(
                self._state.objective_definitions[item]
                for item in goal.objective_ids
                if item in self._state.objective_definitions
            )
            if len(objectives) != len(goal.objective_ids) or owned.intersection(
                goal.objective_ids
            ):
                raise ValueError("Persisted goal objective ownership is invalid.")
            owned.update(goal.objective_ids)
            self._validate_goal(
                goal, objectives, check_existing=False, require_future_deadline=False
            )
            self._validate_state(self._state.goal_states[goal.id], objective=False)
            for objective in objectives:
                if not isinstance(objective, ObjectiveDefinition):
                    raise TypeError(
                        "Persisted objective definitions must be ObjectiveDefinition records."
                    )
                self._validate_state(
                    self._state.objective_states[objective.id], objective=True
                )
        if owned != objective_ids:
            raise ValueError("Every persisted objective must belong to one goal.")

    def _transition(
        self,
        record_id: str,
        status: GoalStatus,
        evidence: ProgressEvidence | None,
        *,
        objective: bool,
    ) -> GoalState | ObjectiveState:
        self._text(record_id, "record id")
        if not isinstance(status, GoalStatus):
            raise TypeError("status must be a GoalStatus.")
        if evidence is not None and not isinstance(evidence, ProgressEvidence):
            raise TypeError("evidence must be ProgressEvidence or None.")
        states = self._state.objective_states if objective else self._state.goal_states
        current = states.get(record_id)
        if current is None:
            raise ValueError(
                f"Unknown {'objective' if objective else 'goal'} '{record_id}'."
            )
        if current.status in _TERMINAL or status not in _TRANSITIONS.get(
            current.status, frozenset()
        ):
            raise ValueError(
                f"Invalid lifecycle transition {current.status.value} -> {status.value}."
            )
        if evidence is not None:
            self._validate_evidence_records((evidence,))
        updated = replace(
            current,
            status=status,
            evidence=current.evidence + (() if evidence is None else (evidence,)),
        )
        event_ids = frozenset(self._state.events)
        try:
            states[record_id] = updated
            self._events.record(
                kind=f"{'objective' if objective else 'goal'}_{status.value}",
                subject_id=record_id,
                attributes={"previous": current.status.value},
            )
        except Exception:
            states[record_id] = current
            for event_id in set(self._state.events) - event_ids:
                self._state.events.pop(event_id, None)
            raise
        return updated

    def _validate_new(
        self, goal: GoalDefinition, objectives: tuple[ObjectiveDefinition, ...]
    ) -> None:
        if goal.id in self._state.goal_definitions or any(
            item.id in self._state.objective_definitions for item in objectives
        ):
            raise ValueError("Goal and objective identifiers must be unique.")
        self._validate_goal(
            goal, objectives, check_existing=True, require_future_deadline=True
        )

    def _validate_goal(
        self,
        goal: GoalDefinition,
        objectives: tuple[ObjectiveDefinition, ...],
        *,
        check_existing: bool,
        require_future_deadline: bool,
    ) -> None:
        if not isinstance(goal.owner_kind, GoalOwnerKind):
            raise TypeError("owner_kind must be a GoalOwnerKind.")
        self._text(goal.owner_id, "goal owner_id")
        owner = self._state.entities.get(goal.owner_id)
        if owner is None or owner.destroyed_tick is not None:
            raise ValueError("Goal owner must be a live entity.")
        self._text(goal.id, "goal id")
        self._visible_text(goal.label, "goal label")
        self._text(goal.purpose, "goal purpose")
        self._visible_text(goal.npc_interpretation, "NPC interpretation")
        self._strings_tuple(goal.objective_ids, "goal objective_ids")
        if len(set(goal.objective_ids)) != len(goal.objective_ids):
            raise ValueError("Goal objective identifiers must be unique.")
        self._deadline(goal.deadline_tick, require_future=require_future_deadline)
        self._priority(goal.priority, "Goal")
        self._actions(goal.authorized_action_categories)
        self._tuple(goal.completion_criteria, "goal completion_criteria")
        self._tuple(goal.failure_criteria, "goal failure_criteria")
        for criterion in goal.completion_criteria + goal.failure_criteria:
            self._criterion(criterion)
        if check_existing and any(
            item.owner_id == goal.owner_id
            and item.label.strip().casefold() == goal.label.strip().casefold()
            for item in self._state.goal_definitions.values()
        ):
            raise ValueError("Goal labels must be unique per owner.")
        for item in objectives:
            self._text(item.id, "objective id")
        by_id = {item.id: item for item in objectives}
        if (
            len(by_id) != len(objectives)
            or set(goal.objective_ids) != set(by_id)
            or not objectives
        ):
            raise ValueError(
                "Goal must reference each supplied objective exactly once."
            )
        labels: set[str] = set()
        for item in objectives:
            self._visible_text(item.label, "objective label")
            self._text(item.purpose, "objective purpose")
            self._visible_text(item.npc_interpretation, "NPC interpretation")
            self._tuple(item.completion_criteria, "objective completion_criteria")
            self._tuple(item.failure_criteria, "objective failure_criteria")
            self._strings_tuple(item.dependencies, "objective dependencies")
            self._strings_tuple(item.alternatives, "objective alternatives")
            if len(set(item.dependencies)) != len(item.dependencies):
                raise ValueError("Objective dependencies must be unique.")
            if len(set(item.alternatives)) != len(item.alternatives):
                raise ValueError("Objective alternatives must be unique.")
            normalized = item.label.strip().casefold()
            if normalized in labels:
                raise ValueError("Objective labels must be unique within a goal.")
            labels.add(normalized)
            self._deadline(item.deadline_tick, require_future=require_future_deadline)
            self._priority(item.priority, "Objective")
            self._actions(item.authorized_action_categories)
            if not item.completion_criteria:
                raise ValueError("Objectives need completion criteria.")
            if set(item.dependencies) & set(item.alternatives):
                raise ValueError(
                    "A reference cannot be both dependency and alternative."
                )
            if item.id in item.dependencies or item.id in item.alternatives:
                raise ValueError("Objectives cannot reference themselves.")
            if not set(item.dependencies + item.alternatives) <= set(by_id):
                raise ValueError("Objective references must remain within the goal.")
            for criterion in item.completion_criteria + item.failure_criteria:
                self._criterion(criterion)
        self._acyclic(by_id)

    @staticmethod
    def _acyclic(by_id: dict[str, ObjectiveDefinition]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> None:
            if key in visiting:
                raise ValueError("Objective graph must be acyclic.")
            if key in visited:
                return
            visiting.add(key)
            for child in by_id[key].dependencies + by_id[key].alternatives:
                visit(child)
            visiting.remove(key)
            visited.add(key)

        for key in by_id:
            visit(key)

    @staticmethod
    def _text(value: str, label: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{label} must be a string.")
        if not value.strip():
            raise ValueError(f"{label} cannot be empty.")

    @staticmethod
    def _visible_text(value: str, label: str) -> None:
        _visible_text(value, label)

    def _deadline(self, value: int | None, *, require_future: bool) -> None:
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool)
        ):
            raise TypeError("Deadline must be an integer or None.")
        if value is not None and value < 0:
            raise ValueError("Deadline cannot be negative.")
        if require_future and value is not None and value <= self._state.tick:
            raise ValueError("Deadline must be later than the current tick.")

    @staticmethod
    def _actions(values: tuple[str, ...]) -> None:
        GoalManager._tuple(values, "authorized action categories")
        if any(not isinstance(value, str) for value in values):
            raise TypeError("Authorized action categories must contain strings.")
        if (
            not values
            or any(not value.strip() for value in values)
            or len({value.strip().casefold() for value in values}) != len(values)
        ):
            raise ValueError(
                "Authorized action categories must be non-empty and unique."
            )

    @staticmethod
    def _criterion(value: object) -> None:
        if isinstance(
            value,
            (
                ResourceMinimumCriterion,
                ConstructedCapabilityCriterion,
                CapacityCriterion,
            ),
        ):
            threshold = (
                value.count
                if isinstance(value, ConstructedCapabilityCriterion)
                else value.minimum
            )
            if not isinstance(threshold, int) or isinstance(threshold, bool):
                raise TypeError("Criterion thresholds must be integers.")
            if threshold <= 0:
                raise ValueError("Criterion thresholds must be positive.")
            text_value = (
                value.capability
                if isinstance(value, ConstructedCapabilityCriterion)
                else (
                    value.capacity
                    if isinstance(value, CapacityCriterion)
                    else value.resource
                )
            )
            GoalManager._text(text_value, "Criterion name")
        elif isinstance(value, SustainedNeedCriterion):
            GoalManager._text(value.need, "Sustained need")
            if not isinstance(value.duration_ticks, int) or isinstance(
                value.duration_ticks, bool
            ):
                raise TypeError("Sustained need duration must be an integer.")
            if not isinstance(value.maximum, int | float) or isinstance(
                value.maximum, bool
            ):
                raise TypeError("Sustained need maximum must be numeric.")
            if not isfinite(value.maximum) or value.maximum < 0:
                raise ValueError(
                    "Sustained need maximum must be finite and non-negative."
                )
            if value.duration_ticks <= 0:
                raise ValueError("Sustained need duration must be positive.")
        elif isinstance(value, ExternalConnectionCriterion):
            GoalManager._text(value.role, "External connection role")
            GoalManager._text(value.state, "External connection state")
        elif isinstance(value, SettlementStageCriterion):
            GoalManager._text(value.stage, "Settlement stage")
        else:
            raise TypeError("Unsupported goal criterion.")

    @staticmethod
    def _validate_evidence(value: ProgressEvidence) -> None:
        if not isinstance(value.tick, int) or isinstance(value.tick, bool):
            raise TypeError("Progress evidence tick must be an integer.")
        GoalManager._text(value.description, "Progress evidence description")
        GoalManager._tuple(value.source_event_ids, "progress evidence source_event_ids")
        if any(not isinstance(item, str) for item in value.source_event_ids):
            raise TypeError("Progress evidence source_event_ids must contain strings.")
        if any(not item.strip() for item in value.source_event_ids):
            raise ValueError("Progress evidence source event IDs cannot be empty.")
        if len(set(value.source_event_ids)) != len(value.source_event_ids):
            raise ValueError("Progress evidence source event IDs must be unique.")
        if value.tick < 0:
            raise ValueError(
                "Progress evidence must have a valid tick and description."
            )

    def _validate_evidence_records(self, values: tuple[ProgressEvidence, ...]) -> None:
        self._tuple(values, "progress evidence")
        for value in values:
            if not isinstance(value, ProgressEvidence):
                raise TypeError(
                    "Progress evidence must contain ProgressEvidence records."
                )
            self._validate_evidence(value)
            if value.tick > self._state.tick:
                raise ValueError("Progress evidence cannot come from a future tick.")
            if any(
                event_id not in self._state.events
                for event_id in value.source_event_ids
            ):
                raise ValueError("Progress evidence must reference existing events.")

    def _validate_state(
        self, value: GoalState | ObjectiveState, *, objective: bool
    ) -> None:
        expected = ObjectiveState if objective else GoalState
        if not isinstance(value, expected):
            raise TypeError(
                f"Persisted {'objective' if objective else 'goal'} states must be "
                f"{expected.__name__} records."
            )
        if not isinstance(value.status, GoalStatus):
            raise TypeError("Persisted lifecycle status must be a GoalStatus.")
        self._validate_evidence_records(value.evidence)

    @staticmethod
    def _tuple(value: object, label: str) -> None:
        if not isinstance(value, tuple):
            raise TypeError(f"{label} must be a tuple.")

    @staticmethod
    def _strings_tuple(value: object, label: str) -> None:
        GoalManager._tuple(value, label)
        if any(not isinstance(item, str) for item in value):
            raise TypeError(f"{label} must contain strings.")

    @staticmethod
    def _priority(value: int, label: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{label} priority must be an integer.")
        if value < 0:
            raise ValueError(f"{label} priority cannot be negative.")
