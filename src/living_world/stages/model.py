import re
from dataclasses import dataclass
from enum import Enum

_ENGINE_ID_IN_TEXT = re.compile(
    r"\b(?:entity|relationship|event|observation|memory|belief|experience|knowledge|npc_relationship|placement|need|goal|objective|external_reference|external_dispatch|dispatch|consumption|storage|maintenance|work|work_reservation)_[A-Za-z0-9][A-Za-z0-9_-]*\b"
)


class SettlementStage(str, Enum):
    FOUNDING_CAMP = "founding_camp"
    SETTLEMENT = "settlement"
    TOWN = "town"


class StageRequirementKind(str, Enum):
    WATER = "water"
    FOOD = "food"
    SHELTER = "shelter"
    STORAGE = "storage"
    MAINTENANCE = "maintenance"
    EXTERNAL_CONNECTION = "external_connection"
    POPULATION = "population"
    CAPABILITY = "capability"


def _text(value: object, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} cannot be empty.")


def _tick(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("Stage ticks must be integers.")
    if value < 0:
        raise ValueError("Stage ticks cannot be negative.")


@dataclass(frozen=True, slots=True)
class StageObjectiveRequirement:
    kind: StageRequirementKind
    objective_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, StageRequirementKind):
            raise TypeError("kind must be a StageRequirementKind.")
        _text(self.objective_id, "objective_id")


@dataclass(frozen=True, slots=True)
class SettlementStageDefinition:
    stage: SettlementStage
    requirements: tuple[StageObjectiveRequirement, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.stage, SettlementStage):
            raise TypeError("stage must be a SettlementStage.")
        if not isinstance(self.requirements, tuple) or any(
            not isinstance(item, StageObjectiveRequirement)
            for item in self.requirements
        ):
            raise TypeError("requirements must be a tuple of stage requirements.")


@dataclass(frozen=True, slots=True)
class SettlementStageProgram:
    settlement_id: str
    stages: tuple[SettlementStageDefinition, ...]

    def __post_init__(self) -> None:
        _text(self.settlement_id, "settlement_id")
        if not isinstance(self.stages, tuple) or any(
            not isinstance(item, SettlementStageDefinition) for item in self.stages
        ):
            raise TypeError("stages must be a tuple of stage definitions.")


@dataclass(frozen=True, slots=True)
class SettlementStageState:
    settlement_id: str
    current_stage: SettlementStage
    entered_tick: int
    last_transition_tick: int | None = None

    def __post_init__(self) -> None:
        _text(self.settlement_id, "settlement_id")
        if not isinstance(self.current_stage, SettlementStage):
            raise TypeError("current_stage must be a SettlementStage.")
        _tick(self.entered_tick)
        if self.last_transition_tick is not None:
            _tick(self.last_transition_tick)
            if self.last_transition_tick != self.entered_tick:
                raise ValueError("Transition tick must equal entered tick.")


@dataclass(frozen=True, slots=True)
class StageRequirementEvidence:
    kind: StageRequirementKind
    objective_id: str
    source_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        StageObjectiveRequirement(self.kind, self.objective_id)
        if not isinstance(self.source_event_ids, tuple):
            raise TypeError("source_event_ids must be a tuple.")
        for item in self.source_event_ids:
            _text(item, "source event ID")
        if tuple(sorted(set(self.source_event_ids))) != self.source_event_ids:
            raise ValueError("Source event IDs must be unique and sorted.")


@dataclass(frozen=True, slots=True)
class NPCSettlementStageInterpretation:
    label: str
    description: str

    def __post_init__(self) -> None:
        for name, value in (("label", self.label), ("description", self.description)):
            _text(value, name)
            if _ENGINE_ID_IN_TEXT.search(value):
                raise ValueError(f"{name} cannot contain internal engine IDs.")
