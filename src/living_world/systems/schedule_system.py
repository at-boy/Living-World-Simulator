from living_world.core.entity import Entity
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.npc.identity import NPCIdentity
from living_world.npc.occupation import Occupation
from living_world.npc.schedule import schedule_from_attribute
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class ScheduleSystem(SimulationSystem):
    """Maintain the engine-owned current activity for scheduled NPC entities."""

    def __init__(self, entities: EntityManager, events: EventManager) -> None:
        self._entities = entities
        self._events = events

    def step(self, state: WorldState) -> None:
        """Synchronize each NPC's activity for the current simulation tick."""

        for entity in sorted(self._entities.all(), key=lambda item: item.id):
            if "npc_identity" not in entity.attributes:
                continue

            self._validate_npc_attributes(entity)
            active_activity = self._active_activity(entity, state.tick)
            previous_activity = self._previous_activity(entity)
            if active_activity == previous_activity:
                continue

            self._entities.set_attribute(
                entity_id=entity.id,
                key="active_activity",
                value=active_activity,
            )
            self._events.record(
                kind="npc_activity_changed",
                subject_id=entity.id,
                attributes={
                    "previous_activity": previous_activity,
                    "active_activity": active_activity,
                },
            )

    def _validate_npc_attributes(self, entity: Entity) -> None:
        NPCIdentity.from_attribute(entity.attributes["npc_identity"])

        if "occupation" in entity.attributes:
            Occupation.from_attribute(entity.attributes["occupation"])

        schedule_from_attribute(entity.attributes.get("schedule", []))

    def _active_activity(self, entity: Entity, tick: int) -> str | None:
        entries = schedule_from_attribute(entity.attributes.get("schedule", []))
        return next(
            (
                entry.activity
                for entry in entries
                if entry.start_tick <= tick < entry.end_tick
            ),
            None,
        )

    def _previous_activity(self, entity: Entity) -> str | None:
        value = entity.attributes.get("active_activity")
        if value is not None and not isinstance(value, str):
            raise TypeError("NPC active_activity must be a string or None.")
        return value
