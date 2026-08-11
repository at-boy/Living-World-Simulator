from __future__ import annotations

from dataclasses import dataclass

import pytest

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.local_llm_cognition_format import serialize_decision_request
from living_world.cognition.npc_cognition_client import ActionOption, NPCDecision
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.core.entity import Entity
from living_world.core.memory import CognitiveSalience, Memory
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
    state.entities["npc_1"] = Entity(
        id="npc_1",
        definition_key="npc",
        name="Erik",
        attributes={"skill": 42},
    )
    state.entities["npc_2"] = Entity(
        id="npc_2",
        definition_key="npc",
        name="Mira",
    )
    state.memories["memory_1"] = Memory(
        id="memory_1",
        tick=1,
        holder_id="npc_1",
        subject_id="forest",
        summary="I remember a quiet grove.",
        salience=CognitiveSalience(importance=0.9, is_core=True),
    )
    state.memories["memory_2"] = Memory(
        id="memory_2",
        tick=1,
        holder_id="npc_2",
        subject_id="forest",
        summary="I remember the river path.",
        salience=CognitiveSalience(importance=0.9, is_core=True),
    )
    return state


def make_service(client: RecordingClient, state: WorldState) -> ConversationService:
    actions = (ActionOption(key="wait", description="Wait quietly."),)
    return ConversationService(
        NPCContextAssembler(state),
        DecisionEngine(client),
        NPCActionResolver(actions),
        ObservationManager(state),
        actions,
    )


def test_conversation_uses_private_context_and_records_visible_recipient_prose() -> (
    None
):
    client = RecordingClient(
        [
            NPCDecision("The grove feels peaceful.", None),
            NPCDecision("The river path sounds useful.", None),
        ]
    )
    state = make_state()
    result = make_service(client, state).conduct(
        participant_ids=("npc_1", "npc_2"),
        topic="where to walk",
        max_turns=2,
    )

    assert tuple(turn.speaker_label for turn in result.turns) == ("Erik", "Mira")
    assert tuple(turn.utterance for turn in result.turns) == (
        "The grove feels peaceful.",
        "The river path sounds useful.",
    )
    assert tuple(item.text for item in client.contexts[0].core_cognition) == (
        "I remember a quiet grove.",
    )
    assert tuple(item.text for item in client.contexts[1].core_cognition) == (
        "I remember the river path.",
    )
    assert client.contexts[1].conversation_history == (
        "Conversation topic: where to walk",
        "Erik: The grove feels peaceful.",
    )
    observations = tuple(state.observations.values())
    assert [
        (item.observer, item.subject, item.description) for item in observations
    ] == [
        ("npc_2", "npc_1", "The grove feels peaceful."),
        ("npc_1", "npc_2", "The river path sounds useful."),
    ]
    assert all(not item.evidence and not item.metadata for item in observations)
    assert all("npc_" not in item.description for item in observations)


def test_serialized_history_has_only_visible_prose() -> None:
    client = RecordingClient([NPCDecision("We can listen.", None)])
    state = make_state()
    service = make_service(client, state)
    service.conduct(
        participant_ids=("npc_1", "npc_2"),
        topic="the weather",
        max_turns=1,
    )

    encoded = serialize_decision_request(
        client.contexts[0], (ActionOption(key="wait", description="Wait quietly."),)
    )
    assert '"conversation_history":["Conversation topic: the weather"]' in encoded
    for forbidden in ("npc_1", "observation_", "metadata", "evidence", "attributes"):
        assert forbidden not in encoded


def test_invalid_inputs_or_unsafe_visible_prose_make_no_observations() -> None:
    state = make_state()
    client = RecordingClient([NPCDecision("The skill is 42.", None)])
    service = make_service(client, state)

    with pytest.raises(ValueError, match="numeric values"):
        service.conduct(
            participant_ids=("npc_1", "npc_2"), topic="the skill is 42", max_turns=1
        )
    assert client.contexts == []
    with pytest.raises(ValueError, match="numeric values"):
        service.conduct(
            participant_ids=("npc_1", "npc_2"), topic="the woods", max_turns=1
        )
    assert state.observations == {}
    assert len(client.contexts) == 1

    for participant_ids, topic, max_turns in (
        ((), "the woods", 1),
        (("npc_1", "npc_1"), "the woods", 1),
        (("unknown",), "the woods", 1),
        (("npc_1",), "", 1),
        (("npc_1",), "the woods", -1),
        (("npc_1",), "the woods", True),
    ):
        with pytest.raises((TypeError, ValueError)):
            service.conduct(
                participant_ids=participant_ids,
                topic=topic,
                max_turns=max_turns,
            )
    assert state.observations == {}


def test_action_proposals_have_deterministic_rejected_resolutions_without_mutation() -> (
    None
):
    from living_world.cognition.npc_cognition_client import ActionRequest

    client = RecordingClient(
        [
            NPCDecision(
                None,
                ActionRequest("wait", None, "I should pause."),
            )
        ]
    )
    state = make_state()
    result = make_service(client, state).conduct(
        participant_ids=("npc_1",), topic="the woods", max_turns=1
    )

    assert result.turns == ()
    assert result.resolutions[0].accepted is False
    assert state.observations == {}
    assert state.events == {}


def test_zero_turns_and_engine_delegation_are_deterministic() -> None:
    client = RecordingClient([NPCDecision("Unused text.", None)])
    state = make_state()
    service = make_service(client, state)
    engine = SimulationEngine()

    result = engine.conduct_npc_conversation(
        service=service,
        participant_ids=("npc_1",),
        topic="the woods",
        max_turns=0,
    )

    assert result.turns == ()
    assert result.resolutions == ()
    assert client.contexts == []
