import pytest

from living_world.perception.llama_cpp_perception_client import LlamaCppPerceptionClient
from living_world.perception.llm_perception_client import (
    LLMPerceptionClientError,
    LLMPerceptionRequest,
)
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


def make_request() -> LLMPerceptionRequest:
    return LLMPerceptionRequest(
        observer_name="Erik",
        capabilities={"woodcraft": 80},
        subject_name="Old Oak",
        subject_attributes={"growth": 87, "health": 92, "wood": 120},
    )


def test_calls_llama_cpp_chat_completions_with_structured_local_request() -> None:
    transport = StubJsonHttpTransport(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"description":"The Old Oak appears mature.",'
                            '"confidence":0.8}'
                        )
                    }
                }
            ]
        }
    )
    client = LlamaCppPerceptionClient(
        model="Qwen3-4B-Q4_K_M.gguf",
        transport=transport,
    )

    response = client.perceive(make_request())

    assert response.description == "The Old Oak appears mature."
    assert response.confidence == 0.8
    assert client.provider_name == "llama.cpp"
    url, payload, timeout_seconds = transport.calls[0]
    assert url == "http://127.0.0.1:8080/v1/chat/completions"
    assert payload["model"] == "Qwen3-4B-Q4_K_M.gguf"
    assert payload["stream"] is False
    assert payload["response_format"] == {
        "type": "json_object",
        "schema": client.RESPONSE_SCHEMA,
    }
    assert payload["messages"] == [
        {"role": "system", "content": client.SYSTEM_INSTRUCTIONS},
        {
            "role": "user",
            "content": (
                '{"capabilities":{"woodcraft":80},"observer_name":"Erik",'
                '"subject_attributes":{"growth":87,"health":92,"wood":120},'
                '"subject_name":"Old Oak"}'
            ),
        },
    ]
    assert timeout_seconds == 30.0


@pytest.mark.parametrize(
    "server_response",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {"content": "not json"}}]},
        {"choices": [{"message": {"content": "{}"}}]},
    ],
)
def test_rejects_malformed_llama_cpp_response(
    server_response: dict[str, object],
) -> None:
    client = LlamaCppPerceptionClient(
        model="Qwen3-4B-Q4_K_M.gguf",
        transport=StubJsonHttpTransport(server_response),
    )

    with pytest.raises(LLMPerceptionClientError, match="invalid perception response"):
        client.perceive(make_request())


def test_wraps_local_http_failure() -> None:
    client = LlamaCppPerceptionClient(
        model="Qwen3-4B-Q4_K_M.gguf",
        transport=FailingJsonHttpTransport(),
    )

    with pytest.raises(LLMPerceptionClientError, match="local llama.cpp server"):
        client.perceive(make_request())
