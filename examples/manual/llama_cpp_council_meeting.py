"""Opt-in five-NPC council smoke example for a loopback llama.cpp server."""

from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.council import (
    CouncilAgenda,
    CouncilCall,
    CouncilResult,
    CouncilService,
)
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.llama_cpp_cognition_client import LlamaCppCognitionClient
from living_world.cognition.meeting import MeetingService
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.npc_context import NPCContextAssembler
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
    """Run an opt-in five-NPC council through the loopback llama.cpp client."""

    _run(LlamaCppCognitionClient(model="qwen3-4b-q4-k-m"))


def _run(client: LlamaCppCognitionClient) -> None:
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
    print(format_council_result(result))


def format_council_result(result: CouncilResult) -> str:
    """Render the safe, operator-facing result of one council call."""

    if not isinstance(result, CouncilResult):
        raise TypeError("result must be a CouncilResult.")

    lines = ["Attendance"]
    for index, attendance in enumerate(result.attendance):
        role = "caller" if index == 0 else "invitee"
        status = "attending" if attendance.attending else "not attending"
        delegation = (
            "; delegates to majority" if attendance.delegates_to_majority else ""
        )
        lines.append(f"- {attendance.participant_label} ({role}): {status}{delegation}")

    caller_only = (
        bool(result.attendance)
        and result.attendance[0].attending
        and not any(attendance.attending for attendance in result.attendance[1:])
    )
    if caller_only:
        lines.append("Only the caller attended; no invited NPC joined.")

    lines.extend(("", "Invitation feedback"))
    for feedback in result.invitation_feedback:
        lines.append(f"- {feedback.participant_label}: {feedback.status.value}")
        if feedback.spoken_text is not None:
            lines.append(f"  statement: {feedback.spoken_text}")
        if feedback.rationale is not None:
            lines.append(f"  rationale: {feedback.rationale}")
        if feedback.diagnostic is not None:
            lines.append(
                "  No usable reply: "
                f"{feedback.diagnostic.value.replace('_', ' ')}."
            )
        elif feedback.spoken_text is None and feedback.rationale is None:
            lines.append("  No displayable text was supplied.")

    lines.extend(("", "Debate"))
    if result.conversation.turns:
        for turn in result.conversation.turns:
            lines.append(f"{turn.speaker_label}: {turn.utterance}")
    elif caller_only:
        lines.append("No debate was held because no invited NPC joined.")
    else:
        lines.append("No debate was held.")

    lines.extend(("", "Votes / proposals"))
    if result.conversation.proposals:
        for proposal in result.conversation.proposals:
            request = proposal.action_request
            lines.append(
                f"- {proposal.speaker_label}: {request.action_key} ({request.rationale})"
            )
    else:
        lines.append("No agenda proposal was cast.")

    lines.append(f"\nMajority proposal: {result.majority_proposal}")
    if result.resolutions:
        lines.append(f"Gateway resolution: {result.resolutions[0]}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
