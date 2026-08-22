"""Read-only snapshots of authoritative simulation state for operators."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Protocol, cast

from fastapi.encoders import jsonable_encoder

from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial.manager import placement_snapshot
from living_world.work import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    MaintenanceWorkTarget,
    ResourceWorkTarget,
)


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

    def placements(self) -> tuple[Mapping[str, object], ...]: ...

    def external_world_references(self) -> tuple[Mapping[str, object], ...]: ...

    def external_dispatches(self) -> tuple[Mapping[str, object], ...]: ...

    def goals(self) -> tuple[Mapping[str, object], ...]: ...

    def needs(self) -> tuple[Mapping[str, object], ...]: ...

    def consequences(self) -> Mapping[str, object]: ...

    def work_orders(self) -> tuple[Mapping[str, object], ...]: ...

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
            "placement_count": len(state.placements),
            "external_world_reference_count": len(state.external_world_references),
            "external_dispatch_count": len(state.external_dispatches),
            "goal_count": len(state.goal_definitions),
            "objective_count": len(state.objective_definitions),
            "need_count": len(state.need_definitions),
            "consumption_policy_count": len(state.consumption_policies),
            "storage_policy_count": len(state.storage_policies),
            "maintenance_policy_count": len(state.maintenance_policies),
            "work_order_count": len(state.work_definitions),
            "work_reservation_count": len(state.work_reservations),
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

    def placements(self) -> tuple[Mapping[str, object], ...]:
        return tuple(
            {
                "entity_id": placement.entity_id,
                **cast(
                    dict[str, object], _snapshot_value(placement_snapshot(placement))
                ),
            }
            for placement in self._engine.spatial.all()
        )

    def external_world_references(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.external_world_references)

    def external_dispatches(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.external_dispatches)

    def goals(self) -> tuple[Mapping[str, object], ...]:
        state = self._engine.state
        return tuple(
            cast(
                Mapping[str, object],
                _snapshot_value(
                    {
                        "definition": state.goal_definitions[goal_id],
                        "state": state.goal_states[goal_id],
                        "objectives": tuple(
                            {
                                "definition": state.objective_definitions[objective_id],
                                "state": state.objective_states[objective_id],
                            }
                            for objective_id in state.goal_definitions[
                                goal_id
                            ].objective_ids
                        ),
                    }
                ),
            )
            for goal_id in sorted(state.goal_definitions)
        )

    def needs(self) -> tuple[Mapping[str, object], ...]:
        state = self._engine.state
        return tuple(
            cast(
                Mapping[str, object],
                _snapshot_value(
                    {
                        "definition": state.need_definitions[need_id],
                        "state": state.need_states[need_id],
                    }
                ),
            )
            for need_id in sorted(state.need_definitions)
        )

    def consequences(self) -> Mapping[str, object]:
        state = self._engine.state
        return cast(
            Mapping[str, object],
            _snapshot_value(
                {
                    "consumption": [
                        {
                            "policy": state.consumption_policies[key],
                            "state": state.consumption_states[key],
                        }
                        for key in sorted(state.consumption_policies)
                    ],
                    "storage": [
                        {
                            "policy": state.storage_policies[key],
                            "state": state.storage_states[key],
                        }
                        for key in sorted(state.storage_policies)
                    ],
                    "maintenance": [
                        {
                            "policy": state.maintenance_policies[key],
                            "state": state.maintenance_states[key],
                        }
                        for key in sorted(state.maintenance_policies)
                    ],
                }
            ),
        )

    def events(self) -> tuple[Mapping[str, object], ...]:
        return self._records(self._engine.state.events)

    def work_orders(self) -> tuple[Mapping[str, object], ...]:
        state = self._engine.state
        return tuple(
            cast(
                Mapping[str, object],
                _snapshot_value(
                    {
                        "definition": _work_definition_snapshot(
                            state.work_definitions[key]
                        ),
                        "state": state.work_states[key],
                        "reservations": self._engine.work.reservations_for(key),
                    }
                ),
            )
            for key in sorted(state.work_definitions)
        )

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


def _work_definition_snapshot(definition: object) -> Mapping[str, object]:
    snapshot = cast(dict[str, object], _snapshot_value(definition))
    target = definition.target
    if isinstance(target, ResourceWorkTarget):
        snapshot["target"] = {
            "kind": "resource",
            "resource": target.resource,
            "quantity": target.quantity,
        }
    elif isinstance(target, CapabilityWorkTarget):
        snapshot["target"] = {
            "kind": "capability",
            "definition_key": target.definition_key,
            "count": target.count,
        }
    elif isinstance(target, MaintenanceWorkTarget):
        snapshot["target"] = {"kind": "maintenance", "policy_id": target.policy_id}
    elif isinstance(target, ExternalConnectionWorkTarget):
        snapshot["target"] = {
            "kind": "external_connection",
            "reference_id": target.reference_id,
        }
    return snapshot


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
