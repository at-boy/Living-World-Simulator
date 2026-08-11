from living_world.cognition.consolidation import DAY_LENGTH_TICKS, SleepCognitiveConsolidator
from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Demonstrate sleep-time NPC cognition from visible observations only."""

    engine = SimulationEngine()
    engine.definitions.register(Definition(key="person"))
    npc = engine.entities.create(
        definition_key="person",
        name="Mira",
        attributes={"active_activity": "sleeping"},
    )

    engine.state.tick = 3
    engine.observations.record(
        observer=npc.id,
        subject="old_oak",
        description="The old oak appears healthy.",
        confidence=0.8,
        evidence={"health": 92, "wood": 120},
    )
    engine.state.tick = 8
    engine.observations.record(
        observer=npc.id,
        subject="old_oak",
        description="The old oak still looks strong.",
        confidence=0.7,
        evidence={"health": 92, "wood": 120},
    )
    engine.state.tick = DAY_LENGTH_TICKS

    consolidator = SleepCognitiveConsolidator(
        entities=engine.entities,
        observations=engine.observations,
        memories=engine.memories,
        experiences=engine.experiences,
        beliefs=engine.beliefs,
    )
    created = consolidator.consolidate(
        holder_id=npc.id,
        through_tick=engine.state.tick,
    )

    print("Created cognitive records:", [type(record).__name__ for record in created])
    print("Memories:", [memory.summary for memory in engine.memories.all()])
    print("Experiences:", [experience.summary for experience in engine.experiences.all()])
    print("Candidate beliefs:", [belief.proposition for belief in engine.beliefs.all()])


if __name__ == "__main__":
    main()
