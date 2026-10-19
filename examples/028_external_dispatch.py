from living_world.core.definition import Definition
from living_world.core.run_metadata import RunMetadata
from living_world.external_world import ContactState, DispatchDirection
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Run one deterministic off-map exchange without exposing policy to an NPC."""

    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    settlement = engine.entities.create(
        definition_key="settlement",
        name="Oakford",
        attributes={"resources": {"coin": 10, "tools": 0}},
    )
    reference = engine.external_world_references.create(
        name="River Guild",
        role="regional exchange",
        allowed_exports=("tools",),
        capacity=4,
        delay_ticks=1,
        cost_per_unit=2,
        reliability=1.0,
        contact_state=ContactState.CONTACTABLE,
    )
    engine.state.run_metadata = RunMetadata("example", 1, 42, "example")
    dispatch = engine.external_dispatches.create(
        source_entity_id=settlement.id,
        reference_id=reference.id,
        direction=DispatchDirection.INBOUND,
        good="tools",
        quantity=2,
    )
    engine.run(2)

    safe = engine.external_dispatches.perception(dispatch.id)
    print("Outcome:", safe.reference_name, safe.description)
    print("Local tools:", settlement.attributes["resources"]["tools"])


if __name__ == "__main__":
    main()
