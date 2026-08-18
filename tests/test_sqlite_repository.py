import json
import sqlite3
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest

from living_world.core.belief import Belief, BeliefStatus
from living_world.core.entity import Entity
from living_world.core.event import Event
from living_world.core.experience import Experience
from living_world.core.knowledge import Knowledge
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.npc_relationship import NPCRelationship
from living_world.core.observation import Observation
from living_world.core.relationship import Relationship
from living_world.core.run_metadata import RunMetadata
from living_world.repositories.sqlite_repository import (
    RepositoryLoadError,
    RepositorySaveError,
    SQLiteRepository,
)
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState


def test_sqlite_repository_round_trips_all_world_records(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    state = _world_state()
    state.run_metadata = RunMetadata("oakford", 1, 42, "fingerprint")

    repository.save_world(state)

    loaded = repository.load_world()

    assert loaded.tick == 7
    assert loaded.run_metadata == state.run_metadata
    assert loaded.entities == state.entities
    assert loaded.relationships == state.relationships
    assert loaded.events == state.events
    assert loaded.observations == state.observations
    assert loaded.beliefs == state.beliefs
    assert loaded.experiences == state.experiences
    assert loaded.memories == state.memories
    assert loaded.npc_relationships == state.npc_relationships
    assert loaded.knowledge == state.knowledge


def test_loaded_history_records_remain_immutable(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    repository.save_world(_world_state())

    loaded = repository.load_world()

    with pytest.raises(FrozenInstanceError):
        loaded.events["event-1"].kind = "changed"
    with pytest.raises(TypeError):
        attributes = cast(
            MutableMapping[str, object], loaded.events["event-1"].attributes
        )
        attributes["distance"] = 5
    with pytest.raises(TypeError):
        journey = cast(
            MutableMapping[str, object], loaded.events["event-1"].attributes["journey"]
        )
        journey["distance"] = 5
    with pytest.raises(TypeError):
        stages = cast(
            MutableMapping[str, object],
            loaded.events["event-1"].attributes["journey"],
        )["stages"]
        stages[0] = "changed"
    with pytest.raises(TypeError):
        evidence = cast(
            MutableMapping[str, object], loaded.observations["observation-1"].evidence
        )
        evidence["visible"] = False
    with pytest.raises(FrozenInstanceError):
        loaded.beliefs["belief-1"].confidence = 0.1
    with pytest.raises(FrozenInstanceError):
        loaded.experiences["experience-1"].summary = "changed"
    with pytest.raises(FrozenInstanceError):
        loaded.memories["memory-1"].summary = "changed"
    with pytest.raises(FrozenInstanceError):
        loaded.npc_relationships["npc-relationship-1"].summary = "changed"
    with pytest.raises(FrozenInstanceError):
        loaded.knowledge["knowledge-1"].statement = "changed"


def test_sqlite_repository_loads_legacy_snapshot_without_knowledge(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database_path))
    repository.save_world(_world_state())

    with sqlite3.connect(database_path) as connection:
        payload = connection.execute(
            "SELECT payload FROM world_snapshots WHERE id = 1"
        ).fetchone()[0]
        legacy_payload = json.loads(payload)
        del legacy_payload["knowledge"]
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(legacy_payload),),
        )

    assert repository.load_world().knowledge == {}


def test_malformed_snapshot_raises_without_returning_partial_state(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database_path))
    repository.save_world(_world_state())
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1", ("{bad json",)
        )

    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


def test_unsupported_schema_version_raises_without_returning_partial_state(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database_path))
    repository.save_world(_world_state())
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE world_snapshots SET schema_version = ? WHERE id = 1", (3,)
        )

    with pytest.raises(RepositoryLoadError, match="Unsupported world schema version"):
        repository.load_world()


def test_invalid_database_path_raises_explicit_repository_error(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "missing" / "world.sqlite3"))

    with pytest.raises(RepositorySaveError, match="Could not save SQLite world"):
        repository.save_world(WorldState())


def test_engine_loads_and_explicitly_saves_composed_repository(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    repository.save_world(_world_state())

    engine = SimulationEngine(repository)
    engine.state.tick = 8
    engine.save_world()

    assert repository.load_world().tick == 8


def _world_state() -> WorldState:
    belief = Belief(
        id="belief-1",
        tick=5,
        holder_id="entity-1",
        subject_id="entity-2",
        proposition="The path is safe.",
        confidence=0.7,
        importance=0.7,
        status=BeliefStatus.ACTIVE,
        supporting_observations=("observation-1",),
        metadata={"source": "observation"},
    ).confirm(tick=6, reason="The route remained clear.")
    experience = Experience(
        id="experience-1",
        tick=5,
        holder_id="entity-1",
        subject_id="entity-2",
        summary="The route has been reliable.",
        supporting_observations=("observation-1",),
        supporting_beliefs=("belief-1",),
        metadata={"source": "travel"},
    ).update(tick=6, reason="A second journey confirmed it.")
    return WorldState(
        tick=7,
        entities={
            "entity-1": Entity(
                id="entity-1",
                definition_key="traveler",
                name="Ari",
                attributes={"resources": {"water": 2}},
                created_tick=1,
            ),
            "entity-2": Entity(
                id="entity-2",
                definition_key="road",
                name="Old Road",
                created_tick=1,
            ),
        },
        relationships={
            "relationship-1": Relationship(
                id="relationship-1",
                kind="travels",
                source_id="entity-1",
                target_id="entity-2",
                attributes={"frequency": "daily"},
                created_tick=2,
            )
        },
        events={
            "event-1": Event(
                id="event-1",
                tick=3,
                kind="journey_completed",
                subject_id="entity-1",
                attributes={
                    "distance": 4,
                    "journey": {"stages": [{"name": "departure"}]},
                },
            )
        },
        observations={
            "observation-1": Observation(
                id="observation-1",
                tick=4,
                observer="entity-1",
                subject="entity-2",
                description="The road is clear.",
                confidence=0.9,
                evidence={"visible": True},
                metadata={"engine": "deterministic"},
            )
        },
        beliefs={belief.id: belief},
        experiences={experience.id: experience},
        memories={
            "memory-1": Memory(
                id="memory-1",
                tick=6,
                holder_id="entity-1",
                subject_id="entity-2",
                summary="I remember the route seemed reliable.",
                salience=CognitiveSalience(importance=0.7),
                source_observation_ids=("observation-1",),
            )
        },
        npc_relationships={
            "npc-relationship-1": NPCRelationship(
                id="npc-relationship-1",
                tick=6,
                holder_id="entity-1",
                subject_id="entity-2",
                summary="I find the road dependable.",
                salience=CognitiveSalience(importance=0.6),
                source_observation_ids=("observation-1",),
            )
        },
        knowledge={
            "knowledge-1": Knowledge(
                id="knowledge-1",
                tick=6,
                holder_id="entity-1",
                subject_id="entity-2",
                statement="The old road may be difficult to cross.",
                source_description="A traveller mentioned it.",
                salience=CognitiveSalience(importance=0.6),
                supporting_observations=("observation-1",),
                supporting_memories=("memory-1",),
                supporting_experiences=("experience-1",),
                metadata={
                    "heard_at": {"location": "the market"},
                    "witnesses": ["traveller"],
                },
            )
        },
    )
