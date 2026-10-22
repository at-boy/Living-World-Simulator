"""Reusable privileged GET-only world inspection routes."""

from collections.abc import Callable, Mapping

from fastapi import APIRouter, Depends, HTTPException, Request

from living_world.api.inspection import WorldInspector


def create_inspection_router(
    resolve_inspector: Callable[[Request], WorldInspector],
) -> APIRouter:
    """Resolve one inspector per request in a synchronous dependency worker."""
    router = APIRouter()
    dependency = Depends(resolve_inspector)

    @router.get("/world/tick")
    async def world_tick(
        inspector: WorldInspector = dependency,
    ) -> dict[str, int]:
        return {"tick": inspector.tick()}

    @router.get("/world/replay")
    async def world_replay(
        inspector: WorldInspector = dependency,
    ) -> Mapping[str, object]:
        return inspector.replay()

    @router.get("/world/run")
    async def world_run(
        inspector: WorldInspector = dependency,
    ) -> Mapping[str, object]:
        snapshot = inspector.run_metadata()
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Run metadata not found.")
        return snapshot

    @router.get("/world")
    async def world_summary(
        inspector: WorldInspector = dependency,
    ) -> Mapping[str, object]:
        return inspector.world_summary()

    @router.get("/world/entities")
    async def entities(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.entities()

    @router.get("/world/entities/{entity_id}")
    async def entity(
        entity_id: str, inspector: WorldInspector = dependency
    ) -> Mapping[str, object]:
        snapshot = inspector.entity(entity_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Entity not found.")
        return snapshot

    @router.get("/world/definitions")
    async def definitions(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.definitions()

    @router.get("/world/resources")
    async def resources(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.resources()

    @router.get("/world/relationships")
    async def relationships(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.relationships()

    @router.get("/world/placements")
    async def world_placements(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.placements()

    @router.get("/world/external-references")
    async def external_world_references(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.external_world_references()

    @router.get("/world/external-dispatches")
    async def external_dispatches(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.external_dispatches()

    @router.get("/world/goals")
    async def goals(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.goals()

    @router.get("/world/settlement-stages")
    def settlement_stages(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.settlement_stages()

    @router.get("/world/needs")
    async def needs(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.needs()

    @router.get("/world/consequences")
    async def consequences(
        inspector: WorldInspector = dependency,
    ) -> Mapping[str, object]:
        return inspector.consequences()

    @router.get("/world/work-orders")
    async def work_orders(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.work_orders()

    @router.get("/world/events")
    async def events(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.events()

    @router.get("/world/npcs")
    async def npcs(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.npcs()

    @router.get("/world/observations")
    async def observations(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.observations()

    @router.get("/world/memories")
    async def memories(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.memories()

    @router.get("/world/knowledge")
    async def knowledge(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.knowledge()

    @router.get("/world/beliefs")
    async def beliefs(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.beliefs()

    @router.get("/world/experiences")
    async def experiences(
        inspector: WorldInspector = dependency,
    ) -> tuple[Mapping[str, object], ...]:
        return inspector.experiences()

    @router.get("/world/cognitive-history/{holder_id}")
    async def cognitive_history(
        holder_id: str, inspector: WorldInspector = dependency
    ) -> Mapping[str, object]:
        snapshot = inspector.cognitive_history(holder_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Holder not found.")
        return snapshot

    return router
