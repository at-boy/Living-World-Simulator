"""Coverage for the narrow unanimous explicit-decline council fallback."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from living_world.cognition.action_resolution import (
    ActionResolution,
    NPCActionResolver,
)
from living_world.cognition.conversation import ConversationService
from living_world.cognition.council import (
    CouncilAgenda,
    CouncilCall,
    CouncilDecisionBasis,
    CouncilInvitationStatus,
    CouncilService,
)
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.meeting import MeetingService
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCCognitionClientError,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.managers.observation_manager import ObservationManager
from living_world.state.world_state import WorldState


@dataclass
class RecordingClient:
    decisions: list[NPCDecision | Exception]
    contexts: list[NPCContext] = field(default_factory=list)

    @property
    def provider_name(self) -> str:
        return "recording"

    def decide(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> NPCDecision:
        self.contexts.append(context)
        response = self.decisions.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@dataclass
class WaitHandler:
    actors: list[str] = field(default_factory=list)

    def supports(self, action_key: str) -> bool:
        return action_key == "wait"

    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        return ActionResolution(True, "Waiting is valid.")

    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        self.actors.append(actor_id)
        return ActionResolution(True, "Waiting was applied.")


def _service(
    decisions: list[NPCDecision | Exception], reject_proposal: bool = False
) -> tuple[CouncilService, WorldState, RecordingClient, WaitHandler]:
    state = WorldState()
    state.entities["council"] = Entity("council", "organization", "Council")
    for identifier, label in (("npc_1", "Aster"), ("npc_2", "Bryn"), ("npc_3", "Cato")):
        state.entities[identifier] = Entity(identifier, "npc", label)
        state.relationships[f"membership_{identifier}"] = Relationship(
            f"membership_{identifier}", "member_of", identifier, "council"
        )
    client = RecordingClient(decisions)
    decisions_engine = DecisionEngine(client)
    actions = (ActionOption("wait", "Wait."),)
    handler = WaitHandler()
    resolver = NPCActionResolver(actions, () if reject_proposal else (handler,))
    assembler = NPCContextAssembler(state)
    conversation = ConversationService(
        assembler,
        decisions_engine,
        resolver,
        ObservationManager(state),
        actions,
    )
    return (
        CouncilService(
            MeetingService(conversation), assembler, decisions_engine, resolver, state
        ),
        state,
        client,
        handler,
    )


def _call(invitees: tuple[str, ...] = ("npc_2", "npc_3")) -> CouncilCall:
    return CouncilCall(
        "npc_1",
        "council",
        invitees,
        CouncilAgenda("whether to wait", (ActionOption("wait", "Wait."),)),
        1,
        participant_self_knowledge={"npc_1": ("I know the path is difficult.",)},
    )


def test_every_explicit_decline_allows_one_safe_caller_gateway_proposal() -> None:
    decline = ActionRequest("decline_council", None, "I delegate.")
    proposal = ActionRequest("wait", None, "Waiting is safer.")
    service, state, client, handler = _service(
        [
            NPCDecision(None, decline),
            NPCDecision(None, decline),
            NPCDecision(None, proposal),
        ]
    )

    result = service.convene(call=_call())

    assert (
        result.decision_basis is CouncilDecisionBasis.EXPLICIT_DECLINE_CALLER_FALLBACK
    )
    assert result.majority_proposal == proposal
    assert result.resolutions == (ActionResolution(True, "Waiting was applied."),)
    assert handler.actors == ["npc_1"]
    assert [item.status for item in result.invitation_feedback] == [
        CouncilInvitationStatus.DECLINED,
        CouncilInvitationStatus.DECLINED,
    ]
    caller_context = client.contexts[-1]
    assert caller_context.identity == "Aster"
    assert caller_context.self_knowledge == ("I know the path is difficult.",)
    assert caller_context.conversation_history == (
        (
            "Every person asked explicitly declined and delegated. You may submit one "
            "offered proposal; it remains subject to normal simulation validation."
        ),
    )
    assert "Bryn" not in caller_context.conversation_history[0]
    assert "Cato" not in caller_context.conversation_history[0]
    assert state.events == {}


@pytest.mark.parametrize(
    ("decisions", "context_count"),
    [
        (
            [
                NPCDecision(
                    None, ActionRequest("decline_council", None, "I delegate.")
                ),
                NPCDecision("I abstain.", None),
            ],
            2,
        ),
        (
            [
                NPCDecision(None, ActionRequest("attend_council", None, "I attend.")),
                NPCDecision(
                    None, ActionRequest("decline_council", None, "I delegate.")
                ),
                NPCDecision("I will speak.", None),
            ],
            3,
        ),
    ],
)
def test_only_unanimous_explicit_declines_enable_fallback(
    decisions: list[NPCDecision], context_count: int
) -> None:
    service, state, client, handler = _service(decisions)

    result = service.convene(call=_call())

    assert result.decision_basis is None
    assert result.majority_proposal is None
    assert result.resolutions == ()
    assert handler.actors == []
    assert len(client.contexts) == context_count
    assert state.events == {}


def test_council_call_requires_at_least_one_invitee() -> None:
    with pytest.raises(ValueError, match="invited_participant_ids cannot be empty"):
        _call(())


def test_unavailable_invitee_never_delegates_to_the_caller() -> None:
    decline = ActionRequest("decline_council", None, "I delegate.")
    service, state, client, handler = _service(
        [
            NPCCognitionClientError("provider unavailable"),
            NPCDecision(None, decline),
        ]
    )

    result = service.convene(call=_call())

    assert result.decision_basis is None
    assert result.majority_proposal is None
    assert result.resolutions == ()
    assert [item.status for item in result.invitation_feedback] == [
        CouncilInvitationStatus.UNAVAILABLE,
        CouncilInvitationStatus.DECLINED,
    ]
    assert len(client.contexts) == 2
    assert handler.actors == []
    assert state.events == {}


def test_fallback_abstention_has_no_resolution_or_mutation() -> None:
    decline = ActionRequest("decline_council", None, "I delegate.")
    service, state, client, handler = _service(
        [
            NPCDecision(None, decline),
            NPCDecision(None, decline),
            NPCDecision("I abstain.", None),
        ]
    )

    result = service.convene(call=_call())

    assert (
        result.decision_basis is CouncilDecisionBasis.EXPLICIT_DECLINE_CALLER_FALLBACK
    )
    assert result.majority_proposal is None
    assert result.resolutions == ()
    assert handler.actors == []
    assert len(client.contexts) == 3
    assert state.events == {}


def test_rejected_fallback_request_has_no_state_mutation() -> None:
    decline = ActionRequest("decline_council", None, "I delegate.")
    proposal = ActionRequest("wait", None, "Waiting is safer.")
    service, state, _, handler = _service(
        [
            NPCDecision(None, decline),
            NPCDecision(None, decline),
            NPCDecision(None, proposal),
        ],
        reject_proposal=True,
    )

    result = service.convene(call=_call())

    assert result.majority_proposal == proposal
    assert result.resolutions == (
        ActionResolution(False, "No handler supports the requested action."),
    )
    assert handler.actors == []
    assert state.events == {}
