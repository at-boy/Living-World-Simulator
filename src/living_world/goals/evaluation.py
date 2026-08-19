from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, cast

from living_world.core.entity import Entity
from living_world.goals.manager import GoalManager
from living_world.goals.model import (
    CapacityCriterion,
    ConstructedCapabilityCriterion,
    ExternalConnectionCriterion,
    GoalCriterion,
    GoalDefinition,
    GoalStatus,
    ObjectiveDefinition,
    ProgressEvidence,
    ResourceMinimumCriterion,
    SettlementStageCriterion,
    SustainedNeedCriterion,
)
from living_world.state.world_state import WorldState


class CriterionDisposition(str, Enum):
    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class CriterionEvaluation:
    disposition: CriterionDisposition
    description: str
    source_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CriterionDisposition):
            raise TypeError("disposition must be a CriterionDisposition.")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string.")
        if not self.description.strip():
            raise ValueError("description cannot be empty.")
        if not isinstance(self.source_event_ids, tuple) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.source_event_ids
        ):
            raise TypeError("source_event_ids must be a tuple of non-empty strings.")
        if tuple(sorted(set(self.source_event_ids))) != self.source_event_ids:
            raise ValueError("source_event_ids must be unique and lexically sorted.")


class CriterionEvaluator(Protocol):
    def evaluate(
        self, criterion: GoalCriterion, *, owner_id: str, state: WorldState
    ) -> CriterionEvaluation: ...


_CRITERION_TYPES = (
    ResourceMinimumCriterion,
    ConstructedCapabilityCriterion,
    CapacityCriterion,
    ExternalConnectionCriterion,
    SustainedNeedCriterion,
    SettlementStageCriterion,
)


class CriterionEvaluatorRegistry:
    """Closed, typed dispatch table for authoritative goal criteria."""

    def __init__(
        self, evaluators: Mapping[type[object], CriterionEvaluator] | None = None
    ) -> None:
        configured = dict(
            default_criterion_evaluators() if evaluators is None else evaluators
        )
        missing = set(_CRITERION_TYPES) - set(configured)
        if missing:
            names = ", ".join(sorted(item.__name__ for item in missing))
            raise ValueError(f"Missing criterion evaluators: {names}.")
        unknown = set(configured) - set(_CRITERION_TYPES)
        if unknown:
            names = ", ".join(sorted(item.__name__ for item in unknown))
            raise TypeError(f"Unregistered criterion types: {names}.")
        if any(not hasattr(evaluator, "evaluate") for evaluator in configured.values()):
            raise TypeError("Criterion evaluators must implement evaluate().")
        self._evaluators = configured

    def evaluate(
        self, criterion: GoalCriterion, *, owner_id: str, state: WorldState
    ) -> CriterionEvaluation:
        evaluator = self._evaluators.get(type(criterion))
        if evaluator is None:
            raise TypeError(
                f"Unregistered criterion type '{type(criterion).__name__}'."
            )
        result = evaluator.evaluate(criterion, owner_id=owner_id, state=state)
        if not isinstance(result, CriterionEvaluation):
            raise TypeError("Criterion evaluators must return CriterionEvaluation.")
        return result


def _event_ids(state: WorldState, subject_ids: set[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            event.id
            for event in state.events.values()
            if event.subject_id in subject_ids
        )
    )


def _scoped_entities(owner_id: str, state: WorldState) -> tuple[Entity, ...]:
    owner = state.entities.get(owner_id)
    if owner is None or owner.destroyed_tick is not None:
        raise ValueError(f"Goal owner '{owner_id}' must be a live entity.")
    target_ids = {
        relationship.target_id
        for relationship in state.relationships.values()
        if relationship.kind == "owns"
        and relationship.source_id == owner_id
        and relationship.destroyed_tick is None
    }
    entities = [owner]
    for target_id in sorted(target_ids):
        target = state.entities.get(target_id)
        if target is None:
            raise ValueError(
                f"Ownership relationship targets unknown entity '{target_id}'."
            )
        if target.destroyed_tick is None:
            entities.append(target)
    return tuple(entities)


