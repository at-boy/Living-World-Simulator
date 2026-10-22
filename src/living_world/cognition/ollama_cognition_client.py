"""Loopback-only Ollama adapter for structured NPC cognition proposals."""

import math

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


class OllamaCognitionClient:
    """Request untrusted structured proposals from a loopback Ollama server."""

    SYSTEM_INSTRUCTIONS = SYSTEM_INSTRUCTIONS
    RESPONSE_SCHEMA = RESPONSE_SCHEMA

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 30.0,
        transport: JsonHttpTransport | None = None,
        max_output_tokens: int = 512,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> None:
        if not isinstance(model, str):
            raise TypeError("Ollama model must be a string.")
        if not model.strip():
            raise ValueError("Ollama model cannot be empty.")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(
            timeout_seconds, bool
        ):
            raise TypeError("Ollama timeout must be a number.")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("Ollama timeout must be positive.")
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
        return "ollama"

    def decide(
        self,
        context: NPCContext,
        actions: tuple[ActionOption, ...],
    ) -> NPCDecision:
        try:
            response = self._transport.post_json(
                url=f"{self._base_url}/api/generate",
                payload=self.build_payload(context, actions),
                timeout_seconds=self._timeout_seconds,
            )
        except LocalLLMHttpError as error:
            raise NPCCognitionClientError(
                "The local Ollama server could not provide an NPC decision."
            ) from error
        return parse_decision_response(response.get("response"), actions)

    def build_payload(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> dict[str, object]:
        """Build the complete HTTP request from filtered NPC values only."""
        options: dict[str, object] = {
            "num_predict": self._max_output_tokens,
            "temperature": self._temperature,
        }
        if self._seed is not None:
            options["seed"] = self._seed
        return {
            "model": self._model,
            "system": self.SYSTEM_INSTRUCTIONS,
            "prompt": serialize_decision_request(context, actions),
            "stream": False,
            "think": False,
            "format": self.RESPONSE_SCHEMA,
            "options": options,
        }
