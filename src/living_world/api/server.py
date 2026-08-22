from collections.abc import Mapping

from fastapi import FastAPI, HTTPException

from living_world import __version__
from living_world.api.inspection import EngineWorldInspector
from living_world.simulation.simulation_engine import SimulationEngine


def create_app(engine: SimulationEngine) -> FastAPI:
    """Create the privileged, read-only engine inspection application."""

    inspector = EngineWorldInspector(engine)
    application = FastAPI(title="Living World Simulator")

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @application.get("/world/tick")
    async def world_tick() -> dict[str, int]:
        return {"tick": inspector.tick()}

    @application.get("/world/run")
    async def world_run() -> Mapping[str, object]:
        snapshot = inspector.run_metadata()
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Run metadata not found.")
        return snapshot

    @application.get("/world")
    async def world_summary() -> Mapping[str, object]:
        return inspector.world_summary()

    @application.get("/world/entities")
    async def entities() -> tuple[Mapping[str, object], ...]:
        return inspector.entities()

    @application.get("/world/entities/{entity_id}")
    async def entity(entity_id: str) -> Mapping[str, object]:
        snapshot = inspector.entity(entity_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Entity not found.")
        return snapshot

    @application.get("/world/definitions")
    async def definitions() -> tuple[Mapping[str, object], ...]:
        return inspector.definitions()

    @application.get("/world/resources")
    async def resources() -> tuple[Mapping[str, object], ...]:
        return inspector.resources()

    @application.get("/world/relationships")
    async def relationships() -> tuple[Mapping[str, object], ...]:
        return inspector.relationships()

    @application.get("/world/placements")
    async def world_placements() -> tuple[Mapping[str, object], ...]:
        return inspector.placements()

    @application.get("/world/external-references")
    async def external_world_references() -> tuple[Mapping[str, object], ...]:
        return inspector.external_world_references()

    @application.get("/world/external-dispatches")
    async def external_dispatches() -> tuple[Mapping[str, object], ...]:
        return inspector.external_dispatches()

    @application.get("/world/goals")
    async def goals() -> tuple[Mapping[str, object], ...]:
        return inspector.goals()

    @application.get("/world/needs")
    async def needs() -> tuple[Mapping[str, object], ...]:
        return inspector.needs()

    @application.get("/world/consequences")
    async def consequences() -> Mapping[str, object]:
        return inspector.consequences()

    @application.get("/world/events")
    async def events() -> tuple[Mapping[str, object], ...]:
        return inspector.events()

    @application.get("/world/npcs")
    async def npcs() -> tuple[Mapping[str, object], ...]:
        return inspector.npcs()

    @application.get("/world/observations")
    async def observations() -> tuple[Mapping[str, object], ...]:
        return inspector.observations()

    @application.get("/world/memories")
    async def memories() -> tuple[Mapping[str, object], ...]:
        return inspector.memories()

    @application.get("/world/knowledge")
    async def knowledge() -> tuple[Mapping[str, object], ...]:
        return inspector.knowledge()

    @application.get("/world/beliefs")
    async def beliefs() -> tuple[Mapping[str, object], ...]:
        return inspector.beliefs()

    @application.get("/world/experiences")
    async def experiences() -> tuple[Mapping[str, object], ...]:
        return inspector.experiences()

    @application.get("/world/cognitive-history/{holder_id}")
    async def cognitive_history(holder_id: str) -> Mapping[str, object]:
        snapshot = inspector.cognitive_history(holder_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Holder not found.")
        return snapshot

    return application


app = create_app(SimulationEngine())
