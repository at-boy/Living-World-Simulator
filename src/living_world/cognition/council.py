"""Bounded, agenda-driven council coordination without governance authority."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from living_world.cognition.action_resolution import (
    ActionResolution,
    NPCActionResolver,
)
from living_world.cognition.conversation import ConversationResult
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.meeting import MeetingRequest, MeetingService
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCCognitionClientError,
)
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.state.world_state import WorldState


@dataclass(frozen=True, slots=True)
class CouncilAgenda:
    """Engine-offered topic and non-authoritative action vocabulary."""

    topic: str
    action_options: tuple[ActionOption, ...]

    def __post_init__(self) -> None:
        _prose(self.topic, "topic")
        _actions(self.action_options, "action_options")


@dataclass(frozen=True, slots=True)
class CouncilCall:
    """Ephemeral engine-side request to convene one council discussion."""

    caller_id: str
    organization_id: str
    invited_participant_ids: tuple[str, ...]
    agenda: CouncilAgenda
    max_rounds: int
    called_speaker_ids: tuple[str, ...] = ()
    participant_self_knowledge: Mapping[str, tuple[str, ...]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _identifier(self.caller_id, "caller_id")
        _identifier(self.organization_id, "organization_id")
        _identifiers(self.invited_participant_ids, "invited_participant_ids", True)
        if not isinstance(self.agenda, CouncilAgenda):
            raise TypeError("agenda must be a CouncilAgenda.")
        _turns(self.max_rounds)
        _identifiers(self.called_speaker_ids, "called_speaker_ids", False)
        object.__setattr__(
            self,
            "participant_self_knowledge",
            _knowledge(self.participant_self_knowledge),
        )


@dataclass(frozen=True, slots=True)
class CouncilAttendance:
    """Safe, limited record of one invitee's attendance selection."""

    participant_label: str
    attending: bool
    delegates_to_majority: bool

    def __post_init__(self) -> None:
        _prose(self.participant_label, "participant_label")
        if not isinstance(self.attending, bool) or not isinstance(
            self.delegates_to_majority, bool
        ):
            raise TypeError("attendance flags must be bool values.")
        if self.attending and self.delegates_to_majority:
            raise ValueError("attending participants cannot delegate to a majority.")


@dataclass(frozen=True, slots=True)
class CouncilResult:
    """Bounded social result plus the ordinary action-gateway result."""

    attendance: tuple[CouncilAttendance, ...]
    conversation: ConversationResult
    majority_proposal: ActionRequest | None
    resolutions: tuple[ActionResolution, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.attendance, tuple) or not all(
            isinstance(item, CouncilAttendance) for item in self.attendance
        ):
            raise TypeError("attendance must be a tuple of CouncilAttendance values.")
        if not isinstance(self.conversation, ConversationResult):
            raise TypeError("conversation must be a ConversationResult.")
        if self.majority_proposal is not None and not isinstance(
            self.majority_proposal, ActionRequest
        ):
            raise TypeError("majority_proposal must be an ActionRequest or None.")
        if not isinstance(self.resolutions, tuple) or not all(
            isinstance(item, ActionResolution) for item in self.resolutions
        ):
            raise TypeError("resolutions must be a tuple of ActionResolution values.")


class _AttendanceHandler:
    """Validate attendance selections without changing world state or events."""

    def __init__(self, eligible_ids: tuple[str, ...]) -> None:
        self._eligible_ids = eligible_ids

    def supports(self, action_key: str) -> bool:
        return action_key in {"attend_council", "decline_council"}

    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        if actor_id not in self._eligible_ids:
            return ActionResolution(False, "NPC is not eligible for this council.")
        return ActionResolution(True, "Council attendance selection accepted.")

    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        return ActionResolution(True, "Council attendance selection recorded.")


