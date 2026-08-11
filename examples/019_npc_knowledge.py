"""Demonstrate holder-scoped NPC knowledge with source attribution."""

from living_world.core.memory import CognitiveSalience
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Record two different NPC claims without asserting either as world truth."""

    engine = SimulationEngine()
    engine.state.tick = 25
    engine.knowledge.record(
        holder_id="mira",
        subject_id="east_bridge",
        statement="The east bridge is closed.",
        source_description="The miller told me.",
        salience=CognitiveSalience(importance=0.7),
        supporting_observations=("observation_000001",),
    )
    engine.knowledge.record(
        holder_id="tomas",
        subject_id="east_bridge",
        statement="The bridge may be difficult to cross.",
        source_description="A traveller mentioned it.",
        salience=CognitiveSalience(importance=0.5),
    )

    print("Mira's knowledge:")
    for knowledge in engine.knowledge.knowledge_for("mira"):
        print(f"- {knowledge.statement} Source: {knowledge.source_description}")
    print("Tomas's knowledge:")
    for knowledge in engine.knowledge.knowledge_for("tomas"):
        print(f"- {knowledge.statement} Source: {knowledge.source_description}")


if __name__ == "__main__":
    main()
