"""Demonstrate bounded, visible NPC dialogue without authoritative actions."""

from dataclasses import dataclass

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.npc_cognition_client import ActionOption, NPCDecision
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.core.entity import Entity
from living_world.simulation.simulation_engine import SimulationEngine


@dataclass
class ScriptedClient:
    """A local stand-in returning visible, non-authoritative dialogue."""

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
    """Run two visible turns and print only the resulting dialogue."""

    engine = SimulationEngine()
    engine.state.entities["npc_1"] = Entity("npc_1", "npc", "Erik")
    engine.state.entities["npc_2"] = Entity("npc_2", "npc", "Mira")
    actions = (ActionOption("wait", "Wait quietly."),)
    service = ConversationService(
        NPCContextAssembler(engine.state),
        DecisionEngine(
            ScriptedClient(
                [
                    NPCDecision("The path seems peaceful.", None),
                    NPCDecision("Let us walk with care.", None),
                ]
            )
        ),
        NPCActionResolver(actions),
        engine.observations,
        actions,
    )

    result = engine.conduct_npc_conversation(
        service=service,
        participant_ids=("npc_1", "npc_2"),
        topic="where to walk",
        max_turns=2,
    )
    for turn in result.turns:
        print(f"{turn.speaker_label}: {turn.utterance}")


if __name__ == "__main__":
    main()
