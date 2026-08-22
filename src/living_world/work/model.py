from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_INTERNAL_ID = re.compile(
    r"(?:entity|relationship|event|observation|memory|belief|experience|knowledge|"
    r"npc_relationship|placement|need|goal|objective|external_reference|"
    r"external_dispatch|dispatch|consumption|storage|maintenance|work|"
    r"work_reservation)_[A-Za-z0-9][A-Za-z0-9_-]*"
)


class WorkCategory(str, Enum):
    GATHER_WATER = "gather_water"
    PRODUCE_FOOD = "produce_food"
    BUILD_SHELTER = "build_shelter"
    BUILD_STORAGE = "build_storage"
    MAINTAIN_CAPABILITY = "maintain_capability"
    ESTABLISH_EXTERNAL_TRADE_CONNECTION = "establish_external_trade_connection"


class WorkStatus(str, Enum):
    PROPOSED = "proposed"
    READY = "ready"
    ASSIGNED = "assigned"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ToolRequirement:
    tool: str
    quantity: int

    def __post_init__(self) -> None:
        text(self.tool, "tool")
        integer(self.quantity, "quantity", 1)


@dataclass(frozen=True, slots=True)
class ResourceRequirement:
    resource: str
    quantity: int

    def __post_init__(self) -> None:
        text(self.resource, "resource")
        integer(self.quantity, "quantity", 1)


@dataclass(frozen=True, slots=True)
class ResourceWorkTarget:
    resource: str
    quantity: int

    def __post_init__(self) -> None:
        text(self.resource, "resource")
        integer(self.quantity, "quantity", 1)


@dataclass(frozen=True, slots=True)
class CapabilityWorkTarget:
    definition_key: str
    count: int

    def __post_init__(self) -> None:
        text(self.definition_key, "definition_key")
        integer(self.count, "count", 1)


@dataclass(frozen=True, slots=True)
class MaintenanceWorkTarget:
    policy_id: str

    def __post_init__(self) -> None:
        text(self.policy_id, "policy_id")


@dataclass(frozen=True, slots=True)
class ExternalConnectionWorkTarget:
    reference_id: str

    def __post_init__(self) -> None:
        text(self.reference_id, "reference_id")


WorkTarget = (
    ResourceWorkTarget
    | CapabilityWorkTarget
    | MaintenanceWorkTarget
    | ExternalConnectionWorkTarget
)


@dataclass(frozen=True, slots=True)
class WorkDefinition:
    id: str
    category: WorkCategory
    target: WorkTarget
    public_label: str
    settlement_id: str
    objective_id: str
    location_id: str
    prerequisite_work_ids: tuple[str, ...]
    labor_required: int
    tools: tuple[ToolRequirement, ...]
    resources: tuple[ResourceRequirement, ...]
    required_progress: int
    priority: int
    deadline_tick: int | None
    created_tick: int

    def __post_init__(self) -> None:
        text(self.id, "id")
        if not isinstance(self.category, WorkCategory):
            raise TypeError("category must be a WorkCategory.")
        visible_text(self.public_label, "public_label")
        for value, name in (
            (self.settlement_id, "settlement_id"),
            (self.objective_id, "objective_id"),
            (self.location_id, "location_id"),
        ):
            text(value, name)
        integer(self.labor_required, "labor_required")
        integer(self.required_progress, "required_progress", 1)
        integer(self.priority, "priority")
        integer(self.created_tick, "created_tick")
        if self.deadline_tick is not None:
            integer(self.deadline_tick, "deadline_tick")
        if not all(
            isinstance(x, tuple)
            for x in (self.prerequisite_work_ids, self.tools, self.resources)
        ):
            raise TypeError("Work collections must be tuples.")


@dataclass(frozen=True, slots=True)
class WorkState:
    work_id: str
    status: WorkStatus = WorkStatus.PROPOSED
    progress: int = 0
    reservation_id: str | None = None
    status_reason: str | None = None
    started_tick: int | None = None
    resolution_tick: int | None = None

    def __post_init__(self) -> None:
        text(self.work_id, "work_id")
        if not isinstance(self.status, WorkStatus):
            raise TypeError("status must be a WorkStatus.")
        integer(self.progress, "progress")

    @property
    def id(self) -> str:
        return self.work_id


@dataclass(frozen=True, slots=True)
class WorkReservation:
    id: str
    work_id: str
    labor_entity_ids: tuple[str, ...]
    tools: tuple[ToolRequirement, ...]
    resources: tuple[ResourceRequirement, ...]
    created_tick: int
    released_tick: int | None = None
    release_status: WorkStatus | None = None

    def __post_init__(self) -> None:
        text(self.id, "id")
        text(self.work_id, "work_id")
        integer(self.created_tick, "created_tick")
        if self.released_tick is not None:
            integer(self.released_tick, "released_tick")
        if self.release_status is not None and not isinstance(
            self.release_status, WorkStatus
        ):
            raise TypeError("release_status must be a WorkStatus or None.")


@dataclass(frozen=True, slots=True)
class NPCWorkInterpretation:
    label: str
    description: str

    def __post_init__(self) -> None:
        visible_text(self.label, "label")
        visible_text(self.description, "description")


def visible_text(value: object, name: str) -> str:
    text(value, name)
    assert isinstance(value, str)
    if _INTERNAL_ID.search(value):
        raise ValueError(f"{name} cannot contain an internal ID.")
    return value


def text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} cannot be empty.")
    return value


def integer(value: object, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return value
