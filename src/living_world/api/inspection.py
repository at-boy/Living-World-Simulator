"""Read-only snapshots of authoritative simulation state for operators."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Protocol, cast

from fastapi.encoders import jsonable_encoder

from living_world.simulation.simulation_engine import SimulationEngine


class WorldInspector(Protocol):
    """Privileged read-only view of a simulation world."""

    def world_summary(self) -> Mapping[str, object]: ...

    def tick(self) -> int: ...

    def run_metadata(self) -> Mapping[str, object] | None: ...

    def entities(self) -> tuple[Mapping[str, object], ...]: ...

    def entity(self, entity_id: str) -> Mapping[str, object] | None: ...

    def definitions(self) -> tuple[Mapping[str, object], ...]: ...

    def resources(self) -> tuple[Mapping[str, object], ...]: ...

    def relationships(self) -> tuple[Mapping[str, object], ...]: ...

    def events(self) -> tuple[Mapping[str, object], ...]: ...

    def npcs(self) -> tuple[Mapping[str, object], ...]: ...

    def observations(self) -> tuple[Mapping[str, object], ...]: ...

    def memories(self) -> tuple[Mapping[str, object], ...]: ...

    def knowledge(self) -> tuple[Mapping[str, object], ...]: ...

    def beliefs(self) -> tuple[Mapping[str, object], ...]: ...

    def experiences(self) -> tuple[Mapping[str, object], ...]: ...

    def cognitive_history(self, holder_id: str) -> Mapping[str, object] | None: ...


class EngineWorldInspector:
    """Create detached JSON-safe snapshots from a ``SimulationEngine``."""

    def __init__(self, engine: SimulationEngine) -> None:
        self._engine = engine

    def world_summary(self) -> Mapping[str, object]:
        state = self._engine.state
        return {
            "tick": state.tick,
            "run": self.run_metadata(),
            "entity_count": len(state.entities),
            "relationship_count": len(state.relationships),
            "event_count": len(state.events),
            "observation_count": len(state.observations),
            "memory_count": len(state.memories),
            "knowledge_count": len(state.knowledge),
            "belief_count": len(state.beliefs),
            "experience_count": len(state.experiences),
            "npc_relationship_count": len(state.npc_relationships),
            "definition_count": len(self._engine.definitions.all()),
            "resource_definition_count": len(self._engine.resource_definitions.all()),
        }

    def tick(self) -> int:
        return self._engine.state.tick

    def run_metadata(self) -> Mapping[str, object] | None:
        metadata = self._engine.state.run_metadata
        return (
            None
            if metadata is None
            else cast(Mapping[str, object], _snapshot_value(metadata))
        )

    def entities(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.entities)

    def entity(self, entity_id: str) -> Mapping[str, object] | None:
        entity = self._engine.state.entities.get(entity_id)
        return None if entity is None else _snapshot_value(entity)

    def definitions(self) -> tuple[Mapping[str, object], ...]:
        return tuple(
            _snapshot_value(definition)
            for definition in sorted(
                self._engine.definitions.all(), key=lambda item: item.key
            )
        )

    def resources(self) -> tuple[Mapping[str, object], ...]:
        return tuple(
            _snapshot_value(definition)
            for definition in sorted(
                self._engine.resource_definitions.all(), key=lambda item: item.key
            )
        )

    def relationships(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.relationships)

    def events(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.events)

    def npcs(self) -> tuple[Mapping[str, object], ...]:
        """Return the presentation attributes of entities declared as NPCs."""

        return tuple(
            _snapshot_value(
                {
                    "id": entity.id,
                    "identity": entity.attributes["npc_identity"],
                    "occupation": entity.attributes.get("occupation"),
                    "schedule": entity.attributes.get("schedule", []),
                    "active_activity": entity.attributes.get("active_activity"),
                }
            )
            for entity in sorted(
                (
                    entity
                    for entity in self._engine.state.entities.values()
                    if "npc_identity" in entity.attributes
                ),
                key=lambda entity: entity.id,
            )
        )

    def observations(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.observations)

    def memories(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.memories)

    def knowledge(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.knowledge)

    def beliefs(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.beliefs)

    def experiences(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.experiences)

    def cognitive_history(self, holder_id: str) -> Mapping[str, object] | None:
        """Return all persisted cognition scoped to one known entity holder."""

        state = self._engine.state
        if holder_id not in state.entities:
            return None
        return _snapshot_value(
            {
                "holder_id": holder_id,
                "observations": self._holder_records(
                    state.observations, holder_id, holder_field="observer"
                ),
                "memories": self._holder_records(state.memories, holder_id),
                "knowledge": self._holder_records(state.knowledge, holder_id),
                "beliefs": self._holder_records(state.beliefs, holder_id),
                "experiences": self._holder_records(state.experiences, holder_id),
                "npc_relationships": self._holder_records(
                    state.npc_relationships, holder_id
                ),
            }
        )

    @staticmethod
    def _holder_records(
        records: Mapping[str, object],
        holder_id: str,
        *,
        holder_field: str = "holder_id",
    ) -> tuple[Mapping[str, object], ...]:
        return tuple(
            _snapshot_value(records[record_id])
            for record_id in sorted(records)
            if getattr(records[record_id], holder_field) == holder_id
        )

    @staticmethod
    def _records(records: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
        return tuple(
            _snapshot_value(records[record_id]) for record_id in sorted(records)
        )


def _snapshot_value(value: object) -> object:
    """Recursively detach domain values and make them JSON-compatible."""

    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Enum):
        return _snapshot_value(value.value)
    if isinstance(value, Mapping):
        return {str(key): _snapshot_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_snapshot_value(item) for item in value]
    if isinstance(value, set | frozenset):
        return [_snapshot_value(item) for item in sorted(value, key=repr)]
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _snapshot_value(getattr(value, field.name))
            for field in fields(value)
        }
    return _snapshot_value(jsonable_encoder(value))
