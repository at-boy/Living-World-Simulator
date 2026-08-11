from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CognitiveSalience:
    """Importance policy shared by NPC-scoped cognitive records."""

    importance: float
    is_core: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.importance, (int, float)) or isinstance(
            self.importance, bool
        ):
            raise TypeError("Cognitive salience importance must be a number.")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(
                "Cognitive salience importance must be between 0.0 and 1.0."
            )
        if not isinstance(self.is_core, bool):
            raise TypeError("Cognitive salience is_core must be a boolean.")
        if self.is_core and self.importance < 0.8:
            raise ValueError("Core cognitive salience requires importance >= 0.8.")

        object.__setattr__(self, "importance", float(self.importance))

    @property
    def is_important(self) -> bool:
        """Return whether this record is important without making it core."""

        return self.importance >= 0.6


@dataclass(frozen=True, slots=True)
class Memory:
    """An immutable, holder-scoped retained interpretation of a perception."""

    id: str
    tick: int
    holder_id: str
    subject_id: str
    summary: str
    salience: CognitiveSalience
    source_observation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty_string(self.id, "Memory id")
        _require_non_empty_string(self.holder_id, "Memory holder_id")
        _require_non_empty_string(self.subject_id, "Memory subject_id")
        _require_non_empty_string(self.summary, "Memory summary")
        if not isinstance(self.tick, int) or isinstance(self.tick, bool):
            raise TypeError("Memory tick must be an integer.")
        if not isinstance(self.salience, CognitiveSalience):
            raise TypeError("Memory salience must be a CognitiveSalience value.")

        if isinstance(self.source_observation_ids, str):
            raise TypeError("Memory source observation IDs must be a tuple of strings.")
        source_ids = tuple(self.source_observation_ids)
        if not all(
            isinstance(source_id, str) and source_id.strip() for source_id in source_ids
        ):
            raise ValueError("Memory source observation IDs must be non-empty strings.")
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Memory source observation IDs must be unique.")
        object.__setattr__(self, "source_observation_ids", source_ids)


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
