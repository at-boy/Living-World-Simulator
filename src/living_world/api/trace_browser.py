"""Public static-only shell for the protected saved trace evidence API."""

from importlib.resources import files

from fastapi import APIRouter, Response


def create_trace_browser_router() -> APIRouter:
    """Expose exactly three packaged resources, independent of catalog or runtime."""
    router = APIRouter()

    def resource(name: str, media: str) -> Response:
        return Response(
            files("living_world.api").joinpath("static", name).read_bytes(),
            media_type=media,
            headers={"Cache-Control": "no-store"},
        )

    @router.get("/analysis")
    def shell() -> Response:
        return resource("analysis.html", "text/html")

    @router.get("/analysis/assets/analysis.css")
    def stylesheet() -> Response:
        return resource("analysis.css", "text/css")

    @router.get("/analysis/assets/analysis.js")
    def script() -> Response:
        return resource("analysis.js", "text/javascript")

    return router
