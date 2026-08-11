"""Tests for safe cognition request recording."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from living_world.cognition.npc_cognition_client import (
    ActionOption,
    NPCCognitionClientError,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.recording_cognition_client import RecordingCognitionClient


class _Client:
    provider_name = "test-provider"

    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[NPCContext, tuple[ActionOption, ...]]] = []

    def decide(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> NPCDecision:
        self.calls.append((context, actions))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, NPCDecision)
        return outcome


def _context(identity: str) -> NPCContext:
    return NPCContext(identity, ("I attend council meetings.",), (), (), ())


def test_records_safe_requests_in_order_and_returns_immutable_snapshot() -> None:
    first_decision = NPCDecision("First answer.", None)
    second_decision = NPCDecision("Second answer.", None)
    inner = _Client([first_decision, second_decision])
    client = RecordingCognitionClient(inner)
    first_context = _context("Aster")
    second_context = _context("Bryn")
    actions = (ActionOption("prepare", "Prepare carefully."),)

    assert client.provider_name == "test-provider"
    assert client.decide(first_context, actions) is first_decision
    snapshot = client.recorded_requests
    assert client.decide(second_context, actions) is second_decision

    assert tuple(item.context for item in client.recorded_requests) == (
        first_context,
        second_context,
    )
    assert snapshot == (client.recorded_requests[0],)
    assert inner.calls == [(first_context, actions), (second_context, actions)]
    with pytest.raises(FrozenInstanceError):
        snapshot[0].context = second_context  # type: ignore[misc]


def test_error_is_reraised_unchanged_without_recording_error_or_response() -> None:
    error = NPCCognitionClientError("private provider payload")
    inner = _Client([error])
    client = RecordingCognitionClient(inner)
    context = _context("Aster")
    actions = (ActionOption("prepare", "Prepare carefully."),)

    with pytest.raises(NPCCognitionClientError) as caught:
        client.decide(context, actions)

    assert caught.value is error
    assert client.recorded_requests[0].context is context
    assert client.recorded_requests[0].actions is actions
    assert not hasattr(client.recorded_requests[0], "response")
    assert not hasattr(client.recorded_requests[0], "error")
    assert len(inner.calls) == 1
