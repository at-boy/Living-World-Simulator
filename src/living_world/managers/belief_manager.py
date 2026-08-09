from __future__ import annotations

from living_world.core.belief import Belief, BeliefHistoryEntry, BeliefStatus
from living_world.core.experience import Experience
from living_world.state.world_state import WorldState


class BeliefManager:
    """Records immutable NPC beliefs about the world."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._next_belief_id = 1

    def add(self, belief: Belief) -> None:
        self._state.beliefs[belief.id] = belief

    def record(
        self,
        *,
        holder_id: str,
        subject_id: str,
        proposition: str,
        confidence: float,
        importance: float,
        status: BeliefStatus | str,
        supporting_observations: tuple[str, ...] | None = None,
        supporting_memories: tuple[str, ...] | None = None,
        supporting_experiences: tuple[str, ...] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Belief:
        """Record a new immutable belief."""

        belief = Belief(
            id=self._generate_id(),
            tick=self._state.tick,
            holder_id=holder_id,
            subject_id=subject_id,
            proposition=proposition,
            confidence=confidence,
            importance=importance,
            status=status,
            supporting_observations=supporting_observations or (),
            supporting_memories=supporting_memories or (),
            supporting_experiences=supporting_experiences or (),
            metadata=metadata or {},
        )

        self.add(belief)
        return belief

    def record_from_experience(
        self,
        *,
        experience: Experience,
        proposition: str,
        confidence: float,
        importance: float,
        status: BeliefStatus | str,
        supporting_observations: tuple[str, ...] | None = None,
        supporting_memories: tuple[str, ...] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Belief:
        """Create a belief from a lived experience while retaining the source link."""

        return self.record(
            holder_id=experience.holder_id,
            subject_id=experience.subject_id,
            proposition=proposition,
            confidence=confidence,
            importance=importance,
            status=status,
            supporting_observations=supporting_observations
            or experience.supporting_observations,
            supporting_memories=supporting_memories or experience.supporting_memories,
            supporting_experiences=(experience.id,),
            metadata={
                **(metadata or {}),
                "source": "experience",
                "experience_id": experience.id,
            },
        )

    def get(self, belief_id: str) -> Belief | None:
        return self._state.beliefs.get(belief_id)

    def beliefs_for(self, holder_id: str) -> tuple[Belief, ...]:
        return tuple(
            belief
            for belief in self._state.beliefs.values()
            if belief.holder_id == holder_id
        )

    def beliefs_about(self, subject_id: str) -> tuple[Belief, ...]:
        return tuple(
            belief
            for belief in self._state.beliefs.values()
            if belief.subject_id == subject_id
        )

    def beliefs_supporting_observation(
        self,
        observation_id: str,
    ) -> tuple[Belief, ...]:
        return tuple(
            belief
            for belief in self._state.beliefs.values()
            if observation_id in belief.supporting_observations
        )

    def beliefs_supporting_memory(
        self,
        memory_id: str,
    ) -> tuple[Belief, ...]:
        return tuple(
            belief
            for belief in self._state.beliefs.values()
            if memory_id in belief.supporting_memories
        )

    def beliefs_supporting_experience(
        self,
        experience_id: str,
    ) -> tuple[Belief, ...]:
        return tuple(
            belief
            for belief in self._state.beliefs.values()
            if experience_id in belief.supporting_experiences
        )

    def history_for(self, belief_id: str) -> tuple[BeliefHistoryEntry, ...]:
        belief = self.get(belief_id)
        if belief is None:
            return ()

        return belief.history

    def all(self) -> tuple[Belief, ...]:
        return tuple(self._state.beliefs.values())

    def _generate_id(self) -> str:
        while True:
            belief_id = f"belief_{self._next_belief_id:06d}"
            self._next_belief_id += 1

            if belief_id not in self._state.beliefs:
                return belief_id
