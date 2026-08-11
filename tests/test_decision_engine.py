import pytest

from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext


class FakeClient:
    provider_name = "fake"

    def __init__(self, decision: NPCDecision) -> None:
        self.decision = decision
        self.received_context: NPCContext | None = None
        self.received_actions: tuple[ActionOption, ...] | None = None

    def decide(
        self,
        context: NPCContext,
        actions: tuple[ActionOption, ...],
    ) -> NPCDecision:
        self.received_context = context
        self.received_actions = actions
        return self.decision


def make_context() -> NPCContext:
    return NPCContext("Erik", (), ("A path lies ahead.",), (), ())


def make_actions() -> tuple[ActionOption, ...]:
    return (
        ActionOption("wait", "Wait quietly."),
        ActionOption("inspect", "Inspect what is visible.", ("the path",)),
    )


def test_decision_engine_returns_only_an_offered_proposal() -> None:
    expected = NPCDecision(
        "I will wait.",
        ActionRequest("wait", None, "A quiet pause is useful."),
    )
    client = FakeClient(expected)

    result = DecisionEngine(client).decide(make_context(), make_actions())

    assert result == expected
    assert client.received_context == make_context()
    assert client.received_actions == make_actions()


@pytest.mark.parametrize(
    "proposal",
    [
        ActionRequest("invent", None, "It seems useful."),
        ActionRequest("wait", "the path", "It seems useful."),
        ActionRequest("inspect", "another path", "It seems useful."),
    ],
)
def test_decision_engine_rejects_direct_client_decisions_outside_vocabulary(
    proposal: ActionRequest,
) -> None:
    client = FakeClient(NPCDecision(None, proposal))

    with pytest.raises(ValueError, match="offered vocabulary"):
        DecisionEngine(client).decide(make_context(), make_actions())


def test_decision_engine_does_not_supply_actor_identity_to_client() -> None:
    client = FakeClient(NPCDecision("I will wait.", None))

    DecisionEngine(client).decide(make_context(), make_actions())

    assert not hasattr(client, "actor_id")
