from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_INTERNAL_ID = re.compile(
    r"(?:entity|relationship|event|observation|belief|experience|memory|"
    r"knowledge|npc_relationship|external_reference|external_dispatch)_\d+|"
    r"(?:goal|objective)_[A-Za-z0-9][A-Za-z0-9_-]*"
)


class GoalOwnerKind(str, Enum):
    NPC = "npc"
    ORGANIZATION = "organization"
    EXPEDITION = "expedition"
    SETTLEMENT = "settlement"


class GoalStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ResourceMinimumCriterion:
    resource: str
    minimum: int


@dataclass(frozen=True, slots=True)
class ConstructedCapabilityCriterion:
    capability: str
    count: int


@dataclass(frozen=True, slots=True)
class CapacityCriterion:
    capacity: str
    minimum: int


@dataclass(frozen=True, slots=True)
class ExternalConnectionCriterion:
    role: str
    state: str


@dataclass(frozen=True, slots=True)
class SustainedNeedCriterion:
    need: str
    maximum: float
    duration_ticks: int


@dataclass(frozen=True, slots=True)
class SettlementStageCriterion:
    stage: str


GoalCriterion = (
    ResourceMinimumCriterion
    | ConstructedCapabilityCriterion
    | CapacityCriterion
    | ExternalConnectionCriterion
    | SustainedNeedCriterion
    | SettlementStageCriterion
)


@dataclass(frozen=True, slots=True)
class ObjectiveDefinition:
    id: str
    label: str
    purpose: str
    npc_interpretation: str
    completion_criteria: tuple[GoalCriterion, ...]
    failure_criteria: tuple[GoalCriterion, ...] = ()
    dependencies: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    deadline_tick: int | None = None
    priority: int = 0
    authorized_action_categories: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GoalDefinition:
    id: str
    owner_kind: GoalOwnerKind
    owner_id: str
    label: str
    purpose: str
    npc_interpretation: str
    objective_ids: tuple[str, ...]
    deadline_tick: int | None = None
    priority: int = 0
    authorized_action_categories: tuple[str, ...] = ()
    completion_criteria: tuple[GoalCriterion, ...] = ()
    failure_criteria: tuple[GoalCriterion, ...] = ()


@dataclass(frozen=True, slots=True)
class ProgressEvidence:
    tick: int
    description: str
    source_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GoalState:
    goal_id: str
    status: GoalStatus = GoalStatus.INACTIVE
    evidence: tuple[ProgressEvidence, ...] = ()

    @property
    def id(self) -> str:
        return self.goal_id


@dataclass(frozen=True, slots=True)
class ObjectiveState:
    objective_id: str
    status: GoalStatus = GoalStatus.INACTIVE
    evidence: tuple[ProgressEvidence, ...] = ()

    @property
    def id(self) -> str:
        return self.objective_id


@dataclass(frozen=True, slots=True)
class NPCGoalInterpretation:
    label: str
    description: str

    def __post_init__(self) -> None:
        _visible_text(self.label, "label")
        _visible_text(self.description, "description")


def _visible_text(value: object, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} cannot be empty.")
    if _INTERNAL_ID.search(value):
        raise ValueError(f"{name} cannot contain an internal ID.")
