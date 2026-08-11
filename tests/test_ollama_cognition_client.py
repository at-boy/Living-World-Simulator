import pytest

from living_world.cognition.npc_cognition_client import (
    ActionOption,
    NPCCognitionClientError,
)
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.ollama_cognition_client import OllamaCognitionClient
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


def test_calls_ollama_with_structured_proposal_request() -> None:
    transport = StubJsonHttpTransport(
        {
            "response": (
                '{"spoken_text":"I will wait.","action_request":'
                '{"action_key":"wait","target_label":null,'
                '"rationale":"I need more information.","arguments":{}}}'
            )
        }
    )
    client = OllamaCognitionClient(model="qwen3:4b", transport=transport)

    decision = client.decide(make_context(), make_actions())

    assert decision.spoken_text == "I will wait."
    assert decision.action_request is not None
    assert client.provider_name == "ollama"
    url, payload, timeout = transport.calls[0]
    assert url == "http://127.0.0.1:11434/api/generate"
    assert payload["model"] == "qwen3:4b"
    assert payload["system"] == client.SYSTEM_INSTRUCTIONS
    assert payload["format"] == client.RESPONSE_SCHEMA
    assert payload["stream"] is False
    assert payload["think"] is False
    assert timeout == 30.0


def test_rejects_non_loopback_url_and_wraps_transport_errors() -> None:
    with pytest.raises(ValueError, match="loopback HTTP URL"):
        OllamaCognitionClient(model="qwen3:4b", base_url="https://ollama.com")
    client = OllamaCognitionClient(
        model="qwen3:4b", transport=FailingJsonHttpTransport()
    )
    with pytest.raises(NPCCognitionClientError, match="local Ollama server"):
        client.decide(make_context(), make_actions())
