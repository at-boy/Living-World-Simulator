import pytest

from living_world.perception.llm_perception_client import (
    LLMPerceptionClientError,
    LLMPerceptionRequest,
)
from living_world.perception.local_llm_http import LocalLLMHttpError
from living_world.perception.ollama_perception_client import OllamaPerceptionClient


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
        raise LocalLLMHttpError("Local LLM server returned HTTP 500.")


def make_request() -> LLMPerceptionRequest:
    return LLMPerceptionRequest(
        observer_name="Erik",
        capabilities={"woodcraft": 80},
        subject_name="Old Oak",
        subject_attributes={"growth": 87, "health": 92, "wood": 120},
    )


def test_calls_ollama_generate_api_with_structured_local_request() -> None:
    transport = StubJsonHttpTransport(
        {
            "response": '{"description":"The Old Oak appears mature.","confidence":0.8}',
        }
    )
    client = OllamaPerceptionClient(
        model="qwen3:4b",
        transport=transport,
    )

    response = client.perceive(make_request())

    assert response.description == "The Old Oak appears mature."
    assert response.confidence == 0.8
    assert client.provider_name == "ollama"
    assert transport.calls == [
        (
            "http://127.0.0.1:11434/api/generate",
            {
                "model": "qwen3:4b",
                "system": client.SYSTEM_INSTRUCTIONS,
                "prompt": (
                    '{"capabilities":{"woodcraft":80},"observer_name":"Erik",'
                    '"subject_attributes":{"growth":87,"health":92,"wood":120},'
                    '"subject_name":"Old Oak"}'
                ),
                "stream": False,
                "think": False,
                "format": client.RESPONSE_SCHEMA,
            },
            30.0,
        )
    ]


@pytest.mark.parametrize(
    "server_response",
    [
        {},
        {"response": "not json"},
        {"response": "{}"},
        {"response": '{"description":"A tree.","confidence":"high"}'},
    ],
)
def test_rejects_malformed_ollama_response(
    server_response: dict[str, object],
) -> None:
    client = OllamaPerceptionClient(
        model="qwen3:4b",
        transport=StubJsonHttpTransport(server_response),
    )

    with pytest.raises(LLMPerceptionClientError, match="invalid perception response"):
        client.perceive(make_request())


def test_wraps_local_http_failure() -> None:
    client = OllamaPerceptionClient(
        model="qwen3:4b",
        transport=FailingJsonHttpTransport(),
    )

    with pytest.raises(LLMPerceptionClientError, match="local Ollama server"):
        client.perceive(make_request())


def test_rejects_non_local_base_url() -> None:
    with pytest.raises(ValueError, match="loopback HTTP URL"):
        OllamaPerceptionClient(model="qwen3:4b", base_url="https://ollama.com")
