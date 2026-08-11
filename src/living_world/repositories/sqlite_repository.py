"""SQLite persistence for generic Living World records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar

from living_world.core.belief import Belief, BeliefHistoryEntry, BeliefStatus
from living_world.core.entity import Entity
from living_world.core.event import Event
from living_world.core.experience import Experience, ExperienceHistoryEntry
from living_world.core.knowledge import Knowledge
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.npc_relationship import NPCRelationship
from living_world.core.observation import Observation
from living_world.core.relationship import Relationship
from living_world.state.world_state import WorldState

_SCHEMA_VERSION = 1
Record = (
    Entity
    | Relationship
    | Event
    | Observation
    | Belief
    | Experience
    | Memory
    | NPCRelationship
    | Knowledge
)
RecordType = TypeVar("RecordType", bound=Record)


class RepositoryError(RuntimeError):
    """Base error for a repository persistence failure."""


class RepositoryLoadError(RepositoryError):
    """Raised when persisted data cannot be loaded safely."""


class RepositorySaveError(RepositoryError):
    """Raised when a world snapshot cannot be saved."""


class SQLiteRepository:
    """Store an atomic, versioned WorldState snapshot in a SQLite database."""

    def __init__(self, database_path: str) -> None:
        if not database_path:
            raise RepositoryError("SQLite database path cannot be empty.")

        self._database_path = Path(database_path)

    def load_world(self) -> WorldState:
        """Load and validate a full world snapshot without mutating callers."""

        try:
            with self._connect() as connection:
                self._create_schema(connection)
                row = connection.execute(
                    "SELECT schema_version, payload FROM world_snapshots WHERE id = 1"
                ).fetchone()
        except sqlite3.Error as exc:
            raise RepositoryLoadError(
                f"Could not load SQLite world at '{self._database_path}'."
            ) from exc

        if row is None:
            return WorldState()

        schema_version, payload = row
        if schema_version != _SCHEMA_VERSION:
            raise RepositoryLoadError(
                f"Unsupported world schema version {schema_version!r}."
            )

        try:
            decoded_payload = json.loads(payload)
            return _deserialize_world(decoded_payload)
        except (TypeError, ValueError, KeyError) as exc:
            raise RepositoryLoadError("Persisted world data is malformed.") from exc

    def save_world(self, state: WorldState) -> None:
        """Serialize and atomically replace the persisted world snapshot."""

        try:
            payload = json.dumps(
                _serialize_world(state),
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise RepositorySaveError("World state is not JSON serializable.") from exc

        try:
            with self._connect() as connection:
                self._create_schema(connection)
                connection.execute(
                    """
                    INSERT INTO world_snapshots (id, schema_version, payload)
                    VALUES (1, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        schema_version = excluded.schema_version,
                        payload = excluded.payload
                    """,
                    (_SCHEMA_VERSION, payload),
                )
        except sqlite3.Error as exc:
            raise RepositorySaveError(
                f"Could not save SQLite world at '{self._database_path}'."
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS world_snapshots (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                schema_version INTEGER NOT NULL,
                payload TEXT NOT NULL
            )
            """)


def _serialize_world(state: WorldState) -> dict[str, object]:
    return {
        "tick": state.tick,
        "entities": [_serialize_entity(entity) for entity in state.entities.values()],
        "relationships": [
            _serialize_relationship(relationship)
            for relationship in state.relationships.values()
        ],
        "events": [_serialize_event(event) for event in state.events.values()],
        "observations": [
            _serialize_observation(observation)
            for observation in state.observations.values()
        ],
        "beliefs": [_serialize_belief(belief) for belief in state.beliefs.values()],
        "experiences": [
            _serialize_experience(experience)
            for experience in state.experiences.values()
        ],
        "memories": [_serialize_memory(memory) for memory in state.memories.values()],
        "npc_relationships": [
            _serialize_npc_relationship(relationship)
            for relationship in state.npc_relationships.values()
        ],
        "knowledge": [
            _serialize_knowledge(knowledge) for knowledge in state.knowledge.values()
        ],
    }


def _serialize_entity(entity: Entity) -> dict[str, object]:
    return {
        "id": entity.id,
        "definition_key": entity.definition_key,
        "name": entity.name,
        "attributes": entity.attributes,
        "created_tick": entity.created_tick,
        "destroyed_tick": entity.destroyed_tick,
    }


