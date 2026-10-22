"""Bounded, credential-free loopback HTTP support for local LLM providers."""

import hashlib
import json
import math
from http.client import HTTPException
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import ParseResult, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class LocalLLMHttpError(Exception):
    """Safe provider error; the response body is never included."""

    def __init__(self, message: str, *, code: str = "transport") -> None:
        super().__init__(message)
        self.code = code


class JsonHttpTransport(Protocol):
    def post_json(
        self, *, url: str, payload: dict[str, object], timeout_seconds: float
    ) -> dict[str, object]: ...


def _origin(url: str) -> ParseResult:
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError("Local LLM base URL must be a loopback HTTP URL.")
    try:
        parsed = urlparse(url)
        port = parsed.port
        authority = "[::1]" if parsed.hostname == "::1" else parsed.hostname
        expected = f"{authority}:{port}" if port is not None else authority
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
            or parsed.username is not None
            or parsed.password is not None
            or "@" in parsed.netloc
            or (port is not None and port <= 0)
            or parsed.netloc.casefold() != expected
            or parsed.netloc.endswith(":")
            or "\\" in parsed.netloc
        ):
            raise ValueError
    except ValueError:
        raise ValueError("Local LLM base URL must be a loopback HTTP URL.") from None
    return parsed


def _invalid_constant(value: str) -> object:
    raise ValueError("Nonfinite JSON number.")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


class UrllibJsonHttpTransport:
    """One bounded response with proxies and redirects disabled."""

    def __init__(self, max_response_bytes: int = 1048576) -> None:
        if type(max_response_bytes) is not int or max_response_bytes <= 0:
            raise ValueError("Response limit must be a positive integer.")
        self._max_response_bytes = max_response_bytes
        self._last_response_digest: str | None = None

    @property
    def last_response_digest(self) -> str | None:
        return self._last_response_digest

    def post_json(
        self, *, url: str, payload: dict[str, object], timeout_seconds: float
    ) -> dict[str, object]:
        self._last_response_digest = None
        _origin(url)
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("Timeout must be finite and positive.")
        try:
            body = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError):
            raise LocalLLMHttpError("Local LLM request could not be encoded.") from None
        request = Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with build_opener(ProxyHandler({}), _NoRedirect()).open(
                request, timeout=timeout_seconds
            ) as response:
                raw = response.read(self._max_response_bytes + 1)
        except HTTPError as error:
            error.close()
            raise LocalLLMHttpError(
                "Local LLM server returned an HTTP error.", code="http_error"
            ) from None
        except (TimeoutError, URLError, OSError, HTTPException) as error:
            timeout = isinstance(error, TimeoutError) or (
                isinstance(error, URLError) and isinstance(error.reason, TimeoutError)
            )
            raise LocalLLMHttpError(
                "Local LLM server is unavailable.",
                code="timeout" if timeout else "transport",
            ) from None
        if len(raw) > self._max_response_bytes:
            raise LocalLLMHttpError(
                "Local LLM response exceeded its limit.", code="oversized_response"
            )
        self._last_response_digest = hashlib.sha256(raw).hexdigest()
        try:
            decoded = json.loads(raw.decode("utf-8"), parse_constant=_invalid_constant)
            if not isinstance(decoded, dict):
                raise TypeError
        except (UnicodeDecodeError, ValueError, TypeError):
            raise LocalLLMHttpError(
                "Local LLM server returned invalid JSON.", code="invalid_response"
            ) from None
        return decoded


def validate_local_base_url(base_url: str) -> str:
    """Normalize a loopback base URL, validating the complete authority."""
    parsed = _origin(base_url)
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("Local LLM base URL cannot include a path or query.")
    return base_url.rstrip("/")
