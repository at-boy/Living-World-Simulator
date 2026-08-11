"""Ephemeral, engine-owned coordination for bounded NPC meetings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from living_world.cognition.conversation import ConversationResult, ConversationService


@dataclass(frozen=True, slots=True)
class MeetingRequest:
    """Engine-side request for a bounded, non-persistent NPC meeting."""

    requester_id: str
    invitee_ids: tuple[str, ...]
    topic: str
    max_turns: int
    called_speaker_ids: tuple[str, ...] = ()
    participant_self_knowledge: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    collect_proposals: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.requester_id, "requester_id")
        _validate_identifier_tuple(
            self.invitee_ids, "invitee_ids", require_non_empty=True
        )
        _require_prose(self.topic, "topic")
        _validate_max_turns(self.max_turns)
        _validate_identifier_tuple(
            self.called_speaker_ids,
            "called_speaker_ids",
            require_non_empty=False,
        )
        object.__setattr__(
            self,
            "participant_self_knowledge",
            _frozen_self_knowledge(self.participant_self_knowledge),
        )
        if not isinstance(self.collect_proposals, bool):
            raise TypeError("collect_proposals must be a bool.")


class MeetingService:
    """Delegate a validated engine-side meeting request to conversation."""

    def __init__(self, conversation_service: ConversationService) -> None:
        if not isinstance(conversation_service, ConversationService):
            raise TypeError("conversation_service must be a ConversationService.")
        self._conversation_service = conversation_service

    def conduct(self, request: MeetingRequest) -> ConversationResult:
        """Conduct one ephemeral meeting without creating meeting state."""

        if not isinstance(request, MeetingRequest):
            raise TypeError("request must be a MeetingRequest.")
        self._validate_membership(request)
        participant_ids = (request.requester_id, *request.invitee_ids)
        return self._conversation_service.conduct(
            participant_ids=participant_ids,
            topic=request.topic,
            max_turns=request.max_turns,
            called_speaker_ids=request.called_speaker_ids,
            participant_self_knowledge=request.participant_self_knowledge,
            collect_proposals=request.collect_proposals,
        )

    def _validate_membership(self, request: MeetingRequest) -> None:
        if request.requester_id in request.invitee_ids:
            raise ValueError("requester_id cannot invite itself.")
        if len(request.invitee_ids) != len(set(request.invitee_ids)):
            raise ValueError("invitee_ids must be distinct.")
        participant_ids = (request.requester_id, *request.invitee_ids)
        if any(
            not self._conversation_service.has_known_entity(participant_id)
            for participant_id in participant_ids
        ):
            raise ValueError(
                "requester_id and invitee_ids must identify known entities."
            )


def _require_identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _validate_identifier_tuple(
    value: object,
    field_name: str,
    *,
    require_non_empty: bool,
) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple of entity IDs.")
    if require_non_empty and not value:
        raise ValueError(f"{field_name} cannot be empty.")
    for item in value:
        _require_identifier(item, field_name)


def _require_prose(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _validate_max_turns(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("max_turns must be a non-boolean integer.")
    if value < 0:
        raise ValueError("max_turns cannot be negative.")


def _frozen_self_knowledge(value: object) -> Mapping[str, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        raise TypeError("participant_self_knowledge must be a mapping.")
    copied: dict[str, tuple[str, ...]] = {}
    for participant_id, knowledge in value.items():
        _require_identifier(participant_id, "participant_self_knowledge key")
        if not isinstance(knowledge, tuple):
            raise TypeError("participant_self_knowledge values must be prose tuples.")
        if not knowledge:
            raise ValueError(
                "participant_self_knowledge values cannot be empty tuples."
            )
        for prose in knowledge:
            _require_prose(prose, "participant_self_knowledge prose")
        copied[participant_id] = tuple(knowledge)
    return MappingProxyType(copied)
