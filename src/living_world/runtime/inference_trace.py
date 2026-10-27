"""Immutable application bytes and privileged observed-prefix evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from living_world.archives.inference import (
    validate_request_trace,
    validate_response_trace,
)
from living_world.archives.model import plain

if TYPE_CHECKING:
    from living_world.cognition.npc_cognition_client import ActionOption
    from living_world.cognition.npc_context import NPCContext

    from .broker import ProviderConfig


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class PreparedInference:
    body: bytes
    request_trace: Mapping[str, object]

    def __post_init__(self) -> None:
        trace = validate_request_trace(self.request_trace)
        if (
            type(self.body) is not bytes
            or trace["body_length"] != len(self.body)
            or trace["body_digest"] != hashlib.sha256(self.body).hexdigest()
        ):
            raise ValueError("Invalid prepared inference bytes.")
        object.__setattr__(self, "request_trace", trace)

    @property
    def url(self) -> str:
        return cast(str, self.request_trace["url"])

    @property
    def timeout_seconds(self) -> float:
        return float(cast(float, self.request_trace["timeout_seconds"]))

    @property
    def max_response_bytes(self) -> int:
        return cast(int, self.request_trace["max_response_bytes"])


def prepare_inference(
    config: ProviderConfig, context: NPCContext, options: tuple[ActionOption, ...]
) -> PreparedInference:
    from .broker import client_for, encoded_body

    body = encoded_body(client_for(config).build_payload(context, options)).encode(
        "ascii"
    )
    return PreparedInference(
        body,
        {
            "format": 1,
            "provider_kind": config.kind,
            "model": config.model,
            "model_digest": config.model_digest,
            "method": "POST",
            "url": config.base_url
            + ("/api/generate" if config.kind == "ollama" else "/v1/chat/completions"),
            "headers": {"Content-Type": "application/json"},
            "body_digest": hashlib.sha256(body).hexdigest(),
            "body_length": len(body),
            "prepared_at": utc_now(),
            "timeout_seconds": config.timeout_seconds,
            "max_response_bytes": config.max_response_bytes,
        },
    )


@dataclass(frozen=True)
class InferenceObservation:
    response_trace: Mapping[str, object]
    body: bytes | None

    def __post_init__(self) -> None:
        trace = validate_response_trace(self.response_trace)
        if trace["body_state"] == "unavailable":
            if self.body is not None:
                raise ValueError("Unavailable body has bytes.")
        elif (
            type(self.body) is not bytes
            or trace["body_length"] != len(self.body)
            or trace["body_digest"] != hashlib.sha256(self.body).hexdigest()
        ):
            raise ValueError("Invalid observed inference bytes.")
        object.__setattr__(self, "response_trace", trace)


def empty_response_trace() -> dict[str, object]:
    return {
        "format": 1,
        "body_state": "unavailable",
        "body_digest": None,
        "body_length": None,
        "http_status": None,
        "timestamps": dict.fromkeys(
            (
                "dispatch_started_at",
                "worker_started_at",
                "http_started_at",
                "headers_received_at",
                "first_body_byte_at",
                "read_finished_at",
                "settled_at",
            )
        ),
        "durations": dict.fromkeys(
            (
                "broker_seconds",
                "worker_seconds",
                "http_seconds",
                "headers_seconds",
                "first_byte_seconds",
                "body_read_seconds",
            )
        ),
    }


def settle_observation(
    observation: InferenceObservation | None,
    *,
    dispatch_started_at: str,
    settled_at: str,
    broker_seconds: float,
) -> InferenceObservation:
    trace = (
        empty_response_trace()
        if observation is None
        else cast(dict[str, object], plain(observation.response_trace))
    )
    cast(dict[str, object], trace["timestamps"]).update(
        dispatch_started_at=dispatch_started_at, settled_at=settled_at
    )
    cast(dict[str, object], trace["durations"])["broker_seconds"] = broker_seconds
    return InferenceObservation(
        trace, None if observation is None else observation.body
    )
