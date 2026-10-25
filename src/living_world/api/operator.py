"""Privileged local HTTP adapter; the runtime service retains all mutation ownership."""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import asdict
from importlib.resources import files
from threading import Lock
from typing import cast

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from living_world.api.auth import AdminSession
from living_world.api.inspection import WorldInspector
from living_world.api.inspection_routes import create_inspection_router
from living_world.api.revision_source import RevisionSource, RevisionSourceError
from living_world.archives import AttemptConfig
from living_world.archives.catalog import (
    SETUP_CODES,
    AttemptSummary,
    config_document,
    read_reservation,
)
from living_world.archives.model import (
    ArchiveError,
    envelope,
    frozen_map,
    identifier,
    loads,
    plain,
)
from living_world.repositories.world_snapshot import decode_world
from living_world.runtime import (
    CommandConflictError,
    RunController,
    RuntimeService,
    RuntimeStartupError,
)


def _error(code: str) -> HTTPException:
    return HTTPException(404 if code == "not_found" else 409, code)


def _summary(item: AttemptSummary) -> dict[str, object]:
    return {
        "attempt_id": item.ref.attempt_id,
        "lineage_id": item.ref.lineage_id,
        "mode": item.mode,
        "scenario": item.scenario,
        "parent": (
            None
            if item.parent is None
            else {"attempt_id": item.parent[0], "revision": item.parent[1]}
        ),
        "started_at": item.started_at,
        "ended_at": item.ended_at,
        "lifecycle": item.lifecycle,
        "last_revision": item.last_revision,
        "tick": item.tick,
        "error_code": item.failure_code,
    }


