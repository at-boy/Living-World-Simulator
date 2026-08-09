"""Local llama.cpp adapter for ``LLMPerceptionEngine``."""

from collections.abc import Mapping

from living_world.perception.llm_perception_client import (
    LLMPerceptionClientError,
    LLMPerceptionRequest,
    LLMPerceptionResponse,
)
from living_world.perception.local_llm_http import (
    JsonHttpTransport,
    LocalLLMHttpError,
    UrllibJsonHttpTransport,
    validate_local_base_url,
)
from living_world.perception.local_llm_perception_format import (
    RESPONSE_SCHEMA,
    SYSTEM_INSTRUCTIONS,
    parse_response,
    serialize_request,
)


class LlamaCppPerceptionClient:
    """Requests a structured perception from a loopback-only llama.cpp server."""

    SYSTEM_INSTRUCTIONS = SYSTEM_INSTRUCTIONS
    RESPONSE_SCHEMA = RESPONSE_SCHEMA

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:8080",
        timeout_seconds: float = 30.0,
        transport: JsonHttpTransport | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("llama.cpp model cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("llama.cpp timeout must be positive.")

        self._model = model
        self._base_url = validate_local_base_url(base_url)
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibJsonHttpTransport()

    @property
    def provider_name(self) -> str:
        return "llama.cpp"

    def perceive(self, request: LLMPerceptionRequest) -> LLMPerceptionResponse:
        try:
            response = self._transport.post_json(
                url=f"{self._base_url}/v1/chat/completions",
                payload={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_INSTRUCTIONS},
                        {"role": "user", "content": serialize_request(request)},
                    ],
                    "stream": False,
                    "response_format": {
                        "type": "json_object",
                        "schema": self.RESPONSE_SCHEMA,
                    },
                },
                timeout_seconds=self._timeout_seconds,
            )
        except LocalLLMHttpError as error:
            raise LLMPerceptionClientError(
                "The local llama.cpp server could not provide a perception."
            ) from error

        return parse_response(self._content_from_response(response))

    @staticmethod
    def _content_from_response(response: Mapping[str, object]) -> object:
        choices = response.get("choices")

        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, Mapping):
            return None

        message = first_choice.get("message")
        if not isinstance(message, Mapping):
            return None

        return message.get("content")
