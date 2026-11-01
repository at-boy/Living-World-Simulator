"""Shared admin-only trace routes and a runtime-free offline application."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import fields
from typing import Literal, TypeVar

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from living_world.api.auth import AdminSession
from living_world.archives.catalog import RunCatalog
from living_world.archives.model import (
    ArchiveFormatError,
    JournalBoundary,
    identifier,
    plain,
)
from living_world.archives.trace_analysis import (
    TraceAnalysisLimitError,
    TraceBody,
    TraceCall,
    read_trace_body,
    read_trace_page,
)
from living_world.archives.trace_catalog import (
    TraceAttemptNotFoundError,
    TraceAttemptSummary,
    list_trace_attempts,
    resolve_trace_attempt,
)

_T = TypeVar("_T")


def _projection(
    value: TraceAttemptSummary | TraceCall | JournalBoundary,
) -> dict[str, object]:
    return {field.name: plain(getattr(value, field.name)) for field in fields(value)}


async def _work(operation: Callable[[], _T]) -> _T:
    try:
        return await asyncio.to_thread(operation)
    except TraceAnalysisLimitError:
        raise HTTPException(413, "analysis_limit_exceeded") from None
    except TraceAttemptNotFoundError:
        raise HTTPException(404, "not_found") from None
    except Exception:  # noqa: BLE001 - sanitize every adapter failure
        raise HTTPException(409, "trace_unavailable") from None


async def _json(payload: Callable[[], dict[str, object]]) -> JSONResponse:
    # Encode before leaving the adapter: FastAPI must receive a ready response,
    # rather than discovering unencodable archived text in a later serializer.
    return await _work(lambda: JSONResponse(payload()))


def _boundary(
    sequence: int | None, digest: str | None, *, required: bool = False
) -> JournalBoundary | None:
    if sequence is None and digest is None and not required:
        return None
    if sequence is None or digest is None:
        raise HTTPException(400, "invalid_query")
    try:
        return JournalBoundary(sequence, digest)
    except ArchiveFormatError:
        raise HTTPException(400, "invalid_query") from None


def _limit(value: int) -> None:
    if not 1 <= value <= 100:
        raise HTTPException(400, "invalid_query")


def create_trace_analysis_router(
    catalog: RunCatalog,
    *,
    auth: AdminSession,
    mode: Literal["live", "offline"] = "live",
) -> APIRouter:
    """Mount the same protected read-only evidence contract in either application."""
    if not isinstance(catalog, RunCatalog) or not isinstance(auth, AdminSession):
        raise TypeError("Expected catalog and admin session.")
    if mode not in ("live", "offline"):
        raise ValueError("Invalid analysis mode.")

    def authorize(request: Request) -> None:
        auth.authorize(request)

    router = APIRouter(prefix="/analysis", dependencies=[Depends(authorize)])

    @router.get("/status")
    async def status() -> JSONResponse:
        return await _json(
            lambda: {
                "mode": mode,
                "access": "read_only",
                "capabilities": ["calls", "body_download", "body_preview"],
                "world_validation": "not_performed",
            }
        )

    @router.get("/attempts")
    async def attempts(
        after_lineage_id: str | None = None,
        after_attempt_id: str | None = None,
        limit: int = 50,
    ) -> JSONResponse:
        _limit(limit)
        after = None
        if after_lineage_id is not None or after_attempt_id is not None:
            try:
                after = (identifier(after_lineage_id), identifier(after_attempt_id))
            except ArchiveFormatError:
                raise HTTPException(400, "invalid_query") from None
        page = await _work(
            lambda: list_trace_attempts(catalog, after=after, limit=limit)
        )
        return await _json(
            lambda: {
                "integrity": page.integrity,
                "attempts": [_projection(item) for item in page.attempts],
                "next_after": (
                    None
                    if page.next_after is None
                    else {
                        "lineage_id": page.next_after[0],
                        "attempt_id": page.next_after[1],
                    }
                ),
                "listing": "current",
            }
        )

    @router.get("/attempts/{attempt_id}/traces")
    async def traces(
        attempt_id: str,
        through_sequence: int | None = None,
        journal_digest: str | None = None,
        after_sequence: int = 0,
        limit: int = 50,
    ) -> JSONResponse:
        _limit(limit)
        if after_sequence < 0:
            raise HTTPException(400, "invalid_query")
        boundary = _boundary(through_sequence, journal_digest)
        page = await _work(
            lambda: read_trace_page(
                resolve_trace_attempt(catalog, attempt_id),
                boundary=boundary,
                after_sequence=after_sequence,
                limit=limit,
            )
        )
        return await _json(
            lambda: {
                "archive_format": page.archive_format,
                "boundary": _projection(page.boundary),
                "calls": [_projection(call) for call in page.calls],
                "next_after_sequence": page.next_after_sequence,
                "integrity": page.integrity,
            }
        )

    async def body(
        attempt_id: str, sha256: str, sequence: int | None, digest: str | None
    ) -> TraceBody:
        boundary = _boundary(sequence, digest, required=True)
        assert boundary is not None
        return await _work(
            lambda: read_trace_body(
                resolve_trace_attempt(catalog, attempt_id), sha256, boundary=boundary
            )
        )

    @router.get("/attempts/{attempt_id}/bodies/{sha256}")
    async def download(
        attempt_id: str,
        sha256: str,
        through_sequence: int | None = None,
        journal_digest: str | None = None,
    ) -> Response:
        result = await body(attempt_id, sha256, through_sequence, journal_digest)
        return await _work(
            lambda: Response(
                result.body,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f'attachment; filename="inference-{result.sha256}.bin"',
                    "X-Content-Type-Options": "nosniff",
                },
            )
        )

    @router.get("/attempts/{attempt_id}/bodies/{sha256}/preview")
    async def preview(
        attempt_id: str,
        sha256: str,
        through_sequence: int | None = None,
        journal_digest: str | None = None,
    ) -> JSONResponse:
        result = await body(attempt_id, sha256, through_sequence, journal_digest)

        def payload() -> dict[str, object]:
            prefix = result.body[:65536]
            replacement = False
            try:
                text = prefix.decode("utf-8")
            except UnicodeDecodeError:
                text = prefix.decode("utf-8", errors="replace")
                replacement = True
            return {
                "sha256": result.sha256,
                "byte_length": result.byte_length,
                "integrity": result.integrity,
                "text": text,
                "truncated": result.byte_length > len(prefix),
                "preview_byte_length": len(prefix),
                "replacement_used": replacement,
                "preview_kind": "utf8_text",
            }

        return await _json(payload)

    return router


def create_analysis_app(catalog: RunCatalog, *, auth: AdminSession) -> FastAPI:
    """Build an inert app: only caller-owned catalog identity and credentials."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def no_store(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(create_trace_analysis_router(catalog, auth=auth, mode="offline"))
    return app
