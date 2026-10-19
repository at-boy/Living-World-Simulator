from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Load a reproducible scenario through public engine interfaces."""

    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "world.yaml").write_text(
            "definitions:\n  - key: settlement\n  - key: person\n",
            encoding="utf-8",
        )
        scenario_path = root / "founders.yaml"
        scenario_path.write_text(
            """schema_version: 1
key: oakford-founders
seed: 42
definitions: world.yaml
run:
  max_ticks: 24
entities:
  - label: oakford
    definition: settlement
    name: Oakford
  - label: rhea
    definition: person
    name: Rhea
relationships:
  - kind: member_of
    source: rhea
    target: oakford
""",
            encoding="utf-8",
        )
        engine = SimulationEngine()
        scenario = engine.load_scenario(scenario_path)

    print("Scenario:", scenario.key)
    print("Seed:", scenario.seed)
    print("Entities:", [entity.name for entity in engine.entities.all()])


if __name__ == "__main__":
    main()
