import re

import pytest

from living_world.cognition.local_llm_cognition_format import (
    RESPONSE_SCHEMA,
    SYSTEM_INSTRUCTIONS,
)


def test_system_instructions_specify_complete_generic_response_shape() -> None:
    for required_text in (
        "exactly one JSON object",
        "no surrounding prose or Markdown",
        "`spoken_text` and `action_request`",
        "`action_key`, `target_label`, `rationale`, and `arguments`",
        "use `{}` when no arguments are needed",
        '"spoken_text": "<NPC-visible string or null>"',
        '"action_key": "<supplied action key>"',
        '"target_label": "<supplied target label or null>"',
        '"rationale": "<NPC-visible rationale>"',
        '"arguments": {"<argument name>": "<string value>"}',
        '"action_request": null',
    ):
        assert required_text in SYSTEM_INSTRUCTIONS

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
