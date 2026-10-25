"""Memory-only credentials for the privileged loopback operator application."""

from dataclasses import dataclass, field
from secrets import compare_digest, token_urlsafe
from urllib.parse import urlsplit

from fastapi import HTTPException, Request


def _origin(value: str) -> str:
    try:
        if not isinstance(value, str) or any(
            c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value
        ):
            raise ValueError()
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parts.username is not None
            or parts.password is not None
            or parts.path
            or "?" in value
            or "#" in value
            or parts.netloc.endswith(":")
        ):
            raise ValueError()
        port = parts.port
        if port is not None and port < 1:
            raise ValueError()
        host = "[::1]" if parts.hostname == "::1" else parts.hostname
        suffix = (
            ""
            if port is None or port == (80 if parts.scheme == "http" else 443)
            else f":{port}"
        )
        return f"{parts.scheme}://{host}{suffix}"
    except (ValueError, TypeError):
        raise ValueError("Invalid operator origin.") from None


def _equal(left: str, right: str) -> bool:
    return compare_digest(left.encode("utf-8"), right.encode("utf-8"))


@dataclass(frozen=True)
class AdminSession:
    token: str = field(repr=False)
    csrf_nonce: str = field(repr=False)
    origin: str

    @classmethod
    def issue(cls, *, origin: str = "http://127.0.0.1:8000") -> "AdminSession":
        return cls(token_urlsafe(32), token_urlsafe(32), _origin(origin))

    def authorize(self, request: Request, *, mutation: bool = False) -> None:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer ") or not _equal(
            authorization[7:], self.token
        ):
            raise HTTPException(
                401, "unauthorized", headers={"WWW-Authenticate": "Bearer"}
            )
        origin = request.headers.get("origin")
        if (origin is not None and not _equal(origin, self.origin)) or (
            mutation
            and (
                origin is None
                or not _equal(request.headers.get("x-csrf-token", ""), self.csrf_nonce)
            )
        ):
            raise HTTPException(403, "forbidden")
