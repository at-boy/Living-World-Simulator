from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum

_NEED_ID = re.compile(r"need_[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_CONSUMPTION_ID = re.compile(r"consumption_[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_STORAGE_ID = re.compile(r"storage_[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_MAINTENANCE_ID = re.compile(r"maintenance_[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_ENGINE_ID_IN_TEXT = re.compile(
    r"\b(?:entity|relationship|event|observation|memory|belief|experience|knowledge|"
    r"npc_relationship|placement|need|goal|objective|external_reference|"
    r"external_dispatch|dispatch|"
    r"consumption|storage|maintenance)_[A-Za-z0-9][A-Za-z0-9_-]*\b"
)


class NeedKind(str, Enum):
    FOOD = "food"
    WATER = "water"
    SHELTER = "shelter"
    STORAGE = "storage"


class NeedLevel(str, Enum):
    UNAVAILABLE = "unavailable"
    CRITICAL = "critical"
    STRAINED = "strained"
    SECURE = "secure"
    SURPLUS = "surplus"


@dataclass(frozen=True, slots=True)
class NeedDefinition:
    id: str
    owner_id: str
    kind: NeedKind
    requirement_per_person: int
    secure_maximum: float
    strained_maximum: float
    assessment_window_ticks: int

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or _NEED_ID.fullmatch(self.id) is None:
            raise ValueError("Need id must match the canonical need identifier format.")
        if not isinstance(self.owner_id, str) or not self.owner_id.strip():
            raise ValueError("Need owner_id cannot be empty.")
        if not isinstance(self.kind, NeedKind):
            raise TypeError("Need kind must be a NeedKind.")
        _positive_integer(self.requirement_per_person, "requirement_per_person")
        _positive_integer(self.assessment_window_ticks, "assessment_window_ticks")
        secure = _finite_number(self.secure_maximum, "secure_maximum")
        strained = _finite_number(self.strained_maximum, "strained_maximum")
        if not 0 <= secure < strained <= 1:
            raise ValueError(
                "Need thresholds must satisfy 0 <= secure < strained <= 1."
            )
        object.__setattr__(self, "secure_maximum", secure)
        object.__setattr__(self, "strained_maximum", strained)


@dataclass(frozen=True, slots=True)
class NeedAssessment:
    tick: int
    level: NeedLevel
    available: int | None
    required: int | None
    balance: int | None
    pressure: float | None

    def __post_init__(self) -> None:
        _nonnegative_integer(self.tick, "tick")
        if not isinstance(self.level, NeedLevel):
            raise TypeError("Need assessment level must be a NeedLevel.")
        values = (self.available, self.required, self.balance, self.pressure)
        if self.level is NeedLevel.UNAVAILABLE:
            if any(value is not None for value in values):
                raise ValueError(
                    "Unavailable assessments cannot contain numeric values."
                )
            return
        if any(value is None for value in values):
            raise ValueError("Available assessments require all numeric values.")
        _nonnegative_integer(self.available, "available")
        _nonnegative_integer(self.required, "required")
        if not isinstance(self.balance, int) or isinstance(self.balance, bool):
            raise TypeError("balance must be an integer.")
        pressure = _finite_number(self.pressure, "pressure")
        if not 0 <= pressure <= 1:
            raise ValueError("pressure must be between zero and one.")
        object.__setattr__(self, "pressure", pressure)


@dataclass(frozen=True, slots=True)
class NeedState:
    need_id: str
    current: NeedAssessment | None = None
    history: tuple[NeedAssessment, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.need_id, str)
            or _NEED_ID.fullmatch(self.need_id) is None
        ):
            raise ValueError(
                "Need state id must match the canonical need identifier format."
            )
        if not isinstance(self.history, tuple) or any(
            not isinstance(item, NeedAssessment) for item in self.history
        ):
            raise TypeError("Need history must be a tuple of assessments.")
        if self.current is None:
            if self.history:
                raise ValueError("Need history requires a current assessment.")
        elif not self.history or self.history[-1] != self.current:
            raise ValueError("Current need assessment must be the last history entry.")

    @property
    def id(self) -> str:
        return self.need_id


@dataclass(frozen=True, slots=True)
class NPCNeedInterpretation:
    label: str
    description: str

    def __post_init__(self) -> None:
        for name, value in (("label", self.label), ("description", self.description)):
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
            if not value.strip():
                raise ValueError(f"{name} cannot be empty.")
            if re.search(r"need_[A-Za-z0-9][A-Za-z0-9_-]*", value):
                raise ValueError(f"{name} cannot contain an internal need identifier.")


def _text(value: object, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} cannot be empty.")


@dataclass(frozen=True, slots=True)
class ConsumptionPolicy:
    id: str
    owner_id: str
    food_per_person_per_tick: int
    water_per_person_per_tick: int

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or _CONSUMPTION_ID.fullmatch(self.id) is None:
            raise ValueError("Consumption id must be canonical.")
        _text(self.owner_id, "owner_id")
        _nonnegative_integer(self.food_per_person_per_tick, "food_per_person_per_tick")
        _nonnegative_integer(
            self.water_per_person_per_tick, "water_per_person_per_tick"
        )
        if not self.food_per_person_per_tick and not self.water_per_person_per_tick:
            raise ValueError("At least one consumption rate must be positive.")


@dataclass(frozen=True, slots=True)
class ConsumptionState:
    policy_id: str
    last_processed_tick: int | None = None
    food_shortage: bool = False
    water_shortage: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.policy_id, str)
            or _CONSUMPTION_ID.fullmatch(self.policy_id) is None
        ):
            raise ValueError("Consumption state id must be canonical.")
        if self.last_processed_tick is not None:
            _nonnegative_integer(self.last_processed_tick, "last_processed_tick")
        if not isinstance(self.food_shortage, bool) or not isinstance(
            self.water_shortage, bool
        ):
            raise TypeError("Shortage flags must be booleans.")

    @property
    def id(self) -> str:
        return self.policy_id


@dataclass(frozen=True, slots=True)
class StorageResourceRule:
    resource: str
    spoilage_per_tick: int

    def __post_init__(self) -> None:
        _text(self.resource, "resource")
        _nonnegative_integer(self.spoilage_per_tick, "spoilage_per_tick")


@dataclass(frozen=True, slots=True)
class StoragePolicy:
    id: str
    owner_id: str
    resources: tuple[StorageResourceRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or _STORAGE_ID.fullmatch(self.id) is None:
            raise ValueError("Storage id must be canonical.")
        _text(self.owner_id, "owner_id")
        if not isinstance(self.resources, tuple) or any(
            not isinstance(x, StorageResourceRule) for x in self.resources
        ):
            raise TypeError("resources must be a tuple of StorageResourceRule values.")
        names = tuple(x.resource for x in self.resources)
        if len(names) != len(set(names)):
            raise ValueError("Storage resources must be unique.")


@dataclass(frozen=True, slots=True)
class StorageState:
    policy_id: str
    last_processed_tick: int | None = None
    overflowing: bool = False
    spoiling: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.policy_id, str)
            or _STORAGE_ID.fullmatch(self.policy_id) is None
        ):
            raise ValueError("Storage state id must be canonical.")
        if self.last_processed_tick is not None:
            _nonnegative_integer(self.last_processed_tick, "last_processed_tick")
        if not isinstance(self.overflowing, bool) or not isinstance(
            self.spoiling, bool
        ):
            raise TypeError("Storage flags must be booleans.")

    @property
    def id(self) -> str:
        return self.policy_id


