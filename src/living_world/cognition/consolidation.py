from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from living_world.core.belief import Belief, BeliefStatus
from living_world.core.experience import Experience
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.observation import Observation
from living_world.managers.belief_manager import BeliefManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.experience_manager import ExperienceManager
from living_world.managers.memory_manager import MemoryManager
from living_world.managers.observation_manager import ObservationManager
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem

DAY_LENGTH_TICKS = 24


class CognitiveConsolidator(Protocol):
    """Create holder-scoped cognitive interpretations from prior perceptions."""

    def consolidate(
        self, *, holder_id: str, through_tick: int
    ) -> tuple[Memory | Experience | Belief, ...]: ...


class SleepCognitiveConsolidator:
    """Consolidate only an NPC's completed prior calendar day while sleeping."""

    def __init__(
        self,
        *,
        entities: EntityManager,
        observations: ObservationManager,
        memories: MemoryManager,
        experiences: ExperienceManager,
        beliefs: BeliefManager,
    ) -> None:
        self._entities = entities
        self._observations = observations
        self._memories = memories
        self._experiences = experiences
        self._beliefs = beliefs

    def consolidate(
        self, *, holder_id: str, through_tick: int
    ) -> tuple[Memory | Experience | Belief, ...]:
        """Create deterministic interpretations from the preceding full day.

        A day contains 24 ticks. At tick 24 through 47 the completed prior day
        is ticks 0 through 23; observations from the current day are excluded.
        Provenance held by the created records makes repeated calls idempotent.
        """

        if not isinstance(holder_id, str):
            raise TypeError("Cognitive consolidation holder_id must be a string.")
        if not holder_id.strip():
            raise ValueError("Cognitive consolidation holder_id cannot be empty.")
        if not isinstance(through_tick, int) or isinstance(through_tick, bool):
            raise TypeError("Cognitive consolidation through_tick must be an integer.")

        holder = self._entities.get(holder_id)
        if holder is None or holder.attributes.get("active_activity") != "sleeping":
            return ()

        completed_day_end = (through_tick // DAY_LENGTH_TICKS) * DAY_LENGTH_TICKS
        if completed_day_end < DAY_LENGTH_TICKS:
            return ()

        completed_day_start = completed_day_end - DAY_LENGTH_TICKS
        observations = tuple(
            observation
            for observation in self._observations.observations_for(holder_id)
            if completed_day_start <= observation.tick < completed_day_end
        )
        ordered_observations = tuple(
            sorted(observations, key=lambda item: (item.tick, item.id))
        )
        created: list[Memory | Experience | Belief] = []

        for observation in ordered_observations:
            if self._memories.has_observation_provenance(holder_id, observation.id):
                continue
            created.append(
                self._memories.record(
                    holder_id=holder_id,
                    subject_id=observation.subject,
                    summary=f"I remember: {observation.description}",
                    salience=CognitiveSalience(importance=observation.confidence),
                    source_observation_ids=(observation.id,),
                )
            )

        observations_by_subject: defaultdict[str, list[Observation]] = defaultdict(list)
        for observation in ordered_observations:
            observations_by_subject[observation.subject].append(observation)

        for subject_id in sorted(observations_by_subject):
            subject_observations = tuple(observations_by_subject[subject_id])
            if len(subject_observations) < 2:
                continue

            source_observation_ids = tuple(
                observation.id for observation in subject_observations
            )
            if self._has_experience_provenance(holder_id, source_observation_ids):
                continue

            descriptions = " ".join(
                observation.description for observation in subject_observations
            )
            memory_ids = tuple(
                memory.id
                for observation_id in source_observation_ids
                for memory in self._memories.memories_for_observation(
                    holder_id, observation_id
                )
            )
            experience = self._experiences.record(
                holder_id=holder_id,
                subject_id=subject_id,
                summary=f"Repeated observations left this impression: {descriptions}",
                supporting_observations=source_observation_ids,
                supporting_memories=memory_ids,
                metadata={"source": "sleep_consolidation"},
                salience=CognitiveSalience(importance=0.6),
            )
            created.append(experience)

            if not self._has_belief_provenance(holder_id, source_observation_ids):
                created.append(
                    self._beliefs.record(
                        holder_id=holder_id,
                        subject_id=subject_id,
                        proposition=(
                            "I suspect, based on repeated observations: "
                            f"{descriptions}"
                        ),
                        confidence=min(
                            observation.confidence
                            for observation in subject_observations
                        ),
                        importance=0.6,
                        status=BeliefStatus.CANDIDATE,
                        supporting_observations=source_observation_ids,
                        supporting_memories=memory_ids,
                        supporting_experiences=(experience.id,),
                        metadata={"source": "sleep_consolidation_candidate"},
                        salience=CognitiveSalience(importance=0.6),
                    )
                )

        return tuple(created)

    def _has_experience_provenance(
        self, holder_id: str, observation_ids: tuple[str, ...]
    ) -> bool:
        return any(
            experience.supporting_observations == observation_ids
            for experience in self._experiences.experiences_for(holder_id)
        )

    def _has_belief_provenance(
        self, holder_id: str, observation_ids: tuple[str, ...]
    ) -> bool:
        return any(
            belief.supporting_observations == observation_ids
            for belief in self._beliefs.beliefs_for(holder_id)
        )


class CognitiveConsolidationSystem(SimulationSystem):
    """Invoke sleep consolidation through the scheduler's deterministic order."""

    def __init__(
        self, consolidator: CognitiveConsolidator, entities: EntityManager
    ) -> None:
        self._consolidator = consolidator
        self._entities = entities

    def step(self, state: WorldState) -> None:
        for entity in sorted(self._entities.all(), key=lambda item: item.id):
            if entity.attributes.get("active_activity") == "sleeping":
                self._consolidator.consolidate(
                    holder_id=entity.id,
                    through_tick=state.tick,
                )
