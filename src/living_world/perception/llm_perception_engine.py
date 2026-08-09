"""LLM-backed perception with an engine-owned observation boundary."""

import re

from living_world.core.observation import Observation
from living_world.perception.deterministic_perception_engine import (
    DeterministicPerceptionEngine,
)
from living_world.perception.llm_perception_client import (
    LLMPerceptionClient,
    LLMPerceptionClientError,
    LLMPerceptionInvalidResponseError,
    LLMPerceptionRequest,
    LLMPerceptionResponse,
)
from living_world.perception.perception_context import PerceptionContext
from living_world.perception.perception_engine import PerceptionEngine


class LLMPerceptionEngine:
    """Produces observations through a local LLM with deterministic fallback."""

    def __init__(
        self,
        client: LLMPerceptionClient,
        *,
        fallback_engine: PerceptionEngine | None = None,
    ) -> None:
        self._client = client
        self._fallback_engine = fallback_engine or DeterministicPerceptionEngine()

    def perceive(self, context: PerceptionContext) -> Observation:
        """Produce an observation without granting model output world authority."""

        request = self._build_request(context)

        try:
            response = self._client.perceive(request)
        except LLMPerceptionInvalidResponseError:
            return self._fallback(context, failure="invalid_response")
        except LLMPerceptionClientError:
            return self._fallback(context, failure="provider_error")

        try:
            self._validate_response(response, context)
        except (TypeError, ValueError):
            return self._fallback(context, failure="invalid_response")

        return Observation(
            id="",
            tick=context.tick,
            observer=context.observer.id,
            subject=context.subject.id,
            description=response.description.strip(),
            confidence=response.confidence,
            evidence=self._evidence(context),
            metadata={
                "engine": "llm",
                "provider": self._client.provider_name,
                "fallback_used": False,
            },
        )

    @staticmethod
    def _build_request(context: PerceptionContext) -> LLMPerceptionRequest:
        return LLMPerceptionRequest(
            observer_name=context.observer.name,
            capabilities=context.capabilities,
            subject_name=context.subject.name,
            subject_attributes=context.subject.attributes,
        )

    @staticmethod
    def _evidence(context: PerceptionContext) -> dict[str, object]:
        return {
            "subject_attributes": dict(context.subject.attributes),
            "observer_capabilities": dict(context.capabilities),
        }

    def _fallback(self, context: PerceptionContext, *, failure: str) -> Observation:
        try:
            fallback = self._fallback_engine.perceive(context)
        except Exception as error:
            raise LLMPerceptionFallbackError(
                "LLM perception failed and deterministic fallback could not run."
            ) from error

        return Observation(
            id=fallback.id,
            tick=fallback.tick,
            observer=fallback.observer,
            subject=fallback.subject,
            description=fallback.description,
            confidence=fallback.confidence,
            evidence=fallback.evidence,
            metadata={
                "engine": "llm",
                "provider": self._client.provider_name,
                "fallback_used": True,
                "failure": failure,
            },
        )

    @staticmethod
    def _validate_response(
        response: object,
        context: PerceptionContext,
    ) -> None:
        if not isinstance(response, LLMPerceptionResponse):
            raise TypeError("Perception provider returned an invalid response.")

        if not response.description.strip():
            raise ValueError("Perception description cannot be empty.")

        if not 0.0 <= response.confidence <= 1.0:
            raise ValueError("Perception confidence must be between 0.0 and 1.0.")

        forbidden_values = (
            context.observer.id,
            context.subject.id,
            *(
                str(value)
                for value in context.subject.attributes.values()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ),
            *(
                str(value)
                for value in context.capabilities.values()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ),
        )

        for value in forbidden_values:
            if LLMPerceptionEngine._contains_exact_value(response.description, value):
                raise ValueError("Perception description exposes engine-only data.")

    @staticmethod
    def _contains_exact_value(description: str, value: str) -> bool:
        if value.startswith("entity_"):
            return value in description

        if value.replace(".", "", 1).isdigit():
            return bool(
                re.search(rf"(?<![0-9.]){re.escape(value)}(?![0-9.])", description)
            )

        if value.replace("_", "").isalnum():
            return bool(
                re.search(rf"(?<![A-Za-z0-9_]){re.escape(value)}(?![A-Za-z0-9_])", description)
            )

        return value in description


class LLMPerceptionFallbackError(RuntimeError):
    """Raised when no LLM or deterministic perception result can be produced."""
