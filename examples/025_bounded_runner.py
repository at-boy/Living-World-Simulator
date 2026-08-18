from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.running import RunConfiguration, ScenarioRunner
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Run and resume a bounded scenario through the public runner service."""

    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "world.yaml").write_text(
            "definitions:\n  - key: project\n", encoding="utf-8"
        )
        scenario = root / "scenario.yaml"
        scenario.write_text(
            """schema_version: 1
key: bounded-runner-example
seed: 42
definitions: world.yaml
run:
  max_ticks: 2
entities:
  - label: project
    definition: project
    name: Founding Project
    attributes:
      progress: 0
      progress_rate: 1
relationships: []
""",
            encoding="utf-8",
        )
        database = root / "world.sqlite3"
        first = ScenarioRunner(SimulationEngine(SQLiteRepository(str(database)))).run(
            scenario, RunConfiguration()
        )
        resumed = ScenarioRunner(SimulationEngine(SQLiteRepository(str(database)))).run(
            scenario, RunConfiguration(max_ticks=1)
        )

    print("First run:", first.start_tick, "->", first.end_tick, first.stop_reason.value)
    print(
        "Resumed run:",
        resumed.start_tick,
        "->",
        resumed.end_tick,
        resumed.stop_reason.value,
    )


if __name__ == "__main__":
    main()
