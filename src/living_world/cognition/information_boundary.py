"""Validation for values crossing into NPC-facing LLM context."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING

from living_world.cognition.retrieval import RetrievedCognition
from living_world.state.world_state import WorldState

if TYPE_CHECKING:
    from living_world.cognition.npc_context import NPCContext


class NPCInformationBoundary:
    """Reject authoritative state from an NPC-readable context projection."""

    def __init__(self, state: WorldState) -> None:
        self._state = state

    def validate_context(self, context: NPCContext) -> None:
        """Ensure context contains only validated prose and retrieval projections."""

        from living_world.cognition.npc_context import NPCContext

        if not isinstance(context, NPCContext):
            raise TypeError("NPC context must be an NPCContext.")
        self._validate_prose(context.identity, "identity")
        self._validate_prose_collection(context.self_knowledge, "self_knowledge")
        self._validate_prose_collection(
            context.current_perceptions,
            "current_perceptions",
        )
        self._validate_prose_collection(
            context.conversation_history,
            "conversation_history",
        )
        if not isinstance(context.core_cognition, tuple):
            raise TypeError("NPC context core_cognition must be a tuple.")
        if not isinstance(context.retrieved_information, tuple):
            raise TypeError("NPC context retrieved_information must be a tuple.")
        for field_name, records in (
            ("core_cognition", context.core_cognition),
            ("retrieved_information", context.retrieved_information),
        ):
            for record in records:
                if not isinstance(record, RetrievedCognition):
                    raise TypeError(
                        f"NPC context {field_name} must contain RetrievedCognition."
                    )
                self._validate_prose(record.text, f"{field_name} text")

    def validate_conversation_prose(self, value: object) -> str:
        """Validate one visible conversation item before it reaches an NPC."""

        self._validate_prose(value, "conversation prose")
        return value

    def _validate_prose_collection(self, value: object, field_name: str) -> None:
        if not isinstance(value, tuple):
            raise TypeError(f"NPC context {field_name} must be a tuple.")
        for item in value:
            self._validate_prose(item, field_name)

    def _validate_prose(self, value: object, field_name: str) -> None:
        if isinstance(value, (Mapping, WorldState)):
            raise TypeError(
                f"NPC context {field_name} cannot contain engine state or mappings."
            )
        if not isinstance(value, str):
            raise TypeError(f"NPC context {field_name} must contain prose strings.")
        if not value.strip():
            raise ValueError(f"NPC context {field_name} cannot contain empty prose.")
        if any(identifier in value for identifier in self._internal_identifiers()):
            raise ValueError(f"NPC context {field_name} cannot expose internal IDs.")
        if self._contains_authoritative_number(value):
            raise ValueError(
                f"NPC context {field_name} cannot expose authoritative numeric values."
            )

    def _internal_identifiers(self) -> tuple[str, ...]:
        collections = (
            self._state.entities,
            self._state.relationships,
            self._state.events,
            self._state.observations,
            self._state.memories,
            self._state.beliefs,
            self._state.experiences,
            self._state.npc_relationships,
            self._state.knowledge,
        )
        return tuple(
            identifier for collection in collections for identifier in collection
        )

    def _contains_authoritative_number(self, value: str) -> bool:
        return any(
            self._number_pattern(number).search(value) is not None
            for number in self._authoritative_numbers()
        )

    def _authoritative_numbers(self) -> tuple[int | float, ...]:
        return tuple(
            value
            for entity in self._state.entities.values()
            for value in self._numeric_values(entity.attributes)
        )

    def _numeric_values(self, value: object) -> tuple[int | float, ...]:
        if isinstance(value, Mapping):
            return tuple(
                number
                for item in value.values()
                for number in self._numeric_values(item)
            )
        if isinstance(value, (tuple, list, set, frozenset)):
            return tuple(
                number for item in value for number in self._numeric_values(item)
            )
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return (value,)
        return ()

    @staticmethod
    def _number_pattern(number: float) -> re.Pattern[str]:
        return re.compile(rf"(?<![\w.]){re.escape(str(number))}(?!\w|\.\d)")