class CouncilService:
    """Coordinate attendance and dialogue while retaining engine action authority."""

    def __init__(
        self,
        meeting_service: MeetingService,
        context_assembler: NPCContextAssembler,
        decision_engine: DecisionEngine,
        action_resolver: NPCActionResolver,
        state: WorldState,
    ) -> None:
        if not isinstance(meeting_service, MeetingService):
            raise TypeError("meeting_service must be a MeetingService.")
        if not isinstance(context_assembler, NPCContextAssembler):
            raise TypeError("context_assembler must be an NPCContextAssembler.")
        if not isinstance(decision_engine, DecisionEngine):
            raise TypeError("decision_engine must be a DecisionEngine.")
        if not isinstance(action_resolver, NPCActionResolver):
            raise TypeError("action_resolver must be an NPCActionResolver.")
        if not isinstance(state, WorldState):
            raise TypeError("state must be a WorldState.")
        self._meetings = meeting_service
        self._contexts = context_assembler
        self._decisions = decision_engine
        self._resolver = action_resolver
        self._state = state

    def convene(self, *, call: CouncilCall) -> CouncilResult:
        """Conduct one council; only a strict agenda majority reaches the gateway."""

        if not isinstance(call, CouncilCall):
            raise TypeError("call must be a CouncilCall.")
        participant_ids = (call.caller_id, *call.invited_participant_ids)
        self._validate_eligible(participant_ids, call.organization_id)
        if call.caller_id in call.invited_participant_ids or len(
            participant_ids
        ) != len(set(participant_ids)):
            raise ValueError("caller and invited participants must be distinct.")
        self_knowledge = self._validated_self_knowledge(
            participant_ids, call.participant_self_knowledge
        )
        labels = self._labels(participant_ids)
        attendance_actions = (
            ActionOption("attend_council", "Attend this council discussion."),
            ActionOption(
                "decline_council", "Decline and delegate to the attendee majority."
            ),
        )
        attendance_resolver = NPCActionResolver(
            attendance_actions, (_AttendanceHandler(participant_ids),)
        )
        attendance: list[CouncilAttendance] = [
            CouncilAttendance(labels[call.caller_id], True, False)
        ]
        attending = [call.caller_id]
        invitation = self._contexts.validate_conversation_prose(
            f"Council invitation from {labels[call.caller_id]}: {call.agenda.topic}"
        )
        for invitee_id in call.invited_participant_ids:
            context = self._contexts.assemble(
                holder_id=invitee_id,
                capability_descriptions=self_knowledge.get(invitee_id, ()),
                conversation_history=(invitation,),
            )
            try:
                decision = self._decisions.decide(context, attendance_actions)
            except NPCCognitionClientError:
                request = None
            except (TypeError, ValueError):
                # This narrow decision boundary treats an invalid direct client
                # response as unavailable, without masking engine validation.
                request = None
            else:
                request = decision.action_request
            resolution = (
                ActionResolution(False, "No attendance selection.")
                if request is None
                else attendance_resolver.resolve(actor_id=invitee_id, request=request)
            )
            is_attending = (
                resolution.accepted
                and request is not None
                and request.action_key == "attend_council"
            )
            delegates = (
                resolution.accepted
                and request is not None
                and request.action_key == "decline_council"
            )
            attendance.append(
                CouncilAttendance(labels[invitee_id], is_attending, delegates)
            )
            if is_attending:
                attending.append(invitee_id)
        if len(attending) == 1:
            return CouncilResult(
                tuple(attendance),
                ConversationResult(turns=(), resolutions=()),
                None,
                (),
            )
        schedule = self._schedule(
            call.called_speaker_ids, tuple(attending), call.max_rounds
        )
        conversation = self._meetings.conduct(
            MeetingRequest(
                requester_id=call.caller_id,
                invitee_ids=tuple(attending[1:]),
                topic=call.agenda.topic,
                max_turns=call.max_rounds,
                called_speaker_ids=schedule,
                participant_self_knowledge={
                    key: value
                    for key, value in self_knowledge.items()
                    if key in attending
                },
                collect_proposals=True,
            )
        )
        majority = self._majority(
            conversation, call.agenda.action_options, len(attending)
        )
        resolutions = (
            ()
            if majority is None
            else (self._resolver.resolve(actor_id=call.caller_id, request=majority),)
        )
        return CouncilResult(tuple(attendance), conversation, majority, resolutions)

    def _validate_eligible(
        self,
        participant_ids: tuple[str, ...],
        organization_id: str,
    ) -> None:
        if organization_id not in self._state.entities:
            raise ValueError("organization_id must identify a known entity.")
        for participant_id in participant_ids:
            if participant_id not in self._state.entities:
                raise ValueError("council participants must identify known entities.")
            if not any(
                relationship.kind == "member_of"
                and relationship.source_id == participant_id
                and relationship.target_id == organization_id
                for relationship in self._state.relationships.values()
            ):
                raise ValueError("council participants must be organization members.")

    def _labels(self, participant_ids: tuple[str, ...]) -> dict[str, str]:
        labels = {
            participant_id: self._state.entities[participant_id].name
            for participant_id in participant_ids
        }
        if len(set(labels.values())) != len(labels):
            raise ValueError("council participants must have distinct display labels.")
        return labels

    def _validated_self_knowledge(
        self,
        participant_ids: tuple[str, ...],
        knowledge: Mapping[str, tuple[str, ...]],
    ) -> dict[str, tuple[str, ...]]:
        """Validate engine perspectives before making any invitation request."""

        if any(participant_id not in participant_ids for participant_id in knowledge):
            raise ValueError(
                "participant_self_knowledge keys must identify participants."
            )
        return {
            participant_id: tuple(
                self._contexts.validate_conversation_prose(prose)
                for prose in prose_items
            )
            for participant_id, prose_items in knowledge.items()
        }

    @staticmethod
    def _schedule(
        called: tuple[str, ...], attending: tuple[str, ...], max_rounds: int
    ) -> tuple[str, ...]:
        if not called:
            return ()
        if any(identifier not in attending for identifier in called):
            raise ValueError("called speakers must attend the council.")
        if len(called) > max_rounds:
            raise ValueError("called speakers cannot exceed max_rounds.")
        return called

    @staticmethod
    def _majority(
        conversation: ConversationResult,
        actions: tuple[ActionOption, ...],
        attendee_count: int,
    ) -> ActionRequest | None:
        first: dict[str, ActionRequest] = {}
        for proposal in conversation.proposals:
            if proposal.speaker_label not in first and any(
                option.key == proposal.action_request.action_key for option in actions
            ):
                first[proposal.speaker_label] = proposal.action_request
        groups: Counter[tuple[str, str | None, tuple[tuple[str, str], ...]]] = Counter()
        choices: dict[
            tuple[str, str | None, tuple[tuple[str, str], ...]], ActionRequest
        ] = {}
        for request in first.values():
            key = (
                request.action_key,
                request.target_label,
                tuple(sorted(request.arguments.items())),
            )
            groups[key] += 1
            choices.setdefault(key, request)
        winners = [key for key, count in groups.items() if count > attendee_count / 2]
        return None if len(winners) != 1 else choices[winners[0]]