class _ResourceMinimumEvaluator:
    def evaluate(
        self, criterion: GoalCriterion, *, owner_id: str, state: WorldState
    ) -> CriterionEvaluation:
        item = cast(ResourceMinimumCriterion, criterion)
        owner = state.entities.get(owner_id)
        if owner is None or owner.destroyed_tick is not None:
            raise ValueError(f"Goal owner '{owner_id}' must be a live entity.")
        resources = owner.attributes.get("resources", {})
        if not isinstance(resources, dict):
            raise TypeError("Owner 'resources' must be a dictionary.")
        quantity = resources.get(item.resource, 0)
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            raise TypeError(f"Resource '{item.resource}' must be an integer.")
        if quantity < 0:
            raise ValueError(f"Resource '{item.resource}' cannot be negative.")
        disposition = (
            CriterionDisposition.SATISFIED
            if quantity >= item.minimum
            else CriterionDisposition.UNSATISFIED
        )
        return CriterionEvaluation(
            disposition,
            f"Resource {item.resource}: {quantity} of {item.minimum} required.",
            _event_ids(state, {owner_id}),
        )


class _ConstructedCapabilityEvaluator:
    def evaluate(
        self, criterion: GoalCriterion, *, owner_id: str, state: WorldState
    ) -> CriterionEvaluation:
        item = cast(ConstructedCapabilityCriterion, criterion)
        entities = _scoped_entities(owner_id, state)
        for entity in entities:
            if "is_constructed" in entity.attributes and not isinstance(
                entity.attributes["is_constructed"], bool
            ):
                raise TypeError(
                    f"Entity '{entity.id}' is_constructed must be a boolean."
                )
        matches = tuple(
            entity
            for entity in entities
            if entity.definition_key == item.capability
            and entity.attributes.get("is_constructed") is True
        )
        disposition = (
            CriterionDisposition.SATISFIED
            if len(matches) >= item.count
            else CriterionDisposition.UNSATISFIED
        )
        return CriterionEvaluation(
            disposition,
            f"Constructed {item.capability}: {len(matches)} of {item.count} required.",
            _event_ids(state, {entity.id for entity in matches}),
        )


class _CapacityEvaluator:
    def evaluate(
        self, criterion: GoalCriterion, *, owner_id: str, state: WorldState
    ) -> CriterionEvaluation:
        item = cast(CapacityCriterion, criterion)
        attribute = f"{item.capacity}_capacity"
        entities = _scoped_entities(owner_id, state)
        values: list[tuple[str, int]] = []
        for entity in entities:
            if attribute not in entity.attributes:
                continue
            value = entity.attributes[attribute]
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"Entity '{entity.id}' {attribute} must be an integer.")
            if value < 0:
                raise ValueError(
                    f"Entity '{entity.id}' {attribute} cannot be negative."
                )
            values.append((entity.id, value))
        if not values:
            return CriterionEvaluation(
                CriterionDisposition.UNAVAILABLE,
                f"Capacity {item.capacity} is not authoritatively available.",
            )
        total = sum(value for _, value in values)
        disposition = (
            CriterionDisposition.SATISFIED
            if total >= item.minimum
            else CriterionDisposition.UNSATISFIED
        )
        return CriterionEvaluation(
            disposition,
            f"Capacity {item.capacity}: {total} of {item.minimum} required.",
            _event_ids(state, {entity_id for entity_id, _ in values}),
        )


class _ExternalConnectionEvaluator:
    def evaluate(
        self, criterion: GoalCriterion, *, owner_id: str, state: WorldState
    ) -> CriterionEvaluation:
        del owner_id
        item = cast(ExternalConnectionCriterion, criterion)
        matches = tuple(
            reference
            for reference in sorted(
                state.external_world_references.values(), key=lambda value: value.id
            )
            if reference.role == item.role
            and reference.contact_state.value == item.state
        )
        disposition = (
            CriterionDisposition.SATISFIED
            if matches
            else CriterionDisposition.UNSATISFIED
        )
        return CriterionEvaluation(
            disposition,
            f"External connection {item.role} in state {item.state}: {len(matches)} found.",
            _event_ids(state, {reference.id for reference in matches}),
        )


class _UnavailableEvaluator:
    def __init__(self, domain: str) -> None:
        self._domain = domain

    def evaluate(
        self, criterion: GoalCriterion, *, owner_id: str, state: WorldState
    ) -> CriterionEvaluation:
        del criterion, owner_id, state
        return CriterionEvaluation(
            CriterionDisposition.UNAVAILABLE,
            f"{self._domain} criterion is not authoritatively available.",
        )


