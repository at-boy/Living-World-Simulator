"""Untrusted local-model proposals for NPC cognition."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

from living_world.cognition.npc_context import NPCContext

_INTERNAL_RECORD_ID_PATTERN = re.compile(
    r"(?:entity|relationship|event|observation|belief|experience|memory|"
    r"knowledge|npc_relationship)_\d+"
)


@dataclass(frozen=True, slots=True)
class ActionOption:
    """A non-authoritative action vocabulary entry offered to an NPC model."""

    key: str
    description: str
    target_labels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_prose(self.key, "Action option key")
        _require_prose(self.description, "Action option description")
        object.__setattr__(
            self,
            "target_labels",
            _validated_unique_strings(
                self.target_labels, "Action option target_labels"
            ),
        )


@dataclass(frozen=True, slots=True)
class ActionRequest:
    """A model proposal; it neither validates nor applies a simulation action."""

    action_key: str
    target_label: str | None
    rationale: str
    arguments: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_prose(self.action_key, "Action request action_key")
        if self.target_label is not None:
            _require_prose(self.target_label, "Action request target_label")
        _require_prose(self.rationale, "Action request rationale")
        if not isinstance(self.arguments, Mapping):
            raise TypeError("Action request arguments must be a mapping.")
        copied_arguments: dict[str, str] = {}
        for key, value in self.arguments.items():
            _require_prose(key, "Action request argument key")
            _require_prose(value, "Action request argument value")
            copied_arguments[key] = value
        object.__setattr__(self, "arguments", MappingProxyType(copied_arguments))


@dataclass(frozen=True, slots=True)
class NPCDecision:
    """An NPC model's untrusted speech and/or action proposal."""

    spoken_text: str | None
    action_request: ActionRequest | None

    def __post_init__(self) -> None:
        if self.spoken_text is not None:
            _require_prose(self.spoken_text, "NPC decision spoken_text")
        if self.action_request is not None and not isinstance(
            self.action_request, ActionRequest
        ):
            raise TypeError(
                "NPC decision action_request must be an ActionRequest or None."
            )
        if self.spoken_text is None and self.action_request is None:
            raise ValueError("NPC decision must contain speech or an action request.")


class NPCCognitionClient(Protocol):
    """Boundary for local, proposal-only NPC reasoning providers."""

    @property
    def provider_name(self) -> str:
        """Return the local provider identifier."""

    def decide(
        self,
        context: NPCContext,
        actions: tuple[ActionOption, ...],
    ) -> NPCDecision:
        """Return an untrusted proposal based only on the filtered context."""


class NPCCognitionClientError(Exception):
    """Raised when a local cognition provider cannot return a valid proposal."""


class NPCCognitionInvalidResponseError(NPCCognitionClientError):
    """Raised when a local provider response violates the decision schema."""


def _require_prose(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    if _INTERNAL_RECORD_ID_PATTERN.search(value) is not None:
        raise ValueError(f"{field_name} cannot contain an internal record ID.")


def _validated_unique_strings(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple of strings.")
    for item in value:
        _require_prose(item, field_name)
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must contain unique strings.")
    return value