def _identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _identifiers(value: object, field_name: str, nonempty: bool) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple of entity IDs.")
    if nonempty and not value:
        raise ValueError(f"{field_name} cannot be empty.")
    for item in value:
        _identifier(item, field_name)


def _prose(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _turns(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("max_rounds must be a non-boolean integer.")
    if value < 0:
        raise ValueError("max_rounds cannot be negative.")


def _actions(value: object, field_name: str) -> None:
    if (
        not isinstance(value, tuple)
        or not value
        or not all(isinstance(item, ActionOption) for item in value)
    ):
        raise TypeError(
            f"{field_name} must be a non-empty tuple of ActionOption values."
        )
    if len({item.key for item in value}) != len(value):
        raise ValueError(f"{field_name} must have unique action keys.")


def _knowledge(value: object) -> Mapping[str, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        raise TypeError("participant_self_knowledge must be a mapping.")
    copied: dict[str, tuple[str, ...]] = {}
    for key, prose in value.items():
        _identifier(key, "participant_self_knowledge key")
        if not isinstance(prose, tuple) or not prose:
            raise TypeError(
                "participant_self_knowledge values must be non-empty prose tuples."
            )
        for item in prose:
            _prose(item, "participant_self_knowledge prose")
        copied[key] = tuple(prose)
    return MappingProxyType(copied)
