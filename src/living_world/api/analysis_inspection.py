"""Authenticated historical inspection without a simulation owner."""

import re
from importlib.resources import files

from fastapi import APIRouter, HTTPException, Request, Response

from living_world.api.analysis_revision_source import AnalysisRevisionSource
from living_world.api.auth import AdminSession
from living_world.api.inspection import WorldInspector
from living_world.api.inspection_routes import create_inspection_router
from living_world.api.revision_source import RevisionSourceError
from living_world.archives import RunCatalog


def create_analysis_inspection_router(
    catalog: RunCatalog, *, auth: AdminSession
) -> APIRouter:
    """Reuse fixed inspector assets and panels for explicit offline selections."""
    if not isinstance(auth, AdminSession):
        raise TypeError("Expected admin session.")
    source = AnalysisRevisionSource(catalog)
    router = APIRouter()

    def resolve(request: Request) -> WorldInspector:
        auth.authorize(request)
        revision = request.path_params["revision"]
        if re.fullmatch(r"[0-9]{1,20}", revision) is None:
            raise HTTPException(404, "not_found")
        value = int(revision)
        if value > 9007199254740991:
            raise HTTPException(404, "not_found")
        try:
            return source.open(request.path_params["attempt_id"], value)
        except RevisionSourceError as failure:
            raise HTTPException(
                404 if failure.code == "not_found" else 409, failure.code
            ) from None

    @router.get("/inspector/assets/{asset_name}")
    def asset(asset_name: str) -> Response:
        media = {"inspector.css": "text/css", "inspector.js": "text/javascript"}
        if asset_name not in media:
            raise HTTPException(404, "not_found")
        return Response(
            files("living_world.api").joinpath(f"static/{asset_name}").read_bytes(),
            media_type=media[asset_name],
        )

    prefix = "/archives/{attempt_id}/checkpoints/{revision}"

    @router.get(prefix + "/inspector")
    def page(request: Request) -> Response:
        resolve(request)
        params = request.path_params
        pin = f'/archives/{params["attempt_id"]}/checkpoints/{int(params["revision"])}'
        template = (
            files("living_world.api").joinpath("static/inspector.html").read_text()
        )
        marker = '<html lang="en">'
        if template.count(marker) != 1:
            raise HTTPException(409, "archive_invalid")
        return Response(
            template.replace(
                marker,
                f'<html lang="en" data-inspection-prefix="{pin}" '
                'data-inspection-kind="historical">',
                1,
            ),
            media_type="text/html",
        )

    router.include_router(create_inspection_router(resolve), prefix=prefix)
    return router
