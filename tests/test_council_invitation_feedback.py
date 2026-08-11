"""Safe, ephemeral feedback for council invitation decisions."""

from __future__ import annotations

from dataclasses import dataclass

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
    NPCCognitionClientError,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.managers.observation_manager import ObservationManager
from living_world.state.world_state import WorldState


@dataclass
class ScriptedClient:
    decisions: list[NPCDecision]

    @property
    def provider_name(self) -> str:
        return "scripted"

    def decide(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> NPCDecision:
        return self.decisions.pop(0)


def _service(decisions: list[NPCDecision]) -> tuple[CouncilService, WorldState]:
    state = WorldState()
    state.entities["council"] = Entity("council", "organization", "Council")
    for identifier, label in (("npc_1", "Erik"), ("npc_2", "Mira"), ("npc_3", "Sana")):
        state.entities[identifier] = Entity(identifier, "npc", label)
        state.relationships[f"membership_{identifier}"] = Relationship(
            f"membership_{identifier}", "member_of", identifier, "council"
        )
    assembler = NPCContextAssembler(state)
    engine = DecisionEngine(ScriptedClient(decisions))
    agenda_actions = (ActionOption("wait", "Wait."),)
    conversation = ConversationService(
        assembler,
        engine,
        NPCActionResolver(agenda_actions),
        ObservationManager(state),
        agenda_actions,
    )
    return (
        CouncilService(
            MeetingService(conversation),
            assembler,
            engine,
            NPCActionResolver(agenda_actions),
            state,
        ),
        state,
    )


def _call(invitees: tuple[str, ...]) -> CouncilCall:
    return CouncilCall(
        "npc_1",
        "council",
        invitees,
        CouncilAgenda("a route", (ActionOption("wait", "Wait."),)),
        0,
    )


def test_feedback_is_invitee_ordered_with_accepted_and_no_selection_outcomes() -> None:
    service, _ = _service(
        [
            NPCDecision(
                "I will come.", ActionRequest("attend_council", None, "I can attend.")
            ),
            NPCDecision(
                "I cannot join.",
                ActionRequest("decline_council", None, "Please count my delegation."),
            ),
            NPCDecision("I have no attendance choice.", None),
        ]
    )

    first = service.convene(call=_call(("npc_2", "npc_3")))
    second = service.convene(call=_call(("npc_2",)))

    assert [item.participant_label for item in first.invitation_feedback] == [
        "Mira",
        "Sana",
    ]
    assert [item.status for item in first.invitation_feedback] == [
        CouncilInvitationStatus.ATTENDING,
        CouncilInvitationStatus.DECLINED,
    ]
    assert first.invitation_feedback[0].spoken_text == "I will come."
    assert first.invitation_feedback[0].rationale == "I can attend."
    assert first.invitation_feedback[1].spoken_text == "I cannot join."
    assert first.invitation_feedback[1].rationale == "Please count my delegation."
    assert second.invitation_feedback[0].status is CouncilInvitationStatus.NO_SELECTION
    assert second.invitation_feedback[0].spoken_text == "I have no attendance choice."
    assert second.invitation_feedback[0].rationale is None


def test_feedback_marks_provider_errors_unavailable_without_error_text() -> None:
    class UnavailableClient:
        @property
        def provider_name(self) -> str:
            return "unavailable"

        def decide(
            self, context: NPCContext, actions: tuple[ActionOption, ...]
        ) -> NPCDecision:
            raise NPCCognitionClientError("private provider failure")

    service, state = _service([])
    assembler = NPCContextAssembler(state)
    decisions = DecisionEngine(UnavailableClient())
    actions = (ActionOption("wait", "Wait."),)
    service = CouncilService(
        MeetingService(
            ConversationService(
                assembler,
                decisions,
                NPCActionResolver(actions),
                ObservationManager(state),
                actions,
            )
        ),
        assembler,
        decisions,
        NPCActionResolver(actions),
        state,
    )

    feedback = service.convene(call=_call(("npc_2",))).invitation_feedback[0]

    assert feedback.status is CouncilInvitationStatus.UNAVAILABLE
    assert feedback.spoken_text is None
    assert feedback.rationale is None
    assert "private provider failure" not in repr(feedback)


def test_feedback_suppresses_internal_and_authoritative_submission_prose() -> None:
    service, state = _service(
        [
            NPCDecision(
                "npc_2 has 42 supplies.",
                ActionRequest("attend_council", None, "Bring 42 supplies."),
            )
        ]
    )
    state.entities["npc_1"].attributes["supplies"] = 42

    feedback = service.convene(call=_call(("npc_2",))).invitation_feedback[0]

    assert feedback.status is CouncilInvitationStatus.ATTENDING
    assert feedback.spoken_text is None
    assert feedback.rationale is None
    assert state.events == {}
