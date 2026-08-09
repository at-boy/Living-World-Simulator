from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.simulation.simulation_engine import SimulationEngine

definition_document: str = """\
definitions:
  - key: oak_tree
    initial_attributes:
      health: 100
      resources:
        wood: 30
    systems:
      - growth
"""

with TemporaryDirectory() as temporary_directory:
    definition_path = Path(temporary_directory) / "world_definitions.yaml"
    definition_path.write_text(definition_document, encoding="utf-8")

    engine = SimulationEngine()
    engine.load_definitions(definition_path)
    oak_tree = engine.entities.create(
        definition_key="oak_tree",
        name="Old Oak",
    )

print(oak_tree)
