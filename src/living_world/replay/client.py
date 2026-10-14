"""Stateless filtered-context adapter; no simulation authority."""

from living_world.cognition.npc_cognition_client import ActionOption, NPCDecision
from living_world.cognition.npc_context import NPCContext
from living_world.replay.model import ProposalTapeEntry, ProposalTapeError


class RecordedProposalClient:
    provider_name = "recorded_proposals"

    def __init__(self, entry: ProposalTapeEntry, *, expected_identity: str) -> None:
        self._entry = entry
        self._expected_identity = expected_identity

    def decide(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> NPCDecision:
        if (
            not isinstance(context, NPCContext)
            or context.identity != self._expected_identity
        ):
            raise ProposalTapeError("actor_mismatch")
        request = self._entry.decision.action_request
        if request is not None:
            option = next(
                (option for option in actions if option.key == request.action_key), None
            )
            if option is None or (
                request.target_label not in option.target_labels
                if option.target_labels
                else request.target_label is not None
            ):
                raise ProposalTapeError("offered_action_mismatch")
        return self._entry.decision
