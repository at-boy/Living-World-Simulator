"""Opt-in five-NPC council scenario for a loopback llama.cpp server."""

import argparse

from living_world.cognition.action_resolution import ActionResolution, NPCActionResolver
from living_world.cognition.conversation import ConversationService
from living_world.cognition.council import (
    CouncilAgenda,
    CouncilCall,
    CouncilDecisionBasis,
    CouncilResult,
    CouncilService,
)
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.llama_cpp_cognition_client import LlamaCppCognitionClient
from living_world.cognition.local_llm_cognition_format import serialize_decision_request
from living_world.cognition.meeting import MeetingService
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCCognitionClient,
)
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.cognition.recording_cognition_client import (
    RecordedCognitionRequest,
    RecordingCognitionClient,
)
from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.simulation.simulation_engine import SimulationEngine

PERSPECTIVES: tuple[tuple[str, str], ...] = (
    ("Aster", "I favour careful preparation before travel."),
    ("Bryn", "I favour a swift route while daylight lasts."),
    ("Cato", "I favour conserving supplies for later."),
    ("Dara", "I favour preparing first so every concern can shape the plan."),
    ("Eris", "I favour the bold daybreak route that benefits the settlement."),
)
PARTICIPANT_IDS = tuple(f"entity_{number}" for number in range(401, 406))
ORGANIZATION_ID = "organization_301"
MAX_ROUNDS = 15
TURN_ORDER_OFFSET = 2
ACTIONS = (
    ActionOption("prepare_then_travel", "Prepare supplies before taking the journey."),
    ActionOption("travel_at_daybreak", "Take the quickest route at daybreak."),
    ActionOption("postpone_journey", "Postpone the journey and conserve supplies."),
)


class ManualCouncilActionHandler:
    """Accept offered demonstration choices without mutating simulation state."""

    def supports(self, action_key: str) -> bool:
        return action_key in {action.key for action in ACTIONS}

    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        return ActionResolution(
            True, "Manual council choice is valid for demonstration."
        )

    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        return ActionResolution(
            True, "Accepted for demonstration; world state unchanged."
        )


def main() -> None:
    """Run an opt-in five-NPC council through the loopback llama.cpp client."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--show-context", action="store_true", help="print filtered model requests"
    )
    args = parser.parse_args()
    _run(
        LlamaCppCognitionClient(model="qwen3-4b-q4-k-m"),
        show_context=args.show_context,
    )


def _run(client: NPCCognitionClient, *, show_context: bool = False) -> None:
    recording_client = RecordingCognitionClient(client)
    engine = SimulationEngine()
    engine.state.entities[ORGANIZATION_ID] = Entity(
        ORGANIZATION_ID, "organization", "Council"
    )
    for index, (identifier, (name, _)) in enumerate(
        zip(PARTICIPANT_IDS, PERSPECTIVES, strict=True), start=1
    ):
        engine.state.entities[identifier] = Entity(identifier, "npc", name)
        relationship_id = f"relationship_{index + 500}"
        engine.state.relationships[relationship_id] = Relationship(
            relationship_id, "member_of", identifier, ORGANIZATION_ID
        )
    assembler = NPCContextAssembler(engine.state)
    decisions = DecisionEngine(recording_client)
    resolver = NPCActionResolver(ACTIONS, (ManualCouncilActionHandler(),))
    conversation = ConversationService(
        assembler, decisions, resolver, engine.observations, ACTIONS
    )
    council = CouncilService(
        MeetingService(conversation),
        assembler,
        decisions,
        resolver,
        engine.state,
    )
    result = council.convene(
        call=CouncilCall(
            PARTICIPANT_IDS[0],
            ORGANIZATION_ID,
            PARTICIPANT_IDS[1:],
            CouncilAgenda(
                "how the settlement should approach a necessary risky journey", ACTIONS
            ),
            MAX_ROUNDS,
            participant_self_knowledge={
                identifier: (perspective,)
                for identifier, (_, perspective) in zip(
                    PARTICIPANT_IDS, PERSPECTIVES, strict=True
                )
            },
            turn_order_offset=TURN_ORDER_OFFSET,
        )
    )
    print(format_council_result(result))
    if show_context:
        print(format_context_trace(recording_client.recorded_requests))


def format_context_trace(requests: tuple[RecordedCognitionRequest, ...]) -> str:
    """Render only serialized, already-filtered cognition request inputs."""

    lines = ["", "Filtered cognition request context"]
    for index, recorded in enumerate(requests, start=1):
        lines.append(
            f"Request {index}: "
            f"{serialize_decision_request(recorded.context, recorded.actions)}"
        )
    return "\n".join(lines)


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
    if result.decision_basis is CouncilDecisionBasis.EXPLICIT_DECLINE_CALLER_FALLBACK:
        lines.append(
            "Every invitee explicitly declined and delegated one fallback proposal."
        )
    elif caller_only:
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
                "  No usable reply: " f"{feedback.diagnostic.value.replace('_', ' ')}."
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

    lines.append(f"\nDecision basis: {result.decision_basis}")
    proposal_label = (
        "Caller fallback proposal"
        if result.decision_basis
        is CouncilDecisionBasis.EXPLICIT_DECLINE_CALLER_FALLBACK
        else "Majority proposal"
    )
    lines.append(f"{proposal_label}: {result.majority_proposal}")
    if result.resolutions:
        lines.append(f"Gateway resolution: {result.resolutions[0]}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
