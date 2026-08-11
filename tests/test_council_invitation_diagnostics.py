"""Safe diagnostic coverage for unavailable council invitations."""

from __future__ import annotations

import pytest

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.council import (
    CouncilAgenda,
    CouncilCall,
    CouncilInvitationDiagnostic,
    CouncilInvitationFeedback,
    CouncilInvitationStatus,
    CouncilService,
)
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.meeting import MeetingService
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.managers.observation_manager import ObservationManager
from living_world.state.world_state import WorldState


class InvalidDecisionClient:
    """Return an invalid direct decision without exposing its details."""

    @property
    def provider_name(self) -> str:
        return "invalid-decision"

    def decide(self, context: NPCContext, actions: tuple[ActionOption, ...]) -> object:
        return object()


def _service() -> CouncilService:
    state = WorldState()
    state.entities["council"] = Entity("council", "organization", "Council")
    for identifier, label in (("npc_1", "Aster"), ("npc_2", "Bryn")):
        state.entities[identifier] = Entity(identifier, "npc", label)
        state.relationships[f"membership_{identifier}"] = Relationship(
            f"membership_{identifier}", "member_of", identifier, "council"
        )
    assembler = NPCContextAssembler(state)
    decisions = DecisionEngine(InvalidDecisionClient())
    actions = (ActionOption("wait", "Wait."),)
    conversation = ConversationService(
        assembler,
        decisions,
        NPCActionResolver(actions),
        ObservationManager(state),
        actions,
    )
    return CouncilService(
        MeetingService(conversation),
        assembler,
        decisions,
        NPCActionResolver(actions),
        state,
    )


def test_invalid_direct_decision_has_fixed_safe_diagnostic() -> None:
    result = _service().convene(
        call=CouncilCall(
            "npc_1",
            "council",
            ("npc_2",),
            CouncilAgenda("a route", (ActionOption("wait", "Wait."),)),
            0,
        )
    )

    feedback = result.invitation_feedback[0]

    assert feedback.status is CouncilInvitationStatus.UNAVAILABLE
    assert feedback.diagnostic is CouncilInvitationDiagnostic.INVALID_DECISION
    assert feedback.spoken_text is None
    assert feedback.rationale is None


@pytest.mark.parametrize(
    ("status", "diagnostic"),
    (
        (
            CouncilInvitationStatus.ATTENDING,
            CouncilInvitationDiagnostic.INVALID_DECISION,
        ),
        (
            CouncilInvitationStatus.DECLINED,
            CouncilInvitationDiagnostic.INVALID_DECISION,
        ),
        (
            CouncilInvitationStatus.NO_SELECTION,
            CouncilInvitationDiagnostic.INVALID_DECISION,
        ),
    ),
)
def test_diagnostic_is_rejected_for_available_feedback(
    status: CouncilInvitationStatus, diagnostic: CouncilInvitationDiagnostic
) -> None:
    with pytest.raises(ValueError, match="only unavailable"):
        CouncilInvitationFeedback("Bryn", status, None, None, diagnostic)


def test_unavailable_feedback_requires_a_diagnostic() -> None:
    with pytest.raises(ValueError, match="must include a diagnostic"):
        CouncilInvitationFeedback(
            "Bryn", CouncilInvitationStatus.UNAVAILABLE, None, None
        )
