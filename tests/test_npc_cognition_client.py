import json
from collections.abc import Callable

import pytest

from living_world.cognition.local_llm_cognition_format import (
    parse_decision_response,
    serialize_decision_request,
)
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCCognitionInvalidResponseError,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.retrieval import RetrievedCognition


def make_context() -> NPCContext:
    return NPCContext(
        identity="Erik",
        self_knowledge=("I know the local forest.",),
        current_perceptions=("A mature oak stands nearby.",),
        core_cognition=(
            RetrievedCognition(
                kind="memory",
                text="I remember the oak is sturdy.",
                importance=0.8,
                is_core=True,
            ),
        ),
        retrieved_information=(),
    )


def make_actions() -> tuple[ActionOption, ...]:
    return (
        ActionOption(
            key="inspect",
            description="Inspect a visible subject.",
            target_labels=("the oak",),
        ),
        ActionOption(key="wait", description="Wait and observe."),
    )


def test_serializes_only_npc_context_and_offered_action_vocabulary() -> None:
    request = json.loads(serialize_decision_request(make_context(), make_actions()))

    assert request == {
        "actions": [
            {
                "description": "Inspect a visible subject.",
                "key": "inspect",
                "target_labels": ["the oak"],
            },
            {"description": "Wait and observe.", "key": "wait", "target_labels": []},
        ],
        "core_cognition": [
            {
                "importance": 0.8,
                "is_core": True,
                "kind": "memory",
                "text": "I remember the oak is sturdy.",
            }
        ],
        "conversation_history": [],
        "current_perceptions": ["A mature oak stands nearby."],
        "identity": "Erik",
        "retrieved_information": [],
        "self_knowledge": ["I know the local forest."],
    }
    encoded = json.dumps(request)
    for forbidden in (
        "WorldState",
        "entity_id",
        "attributes",
        "evidence",
        "metadata",
        "provenance",
        "woodcraft",
    ):
        assert forbidden not in encoded


def test_parses_offered_action_proposal_without_side_effects() -> None:
    decision = parse_decision_response(
        (
            '{"spoken_text":"I will inspect the oak.","action_request":'
            '{"action_key":"inspect","target_label":"the oak",'
            '"rationale":"It may be useful.","arguments":{"care":"gently"}}}'
        ),
        make_actions(),
    )

    assert decision == NPCDecision(
        spoken_text="I will inspect the oak.",
        action_request=ActionRequest(
            action_key="inspect",
            target_label="the oak",
            rationale="It may be useful.",
            arguments={"care": "gently"},
        ),
    )
    assert dict(decision.action_request.arguments) == {"care": "gently"}


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        '{"spoken_text":"hello"}',
        '{"spoken_text":"hello","action_request":null,"extra":true}',
        '{"spoken_text":null,"action_request":null}',
        (
            '{"spoken_text":null,"action_request":{"action_key":"invent",'
            '"target_label":null,"rationale":"because","arguments":{}}}'
        ),
        (
            '{"spoken_text":null,"action_request":{"action_key":"wait",'
            '"target_label":"the oak","rationale":"because","arguments":{}}}'
        ),
        (
            '{"spoken_text":null,"action_request":{"action_key":"inspect",'
            '"target_label":"unknown","rationale":"because","arguments":{}}}'
        ),
    ],
)
def test_rejects_invalid_or_unoffered_model_proposals(content: str) -> None:
    with pytest.raises(NPCCognitionInvalidResponseError):
        parse_decision_response(content, make_actions())


def test_value_objects_are_validated_and_arguments_are_immutable() -> None:
    arguments = {"care": "gently"}
    request = ActionRequest(
        action_key="wait",
        target_label=None,
        rationale="I should pause.",
        arguments=arguments,
    )
    arguments["care"] = "roughly"

    assert dict(request.arguments) == {"care": "gently"}
    with pytest.raises(TypeError):
        request.arguments["new"] = "value"  # type: ignore[index]
    with pytest.raises(ValueError, match="unique"):
        ActionOption("inspect", "Inspect.", ("the oak", "the oak"))


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ActionOption("entity_000001", "Inspect."),
        lambda: ActionOption("inspect", "Inspect observation_000001."),
        lambda: ActionOption("inspect", "Inspect.", ("memory_000001",)),
        lambda: ActionRequest(
            "inspect",
            "the oak",
            "I saw belief_000001.",
        ),
        lambda: ActionRequest(
            "inspect",
            "the oak",
            "I should inspect it.",
            {"event_000001": "quietly"},
        ),
        lambda: NPCDecision("I remember knowledge_000001.", None),
    ],
)
def test_rejects_internal_record_ids_in_client_visible_values(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValueError, match="internal record ID"):
        factory()


@pytest.mark.parametrize(
    "content",
    [
        ('{"spoken_text":"I saw entity_000001.","action_request":null}'),
        (
            '{"spoken_text":null,"action_request":{"action_key":"wait",'
            '"target_label":null,"rationale":"I remember memory_000001.",'
            '"arguments":{}}}'
        ),
    ],
)
def test_parsed_provider_output_rejects_internal_record_ids(content: str) -> None:
    with pytest.raises(NPCCognitionInvalidResponseError):
        parse_decision_response(content, make_actions())
