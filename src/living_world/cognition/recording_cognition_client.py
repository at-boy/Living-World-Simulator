"""Safe request-only recording decorator for NPC cognition clients."""

from __future__ import annotations

from dataclasses import dataclass

from living_world.cognition.npc_cognition_client import (
    ActionOption,
    NPCCognitionClient,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext


@dataclass(frozen=True, slots=True)
class RecordedCognitionRequest:
    """One already-filtered cognition request, captured before provider use."""

    context: NPCContext
    actions: tuple[ActionOption, ...]


class RecordingCognitionClient:
    """Record safe request inputs while transparently delegating cognition."""

    def __init__(self, inner: NPCCognitionClient) -> None:
        self._inner = inner
        self._recorded_requests: list[RecordedCognitionRequest] = []

    @property
    def provider_name(self) -> str:
        """Return the wrapped provider identifier unchanged."""

        return self._inner.provider_name

    @property
    def recorded_requests(self) -> tuple[RecordedCognitionRequest, ...]:
        """Return an immutable snapshot of recorded safe requests."""

        return tuple(self._recorded_requests)

    def decide(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> NPCDecision:
        """Record only request inputs, then delegate once without interception."""

        self._recorded_requests.append(RecordedCognitionRequest(context, actions))
        return self._inner.decide(context, actions)
