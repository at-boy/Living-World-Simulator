"""Translate privileged local geometry into holder-scoped qualitative prose."""

from living_world.api.inspection import EngineWorldInspector
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.core.definition import Definition
from living_world.perception.perception_context import PerceptionContext
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial import Bounds, BoundsKind, Point, SpatialPerceptionEngine


def main() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition("place"))
    engine.definitions.register(Definition("npc"))
    engine.definitions.register(Definition("feature"))

    oakford = engine.entities.create(definition_key="place", name="Oakford")
    erik = engine.entities.create(definition_key="npc", name="Erik")
    well = engine.entities.create(definition_key="feature", name="Well")

    engine.spatial.place(
        entity_id=oakford.id,
        geometry=Bounds(40, 80, 20, 20),
        bounds_kind=BoundsKind.AREA,
    )
    engine.spatial.place(
        entity_id=erik.id,
        geometry=Point(47, 83),
        containing_entity_id=oakford.id,
    )
    engine.spatial.place(
        entity_id=well.id,
        geometry=Point(48, 84),
        containing_entity_id=oakford.id,
    )
    road = engine.relationships.create(
        kind="road",
        source_id=erik.id,
        target_id=well.id,
    )

    perception = SpatialPerceptionEngine().perceive(
        PerceptionContext(
            observer=erik,
            subject=well,
            world_state=engine.state,
            capabilities={},
            relationships=(road,),
            tick=engine.state.tick,
        )
    )
    engine.observations.record(
        observer=perception.observer,
        subject=perception.subject,
        description=perception.description,
        confidence=perception.confidence,
        evidence=dict(perception.evidence),
        metadata=dict(perception.metadata),
    )

    context = NPCContextAssembler(engine.state).assemble(holder_id=erik.id)
    print(context.current_perceptions[0])
    print("Exact geometry remains available only to privileged inspection:")
    print(EngineWorldInspector(engine).placements()[0]["geometry"])


if __name__ == "__main__":
    main()
