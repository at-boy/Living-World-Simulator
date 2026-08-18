from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.api.inspection import EngineWorldInspector
from living_world.core.definition import Definition
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial import Bounds, BoundsKind, Point


def main() -> None:
    """Place, persist, reload, and inspect a small local spatial world."""

    with TemporaryDirectory() as directory:
        repository = SQLiteRepository(str(Path(directory) / "world.sqlite3"))
        engine = SimulationEngine(repository)
        engine.definitions.register(Definition("place"))
        settlement = engine.entities.create(definition_key="place", name="Oakford")
        well = engine.entities.create(definition_key="place", name="Well")
        engine.spatial.place(
            entity_id=settlement.id,
            geometry=Bounds(0, 0, 20, 20),
            bounds_kind=BoundsKind.AREA,
        )
        engine.spatial.place(
            entity_id=well.id,
            geometry=Point(4, 6),
            containing_entity_id=settlement.id,
        )
        engine.save_world()

        resumed = SimulationEngine(repository)
        placements = EngineWorldInspector(resumed).placements()

    print("Placements:", len(placements))
    for placement in placements:
        print(placement["entity_id"], placement["geometry"])


if __name__ == "__main__":
    main()
