from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DispatchDirection(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class DispatchStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    REJECTED = "rejected"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class ExternalDispatch:
    id: str
    source_entity_id: str
    reference_id: str
    direction: DispatchDirection
    good: str
    quantity: int
    reserved_good: int
    reserved_cost: int
    status: DispatchStatus
    created_tick: int
    departure_tick: int | None = None
    resolution_tick: int | None = None

    def __post_init__(self) -> None:
        for name in ("id", "source_entity_id", "reference_id", "good"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
            if not value.strip():
                raise ValueError(f"{name} cannot be empty.")
        if not isinstance(self.direction, DispatchDirection):
            raise TypeError("direction must be a DispatchDirection.")
        if not isinstance(self.status, DispatchStatus):
            raise TypeError("status must be a DispatchStatus.")
        _integer(self.quantity, "quantity", minimum=1)
        _integer(self.reserved_good, "reserved_good", minimum=0)
        _integer(self.reserved_cost, "reserved_cost", minimum=0)
        _integer(self.created_tick, "created_tick", minimum=0)
        _optional_integer(self.departure_tick, "departure_tick")
        _optional_integer(self.resolution_tick, "resolution_tick")
        if self.direction is DispatchDirection.OUTBOUND:
            if self.reserved_good != self.quantity:
                raise ValueError("Outbound dispatch must reserve its full quantity.")
        elif self.reserved_good != 0:
            raise ValueError("Inbound dispatch cannot reserve local goods.")
        if self.status is DispatchStatus.PENDING and (
            self.departure_tick is not None or self.resolution_tick is not None
        ):
            raise ValueError("Pending dispatch cannot have lifecycle ticks.")
        if self.status is DispatchStatus.IN_TRANSIT and (
            self.departure_tick is None or self.resolution_tick is not None
        ):
            raise ValueError("In-transit dispatch requires only departure_tick.")
        if self.status in {
            DispatchStatus.ARRIVED,
            DispatchStatus.LOST,
        } and (self.departure_tick is None or self.resolution_tick is None):
            raise ValueError("Resolved transit dispatch requires both lifecycle ticks.")
        if self.status is DispatchStatus.REJECTED and (
            self.departure_tick is not None or self.resolution_tick is None
        ):
            raise ValueError(
                "Rejected dispatch requires resolution_tick without departure_tick."
            )
        for tick in (self.departure_tick, self.resolution_tick):
            if tick is not None and tick < self.created_tick:
                raise ValueError("Dispatch lifecycle ticks cannot predate creation.")
        if (
            self.departure_tick is not None
            and self.resolution_tick is not None
            and self.resolution_tick < self.departure_tick
        ):
            raise ValueError("Dispatch resolution cannot predate departure.")


@dataclass(frozen=True, slots=True)
class NPCDispatchPerception:
    reference_name: str
    description: str

    def __post_init__(self) -> None:
        for name in ("reference_name", "description"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
            if not value.strip():
                raise ValueError(f"{name} cannot be empty.")


def _integer(value: object, name: str, *, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")


def _optional_integer(value: object, name: str) -> None:
    if value is not None:
        _integer(value, name, minimum=0)
