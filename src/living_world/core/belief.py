from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType

from living_world.core.memory import CognitiveSalience


class BeliefStatus(str, Enum):
    """Valid status states for NPC beliefs."""

    ACTIVE = "active"
    IMPORTANT = "important"
    CORE = "core"
    WEAKENED = "weakened"
    DISPROVEN = "disproven"
    CANDIDATE = "candidate"


@dataclass(frozen=True, slots=True)
class BeliefHistoryEntry:
    """Represents a single historical change in a belief state."""

    tick: int
    reason: str
    old_confidence: float
    new_confidence: float
    old_status: BeliefStatus
    new_status: BeliefStatus


@dataclass(frozen=True, slots=True)
class Belief:
    """Immutable NPC-specific belief derived from perception, memory, and experience."""

    id: str
    tick: int
    holder_id: str
    subject_id: str
    proposition: str
    confidence: float
    importance: float
    status: BeliefStatus
    supporting_observations: tuple[str, ...] = ()
    supporting_memories: tuple[str, ...] = ()
    supporting_experiences: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
    history: tuple[BeliefHistoryEntry, ...] = ()
    salience: CognitiveSalience | None = None

    def __post_init__(self) -> None:
        if not self.holder_id.strip():
            raise ValueError("Belief holder_id cannot be empty.")

        if not self.subject_id.strip():
            raise ValueError("Belief subject_id cannot be empty.")

        if not self.proposition.strip():
            raise ValueError("Belief proposition cannot be empty.")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Belief confidence must be between 0.0 and 1.0.")

        if not 0.0 <= self.importance <= 1.0:
            raise ValueError("Belief importance must be between 0.0 and 1.0.")

        if isinstance(self.status, str):
            try:
                object.__setattr__(self, "status", BeliefStatus(self.status))
            except ValueError as exc:
                raise ValueError(
                    "Belief status must be a valid BeliefStatus value."
                ) from exc
        elif not isinstance(self.status, BeliefStatus):
            raise TypeError("Belief status must be a valid BeliefStatus value.")

        if self.status is BeliefStatus.IMPORTANT and self.importance < 0.6:
            raise ValueError(
                "Important beliefs must have an importance score of at least 0.6."
            )

        if self.status is BeliefStatus.CORE and (
            self.importance < 0.8 or self.confidence < 0.7
        ):
            raise ValueError(
                "Core beliefs must have importance >= 0.8 and confidence >= 0.7."
            )

        salience = self.salience or CognitiveSalience(
            importance=self.importance,
            is_core=self.status is BeliefStatus.CORE,
        )
        if not isinstance(salience, CognitiveSalience):
            raise TypeError("Belief salience must be a CognitiveSalience value.")
        if salience.importance != float(self.importance):
            raise ValueError("Belief salience importance must match belief importance.")
        if salience.is_core != (self.status is BeliefStatus.CORE):
            raise ValueError("Belief core salience must match belief status.")

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
            "supporting_experiences",
            tuple(self.supporting_experiences),
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
        object.__setattr__(self, "salience", salience)

    def strengthen(
        self,
        *,
        tick: int,
        reason: str,
        new_confidence: float | None = None,
    ) -> Belief:
        updated_confidence = (
            min(1.0, self.confidence + 0.3)
            if new_confidence is None
            else new_confidence
        )
        if not 0.0 <= updated_confidence <= 1.0:
            raise ValueError("Belief confidence must be between 0.0 and 1.0.")

        updated_status = self.status
        if updated_status in {BeliefStatus.WEAKENED, BeliefStatus.DISPROVEN}:
            updated_status = BeliefStatus.ACTIVE

        entry = BeliefHistoryEntry(
            tick=tick,
            reason=reason,
            old_confidence=self.confidence,
            new_confidence=updated_confidence,
            old_status=self.status,
            new_status=updated_status,
        )

        return Belief(
            id=self.id,
            tick=tick,
            holder_id=self.holder_id,
            subject_id=self.subject_id,
            proposition=self.proposition,
            confidence=updated_confidence,
            importance=self.importance,
            status=updated_status,
            supporting_observations=self.supporting_observations,
            supporting_memories=self.supporting_memories,
            supporting_experiences=self.supporting_experiences,
            metadata=self.metadata,
            history=self.history + (entry,),
            salience=CognitiveSalience(
                importance=self.importance,
                is_core=updated_status is BeliefStatus.CORE,
            ),
        )

    def weaken(
        self,
        *,
        tick: int,
        reason: str,
        new_confidence: float | None = None,
    ) -> Belief:
        updated_confidence = (
            max(0.0, self.confidence - 0.25)
            if new_confidence is None
            else new_confidence
        )
        if not 0.0 <= updated_confidence <= 1.0:
            raise ValueError("Belief confidence must be between 0.0 and 1.0.")

        updated_status = BeliefStatus.WEAKENED
        if updated_confidence <= 0.2:
            updated_status = BeliefStatus.DISPROVEN

        entry = BeliefHistoryEntry(
            tick=tick,
            reason=reason,
            old_confidence=self.confidence,
            new_confidence=updated_confidence,
            old_status=self.status,
            new_status=updated_status,
        )

        return Belief(
            id=self.id,
            tick=tick,
            holder_id=self.holder_id,
            subject_id=self.subject_id,
            proposition=self.proposition,
            confidence=updated_confidence,
            importance=self.importance,
            status=updated_status,
            supporting_observations=self.supporting_observations,
            supporting_memories=self.supporting_memories,
            supporting_experiences=self.supporting_experiences,
            metadata=self.metadata,
            history=self.history + (entry,),
            salience=CognitiveSalience(
                importance=self.importance,
                is_core=updated_status is BeliefStatus.CORE,
            ),
        )

    def confirm(
        self,
        *,
        tick: int,
        reason: str,
        new_confidence: float | None = None,
    ) -> Belief:
        updated_confidence = (
            max(self.confidence, 0.8) if new_confidence is None else new_confidence
        )
        if not 0.0 <= updated_confidence <= 1.0:
            raise ValueError("Belief confidence must be between 0.0 and 1.0.")

        entry = BeliefHistoryEntry(
            tick=tick,
            reason=reason,
            old_confidence=self.confidence,
            new_confidence=updated_confidence,
            old_status=self.status,
            new_status=BeliefStatus.ACTIVE,
        )

        return Belief(
            id=self.id,
            tick=tick,
            holder_id=self.holder_id,
            subject_id=self.subject_id,
            proposition=self.proposition,
            confidence=updated_confidence,
            importance=self.importance,
            status=BeliefStatus.ACTIVE,
            supporting_observations=self.supporting_observations,
            supporting_memories=self.supporting_memories,
            supporting_experiences=self.supporting_experiences,
            metadata=self.metadata,
            history=self.history + (entry,),
            salience=CognitiveSalience(
                importance=self.importance,
                is_core=False,
            ),
        )

    def disprove(
        self,
        *,
        tick: int,
        reason: str,
        new_confidence: float | None = None,
    ) -> Belief:
        updated_confidence = 0.1 if new_confidence is None else new_confidence
        if not 0.0 <= updated_confidence <= 1.0:
            raise ValueError("Belief confidence must be between 0.0 and 1.0.")

        entry = BeliefHistoryEntry(
            tick=tick,
            reason=reason,
            old_confidence=self.confidence,
            new_confidence=updated_confidence,
            old_status=self.status,
            new_status=BeliefStatus.DISPROVEN,
        )

        return Belief(
            id=self.id,
            tick=tick,
            holder_id=self.holder_id,
            subject_id=self.subject_id,
            proposition=self.proposition,
            confidence=updated_confidence,
            importance=self.importance,
            status=BeliefStatus.DISPROVEN,
            supporting_observations=self.supporting_observations,
            supporting_memories=self.supporting_memories,
            supporting_experiences=self.supporting_experiences,
            metadata=self.metadata,
            history=self.history + (entry,),
            salience=CognitiveSalience(
                importance=self.importance,
                is_core=False,
            ),
        )

    def mark_important(
        self,
        *,
        tick: int,
        reason: str,
        importance: float | None = None,
    ) -> Belief:
        updated_importance = (
            max(self.importance, 0.7) if importance is None else importance
        )
        if not 0.0 <= updated_importance <= 1.0:
            raise ValueError("Belief importance must be between 0.0 and 1.0.")

        if updated_importance < 0.6:
            raise ValueError(
                "Important beliefs must have an importance score of at least 0.6."
            )

        entry = BeliefHistoryEntry(
            tick=tick,
            reason=reason,
            old_confidence=self.confidence,
            new_confidence=self.confidence,
            old_status=self.status,
            new_status=BeliefStatus.IMPORTANT,
        )

        return Belief(
            id=self.id,
            tick=tick,
            holder_id=self.holder_id,
            subject_id=self.subject_id,
            proposition=self.proposition,
            confidence=self.confidence,
            importance=updated_importance,
            status=BeliefStatus.IMPORTANT,
            supporting_observations=self.supporting_observations,
            supporting_memories=self.supporting_memories,
            supporting_experiences=self.supporting_experiences,
            metadata=self.metadata,
            history=self.history + (entry,),
            salience=CognitiveSalience(importance=updated_importance),
        )

    def mark_core(
        self,
        *,
        tick: int,
        reason: str,
        importance: float | None = None,
        confidence: float | None = None,
    ) -> Belief:
        updated_importance = (
            max(self.importance, 0.8) if importance is None else importance
        )
        updated_confidence = (
            max(self.confidence, 0.7) if confidence is None else confidence
        )
        if not 0.0 <= updated_importance <= 1.0:
            raise ValueError("Belief importance must be between 0.0 and 1.0.")
        if not 0.0 <= updated_confidence <= 1.0:
            raise ValueError("Belief confidence must be between 0.0 and 1.0.")
        if updated_importance < 0.8 or updated_confidence < 0.7:
            raise ValueError(
                "Core beliefs must have importance >= 0.8 and confidence >= 0.7."
            )

        entry = BeliefHistoryEntry(
            tick=tick,
            reason=reason,
            old_confidence=self.confidence,
            new_confidence=updated_confidence,
            old_status=self.status,
            new_status=BeliefStatus.CORE,
        )

        return Belief(
            id=self.id,
            tick=tick,
            holder_id=self.holder_id,
            subject_id=self.subject_id,
            proposition=self.proposition,
            confidence=updated_confidence,
            importance=updated_importance,
            status=BeliefStatus.CORE,
            supporting_observations=self.supporting_observations,
            supporting_memories=self.supporting_memories,
            supporting_experiences=self.supporting_experiences,
            metadata=self.metadata,
            history=self.history + (entry,),
            salience=CognitiveSalience(importance=updated_importance, is_core=True),
        )
