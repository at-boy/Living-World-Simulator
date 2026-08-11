"""Deterministic retrieval of NPC-readable cognitive interpretations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from living_world.core.belief import Belief
from living_world.core.experience import Experience
from living_world.core.knowledge import Knowledge
from living_world.core.memory import Memory
from living_world.core.npc_relationship import NPCRelationship
from living_world.state.world_state import WorldState


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """A holder-scoped request for NPC-readable cognitive records."""

    holder_id: str
    topic: str | None = None
    limit: int = 10

    def __post_init__(self) -> None:
        if not isinstance(self.holder_id, str):
            raise TypeError("Retrieval query holder_id must be a string.")
        if not self.holder_id.strip():
            raise ValueError("Retrieval query holder_id cannot be empty.")
        if self.topic is not None:
            if not isinstance(self.topic, str):
                raise TypeError("Retrieval query topic must be a string or None.")
            if not self.topic.strip():
                raise ValueError("Retrieval query topic cannot be empty when supplied.")
        if not isinstance(self.limit, int) or isinstance(self.limit, bool):
            raise TypeError("Retrieval query limit must be an integer.")
        if self.limit <= 0:
            raise ValueError("Retrieval query limit must be positive.")


@dataclass(frozen=True, slots=True)
class RetrievedCognition:
    """A deliberately small NPC-facing projection of a cognitive record."""

    kind: Literal["memory", "belief", "experience", "relationship", "knowledge"]
    text: str
    importance: float
    is_core: bool

    def __post_init__(self) -> None:
        if self.kind not in {
            "memory",
            "belief",
            "experience",
            "relationship",
            "knowledge",
        }:
            raise ValueError("Retrieved cognition kind is not supported.")
        if not isinstance(self.text, str):
            raise TypeError("Retrieved cognition text must be a string.")
        if not self.text.strip():
            raise ValueError("Retrieved cognition text cannot be empty.")
        if not isinstance(self.importance, (int, float)) or isinstance(
            self.importance, bool
        ):
            raise TypeError("Retrieved cognition importance must be a number.")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(
                "Retrieved cognition importance must be between 0.0 and 1.0."
            )
        if not isinstance(self.is_core, bool):
            raise TypeError("Retrieved cognition is_core must be a boolean.")
        object.__setattr__(self, "importance", float(self.importance))


class CognitiveRetriever(Protocol):
    """Read-only cognitive retrieval boundary."""

    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievedCognition, ...]: ...


class DeterministicCognitiveRetriever:
    """Return holder-scoped cognitive prose in deterministic policy order."""

    def __init__(self, state: WorldState) -> None:
        self._state = state

    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievedCognition, ...]:
        if not isinstance(query, RetrievalQuery):
            raise TypeError("query must be a RetrievalQuery.")

        core_records = self._core_records(query.holder_id)
        core = tuple(
            self._to_retrieved(record)
            for record in sorted(core_records, key=self._core_sort_key)
        )[: query.limit]

        if query.topic is None:
            return core

        remaining = query.limit - len(core)
        if remaining <= 0:
            return core

        topic = query.topic.casefold()
        relevant = self._relevant_records(query.holder_id, topic)
        return core + tuple(
            self._to_retrieved(record)
            for record in sorted(relevant, key=self._core_sort_key)[:remaining]
        )

    def _core_records(self, holder_id: str) -> tuple[Memory | Belief | Experience, ...]:
        memories = tuple(
            memory
            for memory in self._state.memories.values()
            if memory.holder_id == holder_id and memory.salience.is_core
        )
        beliefs = tuple(
            belief
            for belief in self._state.beliefs.values()
            if belief.holder_id == holder_id and belief.salience.is_core
        )
        experiences = tuple(
            experience
            for experience in self._state.experiences.values()
            if experience.holder_id == holder_id and experience.salience.is_core
        )
        return memories + beliefs + experiences

    def _relevant_records(
        self, holder_id: str, topic: str
    ) -> tuple[NPCRelationship | Knowledge, ...]:
        relationships = tuple(
            relationship
            for relationship in self._state.npc_relationships.values()
            if relationship.holder_id == holder_id
            and topic in relationship.summary.casefold()
        )
        knowledge = tuple(
            knowledge
            for knowledge in self._state.knowledge.values()
            if knowledge.holder_id == holder_id
            and (
                topic in knowledge.statement.casefold()
                or topic in knowledge.source_description.casefold()
            )
        )
        return relationships + knowledge

    @staticmethod
    def _core_sort_key(
        record: Memory | Belief | Experience | NPCRelationship | Knowledge,
    ) -> tuple[float, int, str]:
        return (-record.salience.importance, -record.tick, record.id)

    @staticmethod
    def _to_retrieved(
        record: Memory | Belief | Experience | NPCRelationship | Knowledge,
    ) -> RetrievedCognition:
        if isinstance(record, Memory):
            return RetrievedCognition(
                kind="memory",
                text=record.summary,
                importance=record.salience.importance,
                is_core=record.salience.is_core,
            )
        if isinstance(record, Belief):
            return RetrievedCognition(
                kind="belief",
                text=record.proposition,
                importance=record.salience.importance,
                is_core=record.salience.is_core,
            )
        if isinstance(record, Experience):
            return RetrievedCognition(
                kind="experience",
                text=record.summary,
                importance=record.salience.importance,
                is_core=record.salience.is_core,
            )
        if isinstance(record, NPCRelationship):
            return RetrievedCognition(
                kind="relationship",
                text=record.summary,
                importance=record.salience.importance,
                is_core=record.salience.is_core,
            )
        return RetrievedCognition(
            kind="knowledge",
            text=f"{record.statement} Source: {record.source_description}",
            importance=record.salience.importance,
            is_core=record.salience.is_core,
        )
