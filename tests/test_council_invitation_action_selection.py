"""Council invitation action-selection guidance remains safe and non-coercive."""

from __future__ import annotations

from dataclasses import dataclass, field

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.council import (
    CouncilAgenda,
    CouncilCall,
    CouncilInvitationStatus,
    CouncilService,
)
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.meeting import MeetingService
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.managers.observation_manager import ObservationManager
from living_world.state.world_state import WorldState

_INVITATION = (
    "Council invitation from Erik: a careful route. "
    "In action_request, return exactly one offered attendance action. "
    "Include a short reason in that action request's rationale. "
    "A statement by itself is not an attendance selection."
)


@dataclass
class CapturingScriptedClient:
    decisions: list[NPCDecision]
    contexts: list[NPCContext] = field(default_factory=list)

    @property
    def provider_name(self) -> str:
        return "scripted"

    def decide(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> NPCDecision:
        self.contexts.append(context)
        return self.decisions.pop(0)


def _service(
    decisions: list[NPCDecision],
) -> tuple[CouncilService, WorldState, CapturingScriptedClient]:
    state = WorldState()
    state.entities["council"] = Entity("council", "organization", "Council")
    for identifier, label in (("npc_1", "Erik"), ("npc_2", "Mira"), ("npc_3", "Sana")):
        state.entities[identifier] = Entity(identifier, "npc", label)
        state.relationships[f"membership_{identifier}"] = Relationship(
            f"membership_{identifier}", "member_of", identifier, "council"
        )
    assembler = NPCContextAssembler(state)
    client = CapturingScriptedClient(decisions)
    decision_engine = DecisionEngine(client)
    agenda_actions = (ActionOption("wait", "Wait quietly."),)
    conversation = ConversationService(
        assembler,
        decision_engine,
        NPCActionResolver(agenda_actions),
        ObservationManager(state),
        agenda_actions,
    )
    return (
        CouncilService(
            MeetingService(conversation),
            assembler,
            decision_engine,
            NPCActionResolver(agenda_actions),
            state,
        ),
        state,
        client,
    )


def _call(invitees: tuple[str, ...], max_rounds: int = 0) -> CouncilCall:
    return CouncilCall(
        "npc_1",
        "council",
        invitees,
        CouncilAgenda("a careful route", (ActionOption("wait", "Wait quietly."),)),
        max_rounds,
    )


def test_every_invitee_receives_exact_safe_action_selection_guidance() -> None:
    service, state, client = _service(
        [
            NPCDecision(
                "I will decide.",
                ActionRequest("decline_council", None, "I cannot attend."),
            ),
            NPCDecision(
                "I will decide.",
                ActionRequest("decline_council", None, "I cannot attend."),
            ),
        ]
    )
    state.entities["npc_1"].attributes["hidden_strength"] = 42

    service.convene(call=_call(("npc_2", "npc_3")))

    assert [context.conversation_history for context in client.contexts] == [
        (_INVITATION,),
        (_INVITATION,),
    ]
    assert all(
        forbidden not in _INVITATION
        for forbidden in (
            "npc_1",
            "npc_2",
            "npc_3",
            "membership_",
            "member_of",
            "hidden_strength",
            "42",
            "attend_council",
            "decline_council",
            "wait",
        )
    )


def test_explicit_attendance_actions_use_ordinary_resolver_and_feedback() -> None:
    attend = ActionRequest("attend_council", None, "I can attend.")
    decline = ActionRequest("decline_council", None, "Please count my delegation.")
    wait = ActionRequest("wait", None, "I support waiting.")
    service, state, _ = _service(
        [
            NPCDecision("I will come.", attend),
            NPCDecision("I cannot join.", decline),
            NPCDecision("We should wait.", wait),
        ]
    )

    result = service.convene(call=_call(("npc_2", "npc_3"), max_rounds=1))

    assert [item.status for item in result.invitation_feedback] == [
        CouncilInvitationStatus.ATTENDING,
        CouncilInvitationStatus.DECLINED,
    ]
    assert [item.rationale for item in result.invitation_feedback] == [
        "I can attend.",
        "Please count my delegation.",
    ]
    assert result.attendance[1].attending is True
    assert result.attendance[2].delegates_to_majority is True
    assert result.conversation.proposals[0].action_request == wait
    assert state.events == {}
    assert [observation.description for observation in state.observations.values()] == [
        "We should wait."
    ]


def test_statement_without_action_request_remains_no_selection() -> None:
    service, state, _ = _service([NPCDecision("I would gladly attend.", None)])

    result = service.convene(call=_call(("npc_2",)))

    assert result.invitation_feedback[0].status is CouncilInvitationStatus.NO_SELECTION
    assert result.invitation_feedback[0].spoken_text == "I would gladly attend."
    assert result.attendance[1].attending is False
    assert result.attendance[1].delegates_to_majority is False
    assert result.conversation.turns == ()
    assert state.events == {}