@dataclass(frozen=True, slots=True)
class MaintenanceRequirement:
    resource: str
    amount: int

    def __post_init__(self) -> None:
        _text(self.resource, "resource")
        _positive_integer(self.amount, "amount")


@dataclass(frozen=True, slots=True)
class MaintenancePolicy:
    id: str
    owner_id: str
    capability_id: str
    label: str
    upkeep: tuple[MaintenanceRequirement, ...]
    initial_condition: int
    maximum_condition: int
    deterioration_per_unpaid_tick: int
    recovery_per_paid_tick: int

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or _MAINTENANCE_ID.fullmatch(self.id) is None:
            raise ValueError("Maintenance id must be canonical.")
        for value, name in (
            (self.owner_id, "owner_id"),
            (self.capability_id, "capability_id"),
            (self.label, "label"),
        ):
            _text(value, name)
        if _ENGINE_ID_IN_TEXT.search(self.label):
            raise ValueError("label cannot contain an internal engine identifier.")
        if self.owner_id == self.capability_id:
            raise ValueError("A maintenance capability must differ from its owner.")
        if (
            not isinstance(self.upkeep, tuple)
            or not self.upkeep
            or any(not isinstance(x, MaintenanceRequirement) for x in self.upkeep)
        ):
            raise TypeError("upkeep must be a nonempty tuple of requirements.")
        names = tuple(x.resource for x in self.upkeep)
        if len(names) != len(set(names)):
            raise ValueError("Upkeep resources must be unique.")
        for value, name in (
            (self.initial_condition, "initial_condition"),
            (self.maximum_condition, "maximum_condition"),
            (self.deterioration_per_unpaid_tick, "deterioration_per_unpaid_tick"),
            (self.recovery_per_paid_tick, "recovery_per_paid_tick"),
        ):
            _positive_integer(value, name)
        if self.initial_condition > self.maximum_condition:
            raise ValueError("initial_condition cannot exceed maximum_condition.")


@dataclass(frozen=True, slots=True)
class MaintenanceState:
    policy_id: str
    condition: int
    last_processed_tick: int | None = None
    upkeep_shortage: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.policy_id, str)
            or _MAINTENANCE_ID.fullmatch(self.policy_id) is None
        ):
            raise ValueError("Maintenance state id must be canonical.")
        _nonnegative_integer(self.condition, "condition")
        if self.last_processed_tick is not None:
            _nonnegative_integer(self.last_processed_tick, "last_processed_tick")
        if not isinstance(self.upkeep_shortage, bool):
            raise TypeError("upkeep_shortage must be a boolean.")

    @property
    def id(self) -> str:
        return self.policy_id


@dataclass(frozen=True, slots=True)
class NPCConsequenceInterpretation:
    label: str
    description: str

    def __post_init__(self) -> None:
        for value, name in ((self.label, "label"), (self.description, "description")):
            _text(value, name)
            if _ENGINE_ID_IN_TEXT.search(value):
                raise ValueError(
                    f"{name} cannot contain an internal engine identifier."
                )


def _positive_integer(value: object, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    if value <= 0:
        raise ValueError(f"{name} must be positive.")


def _nonnegative_integer(value: object, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


def _finite_number(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite.")
    return result
