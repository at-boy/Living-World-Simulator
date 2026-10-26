"""Loopback-only llama.cpp adapter for structured NPC cognition proposals."""

import math
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
        max_output_tokens: int = 512,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> None:
        if not isinstance(model, str):
            raise TypeError("llama.cpp model must be a string.")
        if not model.strip():
            raise ValueError("llama.cpp model cannot be empty.")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(
            timeout_seconds, bool
        ):
            raise TypeError("llama.cpp timeout must be a number.")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("llama.cpp timeout must be positive.")
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("Output tokens must be a positive integer.")
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not math.isfinite(temperature)
            or temperature < 0
        ):
            raise ValueError("Temperature must be finite and nonnegative.")
        if seed is not None and type(seed) is not int:
            raise ValueError("Seed must be an integer.")
        self._max_output_tokens = max_output_tokens
        self._temperature = float(temperature)
        self._seed = seed
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
                payload=self.build_payload(context, actions),
                timeout_seconds=self._timeout_seconds,
            )
        except LocalLLMHttpError as error:
            raise NPCCognitionClientError(
                "The local llama.cpp server could not provide an NPC decision."
            ) from error
        return parse_decision_response(self._content_from_response(response), actions)

    def build_payload(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> dict[str, object]:
        """Build the complete request from filtered NPC values only."""
        payload: dict[str, object] = {
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
        }
        payload.update(
            {
                "max_tokens": self._max_output_tokens,
                "temperature": self._temperature,
                "chat_template_kwargs": {"enable_thinking": False},
            }
        )
        if self._seed is not None:
            payload["seed"] = self._seed
        return payload

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
