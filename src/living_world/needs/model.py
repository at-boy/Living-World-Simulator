from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum

_NEED_ID = re.compile(r"need_[A-Za-z0-9][A-Za-z0-9_-]*\Z")


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
