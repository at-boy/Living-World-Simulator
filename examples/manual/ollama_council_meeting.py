"""Opt-in five-NPC council smoke example for a loopback Ollama server."""

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.council import CouncilAgenda, CouncilCall, CouncilService
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.meeting import MeetingService
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.cognition.ollama_cognition_client import OllamaCognitionClient
from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.simulation.simulation_engine import SimulationEngine

PERSPECTIVES: tuple[tuple[str, str], ...] = (
    ("Aster", "I favour careful preparation before travel."),
    ("Bryn", "I favour a swift route while daylight lasts."),
    ("Cato", "I favour conserving supplies for later."),
    ("Dara", "I favour listening to every concern first."),
    ("Eris", "I favour a bold route that benefits the settlement."),
)


def main() -> None:
    """Run an opt-in five-NPC council through the loopback Ollama client."""

    _run(OllamaCognitionClient(model="hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M"))


def _run(client: OllamaCognitionClient) -> None:
    engine = SimulationEngine()
    engine.state.entities["council"] = Entity("council", "organization", "Council")
    ids: list[str] = []
    for index, (name, _) in enumerate(PERSPECTIVES, start=1):
        identifier = f"npc_{index}"
        ids.append(identifier)
        engine.state.entities[identifier] = Entity(identifier, "npc", name)
        engine.state.relationships[f"membership_{index}"] = Relationship(
            f"membership_{index}", "member_of", identifier, "council"
        )
    actions = (ActionOption("wait", "Support a patient non-authoritative pause."),)
    assembler = NPCContextAssembler(engine.state)
    decisions = DecisionEngine(client)
    conversation = ConversationService(
        assembler, decisions, NPCActionResolver(actions), engine.observations, actions
    )
    council = CouncilService(
        MeetingService(conversation),
        assembler,
        decisions,
        NPCActionResolver(actions),
        engine.state,
    )
    result = council.convene(
        call=CouncilCall(
            ids[0],
            "council",
            tuple(ids[1:]),
            CouncilAgenda(
                "whether the settlement should delay a risky journey", actions
            ),
            5,
            participant_self_knowledge={
                identifier: (perspective,)
                for identifier, (_, perspective) in zip(ids, PERSPECTIVES, strict=True)
            },
        )
    )
    print("Attendance")
    for attendance in result.attendance:
        status = "attending" if attendance.attending else "not attending"
        delegation = (
            "; delegates to majority" if attendance.delegates_to_majority else ""
        )
        print(f"- {attendance.participant_label}: {status}{delegation}")

    print("\nDebate")
    if result.conversation.turns:
        for turn in result.conversation.turns:
            print(f"{turn.speaker_label}: {turn.utterance}")
    else:
        print("No invitee attended, so no debate was held.")

    print("\nVotes / proposals")
    if result.conversation.proposals:
        for proposal in result.conversation.proposals:
            request = proposal.action_request
            print(
                f"- {proposal.speaker_label}: {request.action_key} ({request.rationale})"
            )
    else:
        print("No agenda proposal was cast.")

    print(f"\nMajority proposal: {result.majority_proposal}")
    if result.resolutions:
        print(f"Gateway resolution: {result.resolutions[0]}")


if __name__ == "__main__":
    main()
