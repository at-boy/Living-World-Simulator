"""Assess authoritative settlement needs and project qualitative NPC prose."""

from living_world.core.definition import Definition
from living_world.needs import NeedDefinition, NeedKind
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    settlement = engine.entities.create(
        definition_key="settlement",
        name="Oakford",
        attributes={"population": 12, "resources": {"food": 9, "water": 18}},
    )
    engine.needs.create(
        NeedDefinition(
            "need_oakford_food",
            settlement.id,
            NeedKind.FOOD,
            1,
            0.2,
            0.5,
            3,
        )
    )
    engine.step()
    print(f"Operator assessment: {engine.state.need_states['need_oakford_food'].current}")
    visible = engine.needs.npc_interpretation("need_oakford_food")
    print(f"NPC-safe interpretation: {visible.label}: {visible.description}")


if __name__ == "__main__":
    main()
