"""Assembly of the limited cognitive context supplied to an NPC."""

from __future__ import annotations

from dataclasses import dataclass

from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.retrieval import (
    CognitiveRetriever,
    DeterministicCognitiveRetriever,
    RetrievalQuery,
    RetrievedCognition,
)
from living_world.perception.npc_perception_boundary import (
    DefaultNPCPerceptionBoundary,
    NPCPerceptionBoundary,
)
from living_world.state.world_state import WorldState


@dataclass(frozen=True, slots=True)
class NPCContext:
    """NPC-readable information with no engine holder or entity identifier."""

    identity: str
    self_knowledge: tuple[str, ...]
    current_perceptions: tuple[str, ...]
    core_cognition: tuple[RetrievedCognition, ...]
    retrieved_information: tuple[RetrievedCognition, ...]


class NPCContextAssembler:
    """Build and validate a holder-scoped, NPC-safe cognitive context."""

    def __init__(
        self,
        state: WorldState,
        retriever: CognitiveRetriever | None = None,
        boundary: NPCInformationBoundary | None = None,
        perception_boundary: NPCPerceptionBoundary | None = None,
    ) -> None:
        self._state = state
        self._retriever = (
            DeterministicCognitiveRetriever(state) if retriever is None else retriever
        )
        self._boundary = NPCInformationBoundary(state) if boundary is None else boundary
        self._perception_boundary = (
            DefaultNPCPerceptionBoundary()
            if perception_boundary is None
            else perception_boundary
        )

    def assemble(
        self,
        *,
        holder_id: str,
        capability_descriptions: tuple[str, ...] = (),
        query: RetrievalQuery | None = None,
        max_perceptions: int | None = None,
    ) -> NPCContext:
        if not isinstance(holder_id, str):
            raise TypeError("holder_id must be a string.")
        if not holder_id.strip():
            raise ValueError("holder_id cannot be empty.")
        holder = self._state.entities.get(holder_id)
        if holder is None:
            raise ValueError("holder_id must identify a known entity.")
        self._validate_capability_descriptions(capability_descriptions)
        self._validate_max_perceptions(max_perceptions)
        if query is not None and query.holder_id != holder_id:
            raise ValueError("Retrieval query holder_id must match context holder_id.")

        default_query = RetrievalQuery(holder_id=holder_id)
        current_perceptions = tuple(
            self._perception_boundary.visible_description(observation)
            for observation in sorted(
                (
                    observation
                    for observation in self._state.observations.values()
                    if observation.observer == holder_id
                ),
                key=lambda observation: (-observation.tick, observation.id),
            )
        )
        if max_perceptions is not None:
            current_perceptions = current_perceptions[:max_perceptions]

        context = NPCContext(
            identity=holder.name,
            self_knowledge=capability_descriptions,
            current_perceptions=current_perceptions,
            core_cognition=self._retriever.retrieve(default_query),
            retrieved_information=(
                () if query is None else self._retriever.retrieve(query)
            ),
        )
        self._boundary.validate_context(context)
        return context

    @staticmethod
    def _validate_capability_descriptions(value: object) -> None:
        if not isinstance(value, tuple):
            raise TypeError("capability_descriptions must be a tuple of prose strings.")
        for description in value:
            if not isinstance(description, str):
                raise TypeError(
                    "capability_descriptions must contain only prose strings."
                )
            if not description.strip():
                raise ValueError("capability_descriptions cannot contain empty prose.")

    @staticmethod
    def _validate_max_perceptions(value: object) -> None:
        if value is None:
            return
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("max_perceptions must be an integer or None.")
        if value < 0:
            raise ValueError("max_perceptions cannot be negative.")
