from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.api.inspection import EngineWorldInspector
from living_world.external_world import ContactState
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Create, transition, persist, and safely interpret one off-map anchor."""

    with TemporaryDirectory() as directory:
        repository = SQLiteRepository(str(Path(directory) / "world.sqlite3"))
        engine = SimulationEngine(repository)
        reference = engine.external_world_references.create(
            name="River Guild",
            role="regional grain supplier",
            allowed_imports=("tools",),
            allowed_exports=("grain",),
            capacity=40,
            delay_ticks=3,
            cost_per_unit=2,
            reliability=0.8,
        )
        engine.external_world_references.transition_contact(
            reference.id, ContactState.KNOWN
        )
        visible = engine.external_world_references.npc_interpretation(reference.id)
        engine.save_world()
        privileged = EngineWorldInspector(
            SimulationEngine(repository)
        ).external_world_references()

    print("NPC-visible:", visible.name, visible.role, visible.contact_description)
    print("Privileged references:", len(privileged))


if __name__ == "__main__":
    main()
