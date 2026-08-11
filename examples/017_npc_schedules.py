from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.npc.identity import NPCIdentity
from living_world.npc.occupation import Occupation
from living_world.npc.schedule import ScheduleEntry, schedule_to_attribute
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    """Demonstrate validated NPC data on a generic person entity."""

    definition_document = """\
definitions:
  - key: person
"""

    identity = NPCIdentity(
        name="Mira",
        description="A dependable village woodcutter.",
        capability_descriptions=("Experienced woodcutter",),
    )
    occupation = Occupation(
        title="Woodcutter",
        description="Harvests and prepares timber for the settlement.",
    )
    schedule = schedule_to_attribute(
        (
            ScheduleEntry(start_tick=0, end_tick=2, activity="resting"),
            ScheduleEntry(start_tick=2, end_tick=4, activity="harvesting"),
        )
    )

    with TemporaryDirectory() as temporary_directory:
        definition_path = Path(temporary_directory) / "npc.yaml"
        definition_path.write_text(definition_document, encoding="utf-8")

        engine = SimulationEngine()
        engine.load_definitions(definition_path)
        npc = engine.entities.create(
            definition_key="person",
            name="Mira",
            attributes={
                "npc_identity": identity.to_attribute(),
                "occupation": occupation.to_attribute(),
                "schedule": schedule,
                "active_activity": None,
                "woodcraft": 90,
            },
        )
        engine.run(3)

    print("NPC:", npc.attributes["npc_identity"]["name"])
    print("Occupation:", npc.attributes["occupation"]["title"])
    print("Current activity:", npc.attributes["active_activity"])
    print("Activity events:", [event.kind for event in engine.state.events.values()])


if __name__ == "__main__":
    main()