def default_criterion_evaluators() -> dict[type[object], CriterionEvaluator]:
    return {
        ResourceMinimumCriterion: _ResourceMinimumEvaluator(),
        ConstructedCapabilityCriterion: _ConstructedCapabilityEvaluator(),
        CapacityCriterion: _CapacityEvaluator(),
        ExternalConnectionCriterion: _ExternalConnectionEvaluator(),
        SustainedNeedCriterion: _UnavailableEvaluator("Sustained need"),
        SettlementStageCriterion: _UnavailableEvaluator("Settlement stage"),
    }


@dataclass(frozen=True, slots=True)
class _CriteriaSummary:
    satisfied: bool
    unavailable: bool
    descriptions: tuple[str, ...]
    source_event_ids: tuple[str, ...]


class GoalEvaluationSystem:
    """Derive goal lifecycle changes from authoritative world state."""

    def __init__(
        self,
        goals: GoalManager,
        registry: CriterionEvaluatorRegistry | None = None,
    ) -> None:
        if not isinstance(goals, GoalManager):
            raise TypeError("goals must be a GoalManager.")
        self._goals = goals
        self._registry = registry or CriterionEvaluatorRegistry()

    def step(self, state: WorldState) -> None:
        original_goals = dict(state.goal_states)
        original_objectives = dict(state.objective_states)
        original_event_ids = frozenset(state.events)
        try:
            for goal_id in sorted(state.goal_definitions):
                self._evaluate_goal(state.goal_definitions[goal_id], state)
        except Exception:
            state.goal_states.clear()
            state.goal_states.update(original_goals)
            state.objective_states.clear()
            state.objective_states.update(original_objectives)
            for event_id in set(state.events) - original_event_ids:
                state.events.pop(event_id, None)
            raise

    def _evaluate_goal(self, goal: GoalDefinition, state: WorldState) -> None:
        objectives = {
            objective_id: state.objective_definitions[objective_id]
            for objective_id in goal.objective_ids
        }
        for objective_id in self._stable_order(objectives):
            self._evaluate_objective(goal, objectives[objective_id], state)

        current = state.goal_states[goal.id]
        if current.status in (GoalStatus.COMPLETED, GoalStatus.FAILED):
            return
        required = self._required_objectives(objectives)
        required_states = tuple(state.objective_states[item] for item in required)
        completion = self._criteria(
            goal.completion_criteria, goal.owner_id, state, require_all=True
        )
        failure = self._criteria(
            goal.failure_criteria, goal.owner_id, state, require_all=False
        )
        required_description = ", ".join(
            f"{item}={state.objective_states[item].status.value}" for item in required
        )
        progress_details = completion.descriptions + failure.descriptions
        if required_description:
            progress_details += (f"Required objectives: {required_description}.",)
        progress_description = self._description(
            "Goal evaluation snapshot.", progress_details
        )
        progress_sources = tuple(
            sorted(
                set(completion.source_event_ids)
                | set(failure.source_event_ids)
                | set(_event_ids(state, set(required)))
            )
        )
        deadline_failed = (
            goal.deadline_tick is not None and state.tick >= goal.deadline_tick
        )
        if deadline_failed:
            self._transition_goal(
                goal.id, GoalStatus.FAILED, "Goal deadline reached.", (), state
            )
        elif failure.satisfied and goal.failure_criteria:
            self._transition_goal(
                goal.id,
                GoalStatus.FAILED,
                "Goal failure criteria satisfied.",
                failure.source_event_ids,
                state,
            )
        elif any(item.status is GoalStatus.FAILED for item in required_states):
            self._transition_goal(
                goal.id,
                GoalStatus.FAILED,
                "A required objective failed.",
                _event_ids(state, set(required)),
                state,
            )
        elif (
            all(item.status is GoalStatus.COMPLETED for item in required_states)
            and completion.satisfied
        ):
            if current.status is GoalStatus.INACTIVE:
                self._transition_goal(
                    goal.id,
                    GoalStatus.ACTIVE,
                    progress_description,
                    progress_sources,
                    state,
                )
            else:
                self._transition_goal(
                    goal.id,
                    GoalStatus.COMPLETED,
                    self._description(
                        "Goal completion criteria satisfied.", completion.descriptions
                    ),
                    tuple(
                        sorted(
                            set(completion.source_event_ids)
                            | set(_event_ids(state, set(required)))
                        )
                    ),
                    state,
                )
        elif current.status is GoalStatus.INACTIVE:
            self._transition_goal(
                goal.id,
                GoalStatus.ACTIVE,
                progress_description,
                progress_sources,
                state,
            )
        elif (
            completion.unavailable
            or failure.unavailable
            or any(item.status is GoalStatus.BLOCKED for item in required_states)
        ):
            self._transition_goal(
                goal.id,
                GoalStatus.BLOCKED,
                progress_description,
                progress_sources,
                state,
            )
        elif current.status is GoalStatus.BLOCKED:
            self._transition_goal(
                goal.id,
                GoalStatus.ACTIVE,
                progress_description,
                progress_sources,
                state,
            )
        if state.goal_states[goal.id].status is current.status and current.status in (
            GoalStatus.ACTIVE,
            GoalStatus.BLOCKED,
        ):
            self._goals.record_goal_evidence(
                goal.id,
                self._evidence(
                    progress_description,
                    progress_sources,
                    state,
                ),
            )

    def _evaluate_objective(
        self, goal: GoalDefinition, objective: ObjectiveDefinition, state: WorldState
    ) -> None:
        current = state.objective_states[objective.id]
        if current.status in (GoalStatus.COMPLETED, GoalStatus.FAILED):
            return
        dependencies = tuple(
            state.objective_states[item] for item in objective.dependencies
        )
        completion = self._criteria(
            objective.completion_criteria, goal.owner_id, state, require_all=True
        )
        failure = self._criteria(
            objective.failure_criteria, goal.owner_id, state, require_all=False
        )
        deadline_failed = (
            objective.deadline_tick is not None
            and state.tick >= objective.deadline_tick
        )
        alternative_complete = any(
            state.objective_states[item].status is GoalStatus.COMPLETED
            for item in objective.alternatives
        )
        dependency_description = ", ".join(
            f"{item}={state.objective_states[item].status.value}"
            for item in objective.dependencies
        )
        alternative_description = ", ".join(
            f"{item}={state.objective_states[item].status.value}"
            for item in objective.alternatives
        )
        progress_details = completion.descriptions + failure.descriptions
        if dependency_description:
            progress_details += (f"Dependencies: {dependency_description}.",)
        if alternative_description:
            progress_details += (f"Alternatives: {alternative_description}.",)
        reference_ids = set(objective.dependencies + objective.alternatives)
        progress_description = self._description(
            "Objective evaluation snapshot.", progress_details
        )
        progress_sources = tuple(
            sorted(
                set(completion.source_event_ids)
                | set(failure.source_event_ids)
                | set(_event_ids(state, reference_ids))
            )
        )
        if deadline_failed:
            self._transition_objective(
                objective.id,
                GoalStatus.FAILED,
                "Objective deadline reached.",
                (),
                state,
            )
        elif failure.satisfied and objective.failure_criteria:
            self._transition_objective(
                objective.id,
                GoalStatus.FAILED,
                "Objective failure criteria satisfied.",
                failure.source_event_ids,
                state,
            )
        elif any(item.status is GoalStatus.FAILED for item in dependencies):
            self._transition_objective(
                objective.id,
                GoalStatus.FAILED,
                "An objective dependency failed.",
                _event_ids(state, set(objective.dependencies)),
                state,
            )
        elif dependencies and not all(
            item.status is GoalStatus.COMPLETED for item in dependencies
        ):
            if current.status is GoalStatus.ACTIVE:
                self._transition_objective(
                    objective.id,
                    GoalStatus.BLOCKED,
                    progress_description,
                    progress_sources,
                    state,
                )
        elif completion.satisfied or alternative_complete:
            if current.status is GoalStatus.INACTIVE:
                self._transition_objective(
                    objective.id,
                    GoalStatus.ACTIVE,
                    progress_description,
                    progress_sources,
                    state,
                )
            else:
                completed_alternatives = {
                    item
                    for item in objective.alternatives
                    if state.objective_states[item].status is GoalStatus.COMPLETED
                }
                self._transition_objective(
                    objective.id,
                    GoalStatus.COMPLETED,
                    (
                        self._description(
                            "Objective completion criteria satisfied.",
                            completion.descriptions,
                        )
                        if completion.satisfied
                        else "Alternative objective completed."
                    ),
                    tuple(
                        sorted(
                            set(completion.source_event_ids)
                            | set(_event_ids(state, completed_alternatives))
                        )
                    ),
                    state,
                )
        elif current.status is GoalStatus.INACTIVE:
            self._transition_objective(
                objective.id,
                GoalStatus.ACTIVE,
                progress_description,
                progress_sources,
                state,
            )
        elif completion.unavailable or failure.unavailable:
            self._transition_objective(
                objective.id,
                GoalStatus.BLOCKED,
                progress_description,
                progress_sources,
                state,
            )
        elif current.status is GoalStatus.BLOCKED:
            self._transition_objective(
                objective.id,
                GoalStatus.ACTIVE,
                progress_description,
                progress_sources,
                state,
            )
        if state.objective_states[objective.id].status is current.status and (
            current.status in (GoalStatus.ACTIVE, GoalStatus.BLOCKED)
        ):
            self._goals.record_objective_evidence(
                objective.id,
                self._evidence(
                    progress_description,
                    progress_sources,
                    state,
                ),
            )

    def _criteria(
        self,
        criteria: tuple[GoalCriterion, ...],
        owner_id: str,
        state: WorldState,
        *,
        require_all: bool,
    ) -> _CriteriaSummary:
        results = tuple(
            self._registry.evaluate(item, owner_id=owner_id, state=state)
            for item in criteria
        )
        return _CriteriaSummary(
            satisfied=(
                all(
                    item.disposition is CriterionDisposition.SATISFIED
                    for item in results
                )
                if require_all
                else any(
                    item.disposition is CriterionDisposition.SATISFIED
                    for item in results
                )
            ),
            unavailable=any(
                item.disposition is CriterionDisposition.UNAVAILABLE for item in results
            ),
            descriptions=tuple(item.description for item in results),
            source_event_ids=tuple(
                sorted(
                    {event_id for item in results for event_id in item.source_event_ids}
                )
            ),
        )

    @staticmethod
    def _description(prefix: str, details: tuple[str, ...]) -> str:
        if not details:
            return prefix
        return f"{prefix} {' '.join(details)}"

    @staticmethod
    def _stable_order(
        objectives: Mapping[str, ObjectiveDefinition],
    ) -> tuple[str, ...]:
        ordered: list[str] = []
        visited: set[str] = set()

        def visit(objective_id: str) -> None:
            if objective_id in visited:
                return
            objective = objectives[objective_id]
            for dependency_id in sorted(
                objective.dependencies + objective.alternatives
            ):
                visit(dependency_id)
            visited.add(objective_id)
            ordered.append(objective_id)

        for objective_id in sorted(objectives):
            visit(objective_id)
        return tuple(ordered)

    @staticmethod
    def _required_objectives(
        objectives: Mapping[str, ObjectiveDefinition],
    ) -> tuple[str, ...]:
        alternatives = {
            item for objective in objectives.values() for item in objective.alternatives
        }
        dependencies = {
            item for objective in objectives.values() for item in objective.dependencies
        }
        return tuple(sorted(set(objectives) - (alternatives - dependencies)))

    @staticmethod
    def _evidence(
        description: str, source_event_ids: tuple[str, ...], state: WorldState
    ) -> ProgressEvidence:
        return ProgressEvidence(state.tick, description, source_event_ids)

    def _transition_goal(
        self,
        goal_id: str,
        status: GoalStatus,
        description: str,
        source_event_ids: tuple[str, ...],
        state: WorldState,
    ) -> None:
        if state.goal_states[goal_id].status is status:
            return
        self._goals.transition_goal(
            goal_id, status, self._evidence(description, source_event_ids, state)
        )

    def _transition_objective(
        self,
        objective_id: str,
        status: GoalStatus,
        description: str,
        source_event_ids: tuple[str, ...],
        state: WorldState,
    ) -> None:
        if state.objective_states[objective_id].status is status:
            return
        self._goals.transition_objective(
            objective_id, status, self._evidence(description, source_event_ids, state)
        )