def _serialize_relationship(relationship: Relationship) -> dict[str, object]:
    return {
        "id": relationship.id,
        "kind": relationship.kind,
        "source_id": relationship.source_id,
        "target_id": relationship.target_id,
        "attributes": dict(relationship.attributes),
        "created_tick": relationship.created_tick,
        "destroyed_tick": relationship.destroyed_tick,
    }


def _serialize_event(event: Event) -> dict[str, object]:
    return {
        "id": event.id,
        "tick": event.tick,
        "kind": event.kind,
        "subject_id": event.subject_id,
        "attributes": _event_attributes_as_json(event.attributes),
    }


def _event_attributes_as_json(attributes: Mapping[str, object]) -> dict[str, object]:
    return {key: _event_value_as_json(value) for key, value in attributes.items()}


def _event_value_as_json(value: object) -> object:
    if isinstance(value, Mapping):
        return _event_attributes_as_json(value)
    if isinstance(value, tuple):
        return [_event_value_as_json(item) for item in value]
    if isinstance(value, frozenset):
        values = [_event_value_as_json(item) for item in value]
        return sorted(values, key=_event_value_sort_key)
    return value


def _event_value_sort_key(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _serialize_observation(observation: Observation) -> dict[str, object]:
    return {
        "id": observation.id,
        "tick": observation.tick,
        "observer": observation.observer,
        "subject": observation.subject,
        "description": observation.description,
        "confidence": observation.confidence,
        "evidence": dict(observation.evidence),
        "metadata": dict(observation.metadata),
    }


def _serialize_belief(belief: Belief) -> dict[str, object]:
    return {
        "id": belief.id,
        "tick": belief.tick,
        "holder_id": belief.holder_id,
        "subject_id": belief.subject_id,
        "proposition": belief.proposition,
        "confidence": belief.confidence,
        "importance": belief.importance,
        "status": belief.status.value,
        "supporting_observations": list(belief.supporting_observations),
        "supporting_memories": list(belief.supporting_memories),
        "supporting_experiences": list(belief.supporting_experiences),
        "metadata": dict(belief.metadata),
        "history": [
            {
                "tick": entry.tick,
                "reason": entry.reason,
                "old_confidence": entry.old_confidence,
                "new_confidence": entry.new_confidence,
                "old_status": entry.old_status.value,
                "new_status": entry.new_status.value,
            }
            for entry in belief.history
        ],
        "salience": _serialize_salience(belief.salience),
    }


def _serialize_experience(experience: Experience) -> dict[str, object]:
    return {
        "id": experience.id,
        "tick": experience.tick,
        "holder_id": experience.holder_id,
        "subject_id": experience.subject_id,
        "summary": experience.summary,
        "supporting_observations": list(experience.supporting_observations),
        "supporting_memories": list(experience.supporting_memories),
        "supporting_beliefs": list(experience.supporting_beliefs),
        "metadata": dict(experience.metadata),
        "history": [
            {
                "tick": entry.tick,
                "reason": entry.reason,
                "old_summary": entry.old_summary,
                "new_summary": entry.new_summary,
            }
            for entry in experience.history
        ],
        "salience": _serialize_salience(experience.salience),
    }


def _serialize_memory(memory: Memory) -> dict[str, object]:
    return {
        "id": memory.id,
        "tick": memory.tick,
        "holder_id": memory.holder_id,
        "subject_id": memory.subject_id,
        "summary": memory.summary,
        "salience": _serialize_salience(memory.salience),
        "source_observation_ids": list(memory.source_observation_ids),
    }


def _serialize_npc_relationship(relationship: NPCRelationship) -> dict[str, object]:
    return {
        "id": relationship.id,
        "tick": relationship.tick,
        "holder_id": relationship.holder_id,
        "subject_id": relationship.subject_id,
        "summary": relationship.summary,
        "salience": _serialize_salience(relationship.salience),
        "source_observation_ids": list(relationship.source_observation_ids),
    }


def _serialize_knowledge(knowledge: Knowledge) -> dict[str, object]:
    return {
        "id": knowledge.id,
        "tick": knowledge.tick,
        "holder_id": knowledge.holder_id,
        "subject_id": knowledge.subject_id,
        "statement": knowledge.statement,
        "source_description": knowledge.source_description,
        "salience": _serialize_salience(knowledge.salience),
        "supporting_observations": list(knowledge.supporting_observations),
        "supporting_memories": list(knowledge.supporting_memories),
        "supporting_experiences": list(knowledge.supporting_experiences),
        "metadata": _knowledge_metadata_as_json(knowledge.metadata),
    }


def _serialize_salience(salience: CognitiveSalience) -> dict[str, object]:
    return {"importance": salience.importance, "is_core": salience.is_core}


def _deserialize_world(payload: object) -> WorldState:
    payload_mapping = _mapping(payload)
    state = WorldState(tick=_integer(payload_mapping["tick"]))
    state.entities = _records(payload_mapping["entities"], _deserialize_entity)
    state.relationships = _records(
        payload_mapping["relationships"], _deserialize_relationship
    )
    state.events = _records(payload_mapping["events"], _deserialize_event)
    state.observations = _records(
        payload_mapping["observations"], _deserialize_observation
    )
    state.beliefs = _records(payload_mapping["beliefs"], _deserialize_belief)
    state.experiences = _records(
        payload_mapping["experiences"], _deserialize_experience
    )
    state.memories = _records(payload_mapping.get("memories", []), _deserialize_memory)
    state.npc_relationships = _records(
        payload_mapping.get("npc_relationships", []), _deserialize_npc_relationship
    )
    state.knowledge = _records(
        payload_mapping.get("knowledge", []), _deserialize_knowledge
    )
    return state


def _records(
    values: object,
    factory: Callable[[Mapping[str, object]], RecordType],
) -> dict[str, RecordType]:
    if not isinstance(values, list):
        raise TypeError("Persisted records must be lists.")
    records = [factory(_mapping(value)) for value in values]
    result = {record.id: record for record in records}
    if len(result) != len(records):
        raise ValueError("Persisted record identifiers must be unique.")
    return result


def _deserialize_entity(value: Mapping[str, object]) -> Entity:
    return Entity(
        id=_string(value["id"]),
        definition_key=_string(value["definition_key"]),
        name=_string(value["name"]),
        attributes=dict(_mapping(value["attributes"])),
        created_tick=_integer(value["created_tick"]),
        destroyed_tick=_optional_integer(value["destroyed_tick"]),
    )


def _deserialize_relationship(value: Mapping[str, object]) -> Relationship:
    return Relationship(
        id=_string(value["id"]),
        kind=_string(value["kind"]),
        source_id=_string(value["source_id"]),
        target_id=_string(value["target_id"]),
        attributes=dict(_mapping(value["attributes"])),
        created_tick=_integer(value["created_tick"]),
        destroyed_tick=_optional_integer(value["destroyed_tick"]),
    )


def _deserialize_event(value: Mapping[str, object]) -> Event:
    return Event(
        id=_string(value["id"]),
        tick=_integer(value["tick"]),
        kind=_string(value["kind"]),
        subject_id=_optional_string(value["subject_id"]),
        attributes=_mapping(value["attributes"]),
    )


def _deserialize_observation(value: Mapping[str, object]) -> Observation:
    return Observation(
        id=_string(value["id"]),
        tick=_integer(value["tick"]),
        observer=_string(value["observer"]),
        subject=_string(value["subject"]),
        description=_string(value["description"]),
        confidence=_number(value["confidence"]),
        evidence=_mapping(value["evidence"]),
        metadata=_mapping(value["metadata"]),
    )


def _deserialize_belief(value: Mapping[str, object]) -> Belief:
    return Belief(
        id=_string(value["id"]),
        tick=_integer(value["tick"]),
        holder_id=_string(value["holder_id"]),
        subject_id=_string(value["subject_id"]),
        proposition=_string(value["proposition"]),
        confidence=_number(value["confidence"]),
        importance=_number(value["importance"]),
        status=BeliefStatus(_string(value["status"])),
        supporting_observations=_strings(value["supporting_observations"]),
        supporting_memories=_strings(value["supporting_memories"]),
        supporting_experiences=_strings(value["supporting_experiences"]),
        metadata=_mapping(value["metadata"]),
        history=tuple(
            BeliefHistoryEntry(
                tick=_integer(entry["tick"]),
                reason=_string(entry["reason"]),
                old_confidence=_number(entry["old_confidence"]),
                new_confidence=_number(entry["new_confidence"]),
                old_status=BeliefStatus(_string(entry["old_status"])),
                new_status=BeliefStatus(_string(entry["new_status"])),
            )
            for history_value in _list(value["history"])
            for entry in (_mapping(history_value),)
        ),
        salience=_deserialize_salience(
            value.get("salience"),
            default_importance=_number(value["importance"]),
            default_is_core=BeliefStatus(_string(value["status"])) is BeliefStatus.CORE,
        ),
    )


def _deserialize_experience(value: Mapping[str, object]) -> Experience:
    return Experience(
        id=_string(value["id"]),
        tick=_integer(value["tick"]),
        holder_id=_string(value["holder_id"]),
        subject_id=_string(value["subject_id"]),
        summary=_string(value["summary"]),
        supporting_observations=_strings(value["supporting_observations"]),
        supporting_memories=_strings(value["supporting_memories"]),
        supporting_beliefs=_strings(value["supporting_beliefs"]),
        metadata=_mapping(value["metadata"]),
        history=tuple(
            ExperienceHistoryEntry(
                tick=_integer(entry["tick"]),
                reason=_string(entry["reason"]),
                old_summary=_string(entry["old_summary"]),
                new_summary=_string(entry["new_summary"]),
            )
            for history_value in _list(value["history"])
            for entry in (_mapping(history_value),)
        ),
        salience=_deserialize_salience(value.get("salience")),
    )


def _deserialize_memory(value: Mapping[str, object]) -> Memory:
    return Memory(
        id=_string(value["id"]),
        tick=_integer(value["tick"]),
        holder_id=_string(value["holder_id"]),
        subject_id=_string(value["subject_id"]),
        summary=_string(value["summary"]),
        salience=_deserialize_salience(value.get("salience")),
        source_observation_ids=_strings(value["source_observation_ids"]),
    )


def _deserialize_npc_relationship(value: Mapping[str, object]) -> NPCRelationship:
    return NPCRelationship(
        id=_string(value["id"]),
        tick=_integer(value["tick"]),
        holder_id=_string(value["holder_id"]),
        subject_id=_string(value["subject_id"]),
        summary=_string(value["summary"]),
        salience=_deserialize_salience(value.get("salience")),
        source_observation_ids=_strings(value["source_observation_ids"]),
    )


def _deserialize_knowledge(value: Mapping[str, object]) -> Knowledge:
    return Knowledge(
        id=_string(value["id"]),
        tick=_integer(value["tick"]),
        holder_id=_string(value["holder_id"]),
        subject_id=_string(value["subject_id"]),
        statement=_string(value["statement"]),
        source_description=_string(value["source_description"]),
        salience=_deserialize_salience(value.get("salience")),
        supporting_observations=_strings(value["supporting_observations"]),
        supporting_memories=_strings(value["supporting_memories"]),
        supporting_experiences=_strings(value["supporting_experiences"]),
        metadata=_mapping(value["metadata"]),
    )


def _knowledge_metadata_as_json(metadata: Mapping[str, object]) -> dict[str, object]:
    """Return recursively frozen knowledge metadata as JSON-safe mutable values."""

    return _event_attributes_as_json(metadata)


def _deserialize_salience(
    value: object,
    *,
    default_importance: float = 0.0,
    default_is_core: bool = False,
) -> CognitiveSalience:
    if value is None:
        return CognitiveSalience(
            importance=default_importance,
            is_core=default_is_core,
        )
    mapping = _mapping(value)
    return CognitiveSalience(
        importance=_number(mapping["importance"]),
        is_core=_boolean(mapping["is_core"]),
    )


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Persisted value must be an object with string keys.")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError("Persisted value must be a list.")
    return value


def _strings(value: object) -> tuple[str, ...]:
    return tuple(_string(item) for item in _list(value))


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("Persisted value must be a string.")
    return value


def _optional_string(value: object) -> str | None:
    return None if value is None else _string(value)


def _integer(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("Persisted value must be an integer.")
    return value


def _optional_integer(value: object) -> int | None:
    return None if value is None else _integer(value)


def _number(value: object) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("Persisted value must be a number.")
    return float(value)


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        raise TypeError("Persisted value must be a boolean.")
    return value
