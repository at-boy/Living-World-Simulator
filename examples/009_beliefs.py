from living_world.core.belief import BeliefStatus
from living_world.core.definition import Definition
from living_world.perception.deterministic_perception_engine import (
    DeterministicPerceptionEngine,
)
from living_world.perception.perception_context import PerceptionContext
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    engine = SimulationEngine()

    engine.definitions.register(Definition(key="npc"))
    engine.definitions.register(Definition(key="tree"))

    observer = engine.entities.create(
        definition_key="npc",
        name="Erik",
    )

    subject = engine.entities.create(
        definition_key="tree",
        name="Old Oak",
        attributes={
            "growth": 87,
            "health": 92,
            "wood": 120,
        },
    )

    context = PerceptionContext(
        observer=observer,
        subject=subject,
        world_state=engine.state,
        capabilities={"woodcraft": 80},
        relationships=(),
        tick=engine.state.tick,
    )

    perception = DeterministicPerceptionEngine().perceive(context)

    observation = engine.observations.record(
        observer=perception.observer,
        subject=perception.subject,
        description=perception.description,
        confidence=perception.confidence,
        evidence=dict(perception.evidence),
        metadata=dict(perception.metadata),
    )

    belief = engine.beliefs.record(
        holder_id=observer.id,
        subject_id=subject.id,
        proposition=perception.description,
        confidence=perception.confidence,
        importance=0.8,
        status=BeliefStatus.ACTIVE,
        supporting_observations=(observation.id,),
        supporting_memories=("memory_000001",),
        metadata={"source": "deterministic_perception"},
    )

    important = belief.mark_important(
        tick=engine.state.tick + 1,
        reason="The tree has repeatedly proven to be valuable and healthy.",
    )

    print("Belief")
    print(f"ID: {important.id}")
    print(f"Holder: {observer.name}")
    print(f"Subject: {subject.name}")
    print(f"Proposition: {important.proposition}")
    print(f"Confidence: {important.confidence}")
    print(f"Importance: {important.importance}")
    print(f"Status: {important.status.value}")
    print(f"Observation support: {important.supporting_observations}")
    print(f"Memory support: {important.supporting_memories}")

    print()
    print("Recorded Beliefs")
    for recorded in engine.beliefs.all():
        print(
            recorded.id,
            recorded.holder_id,
            "->",
            recorded.subject_id,
            recorded.status.value,
        )


if __name__ == "__main__":
    main()
