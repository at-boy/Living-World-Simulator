"""Lifecycle manager for NPC-held knowledge claims."""

from __future__ import annotations

from collections.abc import Mapping

from living_world.core.knowledge import Knowledge
from living_world.core.memory import CognitiveSalience
from living_world.state.world_state import WorldState


class KnowledgeManager:
    """Own the lifecycle of immutable, holder-scoped knowledge claims."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._next_knowledge_id = 1

    def add(self, knowledge: Knowledge) -> None:
        """Register a fully constructed knowledge record."""

        self._state.knowledge[knowledge.id] = knowledge

    def record(
        self,
        *,
        holder_id: str,
        subject_id: str,
        statement: str,
        source_description: str,
        salience: CognitiveSalience,
        supporting_observations: tuple[str, ...] = (),
        supporting_memories: tuple[str, ...] = (),
        supporting_experiences: tuple[str, ...] = (),
        metadata: Mapping[str, object] | None = None,
    ) -> Knowledge:
        """Record a source-attributed claim without asserting world truth."""

        knowledge = Knowledge(
            id=self._generate_id(),
            tick=self._state.tick,
            holder_id=holder_id,
            subject_id=subject_id,
            statement=statement,
            source_description=source_description,
            salience=salience,
            supporting_observations=supporting_observations,
            supporting_memories=supporting_memories,
            supporting_experiences=supporting_experiences,
            metadata={} if metadata is None else metadata,
        )
        self.add(knowledge)
        return knowledge

    def get(self, knowledge_id: str) -> Knowledge | None:
        """Return one knowledge record by its internal identifier."""

        return self._state.knowledge.get(knowledge_id)

    def knowledge_for(self, holder_id: str) -> tuple[Knowledge, ...]:
        """Return only the knowledge claims held by the requested NPC."""

        return tuple(
            knowledge
            for knowledge in self._state.knowledge.values()
            if knowledge.holder_id == holder_id
        )

    def all(self) -> tuple[Knowledge, ...]:
        """Return all knowledge records for engine-side inspection only."""

        return tuple(self._state.knowledge.values())

    def _generate_id(self) -> str:
        while True:
            knowledge_id = f"knowledge_{self._next_knowledge_id:06d}"
            self._next_knowledge_id += 1
            if knowledge_id not in self._state.knowledge:
                return knowledge_id
