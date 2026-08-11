"""Opt-in five-NPC council scenario for a loopback llama.cpp server."""

import argparse

from council_scenarios import (
    DEFAULT_SCENARIO_NAME,
    JOURNEY,
    SCENARIO_NAMES,
    ManualCouncilScenario,
    get_scenario,
)

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

PERSPECTIVES = tuple(
    (participant.name, participant.self_knowledge)
    for participant in JOURNEY.participants
)
PARTICIPANT_IDS = JOURNEY.participant_ids
ORGANIZATION_ID = JOURNEY.organization_id
MAX_ROUNDS = JOURNEY.max_rounds
TURN_ORDER_OFFSET = JOURNEY.turn_order_offset
ACTIONS = JOURNEY.actions


class ManualCouncilActionHandler:
    """Accept offered demonstration choices without mutating simulation state."""

    def __init__(self, actions: tuple[ActionOption, ...] = ACTIONS) -> None:
        self._action_keys = frozenset(action.key for action in actions)

    def supports(self, action_key: str) -> bool:
        return action_key in self._action_keys

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
    parser.add_argument(
        "--scenario",
        choices=SCENARIO_NAMES,
        default=DEFAULT_SCENARIO_NAME,
        help="select a deterministic manual council scenario",
    )
    args = parser.parse_args()
    _run(
        LlamaCppCognitionClient(model="qwen3-4b-q4-k-m"),
        show_context=args.show_context,
        scenario=get_scenario(args.scenario),
    )


def _run(
    client: NPCCognitionClient,
    *,
    show_context: bool = False,
    scenario: ManualCouncilScenario = JOURNEY,
) -> None:
    recording_client = RecordingCognitionClient(client)
    engine = SimulationEngine()
    engine.state.entities[scenario.organization_id] = Entity(
        scenario.organization_id, "organization", scenario.organization_name
    )
    for index, participant in enumerate(scenario.participants, start=1):
        engine.state.entities[participant.identifier] = Entity(
            participant.identifier, "npc", participant.name
        )
        relationship_id = f"relationship_{index + 500}"
        engine.state.relationships[relationship_id] = Relationship(
            relationship_id,
            "member_of",
            participant.identifier,
            scenario.organization_id,
        )
    assembler = NPCContextAssembler(engine.state)
    decisions = DecisionEngine(recording_client)
    resolver = NPCActionResolver(
        scenario.actions, (ManualCouncilActionHandler(scenario.actions),)
    )
    conversation = ConversationService(
        assembler, decisions, resolver, engine.observations, scenario.actions
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
            scenario.participant_ids[0],
            scenario.organization_id,
            scenario.participant_ids[1:],
            CouncilAgenda(scenario.agenda, scenario.actions),
            scenario.max_rounds,
            participant_self_knowledge={
                participant.identifier: (participant.self_knowledge,)
                for participant in scenario.participants
            },
            turn_order_offset=scenario.turn_order_offset,
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
