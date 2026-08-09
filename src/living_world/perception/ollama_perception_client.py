"""Local Ollama adapter for ``LLMPerceptionEngine``."""

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


class OllamaPerceptionClient:
    """Requests a structured perception from a loopback-only Ollama server."""

    SYSTEM_INSTRUCTIONS = SYSTEM_INSTRUCTIONS
    RESPONSE_SCHEMA = RESPONSE_SCHEMA

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 30.0,
        transport: JsonHttpTransport | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("Ollama model cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("Ollama timeout must be positive.")

        self._model = model
        self._base_url = validate_local_base_url(base_url)
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibJsonHttpTransport()

    @property
    def provider_name(self) -> str:
        return "ollama"

    def perceive(self, request: LLMPerceptionRequest) -> LLMPerceptionResponse:
        try:
            response = self._transport.post_json(
                url=f"{self._base_url}/api/generate",
                payload={
                    "model": self._model,
                    "system": self.SYSTEM_INSTRUCTIONS,
                    "prompt": serialize_request(request),
                    "stream": False,
                    "think": False,
                    "format": self.RESPONSE_SCHEMA,
                },
                timeout_seconds=self._timeout_seconds,
            )
        except LocalLLMHttpError as error:
            raise LLMPerceptionClientError(
                "The local Ollama server could not provide a perception."
            ) from error

        return parse_response(response.get("response"))
