from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Build organization and settlement structure using only graph conventions."""

    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="region"),
            Definition(key="person"),
            Definition(key="organization", systems=("organization",)),
            Definition(key="settlement", systems=("settlement",)),
        )
    )
    northreach = engine.entities.create(definition_key="region", name="Northreach")
    guild = engine.entities.create(definition_key="organization", name="Oak Guild")
    alice = engine.entities.create(definition_key="person", name="Alice")
    oakstead = engine.entities.create(definition_key="settlement", name="Oakstead")

    engine.relationships.create(kind="member_of", source_id=alice.id, target_id=guild.id)
    engine.relationships.create(kind="owns", source_id=guild.id, target_id=oakstead.id)
    engine.relationships.create(
        kind="located_in", source_id=oakstead.id, target_id=northreach.id
    )

    engine.step()

    print("Organization members:", guild.attributes["member_count"])
    print("Settlement located:", oakstead.attributes["is_located"])
    print("Settlement owners:", oakstead.attributes["owner_count"])
    print("Events:", [event.kind for event in engine.state.events.values()])


if __name__ == "__main__":
    main()
