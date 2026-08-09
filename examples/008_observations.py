from living_world.core.definition import Definition
from living_world.perception.deterministic_perception_engine import (
    DeterministicPerceptionEngine,
)
from living_world.perception.perception_context import PerceptionContext
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    engine = SimulationEngine()

    engine.definitions.register(
        Definition(
            key="npc",
        )
    )

    engine.definitions.register(
        Definition(
            key="tree",
        )
    )

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
        capabilities={
            "woodcraft": 80,
        },
        relationships=(),
        tick=engine.state.tick,
    )

    perception_engine = DeterministicPerceptionEngine()
    perception = perception_engine.perceive(context)

    observation = engine.observations.record(
        observer=perception.observer,
        subject=perception.subject,
        description=perception.description,
        confidence=perception.confidence,
        evidence=dict(perception.evidence),
        metadata=dict(perception.metadata),
    )

    print("Observation")
    print(f"ID: {observation.id}")
    print(f"Tick: {observation.tick}")
    print(f"Observer: {observer.name}")
    print(f"Subject: {subject.name}")
    print(f"Description: {observation.description}")
    print(f"Confidence: {observation.confidence}")

    print()
    print("Internal Evidence")
    print(observation.evidence)

    print()
    print("Recorded Observations")

    for recorded in engine.observations.all():
        print(
            recorded.id,
            recorded.observer,
            "->",
            recorded.subject,
        )


if __name__ == "__main__":
    main()
