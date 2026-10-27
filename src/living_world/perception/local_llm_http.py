"""Bounded, credential-free loopback HTTP support for local LLM providers."""

import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPException, IncompleteRead
from types import MappingProxyType
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import ParseResult, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class LocalLLMHttpError(Exception):
    """Safe provider error; the response body is never included."""

    def __init__(self, message: str, *, code: str = "transport") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class HttpObservation:
    body: bytes | None
    complete: bool
    status_code: int | None
    timestamps: Mapping[str, str | None]
    durations: Mapping[str, float | None]

    def __post_init__(self) -> None:
        if self.body is not None and type(self.body) is not bytes:
            raise ValueError("Expected observed bytes.")
        if type(self.complete) is not bool or (self.complete and self.body is None):
            raise ValueError("Invalid complete observation.")
        if self.status_code is not None and (
            type(self.status_code) is not int or not 100 <= self.status_code <= 599
        ):
            raise ValueError("Invalid HTTP status.")
        if set(self.timestamps) != {
            "http_started_at",
            "headers_received_at",
            "first_body_byte_at",
            "read_finished_at",
        } or set(self.durations) != {
            "http_seconds",
            "headers_seconds",
            "first_byte_seconds",
            "body_read_seconds",
        }:
            raise ValueError("Invalid HTTP timing fields.")
        for value in self.timestamps.values():
            if value is not None and (
                type(value) is not str
                or datetime.fromisoformat(value).utcoffset() != UTC.utcoffset(None)
            ):
                raise ValueError("Expected UTC timestamp.")
        for value in self.durations.values():
            if value is not None and (
                type(value) not in (int, float) or not math.isfinite(value) or value < 0
            ):
                raise ValueError("Expected finite duration.")
        object.__setattr__(self, "timestamps", MappingProxyType(dict(self.timestamps)))
        object.__setattr__(self, "durations", MappingProxyType(dict(self.durations)))


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


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Nonfinite JSON number.")
    return result


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
        return self._request_json(url, timeout_seconds, body=body)

    def post_bytes(
        self,
        *,
        url: str,
        body: bytes,
        timeout_seconds: float,
        observer: Callable[[HttpObservation], None] | None = None,
    ) -> dict[str, object]:
        if type(body) is not bytes:
            raise ValueError("Expected exact request bytes.")
        if observer is None:
            return self._request_json(url, timeout_seconds, body=body)
        self._last_response_digest = None
        _origin(url)
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("Timeout must be finite and positive.")
        started = time.monotonic()
        headers_at: float | None = None
        timestamps: dict[str, str | None] = dict.fromkeys(
            (
                "http_started_at",
                "headers_received_at",
                "first_body_byte_at",
                "read_finished_at",
            )
        )
        durations: dict[str, float | None] = dict.fromkeys(
            (
                "http_seconds",
                "headers_seconds",
                "first_byte_seconds",
                "body_read_seconds",
            )
        )
        timestamps["http_started_at"] = datetime.now(UTC).isoformat()
        raw: bytes | None = None
        complete = False
        status: int | None = None

        def emit() -> None:
            try:
                observer(HttpObservation(raw, complete, status, timestamps, durations))
            except Exception:  # noqa: BLE001 - capture failures must be fail-closed
                raise LocalLLMHttpError(
                    "Local LLM capture failed.", code="worker_failed"
                ) from None

        emit()
        response = None
        http_error = False
        entered_read = False
        failure: LocalLLMHttpError | None = None
        try:
            request = Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                response = build_opener(ProxyHandler({}), _NoRedirect()).open(
                    request, timeout=timeout_seconds
                )
            except HTTPError as error:
                response = error
                http_error = True
            status = response.code
            headers_at = time.monotonic()
            timestamps["headers_received_at"] = datetime.now(UTC).isoformat()
            durations["headers_seconds"] = headers_at - started
            raw = b""
            emit()
            entered_read = True
            while len(raw) <= self._max_response_bytes:
                if time.monotonic() - started >= timeout_seconds:
                    raise TimeoutError()
                amount = (
                    1
                    if not raw
                    else min(65536, self._max_response_bytes + 1 - len(raw))
                )
                read = getattr(response, "read1", response.read)
                try:
                    chunk = read(amount)
                except IncompleteRead as error:
                    chunk = error.partial[:amount]
                    if chunk:
                        if not raw:
                            timestamps["first_body_byte_at"] = datetime.now(
                                UTC
                            ).isoformat()
                            durations["first_byte_seconds"] = time.monotonic() - started
                        raw += chunk
                        emit()
                    raise
                if not chunk:
                    if getattr(response, "length", 0):
                        raise IncompleteRead(b"", response.length)
                    complete = True
                    break
                if not raw:
                    timestamps["first_body_byte_at"] = datetime.now(UTC).isoformat()
                    durations["first_byte_seconds"] = time.monotonic() - started
                raw += chunk[:amount]
                emit()
        except LocalLLMHttpError:
            raise
        except (TimeoutError, URLError, OSError, HTTPException) as error:
            timeout = isinstance(error, TimeoutError) or (
                isinstance(error, URLError) and isinstance(error.reason, TimeoutError)
            )
            failure = LocalLLMHttpError(
                "Local LLM server is unavailable.",
                code="timeout" if timeout else "transport",
            )
        finally:
            if response is not None:
                response.close()
        ended = time.monotonic()
        durations["http_seconds"] = ended - started
        if entered_read:
            timestamps["read_finished_at"] = datetime.now(UTC).isoformat()
            assert headers_at is not None
            durations["body_read_seconds"] = ended - headers_at
        emit()
        if http_error:
            raise LocalLLMHttpError(
                "Local LLM server returned an HTTP error.", code="http_error"
            )
        if failure is not None:
            raise failure
        assert raw is not None
        if len(raw) > self._max_response_bytes:
            raise LocalLLMHttpError(
                "Local LLM response exceeded its limit.", code="oversized_response"
            )
        self._last_response_digest = hashlib.sha256(raw).hexdigest()
        try:
            decoded = json.loads(
                raw.decode("utf-8"),
                parse_constant=_invalid_constant,
                parse_float=_finite_float,
            )
            if not isinstance(decoded, dict):
                raise TypeError()
        except (UnicodeDecodeError, ValueError, TypeError, RecursionError):
            raise LocalLLMHttpError(
                "Local LLM server returned invalid JSON.", code="invalid_response"
            ) from None
        return decoded

    def get_json(self, *, url: str, timeout_seconds: float) -> dict[str, object]:
        return self._request_json(url, timeout_seconds)

    def _request_json(
        self, url: str, timeout_seconds: float, *, body: bytes | None = None
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
        request = Request(
            url,
            data=body,
            headers={} if body is None else {"Content-Type": "application/json"},
            method="GET" if body is None else "POST",
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
            decoded = json.loads(
                raw.decode("utf-8"),
                parse_constant=_invalid_constant,
                parse_float=_finite_float,
            )
            if not isinstance(decoded, dict):
                raise TypeError
        except (UnicodeDecodeError, ValueError, TypeError, RecursionError):
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
