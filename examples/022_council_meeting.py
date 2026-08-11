"""Demonstrate a small deterministic council whose proposal remains untrusted."""

from dataclasses import dataclass

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.council import CouncilAgenda, CouncilCall, CouncilService
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
from living_world.simulation.simulation_engine import SimulationEngine


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


def main() -> None:
    engine = SimulationEngine()
    engine.state.entities["council"] = Entity("council", "organization", "Council")
    for identifier, name in (("npc_1", "Erik"), ("npc_2", "Mira"), ("npc_3", "Sana")):
        engine.state.entities[identifier] = Entity(identifier, "npc", name)
        engine.state.relationships[f"membership_{identifier}"] = Relationship(
            f"membership_{identifier}", "member_of", identifier, "council"
        )
    actions = (ActionOption("wait", "Wait quietly."),)
    client = ScriptedClient(
        [
            NPCDecision(None, ActionRequest("attend_council", None, "I will attend.")),
            NPCDecision(None, ActionRequest("decline_council", None, "I delegate.")),
            NPCDecision("Care is sensible.", ActionRequest("wait", None, "Wait.")),
            NPCDecision("I agree.", ActionRequest("wait", None, "Wait.")),
        ]
    )
    assembler = NPCContextAssembler(engine.state)
    decision_engine = DecisionEngine(client)
    conversation = ConversationService(
        assembler,
        decision_engine,
        NPCActionResolver(actions),
        engine.observations,
        actions,
    )
    council = CouncilService(
        MeetingService(conversation),
        assembler,
        decision_engine,
        NPCActionResolver(actions),
        engine.state,
    )
    result = engine.convene_npc_council(
        service=council,
        call=CouncilCall(
            "npc_1",
            "council",
            ("npc_2", "npc_3"),
            CouncilAgenda("choosing a route", actions),
            2,
            participant_self_knowledge={
                "npc_1": ("I value caution.",),
                "npc_2": ("I value preparation.",),
                "npc_3": ("I value speed.",),
            },
        ),
    )
    for turn in result.conversation.turns:
        print(f"{turn.speaker_label}: {turn.utterance}")
    print(f"Majority proposal: {result.majority_proposal}")


if __name__ == "__main__":
    main()
