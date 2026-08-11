"""Validation for the NPC-readable projection of an observation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Protocol

from living_world.core.observation import Observation
from living_world.perception.perception_context import PerceptionContext


class NPCPerceptionBoundary(Protocol):
    """Projects an observation into the prose an NPC may receive."""

    def visible_description(
        self,
        observation: Observation,
        *,
        context: PerceptionContext | None = None,
    ) -> str:
        """Validate and return only an NPC-readable observation description."""


class DefaultNPCPerceptionBoundary:
    """Reject engine-only wording from an observation's visible projection."""

    _RAW_ATTRIBUTE_PATTERN = re.compile(
        r"\b[A-Za-z_][A-Za-z0-9_.]*\s*(?:=|:=)\s*[^\s,;]+"
    )
    _FORBIDDEN_TERMS = (
        "evidence",
        "metadata",
        "subject_attributes",
        "observer_capabilities",
        "hidden state",
        "hidden-state",
        "engine state",
        "engine-state",
        "worldstate",
        "world_state",
        "entitymanager",
        "entity_manager",
        "perceptioncontext",
        "perception_context",
        "observationmanager",
        "observation_manager",
    )

    def visible_description(
        self,
        observation: Observation,
        *,
        context: PerceptionContext | None = None,
    ) -> str:
        """Validate and return the prose projection without engine data."""

        if not isinstance(observation, Observation):
            raise TypeError("NPC perception must be an Observation.")
        if not isinstance(observation.description, str):
            raise TypeError("Observation description must be a string.")

        description = observation.description.strip()
        if not description:
            raise ValueError("Observation description cannot be empty.")

        self._reject_internal_ids(
            description,
            (observation.id, observation.observer, observation.subject),
        )
        self._reject_forbidden_constructs(description)

        if context is not None:
            if not isinstance(context, PerceptionContext):
                raise TypeError("Perception context must be a PerceptionContext.")
            self._reject_internal_ids(
                description,
                (context.observer.id, context.subject.id),
            )
            self._reject_protected_numbers(description, context)

        return description

    def _reject_forbidden_constructs(self, description: str) -> None:
        if self._RAW_ATTRIBUTE_PATTERN.search(description) is not None:
            raise ValueError("Observation description exposes raw attribute notation.")
        normalized = description.casefold()
        if any(term in normalized for term in self._FORBIDDEN_TERMS):
            raise ValueError("Observation description exposes engine-only wording.")

    @staticmethod
    def _reject_internal_ids(description: str, identifiers: tuple[str, ...]) -> None:
        for identifier in identifiers:
            if identifier and DefaultNPCPerceptionBoundary._contains_exact_value(
                description, identifier
            ):
                raise ValueError("Observation description exposes an internal ID.")

    def _reject_protected_numbers(
        self,
        description: str,
        context: PerceptionContext,
    ) -> None:
        protected_values = (
            *self._numeric_values(context.subject.attributes),
            *self._numeric_values(context.capabilities),
        )
        for value in protected_values:
            if self._contains_exact_number(description, value):
                raise ValueError(
                    "Observation description exposes an authoritative numeric value."
                )

    @classmethod
    def _numeric_values(cls, value: object) -> tuple[int | float, ...]:
        if isinstance(value, Mapping):
            return tuple(
                number
                for nested_value in value.values()
                for number in cls._numeric_values(nested_value)
            )
        if isinstance(value, (tuple, list, set, frozenset)):
            return tuple(
                number
                for nested_value in value
                for number in cls._numeric_values(nested_value)
            )
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return (value,)
        return ()

    @staticmethod
    def _contains_exact_value(description: str, value: str) -> bool:
        return (
            re.search(
                rf"(?<![A-Za-z0-9_]){re.escape(value)}(?![A-Za-z0-9_])",
                description,
            )
            is not None
        )

    @staticmethod
    def _contains_exact_number(description: str, value: float) -> bool:
        return (
            re.search(
                rf"(?<![\w.]){re.escape(str(value))}(?!\w|\.\d)",
                description,
            )
            is not None
        )
