from __future__ import annotations

from living_world.core.experience import Experience
from living_world.state.world_state import WorldState


class ExperienceManager:
    """Records immutable NPC experiences learned through lived interaction."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._next_experience_id = 1

    def add(self, experience: Experience) -> None:
        self._state.experiences[experience.id] = experience

    def record(
        self,
        *,
        holder_id: str,
        subject_id: str,
        summary: str,
        supporting_observations: tuple[str, ...] | None = None,
        supporting_memories: tuple[str, ...] | None = None,
        supporting_beliefs: tuple[str, ...] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Experience:
        """Record a new immutable experience."""

        if not holder_id.strip():
            raise ValueError("Experience holder_id cannot be empty.")

        if not subject_id.strip():
            raise ValueError("Experience subject_id cannot be empty.")

        if not summary.strip():
            raise ValueError("Experience summary cannot be empty.")

        experience = Experience(
            id=self._generate_id(),
            tick=self._state.tick,
            holder_id=holder_id,
            subject_id=subject_id,
            summary=summary,
            supporting_observations=supporting_observations or (),
            supporting_memories=supporting_memories or (),
            supporting_beliefs=supporting_beliefs or (),
            metadata=metadata or {},
        )

        self.add(experience)
        return experience

    def generate_from_observations(
        self,
        *,
        holder_id: str,
        subject_id: str,
        observations: tuple[str, ...],
        summary: str,
        supporting_memories: tuple[str, ...] | None = None,
        supporting_beliefs: tuple[str, ...] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Experience:
        """Create an experience from repeated or consolidated observations."""

        return self.record(
            holder_id=holder_id,
            subject_id=subject_id,
            summary=summary,
            supporting_observations=observations,
            supporting_memories=supporting_memories,
            supporting_beliefs=supporting_beliefs,
            metadata=metadata,
        )

    def consolidate_repeated_observations(
        self,
        *,
        holder_id: str,
        subject_id: str,
        observations: tuple[str, ...],
        threshold: int = 2,
        summary: str | None = None,
        supporting_memories: tuple[str, ...] | None = None,
        supporting_beliefs: tuple[str, ...] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Experience:
        """Create an experience when repeated observations point to a stable pattern."""

        unique_observations = tuple(dict.fromkeys(observations))
        if len(unique_observations) < threshold:
            raise ValueError(
                f"At least {threshold} distinct observations are required to create an experience."
            )

        final_summary = summary or (
            "Repeated observations of subject "
            f"{subject_id} suggest a consistent pattern worth remembering."
        )

        return self.record(
            holder_id=holder_id,
            subject_id=subject_id,
            summary=final_summary,
            supporting_observations=unique_observations,
            supporting_memories=supporting_memories,
            supporting_beliefs=supporting_beliefs,
            metadata=metadata,
        )

    def get(self, experience_id: str) -> Experience | None:
        return self._state.experiences.get(experience_id)

    def experiences_for(self, holder_id: str) -> tuple[Experience, ...]:
        return tuple(
            experience
            for experience in self._state.experiences.values()
            if experience.holder_id == holder_id
        )

    def experiences_about(self, subject_id: str) -> tuple[Experience, ...]:
        return tuple(
            experience
            for experience in self._state.experiences.values()
            if experience.subject_id == subject_id
        )

    def experiences_supporting_belief(
        self,
        belief_id: str,
    ) -> tuple[Experience, ...]:
        return tuple(
            experience
            for experience in self._state.experiences.values()
            if belief_id in experience.supporting_beliefs
        )

    def history_for(self, experience_id: str) -> tuple[object, ...]:
        experience = self.get(experience_id)
        if experience is None:
            return ()

        return experience.history

    def all(self) -> tuple[Experience, ...]:
        return tuple(self._state.experiences.values())

    def _generate_id(self) -> str:
        while True:
            experience_id = f"experience_{self._next_experience_id:06d}"
            self._next_experience_id += 1

            if experience_id not in self._state.experiences:
                return experience_id