def create_operator_app(
    service: RuntimeService, controller: RunController | None, *, auth: AdminSession
) -> FastAPI:
    if not isinstance(service, RuntimeService) or not isinstance(auth, AdminSession):
        raise TypeError("Expected runtime service and admin session.")
    if controller is not None and (
        not isinstance(controller, RunController)
        or controller is not service.controller
    ):
        raise ValueError("Runtime controller association mismatch.")
    catalog = service.catalog
    source = RevisionSource(catalog)
    metadata: dict[str, Mapping[str, object]] = {}
    metadata_lock = Lock()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await asyncio.to_thread(service.shutdown)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def no_store(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    def read(request: Request) -> None:
        auth.authorize(request)

    def write(request: Request) -> None:
        auth.authorize(request, mutation=True)

    def lookup(attempt_id: str) -> AttemptSummary:
        try:
            identifier(attempt_id)
        except ArchiveError:
            raise _error("not_found") from None
        try:
            matches = [
                item for item in catalog.attempts() if item.ref.attempt_id == attempt_id
            ]
            if not matches:
                raise _error("not_found")
            if len(matches) != 1 or matches[0].failure_code in {
                "archive_invalid",
                "archive_incomplete",
            }:
                raise _error("archive_invalid")
            return matches[0]
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001 - safe HTTP boundary
            raise _error("archive_invalid") from None

    def no_archive(item: AttemptSummary) -> bool:
        return item.last_revision is None and (
            item.failure_code == "archive_initialization_failed"
            or (
                item.mode == "ollama"
                and (
                    item.failure_code in SETUP_CODES
                    or (
                        item.failure_code is None
                        and item.lifecycle in {"initializing", "interrupted"}
                    )
                )
            )
        )

    def configuration(item: AttemptSummary) -> tuple[AttemptConfig, str]:
        if not no_archive(item):
            with catalog.open_attempt(item.ref.attempt_id, read_only=True) as archive:
                return archive.config, "archive"
        if item.failure_code == "archive_initialization_failed":
            return read_reservation(item.ref)[0], "reservation"
        return catalog.setup_config(item.ref), "requested"

    def live_metadata(attempt_id: str) -> Mapping[str, object]:
        with metadata_lock:
            if attempt_id not in metadata:
                try:
                    config, _ = configuration(lookup(attempt_id))
                    provider = config.settings.get("provider", {})
                    model = None
                    if isinstance(provider, Mapping) and isinstance(
                        provider.get("model"), str
                    ):
                        model = {
                            "name": provider["model"],
                            "digest": provider.get("model_digest"),
                        }
                    metadata[attempt_id] = frozen_map(
                        {
                            "mode": config.mode,
                            "scenario": config.scenario_key,
                            "model": model,
                            "configuration_error": None,
                        }
                    )
                except Exception:  # noqa: BLE001 - safe HTTP boundary
                    metadata[attempt_id] = frozen_map(
                        {
                            "mode": None,
                            "scenario": None,
                            "model": None,
                            "configuration_error": "archive_invalid",
                        }
                    )
            return metadata[attempt_id]

    @app.get("/runtime/status", dependencies=[Depends(read)])
    async def status(response: Response) -> dict[str, object]:
        response.headers["X-CSRF-Token"] = auth.csrf_nonce
        current = service.controller
        if current is None:
            return {"live": None}
        snapshot = current.status()
        info = cast(
            Mapping[str, object],
            plain(await asyncio.to_thread(live_metadata, snapshot.attempt.attempt_id)),
        )
        return {
            "live": {
                "attempt_id": snapshot.attempt.attempt_id,
                "lineage_id": snapshot.attempt.lineage_id,
                "state": snapshot.state.value,
                "state_version": snapshot.state_version,
                "revision": snapshot.revision,
                "tick": snapshot.tick,
                "activity": snapshot.activity,
                "error_code": snapshot.error_code,
                **info,
                "inspection_prefix": (
                    None
                    if snapshot.revision is None
                    else f"/live/checkpoints/{snapshot.revision}"
                ),
            }
        }

    @app.post("/runtime/commands", dependencies=[Depends(write)])
    async def submit(request: Request) -> JSONResponse:
        try:
            command = envelope(loads((await request.body()).decode("utf-8")))
        except Exception:  # noqa: BLE001 - safe HTTP boundary
            raise HTTPException(422, "invalid_command") from None
        if service.controller is None:
            raise _error("runtime_unavailable")
        try:
            result = await asyncio.wrap_future(service.submit(command))
        except CommandConflictError:
            raise _error("command_conflict") from None
        except RuntimeStartupError as failure:
            raise _error(
                "runtime_unavailable"
                if failure.code in {"service_closed", "service_not_ready"}
                else "archive_invalid"
            ) from None
        except Exception:  # noqa: BLE001 - safe HTTP boundary
            raise _error("archive_invalid") from None
        return JSONResponse(
            asdict(result),
            status_code={"queued": 202, "applied": 200, "rejected": 409}[result.status],
        )

    @app.get("/runtime/commands/{command_id:path}", dependencies=[Depends(read)])
    def command_status(command_id: str) -> dict[str, object]:
        current = service.controller
        if current is None:
            raise _error("not_found")
        try:
            with catalog.open_attempt(
                current.status().attempt.attempt_id, read_only=True
            ) as archive:
                receipt = archive.command(command_id)
                if receipt is None:
                    raise _error("not_found")
                return asdict(receipt)
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001 - safe HTTP boundary
            raise _error("archive_invalid") from None

    @app.get("/archives", dependencies=[Depends(read)])
    def archives() -> dict[str, object]:
        try:
            return {"attempts": [_summary(item) for item in catalog.attempts()]}
        except Exception:  # noqa: BLE001 - safe HTTP boundary
            raise _error("archive_invalid") from None

    @app.get("/archives/{attempt_id}", dependencies=[Depends(read)])
    def detail(attempt_id: str) -> dict[str, object]:
        item = lookup(attempt_id)
        try:
            config, label = configuration(item)
            entries = ()
            if not no_archive(item):
                with catalog.open_attempt(attempt_id, read_only=True) as archive:
                    entries = archive.entries()
            outcomes = [
                entry.payload["outcome"]
                for entry in entries
                if entry.kind == "attempt_finished"
            ]
            return {
                "attempt": _summary(item),
                "configuration": plain(config_document(config)),
                "configuration_source": label,
                "outcome": outcomes[-1] if outcomes else None,
                "journal_total": len(entries),
                "recent_journal": [
                    {"kind": entry.kind, "payload": plain(entry.payload)}
                    for entry in entries[-50:]
                ],
            }
        except Exception:  # noqa: BLE001 - safe HTTP boundary
            raise _error("archive_invalid") from None

    @app.get("/archives/{attempt_id}/checkpoints", dependencies=[Depends(read)])
    def checkpoints(attempt_id: str) -> dict[str, object]:
        item = lookup(attempt_id)
        try:
            if no_archive(item):
                configuration(item)
                return {"checkpoints": []}
            with catalog.open_attempt(attempt_id, read_only=True) as archive:
                latest = archive.latest_revision
                return {
                    "checkpoints": [
                        {
                            "revision": revision,
                            "tick": decode_world(
                                archive.checkpoint(revision).snapshot
                            ).tick,
                        }
                        for revision in range(0 if latest is None else latest + 1)
                    ]
                }
        except Exception:  # noqa: BLE001 - safe HTTP boundary
            raise _error("archive_invalid") from None

    def resolve(request: Request) -> WorldInspector:
        auth.authorize(request)
        params = request.path_params
        revision = params["revision"]
        if re.fullmatch(r"[0-9]+", revision) is None:
            raise _error("not_found")
        attempt_id = params.get("attempt_id")
        if attempt_id is None:
            current = service.controller
            if current is None:
                raise _error("not_found")
            attempt_id = current.status().attempt.attempt_id
        try:
            return source.open(attempt_id, int(revision))
        except RevisionSourceError as failure:
            raise _error(failure.code) from None
        except (ValueError, OverflowError):
            raise _error("not_found") from None

    @app.get("/inspector/assets/{asset_name}")
    def inspector_asset(asset_name: str) -> Response:
        media_types = {"inspector.css": "text/css", "inspector.js": "text/javascript"}
        if asset_name not in media_types:
            raise _error("not_found")
        return Response(
            files("living_world.api").joinpath(f"static/{asset_name}").read_bytes(),
            media_type=media_types[asset_name],
        )

    @app.get("/live/checkpoints/{revision}/inspector", dependencies=[Depends(read)])
    @app.get(
        "/archives/{attempt_id}/checkpoints/{revision}/inspector",
        dependencies=[Depends(read)],
    )
    def inspector_page(request: Request) -> Response:
        resolve(request)
        params = request.path_params
        revision = str(int(params["revision"]))
        attempt_id = params.get("attempt_id")
        kind = "live" if attempt_id is None else "historical"
        prefix = (
            f"/live/checkpoints/{revision}"
            if attempt_id is None
            else f"/archives/{attempt_id}/checkpoints/{revision}"
        )
        template = (
            files("living_world.api").joinpath("static/inspector.html").read_text()
        )
        marker = '<html lang="en">'
        if template.count(marker) != 1:
            raise _error("archive_invalid")
        return Response(
            template.replace(
                marker,
                f'<html lang="en" data-inspection-prefix="{prefix}" '
                f'data-inspection-kind="{kind}">',
                1,
            ),
            media_type="text/html",
        )

    app.include_router(
        create_inspection_router(resolve),
        prefix="/archives/{attempt_id}/checkpoints/{revision}",
    )
    app.include_router(
        create_inspection_router(resolve), prefix="/live/checkpoints/{revision}"
    )
    return app
