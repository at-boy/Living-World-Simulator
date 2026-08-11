"""Validation wrapper for untrusted, proposal-only NPC cognition."""

from __future__ import annotations

from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCCognitionClient,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext


class DecisionEngine:
    """Request and validate an NPC proposal against offered action vocabulary."""

    def __init__(self, client: NPCCognitionClient) -> None:
        if not callable(getattr(client, "decide", None)):
            raise TypeError("client must provide a decide method.")
        self._client = client

    def decide(
        self,
        context: NPCContext,
        actions: tuple[ActionOption, ...],
    ) -> NPCDecision:
        """Return a vocabulary-valid proposal without applying any action."""

        if not isinstance(context, NPCContext):
            raise TypeError("context must be an NPCContext.")
        _validate_actions(actions)
        decision = self._client.decide(context, actions)
        if not isinstance(decision, NPCDecision):
            raise TypeError("client decide must return an NPCDecision.")
        if decision.action_request is not None and not _request_is_offered(
            decision.action_request, actions
        ):
            raise ValueError(
                "NPC decision action request is outside offered vocabulary."
            )
        return decision


def _validate_actions(actions: object) -> None:
    if not isinstance(actions, tuple):
        raise TypeError("actions must be a tuple of ActionOption values.")
    if not all(isinstance(action, ActionOption) for action in actions):
        raise TypeError("actions must contain only ActionOption values.")
    keys = tuple(action.key for action in actions)
    if len(keys) != len(set(keys)):
        raise ValueError("actions must have unique keys.")


def _request_is_offered(
    request: ActionRequest,
    actions: tuple[ActionOption, ...],
) -> bool:
    option = next(
        (action for action in actions if action.key == request.action_key), None
    )
    if option is None:
        return False
    if option.target_labels:
        return request.target_label in option.target_labels
    return request.target_label is None
