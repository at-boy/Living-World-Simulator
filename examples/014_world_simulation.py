from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Run deterministic weather and population systems over generic entities."""

    definition_document = """\
definitions:
  - key: region
    initial_attributes:
      weather: clear
      weather_cycle: [clear, rain, wind]
      population: 120
      population_change: 5
      population_min: 0
      population_max: 130
    systems: [weather, population]
  - key: terrain
    initial_attributes:
      terrain_type: forest
    systems: [weather]
"""
    with TemporaryDirectory() as temporary_directory:
        definitions_path = Path(temporary_directory) / "world.yaml"
        definitions_path.write_text(definition_document, encoding="utf-8")

        engine = SimulationEngine()
        engine.load_definitions(definitions_path)
        northreach = engine.entities.create(definition_key="region", name="Northreach")
        forest = engine.entities.create(
            definition_key="terrain",
            name="Pinewood",
            attributes={"weather_cycle": ["mist", "clear"]},
        )
        engine.relationships.create(
            kind="contains", source_id=northreach.id, target_id=forest.id
        )

        engine.run(2)

    print(
        "Northreach:",
        northreach.attributes["weather"],
        northreach.attributes["population"],
    )
    print("Pinewood:", forest.attributes["weather"])
    print("Events:", [(event.kind, event.subject_id) for event in engine.state.events.values()])


if __name__ == "__main__":
    main()
