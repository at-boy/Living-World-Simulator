"""Minimal, standard-library HTTP support for local LLM providers."""

import json
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class LocalLLMHttpError(Exception):
    """Raised when a local LLM HTTP server cannot provide JSON."""


class JsonHttpTransport(Protocol):
    """Posts a JSON object to a local HTTP endpoint."""

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        """Return a JSON object or raise ``LocalLLMHttpError``."""


class UrllibJsonHttpTransport:
    """JSON transport using only Python's standard library."""

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        try:
            body = json.dumps(payload).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise LocalLLMHttpError(
                "Local LLM request could not be encoded."
            ) from error

        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            raise LocalLLMHttpError(
                f"Local LLM server returned HTTP {error.code}."
            ) from error
        except (TimeoutError, URLError) as error:
            raise LocalLLMHttpError("Local LLM server is unavailable.") from error

        try:
            decoded = json.loads(response_body)
        except json.JSONDecodeError as error:
            raise LocalLLMHttpError(
                "Local LLM server returned invalid JSON."
            ) from error

        if not isinstance(decoded, dict):
            raise LocalLLMHttpError(
                "Local LLM server returned a JSON value, not an object."
            )

        return decoded


def validate_local_base_url(base_url: str) -> str:
    """Normalize a loopback HTTP base URL and reject remote providers."""

    parsed = urlparse(base_url)

    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "::1",
        "localhost",
    }:
        raise ValueError("Local LLM base URL must be a loopback HTTP URL.")

    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("Local LLM base URL cannot include a path or query.")

    return base_url.rstrip("/")
