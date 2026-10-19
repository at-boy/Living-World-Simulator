from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum

_INTERNAL_ID = re.compile(
    r"(?:entity|relationship|event|observation|belief|experience|memory|"
    r"knowledge|npc_relationship|external_reference)_\d+"
)


class ContactState(str, Enum):
    UNKNOWN = "unknown"
    KNOWN = "known"
    CONTACTABLE = "contactable"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ExternalWorldReference:
    id: str
    name: str
    role: str
    allowed_imports: tuple[str, ...]
    allowed_exports: tuple[str, ...]
    capacity: int
    delay_ticks: int
    cost_per_unit: int
    reliability: float
    contact_state: ContactState
    created_tick: int

    def __post_init__(self) -> None:
        _text(self.id, "id")
        _visible_text(self.name, "name")
        _visible_text(self.role, "role")
        _goods(self.allowed_imports, "allowed_imports")
        _goods(self.allowed_exports, "allowed_exports")
        _integer(self.capacity, "capacity", minimum=1)
        _integer(self.delay_ticks, "delay_ticks", minimum=0)
        _integer(self.cost_per_unit, "cost_per_unit", minimum=0)
        if (
            not isinstance(self.reliability, int | float)
            or isinstance(self.reliability, bool)
            or not math.isfinite(self.reliability)
        ):
            raise TypeError("reliability must be a finite number.")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be between zero and one.")
        object.__setattr__(self, "reliability", float(self.reliability))
        if not isinstance(self.contact_state, ContactState):
            raise TypeError("contact_state must be a ContactState.")
        _integer(self.created_tick, "created_tick", minimum=0)


@dataclass(frozen=True, slots=True)
class NPCExternalReference:
    name: str
    role: str
    contact_description: str

    def __post_init__(self) -> None:
        _visible_text(self.name, "name")
        _visible_text(self.role, "role")
        _visible_text(self.contact_description, "contact_description")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} cannot be empty.")
    return value


def _visible_text(value: object, name: str) -> str:
    text = _text(value, name)
    if _INTERNAL_ID.search(text):
        raise ValueError(f"{name} cannot contain an internal ID.")
    return text


def _goods(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple.")
    goods = tuple(_text(item, name) for item in value)
    if len(goods) != len(set(goods)):
        raise ValueError(f"{name} cannot contain duplicates.")
    return goods


def _integer(value: object, name: str, *, minimum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return value
