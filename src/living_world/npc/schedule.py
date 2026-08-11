from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    """One inclusive-start, exclusive-end activity interval."""

    start_tick: int
    end_tick: int
    activity: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.start_tick, int)
            or isinstance(self.start_tick, bool)
            or self.start_tick < 0
        ):
            raise ValueError("Schedule start_tick must be a non-negative integer.")
        if (
            not isinstance(self.end_tick, int)
            or isinstance(self.end_tick, bool)
            or self.end_tick < 0
        ):
            raise ValueError("Schedule end_tick must be a non-negative integer.")
        if self.start_tick >= self.end_tick:
            raise ValueError("Schedule start_tick must be less than end_tick.")
        if not isinstance(self.activity, str):
            raise TypeError("Schedule activity must be a string.")
        if not self.activity.strip():
            raise ValueError("Schedule activity cannot be empty.")

    def to_attribute(self) -> dict[str, object]:
        """Return the JSON-compatible entity attribute representation."""

        return {
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "activity": self.activity,
        }

    @classmethod
    def from_attribute(cls, value: object) -> ScheduleEntry:
        """Validate and construct one schedule entry from an attribute value."""

        if not isinstance(value, Mapping):
            raise TypeError("Schedule entry must be a mapping.")
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Schedule entry keys must be strings.")

        unknown_fields = set(value).difference({"start_tick", "end_tick", "activity"})
        if unknown_fields:
            field_names = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Schedule entry has unknown fields: {field_names}.")

        if set(value) != {"start_tick", "end_tick", "activity"}:
            raise ValueError(
                "Schedule entry requires start_tick, end_tick, and activity."
            )

        return cls(
            start_tick=value["start_tick"],
            end_tick=value["end_tick"],
            activity=value["activity"],
        )


def schedule_to_attribute(entries: Sequence[ScheduleEntry]) -> list[dict[str, object]]:
    """Validate entries and return the canonical JSON-compatible schedule."""

    canonical_entries = _validate_entries(entries)
    return [entry.to_attribute() for entry in canonical_entries]


def schedule_from_attribute(value: object) -> tuple[ScheduleEntry, ...]:
    """Validate a JSON-compatible schedule and return its sorted entries."""

    if not isinstance(value, list):
        raise TypeError("Schedule must be a list of entries.")

    return _validate_entries(
        tuple(ScheduleEntry.from_attribute(entry) for entry in value)
    )


def _validate_entries(entries: Sequence[ScheduleEntry]) -> tuple[ScheduleEntry, ...]:
    if any(not isinstance(entry, ScheduleEntry) for entry in entries):
        raise TypeError("Schedule entries must be ScheduleEntry values.")

    ordered_entries = tuple(
        sorted(
            entries,
            key=lambda entry: (entry.start_tick, entry.end_tick, entry.activity),
        )
    )
    for previous, current in pairwise(ordered_entries):
        if current.start_tick < previous.end_tick:
            raise ValueError("Schedule entries cannot overlap.")

    return ordered_entries
