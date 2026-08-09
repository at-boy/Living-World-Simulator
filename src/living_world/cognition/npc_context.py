from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from living_world.core.entity import Entity
from living_world.state.world_state import WorldState


@dataclass(frozen=True, slots=True)
class NPCContext:
    """NPC-readable context assembled from filtered cognitive information."""

    holder_id: str
    identity: str
    capabilities: Mapping[str, object] = field(default_factory=dict)
    current_perceptions: tuple[str, ...] = ()
    retrieved_information: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capabilities",
            MappingProxyType(dict(self.capabilities)),
        )
        object.__setattr__(
            self,
            "current_perceptions",
            tuple(self.current_perceptions),
        )
        object.__setattr__(
            self,
            "retrieved_information",
            tuple(dict.fromkeys(self.retrieved_information)),
        )


class NPCContextAssembler:
    """Assembles NPC-visible context from observations, beliefs, and experiences."""

    def __init__(self, state: WorldState) -> None:
        self._state = state

    def assemble(
        self,
        *,
        holder_id: str,
        capabilities: Mapping[str, object] | None = None,
        max_items: int | None = None,
    ) -> NPCContext:
        if not holder_id.strip():
            raise ValueError("holder_id cannot be empty.")

        holder = self._state.entities.get(holder_id)
        identity = holder.name if isinstance(holder, Entity) else holder_id

        capability_map = dict(capabilities or {})
        current_perceptions = self._current_perceptions(holder_id)
        retrieved_information = self._retrieved_information(holder_id)

        if max_items is not None:
            current_perceptions = current_perceptions[:max_items]
            retrieved_information = retrieved_information[:max_items]

        return NPCContext(
            holder_id=holder_id,
            identity=identity,
            capabilities=capability_map,
            current_perceptions=current_perceptions,
            retrieved_information=retrieved_information,
        )

    def _current_perceptions(self, holder_id: str) -> tuple[str, ...]:
        observations = tuple(
            observation.description
            for observation in self._state.observations.values()
            if observation.observer == holder_id
        )
        return tuple(sorted(observations, key=self._sort_by_tick_desc))

    def _retrieved_information(self, holder_id: str) -> tuple[str, ...]:
        observations = tuple(
            observation.description
            for observation in self._state.observations.values()
            if observation.observer == holder_id
        )
        beliefs = tuple(
            belief.proposition
            for belief in self._state.beliefs.values()
            if belief.holder_id == holder_id
        )
        experiences = tuple(
            experience.summary
            for experience in self._state.experiences.values()
            if experience.holder_id == holder_id
        )

        combined = observations + beliefs + experiences
        unique = tuple(dict.fromkeys(combined))

        return tuple(sorted(unique, key=self._sort_by_tick_desc))

    @staticmethod
    def _sort_by_tick_desc(value: str) -> str:
        return value
