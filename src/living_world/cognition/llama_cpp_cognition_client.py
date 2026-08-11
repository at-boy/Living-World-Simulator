"""Loopback-only llama.cpp adapter for structured NPC cognition proposals."""

from collections.abc import Mapping

from living_world.cognition.local_llm_cognition_format import (
    RESPONSE_SCHEMA,
    SYSTEM_INSTRUCTIONS,
    parse_decision_response,
    serialize_decision_request,
)
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    NPCCognitionClientError,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext
from living_world.perception.local_llm_http import (
    JsonHttpTransport,
    LocalLLMHttpError,
    UrllibJsonHttpTransport,
    validate_local_base_url,
)


class LlamaCppCognitionClient:
    """Request untrusted structured proposals from a loopback llama.cpp server."""

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
        if not isinstance(model, str):
            raise TypeError("llama.cpp model must be a string.")
        if not model.strip():
            raise ValueError("llama.cpp model cannot be empty.")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(
            timeout_seconds, bool
        ):
            raise TypeError("llama.cpp timeout must be a number.")
        if timeout_seconds <= 0:
            raise ValueError("llama.cpp timeout must be positive.")
        self._model = model
        self._base_url = validate_local_base_url(base_url)
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport or UrllibJsonHttpTransport()

    @property
    def provider_name(self) -> str:
        return "llama.cpp"

    def decide(
        self,
        context: NPCContext,
        actions: tuple[ActionOption, ...],
    ) -> NPCDecision:
        try:
            response = self._transport.post_json(
                url=f"{self._base_url}/v1/chat/completions",
                payload={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_INSTRUCTIONS},
                        {
                            "role": "user",
                            "content": serialize_decision_request(context, actions),
                        },
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
            raise NPCCognitionClientError(
                "The local llama.cpp server could not provide an NPC decision."
            ) from error
        return parse_decision_response(self._content_from_response(response), actions)

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
