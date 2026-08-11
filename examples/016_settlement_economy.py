from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Demonstrate construction, housing, production, roads, and trade."""

    definition_document = """\
definitions:
  - key: person
  - key: settlement
  - key: house
    initial_attributes:
      progress: 100
      progress_rate: 0
      progress_max: 100
      construction_requirements:
        wood: 4
      resources:
        wood: 4
      housing_capacity: 2
    systems:
      - construction
      - housing
  - key: farm
    initial_attributes:
      production_inputs:
        seed: 1
      production_outputs:
        grain: 3
      resources:
        seed: 1
    systems:
      - production
"""

    with TemporaryDirectory() as temporary_directory:
        definition_path = Path(temporary_directory) / "settlement.yaml"
        definition_path.write_text(definition_document, encoding="utf-8")

        engine = SimulationEngine()
        engine.load_definitions(definition_path)
        riverford = engine.entities.create(
            definition_key="settlement",
            name="Riverford",
        )
        house = engine.entities.create(definition_key="house", name="Longhouse")
        resident = engine.entities.create(definition_key="person", name="Ari")
        farm = engine.entities.create(definition_key="farm", name="Oakstead Farm")
        engine.relationships.create(
            kind="housed_in",
            source_id=resident.id,
            target_id=house.id,
        )
        engine.relationships.create(
            kind="road",
            source_id=farm.id,
            target_id=riverford.id,
        )
        engine.relationships.create(
            kind="trade",
            source_id=farm.id,
            target_id=riverford.id,
            attributes={"resource": "grain", "amount": 2},
        )

        engine.step()

    print("House constructed:", house.attributes["is_constructed"])
    print("House allocation:", house.attributes["housing_allocated"])
    print("Farm resources:", farm.attributes["resources"])
    print("Riverford resources:", riverford.attributes["resources"])
    print("Events:", [event.kind for event in engine.state.events.values()])


if __name__ == "__main__":
    main()
