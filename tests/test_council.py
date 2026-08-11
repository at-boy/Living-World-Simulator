from __future__ import annotations

from dataclasses import dataclass

import pytest

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.council import (
    CouncilAgenda,
    CouncilCall,
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
    client = ScriptedClient(decisions)
    engine = DecisionEngine(client)
    agenda_actions = (ActionOption("wait", "Wait quietly."),)
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


def test_council_can_proceed_below_five_and_resolves_only_majority_once() -> None:
    attend = ActionRequest("attend_council", None, "I will attend.")
    decline = ActionRequest("decline_council", None, "I delegate.")
    wait = ActionRequest("wait", None, "I support waiting.")
    service, state = _service(
        [
            NPCDecision(None, attend),
            NPCDecision(None, decline),
            NPCDecision("We should wait.", wait),
            NPCDecision("Waiting is prudent.", wait),
        ]
    )

    result = service.convene(
        call=CouncilCall(
            "npc_1",
            "council",
            ("npc_2", "npc_3"),
            CouncilAgenda("a careful route", (ActionOption("wait", "Wait quietly."),)),
            2,
            called_speaker_ids=("npc_1", "npc_2"),
            participant_self_knowledge={
                "npc_1": ("I prefer care.",),
                "npc_2": ("I prefer patience.",),
                "npc_3": ("I prefer speed.",),
            },
        )
    )

    assert [
        (item.participant_label, item.attending, item.delegates_to_majority)
        for item in result.attendance
    ] == [("Erik", True, False), ("Mira", True, False), ("Sana", False, True)]
    assert result.majority_proposal == wait
    assert len(result.resolutions) == 1
    assert result.resolutions[0].accepted is False
    assert len(result.conversation.proposals) == 2
    assert state.events == {}


def test_ineligible_participants_fail_before_any_model_call() -> None:
    service, state = _service(
        [NPCDecision(None, ActionRequest("attend_council", None, "I will attend."))]
    )
    state.relationships.clear()

    with pytest.raises(ValueError, match="organization members"):
        service.convene(
            call=CouncilCall(
                "npc_1",
                "council",
                ("npc_2",),
                CouncilAgenda("a route", (ActionOption("wait", "Wait."),)),
                1,
            )
        )

    assert state.observations == {}
    assert state.events == {}


def test_tie_or_abstention_has_no_gateway_resolution() -> None:
    attend = ActionRequest("attend_council", None, "I will attend.")
    service, state = _service(
        [
            NPCDecision(None, attend),
            NPCDecision(None, attend),
            NPCDecision("I am undecided.", None),
            NPCDecision("I am also undecided.", None),
            NPCDecision("I will listen.", None),
        ]
    )
    result = service.convene(
        call=CouncilCall(
            "npc_1",
            "council",
            ("npc_2", "npc_3"),
            CouncilAgenda("a route", (ActionOption("wait", "Wait."),)),
            3,
        )
    )

    assert result.majority_proposal is None
    assert result.resolutions == ()
    assert state.events == {}


def test_unavailable_or_declining_invitees_leave_a_safe_caller_only_result() -> None:
    class UnavailableClient:
        @property
        def provider_name(self) -> str:
            return "unavailable"

        def decide(
            self, context: NPCContext, actions: tuple[ActionOption, ...]
        ) -> NPCDecision:
            raise NPCCognitionClientError("local model unavailable")

    service, state = _service([])
    assembler = NPCContextAssembler(state)
    agenda_actions = (ActionOption("wait", "Wait."),)
    decisions = DecisionEngine(UnavailableClient())
    conversation = ConversationService(
        assembler,
        decisions,
        NPCActionResolver(agenda_actions),
        ObservationManager(state),
        agenda_actions,
    )
    service = CouncilService(
        MeetingService(conversation),
        assembler,
        decisions,
        NPCActionResolver(agenda_actions),
        state,
    )

    result = service.convene(
        call=CouncilCall(
            "npc_1",
            "council",
            ("npc_2",),
            CouncilAgenda("a route", agenda_actions),
            1,
        )
    )

    assert [
        (item.attending, item.delegates_to_majority) for item in result.attendance
    ] == [
        (True, False),
        (False, False),
    ]
    assert result.conversation.turns == ()
    assert result.majority_proposal is None
    assert result.resolutions == ()
    assert state.observations == {}
    assert state.events == {}


def test_unsafe_engine_perspective_fails_before_any_invitation_model_call() -> None:
    attend = ActionRequest("attend_council", None, "I will attend.")
    service, state = _service([NPCDecision(None, attend)])
    state.entities["npc_1"].attributes["skill"] = 42

    with pytest.raises(ValueError, match="numeric values"):
        service.convene(
            call=CouncilCall(
                "npc_1",
                "council",
                ("npc_2",),
                CouncilAgenda("a route", (ActionOption("wait", "Wait."),)),
                1,
                participant_self_knowledge={"npc_1": ("The skill is 42.",)},
            )
        )

    assert state.observations == {}
    assert state.events == {}
    assert len(service._decisions._client.decisions) == 1  # type: ignore[attr-defined]
