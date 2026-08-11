"""Shared structured prompt and response handling for local perception clients."""

import json
from collections.abc import Mapping

from living_world.perception.llm_perception_client import (
    LLMPerceptionClientError,
    LLMPerceptionInvalidResponseError,
    LLMPerceptionRequest,
    LLMPerceptionResponse,
)

SYSTEM_INSTRUCTIONS = """You are a simulation perception subsystem, not an NPC.
Describe only what the observer could perceive about the subject. Return JSON
matching the supplied schema with a concise NPC-readable description and a
confidence from 0.0 to 1.0. Do not include internal entity identifiers, exact
numeric values, raw attribute notation, evidence, metadata, hidden state,
engine objects, actions, or explanations."""

RESPONSE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["description", "confidence"],
    "additionalProperties": False,
}


def serialize_request(request: LLMPerceptionRequest) -> str:
    """Encode the provider input as data instead of prompt interpolation."""

    try:
        return json.dumps(
            {
                "observer_name": request.observer_name,
                "capabilities": dict(request.capabilities),
                "subject_name": request.subject_name,
                "subject_attributes": dict(request.subject_attributes),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise LLMPerceptionClientError(
            "Perception request could not be encoded for the local model."
        ) from error


def parse_response(content: object) -> LLMPerceptionResponse:
    """Validate a structured model response at the provider boundary."""

    if not isinstance(content, str):
        raise LLMPerceptionInvalidResponseError(
            "Provider returned an invalid perception response."
        )

    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as error:
        raise LLMPerceptionInvalidResponseError(
            "Provider returned an invalid perception response."
        ) from error

    if not isinstance(decoded, Mapping):
        raise LLMPerceptionInvalidResponseError(
            "Provider returned an invalid perception response."
        )

    description = decoded.get("description")
    confidence = decoded.get("confidence")

    if (
        not isinstance(description, str)
        or not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0.0 <= confidence <= 1.0
    ):
        raise LLMPerceptionInvalidResponseError(
            "Provider returned an invalid perception response."
        )

    return LLMPerceptionResponse(
        description=description,
        confidence=float(confidence),
    )
