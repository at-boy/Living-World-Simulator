from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from living_world.core.memory import CognitiveSalience


@dataclass(frozen=True, slots=True)
class ExperienceHistoryEntry:
    """Represents a single historical change in an NPC experience."""

    tick: int
    reason: str
    old_summary: str
    new_summary: str


@dataclass(frozen=True, slots=True)
class Experience:
    """Immutable NPC-specific learning generated from lived interaction."""

    id: str
    tick: int
    holder_id: str
    subject_id: str
    summary: str
    supporting_observations: tuple[str, ...] = ()
    supporting_memories: tuple[str, ...] = ()
    supporting_beliefs: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
    history: tuple[ExperienceHistoryEntry, ...] = ()
    salience: CognitiveSalience = field(
        default_factory=lambda: CognitiveSalience(importance=0.0)
    )

    def __post_init__(self) -> None:
        if not self.holder_id.strip():
            raise ValueError("Experience holder_id cannot be empty.")

        if not self.subject_id.strip():
            raise ValueError("Experience subject_id cannot be empty.")

        if not self.summary.strip():
            raise ValueError("Experience summary cannot be empty.")
        if not isinstance(self.salience, CognitiveSalience):
            raise TypeError("Experience salience must be a CognitiveSalience value.")

        object.__setattr__(
            self,
            "supporting_observations",
            tuple(self.supporting_observations),
        )
        object.__setattr__(
            self,
            "supporting_memories",
            tuple(self.supporting_memories),
        )
        object.__setattr__(
            self,
            "supporting_beliefs",
            tuple(self.supporting_beliefs),
        )
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )
        object.__setattr__(
            self,
            "history",
            tuple(self.history),
        )

    def update(
        self,
        *,
        tick: int,
        reason: str,
        new_summary: str | None = None,
    ) -> Experience:
        updated_summary = self.summary if new_summary is None else new_summary
        if not updated_summary.strip():
            raise ValueError("Experience summary cannot be empty.")

        entry = ExperienceHistoryEntry(
            tick=tick,
            reason=reason,
            old_summary=self.summary,
            new_summary=updated_summary,
        )

        return Experience(
            id=self.id,
            tick=tick,
            holder_id=self.holder_id,
            subject_id=self.subject_id,
            summary=updated_summary,
            supporting_observations=self.supporting_observations,
            supporting_memories=self.supporting_memories,
            supporting_beliefs=self.supporting_beliefs,
            metadata=self.metadata,
            history=self.history + (entry,),
            salience=self.salience,
        )
