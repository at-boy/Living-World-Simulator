from importlib.resources import files

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from living_world import __version__
from living_world.api.inspection import EngineWorldInspector
from living_world.api.inspection_routes import create_inspection_router
from living_world.simulation.simulation_engine import SimulationEngine


def create_app(engine: SimulationEngine) -> FastAPI:
    """Create the privileged, read-only engine inspection application."""

    inspector = EngineWorldInspector(engine)
    application = FastAPI(title="Living World Simulator")

    @application.get("/inspector")
    async def inspector_page() -> Response:
        return Response(
            files("living_world.api").joinpath("static/inspector.html").read_bytes(),
            media_type="text/html",
        )

    @application.get("/inspector/assets/{asset_name}")
    async def inspector_asset(asset_name: str) -> Response:
        media_types = {"inspector.css": "text/css", "inspector.js": "text/javascript"}
        if asset_name not in media_types:
            raise HTTPException(status_code=404, detail="Asset not found.")
        return Response(
            files("living_world.api").joinpath(f"static/{asset_name}").read_bytes(),
            media_type=media_types[asset_name],
        )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    def resolve_inspector(request: Request) -> EngineWorldInspector:
        return inspector

    # Attach concrete routes before startup to preserve the public flat inventory.
    application.router.routes.extend(create_inspection_router(resolve_inspector).routes)

    return application


app = create_app(SimulationEngine())
