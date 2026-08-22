"""Validation for values crossing into NPC-facing LLM context."""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from living_world.cognition.retrieval import RetrievedCognition
from living_world.state.world_state import WorldState

if TYPE_CHECKING:
    from living_world.cognition.npc_context import NPCContext


class NPCInformationBoundary:
    """Reject authoritative state from an NPC-readable context projection."""

    _COORDINATE_NOTATION_PATTERN = re.compile(r"(?<![\w.])-?\d+\s*,\s*-?\d+(?![\w.])")
    _SPATIAL_LABEL_NOTATION_PATTERN = re.compile(
        r"\b(?:x|y|width|height)\s*[-+]?"
        r"(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"
        r"(?!\w|\.\d)",
        re.IGNORECASE,
    )
    _PRIVILEGED_SPATIAL_PATTERN = re.compile(
        r"\b(?:coordinates|coordinate (?:axis|notation|pair|value)|bounds?|"
        r"placement records?|overlap polic(?:y|ies))\b"
        r"|\b(?:placement_record|overlap_policy)\b",
        re.IGNORECASE,
    )
    _NEED_NUMERIC_NOTATION_PATTERN = re.compile(
        r"\b(?:need|pressure|available|required|balance|threshold|window)\s*"
        r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?(?!\w|\.\d)",
        re.IGNORECASE,
    )
    _NUMERIC_LITERAL_PATTERN = re.compile(
        r"(?<![\w.+-])[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?" r"(?!\w|\.\d)"
    )

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
        if self._COORDINATE_NOTATION_PATTERN.search(value) is not None:
            raise ValueError(
                f"NPC context {field_name} cannot expose raw coordinate notation."
            )
        if self._SPATIAL_LABEL_NOTATION_PATTERN.search(value) is not None:
            raise ValueError(
                f"NPC context {field_name} cannot expose raw coordinate notation."
            )
        if self._PRIVILEGED_SPATIAL_PATTERN.search(value) is not None:
            raise ValueError(
                f"NPC context {field_name} cannot expose privileged spatial terms."
            )
        if self._NEED_NUMERIC_NOTATION_PATTERN.search(value) is not None:
            raise ValueError(
                f"NPC context {field_name} cannot expose authoritative numeric values."
            )
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
            self._state.placements,
            self._state.need_definitions,
            self._state.need_states,
            self._state.consumption_policies,
            self._state.consumption_states,
            self._state.storage_policies,
            self._state.storage_states,
            self._state.maintenance_policies,
            self._state.maintenance_states,
            self._state.work_definitions,
            self._state.work_states,
            self._state.work_reservations,
        )
        return tuple(
            identifier for collection in collections for identifier in collection
        )

    def _contains_authoritative_number(self, value: str) -> bool:
        authoritative = {
            Decimal(str(number)) for number in self._authoritative_numbers()
        }
        for match in self._NUMERIC_LITERAL_PATTERN.finditer(value):
            try:
                if Decimal(match.group()) in authoritative:
                    return True
            except InvalidOperation:
                continue
        return False

    def _authoritative_numbers(self) -> tuple[int | float, ...]:
        entity_numbers = tuple(
            value
            for entity in self._state.entities.values()
            for value in self._numeric_values(entity.attributes)
        )
        spatial_numbers = tuple(
            value
            for placement in self._state.placements.values()
            for value in self._numeric_values(placement.geometry)
        )
        need_numbers = tuple(
            number
            for definition in self._state.need_definitions.values()
            for number in (
                definition.requirement_per_person,
                definition.secure_maximum,
                definition.strained_maximum,
                definition.assessment_window_ticks,
            )
        ) + tuple(
            number
            for need_state in self._state.need_states.values()
            for assessment in need_state.history
            for number in (
                assessment.available,
                assessment.required,
                assessment.balance,
                assessment.pressure,
            )
            if number is not None
        )
        consequence_numbers = tuple(
            number
            for collections in (
                self._state.consumption_policies.values(),
                self._state.consumption_states.values(),
                self._state.storage_policies.values(),
                self._state.storage_states.values(),
                self._state.maintenance_policies.values(),
                self._state.maintenance_states.values(),
            )
            for record in collections
            for number in self._numeric_values(record)
        )
        work_numbers = tuple(
            number
            for collections in (
                self._state.work_definitions.values(),
                self._state.work_states.values(),
                self._state.work_reservations.values(),
            )
            for record in collections
            for number in self._numeric_values(record)
        )
        return (
            entity_numbers
            + spatial_numbers
            + need_numbers
            + consequence_numbers
            + work_numbers
        )

    def _numeric_values(self, value: object) -> tuple[int | float, ...]:
        from dataclasses import fields, is_dataclass

        from living_world.spatial.model import Bounds, Point

        if isinstance(value, Point):
            return value.x, value.y
        if isinstance(value, Bounds):
            return value.x, value.y, value.width, value.height
        if isinstance(value, Mapping):
            return tuple(
                number
                for item in value.values()
                for number in self._numeric_values(item)
            )
        if is_dataclass(value):
            return tuple(
                number
                for field in fields(value)
                for number in self._numeric_values(getattr(value, field.name))
            )
        if isinstance(value, (tuple, list, set, frozenset)):
            return tuple(
                number for item in value for number in self._numeric_values(item)
            )
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return (value,)
        return ()
