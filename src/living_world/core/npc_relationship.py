from __future__ import annotations

from dataclasses import dataclass

from living_world.core.memory import CognitiveSalience


@dataclass(frozen=True, slots=True)
class NPCRelationship:
    """An immutable NPC interpretation of its relationship with a subject."""

    id: str
    tick: int
    holder_id: str
    subject_id: str
    summary: str
    salience: CognitiveSalience
    source_observation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name, value in (
            ("NPC relationship id", self.id),
            ("NPC relationship holder_id", self.holder_id),
            ("NPC relationship subject_id", self.subject_id),
            ("NPC relationship summary", self.summary),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string.")
            if not value.strip():
                raise ValueError(f"{field_name} cannot be empty.")
        if not isinstance(self.tick, int) or isinstance(self.tick, bool):
            raise TypeError("NPC relationship tick must be an integer.")
        if not isinstance(self.salience, CognitiveSalience):
            raise TypeError(
                "NPC relationship salience must be a CognitiveSalience value."
            )

        if isinstance(self.source_observation_ids, str):
            raise TypeError(
                "NPC relationship source observation IDs must be a tuple of strings."
            )
        source_ids = tuple(self.source_observation_ids)
        if not all(
            isinstance(source_id, str) and source_id.strip() for source_id in source_ids
        ):
            raise ValueError(
                "NPC relationship source observation IDs must be non-empty strings."
            )
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("NPC relationship source observation IDs must be unique.")
        object.__setattr__(self, "source_observation_ids", source_ids)
