"""Demonstrate a bounded NPC meeting with engine-owned speaker calls."""

from dataclasses import dataclass

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.meeting import MeetingRequest, MeetingService
from living_world.cognition.npc_cognition_client import ActionOption, NPCDecision
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.core.entity import Entity
from living_world.simulation.simulation_engine import SimulationEngine


@dataclass
class ScriptedClient:
    """A deterministic local stand-in for non-authoritative NPC proposals."""

    decisions: list[NPCDecision]

    @property
    def provider_name(self) -> str:
        return "scripted"

    def decide(
        self,
        context: NPCContext,
        actions: tuple[ActionOption, ...],
    ) -> NPCDecision:
        return self.decisions.pop(0)


def main() -> None:
    """Run a requester-first meeting with an engine-owned speaker schedule."""

    engine = SimulationEngine()
    engine.state.entities["npc_1"] = Entity("npc_1", "npc", "Erik")
    engine.state.entities["npc_2"] = Entity("npc_2", "npc", "Mira")
    engine.state.entities["npc_3"] = Entity("npc_3", "npc", "Sana")
    actions = (ActionOption("wait", "Wait quietly."),)
    conversation = ConversationService(
        NPCContextAssembler(engine.state),
        DecisionEngine(
            ScriptedClient(
                [
                    NPCDecision("We should travel carefully.", None),
                    NPCDecision("The quiet route seems sensible.", None),
                    NPCDecision("Let us prepare before leaving.", None),
                ]
            )
        ),
        NPCActionResolver(actions),
        engine.observations,
        actions,
    )
    meeting = MeetingService(conversation)
    result = engine.conduct_npc_meeting(
        service=meeting,
        request=MeetingRequest(
            requester_id="npc_1",
            invitee_ids=("npc_2", "npc_3"),
            topic="choosing a route",
            max_turns=3,
            called_speaker_ids=("npc_2", "npc_3", "npc_1"),
            participant_self_knowledge={
                "npc_1": ("I prefer careful preparation.",),
                "npc_2": ("I prefer swift travel.",),
                "npc_3": ("I prefer quiet routes.",),
            },
        ),
    )
    for turn in result.turns:
        print(f"{turn.speaker_label}: {turn.utterance}")


if __name__ == "__main__":
    main()
