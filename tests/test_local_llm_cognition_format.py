import json
import re

import pytest

from living_world.cognition.local_llm_cognition_format import (
    RESPONSE_SCHEMA,
    SYSTEM_INSTRUCTIONS,
    serialize_decision_request,
)
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.npc_context import NPCContext


def test_system_instructions_specify_complete_generic_response_shape() -> None:
    normalized_instructions = " ".join(SYSTEM_INSTRUCTIONS.split())
    for required_text in (
        "exactly one JSON object",
        "no surrounding prose or Markdown",
        "`spoken_text` and `action_request`",
        "`action_key`, `target_label`, `rationale`, and `arguments`",
        "use `{}` when no arguments are needed",
        "topic or agenda by itself as context",
        "begin with your own direct position",
        "respond only to that visible dialogue",
        '"spoken_text": "<NPC-visible string or null>"',
        '"action_key": "<supplied action key>"',
        '"target_label": "<supplied target label or null>"',
        '"rationale": "<NPC-visible rationale>"',
        '"arguments": {"<argument name>": "<string value>"}',
        '"action_request": null',
    ):
        assert required_text in normalized_instructions

    for forbidden_text in (
        "inspect",
        "wait",
        "oak",
        "Erik",
        "0.8",
    ):
        assert forbidden_text not in SYSTEM_INSTRUCTIONS
    assert (
        re.search(
            r"\\b(?:entity|memory|observation|knowledge|belief|event)_\\d+\\b",
            SYSTEM_INSTRUCTIONS,
        )
        is None
    )


def test_response_schema_retains_the_strict_shared_contract() -> None:
    assert RESPONSE_SCHEMA["required"] == ["spoken_text", "action_request"]
    assert RESPONSE_SCHEMA["additionalProperties"] is False
    action_request = RESPONSE_SCHEMA["properties"]
    assert isinstance(action_request, dict)
    action_request_schema = action_request["action_request"]
    assert isinstance(action_request_schema, dict)
    assert action_request_schema["type"] == ["object", "null"]


@pytest.mark.parametrize("forbidden_text", ("```", "#", "- action_key"))
def test_system_instruction_template_does_not_invite_markdown(
    forbidden_text: str,
) -> None:
    assert forbidden_text not in SYSTEM_INSTRUCTIONS


def test_serialized_complete_work_vocabulary_contains_only_safe_public_fields() -> None:
    actions = (
        ActionOption(
            "gather_water",
            "Propose gathering water for the settlement.",
            ("Gather from the stream",),
        ),
        ActionOption(
            "produce_food",
            "Propose producing food for the settlement.",
            ("Plant the first crop",),
        ),
        ActionOption(
            "build_shelter",
            "Propose building shelter for the settlement.",
            ("Raise a shared shelter",),
        ),
        ActionOption(
            "build_storage",
            "Propose building storage for the settlement.",
            ("Raise a storehouse",),
        ),
        ActionOption(
            "maintain_capability",
            "Propose maintaining a settlement capability.",
            ("Care for the village well",),
        ),
        ActionOption(
            "establish_external_trade_connection",
            "Propose establishing an external trade connection.",
            ("Open trade with the river guild",),
        ),
        ActionOption(
            "prioritize_work",
            "Propose changing the priority of one offered work order.",
            ("Raise the orchard priority",),
        ),
        ActionOption(
            "volunteer_for_work",
            "Volunteer for one offered work order.",
            ("Volunteer for the garden",),
        ),
    )
    payload = json.loads(
        serialize_decision_request(
            NPCContext("Mara", (), (), (), ()),
            actions,
        )
    )
    assert payload["actions"] == [
        {
            "key": action.key,
            "description": action.description,
            "target_labels": list(action.target_labels),
        }
        for action in actions
    ]
    encoded = json.dumps(payload["actions"])
    for hidden_field in (
        "settlement_id",
        "objective_id",
        "location_id",
        "work_id",
        "prerequisite_work_ids",
        "labor_required",
        "tools",
        "resources",
        "required_progress",
        '"priority":',
        "deadline_tick",
        "definition_key",
        "policy_id",
        "reference_id",
        "quantity",
    ):
        assert hidden_field not in encoded
