from __future__ import annotations

from dataclasses import dataclass

import pytest

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.meeting import MeetingRequest, MeetingService
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.core.entity import Entity
from living_world.managers.observation_manager import ObservationManager
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState


@dataclass
class RecordingClient:
    decisions: list[NPCDecision]

    def __post_init__(self) -> None:
        self.contexts: list[NPCContext] = []

    @property
    def provider_name(self) -> str:
        return "recording"

    def decide(
        self,
        context: NPCContext,
        actions: tuple[ActionOption, ...],
    ) -> NPCDecision:
        self.contexts.append(context)
        return self.decisions.pop(0)


def make_state() -> WorldState:
    state = WorldState()
    for identifier, name in (
        ("npc_1", "Erik"),
        ("npc_2", "Mira"),
        ("npc_3", "Sana"),
        ("npc_4", "Tomas"),
        ("npc_5", "Lina"),
    ):
        state.entities[identifier] = Entity(
            identifier,
            "npc",
            name,
            attributes={"skill": 42} if identifier == "npc_1" else {},
        )
    return state


def make_service(
    client: RecordingClient,
    state: WorldState,
) -> tuple[ConversationService, MeetingService]:
    actions = (ActionOption("wait", "Wait quietly."),)
    conversation = ConversationService(
        NPCContextAssembler(state),
        DecisionEngine(client),
        NPCActionResolver(actions),
        ObservationManager(state),
        actions,
    )
    return conversation, MeetingService(conversation)


def test_meeting_explicit_schedule_and_private_perspectives_are_holder_scoped() -> None:
    state = make_state()
    client = RecordingClient(
        [
            NPCDecision("I favour a careful path.", None),
            NPCDecision("I favour a swift path.", None),
            NPCDecision("I favour a quiet path.", None),
            NPCDecision("I favour a bold path.", None),
            NPCDecision("I favour a patient path.", None),
        ]
    )
    _, service = make_service(client, state)
    perspectives = {
        "npc_1": ("I prefer careful preparation.",),
        "npc_2": ("I prefer swift progress.",),
        "npc_3": ("I prefer a quiet approach.",),
        "npc_4": ("I prefer bold action.",),
        "npc_5": ("I prefer patient planning.",),
    }

    result = service.conduct(
        MeetingRequest(
            requester_id="npc_1",
            invitee_ids=("npc_2", "npc_3", "npc_4", "npc_5"),
            topic="choosing a path",
            max_turns=5,
            called_speaker_ids=("npc_5", "npc_3", "npc_1", "npc_3", "npc_2"),
            participant_self_knowledge=perspectives,
        )
    )

    assert tuple(turn.speaker_label for turn in result.turns) == (
        "Lina",
        "Sana",
        "Erik",
        "Sana",
        "Mira",
    )
    assert [context.self_knowledge for context in client.contexts] == [
        perspectives["npc_5"],
        perspectives["npc_3"],
        perspectives["npc_1"],
        perspectives["npc_3"],
        perspectives["npc_2"],
    ]
    for context, expected in zip(
        client.contexts,
        (
            perspectives["npc_5"],
            perspectives["npc_3"],
            perspectives["npc_1"],
            perspectives["npc_3"],
            perspectives["npc_2"],
        ),
        strict=True,
    ):
        assert all("npc_" not in item for item in context.self_knowledge)
        assert context.self_knowledge == expected
        assert all(
            perspective == expected or perspective[0] not in context.self_knowledge
            for perspective in perspectives.values()
        )
    assert all(
        "npc_" not in item for turn in result.turns for item in (turn.utterance,)
    )


def test_empty_schedule_cycles_requester_then_invitees() -> None:
    state = make_state()
    client = RecordingClient([NPCDecision("I can speak.", None)] * 3)
    _, service = make_service(client, state)

    result = service.conduct(
        MeetingRequest(
            requester_id="npc_1",
            invitee_ids=("npc_2", "npc_3"),
            topic="a route",
            max_turns=3,
        )
    )

    assert tuple(turn.speaker_label for turn in result.turns) == (
        "Erik",
        "Mira",
        "Sana",
    )


@pytest.mark.parametrize(
    "meeting_request",
    (
        MeetingRequest("npc_1", ("npc_1",), "a route", 1),
        MeetingRequest("npc_1", ("npc_2", "npc_2"), "a route", 1),
        MeetingRequest("npc_1", ("unknown",), "a route", 1),
        MeetingRequest("npc_1", ("npc_2",), "a route", 1, ("npc_3",)),
        MeetingRequest("npc_1", ("npc_2",), "a route", 1, ("npc_1", "npc_2")),
        MeetingRequest(
            "npc_1",
            ("npc_2",),
            "a route",
            1,
            participant_self_knowledge={"unknown": ("I prefer calm.",)},
        ),
        MeetingRequest(
            "npc_1",
            ("npc_2",),
            "a route",
            1,
            participant_self_knowledge={"npc_1": ("The skill is 42.",)},
        ),
    ),
)
def test_invalid_meeting_requests_have_no_side_effects(
    meeting_request: MeetingRequest,
) -> None:
    state = make_state()
    client = RecordingClient([NPCDecision("Unused.", None)])
    _, service = make_service(client, state)

    with pytest.raises((TypeError, ValueError)):
        service.conduct(meeting_request)

    assert client.contexts == []
    assert state.observations == {}
    assert state.events == {}


def test_rejected_meeting_action_and_engine_delegation_are_non_mutating() -> None:
    state = make_state()
    client = RecordingClient(
        [NPCDecision(None, ActionRequest("wait", None, "I should pause."))]
    )
    _, service = make_service(client, state)
    engine = SimulationEngine()

    result = engine.conduct_npc_meeting(
        service=service,
        request=MeetingRequest("npc_1", ("npc_2",), "a route", 1),
    )

    assert result.turns == ()
    assert result.resolutions[0].accepted is False
    assert state.observations == {}
    assert state.events == {}


def test_request_owns_an_immutable_copy_of_perspectives() -> None:
    perspectives = {"npc_1": ("I prefer calm.",)}
    request = MeetingRequest(
        "npc_1",
        ("npc_2",),
        "a route",
        1,
        participant_self_knowledge=perspectives,
    )
    perspectives["npc_2"] = ("I prefer speed.",)

    assert dict(request.participant_self_knowledge) == {"npc_1": ("I prefer calm.",)}
    with pytest.raises(TypeError):
        request.participant_self_knowledge["npc_2"] = ("I prefer speed.",)  # type: ignore[index]
