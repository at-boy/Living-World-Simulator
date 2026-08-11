"""Structured local-model format for proposal-only NPC cognition."""

from __future__ import annotations

import json
from collections.abc import Mapping

from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCCognitionClientError,
    NPCCognitionInvalidResponseError,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.retrieval import RetrievedCognition

SYSTEM_INSTRUCTIONS = """You are reasoning as an NPC in a simulation.
Use only the supplied NPC-readable context and offered action vocabulary. Your
proposed action is not authoritative and does not execute it. Do not claim
action success. Do not invent identifiers, hidden state, evidence, metadata,
raw attributes, numerical capabilities, tools, or actions outside the offered
vocabulary.

Treat a topic or agenda by itself as context, not as something a prior speaker
said. When no labelled prior dialogue is present, begin with your own direct
position; do not use acknowledgement language such as "I see" or "I agree" as
though replying to non-existent dialogue. When labelled prior dialogue is
present, respond only to that visible dialogue. Never invent unseen speakers or
claims beyond the supplied NPC-readable context.

Return exactly one JSON object and no surrounding prose or Markdown, including
no code fence. The object must contain both top-level fields: `spoken_text` and `action_request`.
Set `spoken_text` to an NPC-visible string or `null`. Set
`action_request` to `null` when you genuinely do not propose an action. When
you do propose an action, `action_request` must contain all four fields:
`action_key`, `target_label`, `rationale`, and `arguments`. Use one supplied
action key, use a supplied target label or `null` when no target is offered,
provide an NPC-visible rationale string, and use `{}` when no arguments are needed.

Response shape when proposing an action:
{
  "spoken_text": "<NPC-visible string or null>",
  "action_request": {
    "action_key": "<supplied action key>",
    "target_label": "<supplied target label or null>",
    "rationale": "<NPC-visible rationale>",
    "arguments": {"<argument name>": "<string value>"}
  }
}

Response shape when not proposing an action:
{
  "spoken_text": "<NPC-visible string or null>",
  "action_request": null
}"""

RESPONSE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "spoken_text": {"type": ["string", "null"]},
        "action_request": {
            "type": ["object", "null"],
            "properties": {
                "action_key": {"type": "string"},
                "target_label": {"type": ["string", "null"]},
                "rationale": {"type": "string"},
                "arguments": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["action_key", "target_label", "rationale", "arguments"],
            "additionalProperties": False,
        },
    },
    "required": ["spoken_text", "action_request"],
    "additionalProperties": False,
}


def serialize_decision_request(
    context: NPCContext,
    actions: tuple[ActionOption, ...],
) -> str:
    """Encode only filtered context and offered proposal vocabulary as JSON."""

    if not isinstance(context, NPCContext):
        raise TypeError("context must be an NPCContext.")
    _validate_actions(actions)
    payload = {
        "identity": context.identity,
        "self_knowledge": context.self_knowledge,
        "current_perceptions": context.current_perceptions,
        "core_cognition": tuple(
            _serialize_cognition(item) for item in context.core_cognition
        ),
        "retrieved_information": tuple(
            _serialize_cognition(item) for item in context.retrieved_information
        ),
        "conversation_history": context.conversation_history,
        "actions": tuple(
            {
                "key": action.key,
                "description": action.description,
                "target_labels": action.target_labels,
            }
            for action in actions
        ),
    }
    try:
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as error:
        raise NPCCognitionClientError(
            "NPC cognition request could not be encoded for the local model."
        ) from error


def parse_decision_response(
    content: object,
    actions: tuple[ActionOption, ...],
) -> NPCDecision:
    """Validate an untrusted JSON proposal against the offered vocabulary."""

    _validate_actions(actions)
    if not isinstance(content, str):
        raise _invalid_response()
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as error:
        raise _invalid_response() from error
    if not isinstance(decoded, Mapping) or set(decoded) != {
        "spoken_text",
        "action_request",
    }:
        raise _invalid_response()

    spoken_text = decoded["spoken_text"]
    if spoken_text is not None and (
        not isinstance(spoken_text, str) or not spoken_text.strip()
    ):
        raise _invalid_response()
    action_request = _parse_action_request(decoded["action_request"], actions)
    try:
        return NPCDecision(spoken_text=spoken_text, action_request=action_request)
    except (TypeError, ValueError) as error:
        raise _invalid_response() from error


def _serialize_cognition(item: RetrievedCognition) -> dict[str, object]:
    return {
        "kind": item.kind,
        "text": item.text,
        "importance": item.importance,
        "is_core": item.is_core,
    }


def _parse_action_request(
    value: object,
    actions: tuple[ActionOption, ...],
) -> ActionRequest | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {
        "action_key",
        "target_label",
        "rationale",
        "arguments",
    }:
        raise _invalid_response()
    action_key = value["action_key"]
    target_label = value["target_label"]
    rationale = value["rationale"]
    arguments = value["arguments"]
    if not isinstance(action_key, str) or not isinstance(rationale, str):
        raise _invalid_response()
    if target_label is not None and not isinstance(target_label, str):
        raise _invalid_response()
    if not isinstance(arguments, Mapping) or any(
        not isinstance(key, str) or not isinstance(argument, str)
        for key, argument in arguments.items()
    ):
        raise _invalid_response()
    option = next((option for option in actions if option.key == action_key), None)
    if option is None:
        raise _invalid_response()
    if option.target_labels:
        if target_label not in option.target_labels:
            raise _invalid_response()
    elif target_label is not None:
        raise _invalid_response()
    try:
        return ActionRequest(
            action_key=action_key,
            target_label=target_label,
            rationale=rationale,
            arguments=dict(arguments),
        )
    except (TypeError, ValueError) as error:
        raise _invalid_response() from error


def _validate_actions(actions: object) -> None:
    if not isinstance(actions, tuple):
        raise TypeError("actions must be a tuple of ActionOption values.")
    if not all(isinstance(action, ActionOption) for action in actions):
        raise TypeError("actions must contain only ActionOption values.")
    keys = tuple(action.key for action in actions)
    if len(keys) != len(set(keys)):
        raise ValueError("actions must have unique keys.")


def _invalid_response() -> NPCCognitionInvalidResponseError:
    return NPCCognitionInvalidResponseError(
        "Provider returned an invalid NPC cognition response."
    )
