"""Versioned provider constraints preserve proposal parsing and legacy bytes."""

import hashlib
import json
from copy import deepcopy

import pytest

from living_world.cognition import local_llm_cognition_format as format_module
from living_world.cognition.llama_cpp_cognition_client import LlamaCppCognitionClient
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.ollama_cognition_client import OllamaCognitionClient
from living_world.runtime.broker import encoded_body

NEW = "founders_empty_arguments_v1"
OFFER_BOUND = "founders_offer_bound_v1"
CONTEXT = NPCContext("Erik", (), ("An oak is nearby.",), (), ())
ACTIONS = (ActionOption("wait", "Wait and observe."),)


@pytest.mark.parametrize(
    "client_type", [OllamaCognitionClient, LlamaCppCognitionClient]
)
def test_selected_contract_constrains_schema_without_mutating_legacy(client_type):
    legacy = client_type(model="tiny", seed=7)
    selected = client_type(model="tiny", seed=7, request_contract=NEW)
    other = client_type(model="tiny", request_contract=NEW)
    prompt, schema = format_module.request_contract_format(NEW)
    expected_schema = deepcopy(format_module.RESPONSE_SCHEMA)
    expected_schema["properties"]["action_request"]["properties"]["arguments"] = {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    assert schema == expected_schema
    assert selected.SYSTEM_INSTRUCTIONS == prompt
    assert selected.RESPONSE_SCHEMA == schema
    assert schema["properties"]["action_request"]["properties"]["arguments"] == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    assert '"arguments": {}' in prompt and "<argument name>" not in prompt
    assert prompt.endswith("only in target_label; never duplicate it in arguments.")
    assert legacy.RESPONSE_SCHEMA is format_module.RESPONSE_SCHEMA
    assert legacy.SYSTEM_INSTRUCTIONS == format_module.SYSTEM_INSTRUCTIONS
    selected.RESPONSE_SCHEMA["properties"]["spoken_text"]["test"] = True
    assert "test" not in other.RESPONSE_SCHEMA["properties"]["spoken_text"]
    assert "test" not in legacy.RESPONSE_SCHEMA["properties"]["spoken_text"]


@pytest.mark.parametrize(
    "client_type,body_hash,input_hash",
    [
        (
            OllamaCognitionClient,
            "3152d6ed472fec0b74f25d852052fe7313595d4edff025f59d3870e707ca7824",
            "67f70f9bdc6b8a606eb3cc84efa6574a9baa7d122858cb4642d60538690aa143",
        ),
        (
            LlamaCppCognitionClient,
            "1a5e0d03ca2944fc64bed27d341afd729ca897bc213a0888f2311ad3ec169619",
            "104a2a73c5492488d0debd66c7bd3dfb6c4c6abbbd0fbc7ffbd673cfff8ba2a8",
        ),
    ],
)
def test_baseline_legacy_bytes_and_input_hash(client_type, body_hash, input_hash):
    for kwargs in ({}, {"request_contract": "legacy_v1"}):
        payload = client_type(model="tiny", seed=7, **kwargs).build_payload(
            CONTEXT, ACTIONS
        )
        assert hashlib.sha256(encoded_body(payload).encode()).hexdigest() == body_hash
        value = {"feedback_input": "a" * 64, "payload": payload}
        assert hashlib.sha256(encoded_body(value).encode()).hexdigest() == input_hash
    new_payload = client_type(model="tiny", seed=7, request_contract=NEW).build_payload(
        CONTEXT, ACTIONS
    )
    assert hashlib.sha256(encoded_body(new_payload).encode()).hexdigest() != body_hash


@pytest.mark.parametrize("value", [None, True, False, 1, "unknown", ""])
def test_helper_and_clients_reject_invalid_selectors(value):
    for factory in (
        format_module.request_contract_format,
        lambda v: OllamaCognitionClient(model="tiny", request_contract=v),
        lambda v: LlamaCppCognitionClient(model="tiny", request_contract=v),
    ):
        with pytest.raises((ValueError, TypeError)):
            factory(value)


def test_selected_contract_does_not_coerce_untrusted_arguments():
    content = json.dumps(
        {
            "spoken_text": None,
            "action_request": {
                "action_key": "wait",
                "target_label": None,
                "rationale": "Wait.",
                "arguments": {"target": "oak"},
            },
        }
    )
    decision = format_module.parse_decision_response(content, ACTIONS)
    assert dict(decision.action_request.arguments) == {"target": "oak"}


def test_legacy_helper_returns_original_constants():
    instructions, schema = format_module.request_contract_format("legacy_v1")
    assert instructions is format_module.SYSTEM_INSTRUCTIONS
    assert schema is format_module.RESPONSE_SCHEMA


@pytest.mark.parametrize(
    "client_type,body_hash,input_hash",
    [
        (
            OllamaCognitionClient,
            "38f21b1222dcba443d5187b6ca9e91782498bc66070863118ce949f468aaa610",
            "4440c46dfe3c3a9217177d820ad6c6f64d56842c8ac89e3e4724931ed9bc6d7e",
        ),
        (
            LlamaCppCognitionClient,
            "cd102a807a764aec77923afac9edac1a729a68eac5d7e4181086fe4cd0d73185",
            "9bf3e9fc13f5c567bb969598e4d3b41b20288259f7a0e73cafecdffcaa660c06",
        ),
    ],
)
def test_baseline_empty_arguments_bytes_and_input_hash(
    client_type, body_hash, input_hash
):
    client = client_type(model="tiny", seed=7, request_contract=NEW)
    payload = client.build_payload(CONTEXT, ACTIONS)
    assert hashlib.sha256(encoded_body(payload).encode()).hexdigest() == body_hash
    value = {"feedback_input": "a" * 64, "payload": payload}
    assert hashlib.sha256(encoded_body(value).encode()).hexdigest() == input_hash


def test_offer_bound_base_format_matches_empty_arguments_format():
    prompt, schema = format_module.request_contract_format(OFFER_BOUND)
    prior = format_module.request_contract_format(NEW)
    assert (prompt, schema) == prior
    schema["properties"]["action_request"]["properties"]["arguments"]["changed"] = True
    assert format_module.request_contract_format(OFFER_BOUND) == prior
    assert format_module.request_contract_format(NEW) == prior


def _offered_branch(key, target):
    return {
        "type": "object",
        "properties": {
            "action_key": {"type": "string", "enum": [key]},
            "target_label": target,
            "rationale": {"type": "string"},
            "arguments": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        "required": ["action_key", "target_label", "rationale", "arguments"],
        "additionalProperties": False,
    }


@pytest.mark.parametrize(
    "client_type", [OllamaCognitionClient, LlamaCppCognitionClient]
)
def test_offer_bound_only_changes_wire_action_schema_and_isolates_requests(client_type):
    offers = (
        ActionOption("gather", "Collect supplies.", ("Oak", "Ash")),
        ActionOption("inspect", "Check storage.", ("Chest",)),
        ACTIONS[0],
    )
    client = client_type(model="tiny", seed=7, request_contract=OFFER_BOUND)
    prior = client_type(model="tiny", seed=7, request_contract=NEW)

    def schema_for(payload):
        return (
            payload["format"]
            if "format" in payload
            else payload["response_format"]["schema"]
        )

    expected = deepcopy(prior.build_payload(CONTEXT, offers))
    schema_for(expected)["properties"]["action_request"] = {
        "anyOf": [
            {"type": "null"},
            _offered_branch("gather", {"type": "string", "enum": ["Oak", "Ash"]}),
            _offered_branch("inspect", {"type": "string", "enum": ["Chest"]}),
            _offered_branch("wait", {"type": "null"}),
        ],
    }
    first = client.build_payload(CONTEXT, offers)
    assert first == expected
    schema = schema_for(first)
    first_branch, second_branch = schema["properties"]["action_request"]["anyOf"][1:3]
    first_branch["required"].clear()
    first_branch["properties"]["arguments"]["properties"]["inserted"] = {}
    assert second_branch == _offered_branch(
        "inspect", {"type": "string", "enum": ["Chest"]}
    )
    schema["properties"]["spoken_text"]["type"].clear()
    assert client.build_payload(CONTEXT, offers) == expected
    assert client.RESPONSE_SCHEMA == prior.RESPONSE_SCHEMA

    empty = deepcopy(prior.build_payload(CONTEXT, ()))
    schema_for(empty)["properties"]["action_request"] = {"type": "null"}
    assert client.build_payload(CONTEXT, ()) == empty
    assert client.build_payload(CONTEXT, offers) == expected
    assert offers[0].target_labels == ("Oak", "Ash")


@pytest.mark.parametrize(
    "offers,error",
    [([], TypeError), ((object(),), TypeError), (ACTIONS * 2, ValueError)],
)
def test_offer_schema_helper_rejects_invalid_action_tuple(offers, error):
    helper = getattr(format_module, "offer_bound_response_schema", None)
    assert callable(helper)
    _, schema = format_module.request_contract_format(NEW)
    untouched = deepcopy(schema)
    with pytest.raises(error):
        helper(schema, offers)
    assert schema == untouched
