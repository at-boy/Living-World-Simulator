"""Privileged opaque inference bodies and closed engine-only trace documents."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from ipaddress import ip_address
from urllib.parse import urlsplit

from living_world.archives.model import (
    ArchiveFormatError,
    digest,
    document,
    frozen_map,
    integer,
    text,
)


@dataclass(frozen=True)
class InferenceBlob:
    """Exact observed bytes; an empty observation is still available evidence."""

    body: bytes

    def __post_init__(self) -> None:
        if type(self.body) is not bytes:
            raise ArchiveFormatError("Inference body must be exact bytes.")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    @property
    def byte_length(self) -> int:
        return len(self.body)


def _utc(value: object) -> None:
    try:
        parsed = datetime.fromisoformat(text(value))
        if parsed.utcoffset() != UTC.utcoffset(parsed):
            raise ValueError()
    except ValueError as exc:
        raise ArchiveFormatError("Expected timezone-aware UTC timestamp.") from exc


def _number(value: object, *, positive: bool = False) -> None:
    try:
        valid = (
            type(value) in (int, float)
            and math.isfinite(value)
            and (value > 0 if positive else value >= 0)
        )
    except OverflowError:
        valid = False
    if not valid:
        raise ArchiveFormatError("Expected finite duration in range.")


def validate_request_trace(value: object) -> Mapping[str, object]:
    """Validate the complete application-declared request metadata."""
    p = document(
        value,
        {
            "format",
            "provider_kind",
            "model",
            "model_digest",
            "method",
            "url",
            "headers",
            "body_digest",
            "body_length",
            "prepared_at",
            "timeout_seconds",
            "max_response_bytes",
        },
    )
    if integer(p["format"]) != 1 or p["provider_kind"] not in ("ollama", "llama_cpp"):
        raise ArchiveFormatError("Unsupported request trace format/provider.")
    text(p["model"])
    if p["model_digest"] is not None:
        text(p["model_digest"])
    if p["method"] != "POST":
        raise ArchiveFormatError("Expected POST request.")
    try:
        raw_url = text(p["url"])
        url = urlsplit(raw_url)
        host = url.hostname
        loopback = host == "localhost"
        if not loopback and host is not None:
            loopback = ip_address(host).is_loopback
        endpoint = (
            "/api/generate"
            if p["provider_kind"] == "ollama"
            else "/v1/chat/completions"
        )
        if (
            not loopback
            or url.scheme != "http"
            or url.username is not None
            or url.password is not None
            or url.path != endpoint
            or "?" in raw_url
            or "#" in raw_url
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in raw_url)
        ):
            raise ValueError()
        _ = url.port
    except ValueError as exc:
        raise ArchiveFormatError(
            "Expected credential-free loopback HTTP endpoint."
        ) from exc
    headers = document(p["headers"], {"Content-Type"})
    if headers["Content-Type"] != "application/json":
        raise ArchiveFormatError("Expected application/json headers.")
    digest(p["body_digest"])
    if integer(p["body_length"], minimum=1) > 16000:
        raise ArchiveFormatError("Request body exceeds trace limit.")
    _utc(p["prepared_at"])
    _number(p["timeout_seconds"], positive=True)
    integer(p["max_response_bytes"], minimum=1)
    return frozen_map(p)


def validate_response_trace(value: object) -> Mapping[str, object]:
    """Validate observed-prefix metadata without inferring activity or clock order."""
    p = document(
        value,
        {
            "format",
            "body_state",
            "body_digest",
            "body_length",
            "http_status",
            "timestamps",
            "durations",
        },
    )
    if integer(p["format"]) != 1 or p["body_state"] not in (
        "complete",
        "incomplete",
        "unavailable",
    ):
        raise ArchiveFormatError("Unsupported response trace format/state.")
    if p["body_state"] == "unavailable":
        if p["body_digest"] is not None or p["body_length"] is not None:
            raise ArchiveFormatError("Unavailable body cannot reference bytes.")
    else:
        digest(p["body_digest"])
        integer(p["body_length"])
    if p["http_status"] is not None and integer(p["http_status"], minimum=100) > 599:
        raise ArchiveFormatError("Invalid HTTP status.")
    timestamps = document(
        p["timestamps"],
        {
            "dispatch_started_at",
            "worker_started_at",
            "http_started_at",
            "headers_received_at",
            "first_body_byte_at",
            "read_finished_at",
            "settled_at",
        },
    )
    durations = document(
        p["durations"],
        {
            "broker_seconds",
            "worker_seconds",
            "http_seconds",
            "headers_seconds",
            "first_byte_seconds",
            "body_read_seconds",
        },
    )
    for timestamp in timestamps.values():
        if timestamp is not None:
            _utc(timestamp)
    for duration in durations.values():
        if duration is not None:
            _number(duration)
    return frozen_map(p)
