import pytest

from living_world.cognition.llama_cpp_cognition_client import LlamaCppCognitionClient
from living_world.cognition.local_llm_cognition_format import (
    RESPONSE_SCHEMA,
    SYSTEM_INSTRUCTIONS,
)
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    NPCCognitionClientError,
)
from living_world.cognition.npc_context import NPCContext
from living_world.perception.local_llm_http import LocalLLMHttpError


class StubJsonHttpTransport:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object], float]] = []

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        self.calls.append((url, payload, timeout_seconds))
        return self.response


class FailingJsonHttpTransport:
    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        raise LocalLLMHttpError("Local LLM server is unavailable.")


def make_context() -> NPCContext:
    return NPCContext("Erik", (), ("An oak is nearby.",), (), ())


def make_actions() -> tuple[ActionOption, ...]:
    return (ActionOption("wait", "Wait and observe."),)


def test_calls_llama_cpp_with_structured_proposal_request() -> None:
    transport = StubJsonHttpTransport(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"spoken_text":null,"action_request":'
                            '{"action_key":"wait","target_label":null,'
                            '"rationale":"I need more information.","arguments":{}}}'
                        )
                    }
                }
            ]
        }
    )
    client = LlamaCppCognitionClient(model="qwen3.gguf", transport=transport)

    decision = client.decide(make_context(), make_actions())

    assert decision.action_request is not None
    assert client.provider_name == "llama.cpp"
    url, payload, timeout = transport.calls[0]
    assert url == "http://127.0.0.1:8080/v1/chat/completions"
    assert payload["model"] == "qwen3.gguf"
    assert payload["response_format"] == {
        "type": "json_object",
        "schema": RESPONSE_SCHEMA,
    }
    assert payload["messages"][0] == {
        "role": "system",
        "content": SYSTEM_INSTRUCTIONS,
    }
    assert client.SYSTEM_INSTRUCTIONS == SYSTEM_INSTRUCTIONS
    assert client.RESPONSE_SCHEMA == RESPONSE_SCHEMA
    assert timeout == 30.0


def test_rejects_non_loopback_url_and_wraps_transport_errors() -> None:
    with pytest.raises(ValueError, match="loopback HTTP URL"):
        LlamaCppCognitionClient(model="qwen3.gguf", base_url="https://remote.test")
    client = LlamaCppCognitionClient(
        model="qwen3.gguf", transport=FailingJsonHttpTransport()
    )
    with pytest.raises(NPCCognitionClientError, match="local llama.cpp server"):
        client.decide(make_context(), make_actions())
