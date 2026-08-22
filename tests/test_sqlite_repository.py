import json
import sqlite3
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest

from living_world.core.belief import Belief, BeliefStatus
from living_world.core.definition import Definition
from living_world.core.entity import Entity
from living_world.core.event import Event
from living_world.core.experience import Experience
from living_world.core.knowledge import Knowledge
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.npc_relationship import NPCRelationship
from living_world.core.observation import Observation
from living_world.core.relationship import Relationship
from living_world.core.run_metadata import RunMetadata
from living_world.goals import (
    GoalDefinition,
    GoalOwnerKind,
    GoalState,
    GoalStatus,
    ObjectiveDefinition,
    ObjectiveState,
    ResourceMinimumCriterion,
    SustainedNeedCriterion,
)
from living_world.needs import (
    ConsumptionPolicy,
    MaintenancePolicy,
    MaintenanceRequirement,
    NeedDefinition,
    NeedKind,
    StoragePolicy,
    StorageResourceRule,
)
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


def test_sqlite_repository_round_trips_schema_eight_needs(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "needs.sqlite3"))
    engine = SimulationEngine(repository)
    engine.definitions.register(Definition("settlement"))
    owner = engine.entities.create(
        definition_key="settlement",
        name="Oakford",
        attributes={"population": 4, "resources": {"food": 3}},
    )
    definition = engine.needs.create(
        NeedDefinition("need_food", owner.id, NeedKind.FOOD, 1, 0.2, 0.5, 2)
    )
    engine.step()
    expected = engine.state.need_states[definition.id]
    engine.save_world()

    loaded = repository.load_world()
    assert loaded.need_definitions[definition.id] == definition
    assert loaded.need_states[definition.id] == expected
    with sqlite3.connect(tmp_path / "needs.sqlite3") as connection:
        assert (
            connection.execute(
                "SELECT schema_version FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
            == 8
        )


@pytest.mark.parametrize("schema_version", range(1, 7))
def test_legacy_schema_loads_empty_needs_and_rewrites_eight(
    tmp_path: Path, schema_version: int
) -> None:
    database = tmp_path / f"legacy-{schema_version}.sqlite3"
    repository = SQLiteRepository(str(database))
    repository.save_world(_world_state())
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        payload["need_definitions"] = [{"id": "need_ignored"}]
        payload["need_states"] = [{"need_id": "need_ignored"}]
        connection.execute(
            "UPDATE world_snapshots SET schema_version = ?, payload = ? WHERE id = 1",
            (schema_version, json.dumps(payload)),
        )
    loaded = repository.load_world()
    assert loaded.need_definitions == {}
    assert loaded.need_states == {}
    repository.save_world(loaded)
    with sqlite3.connect(database) as connection:
        assert (
            connection.execute(
                "SELECT schema_version FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
            == 8
        )


@pytest.mark.parametrize(
    "case",
    (
        "duplicate_definition",
        "duplicate_state",
        "state_id_mismatch",
        "unexpected_field",
        "overlong_history",
        "out_of_order_history",
        "future_history",
        "partial_unavailable",
        "bad_balance",
        "bad_pressure",
        "bad_level",
        "invalid_owner",
        "invalid_enum",
        "invalid_number",
    ),
)
def test_schema_seven_rejects_malformed_need_records(tmp_path: Path, case: str) -> None:
    database = tmp_path / f"invalid-{case}.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    engine.definitions.register(Definition("settlement"))
    owner = engine.entities.create(
        definition_key="settlement",
        name="Oakford",
        attributes={"population": 4, "resources": {"food": 3}},
    )
    engine.needs.create(
        NeedDefinition("need_food", owner.id, NeedKind.FOOD, 1, 0.2, 0.5, 2)
    )
    engine.step()
    engine.save_world()
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        definition = payload["need_definitions"][0]
        state = payload["need_states"][0]
        current = state["current"]
        if case == "duplicate_definition":
            payload["need_definitions"].append(dict(definition))
        elif case == "duplicate_state":
            payload["need_states"].append(dict(state))
        elif case == "state_id_mismatch":
            state["need_id"] = "need_other"
        elif case == "unexpected_field":
            definition["extra"] = "not allowed"
        elif case == "overlong_history":
            definition["assessment_window_ticks"] = 1
            earlier = dict(current)
            earlier["tick"] = 0
            current["tick"] = 1
            state["history"] = [earlier, dict(current)]
            payload["tick"] = 1
        elif case == "out_of_order_history":
            later = dict(current)
            later["tick"] = 1
            state["history"] = [later, dict(current)]
            payload["tick"] = 1
        elif case == "future_history":
            current["tick"] = 2
            state["history"] = [dict(current)]
        elif case == "partial_unavailable":
            current["level"] = "unavailable"
        elif case == "bad_balance":
            current["balance"] = 99
            state["history"] = [dict(current)]
        elif case == "bad_pressure":
            current["pressure"] = 0.4
            state["history"] = [dict(current)]
        elif case == "bad_level":
            current["level"] = "secure"
            state["history"] = [dict(current)]
        elif case == "invalid_owner":
            definition["owner_id"] = "entity_missing"
        elif case == "invalid_enum":
            definition["kind"] = "warmth"
        elif case == "invalid_number":
            definition["requirement_per_person"] = True
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(payload),),
        )
    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


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


def test_schema_v6_load_rejects_duplicate_goal_labels_for_one_owner(
    tmp_path: Path,
) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    state = _world_state()
    for suffix, label in (("a", "Found Home"), ("b", " found home ")):
        objective_id = f"objective_{suffix}"
        goal_id = f"goal_{suffix}"
        state.objective_definitions[objective_id] = ObjectiveDefinition(
            objective_id,
            f"Objective {suffix.upper()}",
            "Operator purpose",
            "Prepare a safe home.",
            (ResourceMinimumCriterion("wood", 1),),
            authorized_action_categories=("work",),
        )
        state.objective_states[objective_id] = ObjectiveState(objective_id)
        state.goal_definitions[goal_id] = GoalDefinition(
            goal_id,
            GoalOwnerKind.SETTLEMENT,
            "entity-1",
            label,
            "Operator purpose",
            "Help establish a home.",
            (objective_id,),
            authorized_action_categories=("work",),
        )
        state.goal_states[goal_id] = GoalState(goal_id)
    repository.save_world(state)

    with pytest.raises(RepositoryLoadError, match="malformed") as error:
        repository.load_world()
    assert error.value.__cause__ is not None
    assert "unique per owner" in str(error.value.__cause__)


def test_unsupported_schema_version_raises_without_returning_partial_state(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database_path))
    repository.save_world(_world_state())
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE world_snapshots SET schema_version = ? WHERE id = 1", (9,)
        )

    with pytest.raises(RepositoryLoadError, match="Unsupported world schema version"):
        repository.load_world()


def _consequence_engine(repository: SQLiteRepository) -> SimulationEngine:
    engine = SimulationEngine(repository)
    engine.definitions.register(Definition("thing"))
    owner = engine.entities.create(
        definition_key="thing",
        name="Town",
        attributes={
            "population": 1,
            "resources": {"food": 4, "water": 4, "wood": 2},
            "storage_capacity": 5,
        },
    )
    capability = engine.entities.create(
        definition_key="thing", name="Well", attributes={"is_constructed": True}
    )
    engine.relationships.create(
        kind="owns", source_id=owner.id, target_id=capability.id
    )
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner.id, 1, 1)
    )
    engine.consequences.create_storage(
        StoragePolicy("storage_town", owner.id, (StorageResourceRule("food", 1),))
    )
    engine.consequences.create_maintenance(
        MaintenancePolicy(
            "maintenance_well",
            owner.id,
            capability.id,
            "Well",
            (MaintenanceRequirement("wood", 1),),
            2,
            3,
            1,
            1,
        )
    )
    engine.needs.create(
        NeedDefinition("need_food", owner.id, NeedKind.FOOD, 1, 0.2, 0.5, 3)
    )
    objective = ObjectiveDefinition(
        "objective_food",
        "Food pressure",
        "Food pressure",
        "Observe pressure.",
        (SustainedNeedCriterion("food", 1.0, 2),),
        authorized_action_categories=("supply",),
    )
    goal = GoalDefinition(
        "goal_food",
        GoalOwnerKind.SETTLEMENT,
        owner.id,
        "Food security",
        "Food security",
        "Keep food supplied.",
        (objective.id,),
        authorized_action_categories=("supply",),
    )
    engine.goals.create(goal, (objective,))
    engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)
    engine.goals.transition_objective(objective.id, GoalStatus.ACTIVE)
    return engine


def test_schema_eight_round_trips_all_six_consequence_collections(
    tmp_path: Path,
) -> None:
    repository = SQLiteRepository(str(tmp_path / "consequences.sqlite3"))
    engine = _consequence_engine(repository)
    engine.step()
    engine.save_world()
    loaded = repository.load_world()
    for name in (
        "consumption_policies",
        "consumption_states",
        "storage_policies",
        "storage_states",
        "maintenance_policies",
        "maintenance_states",
    ):
        assert getattr(loaded, name) == getattr(engine.state, name)


@pytest.mark.parametrize("schema_version", range(1, 8))
def test_versions_one_through_seven_ignore_stray_consequences_and_write_forward(
    tmp_path: Path, schema_version: int
) -> None:
    database = tmp_path / f"legacy-consequences-{schema_version}.sqlite3"
    repository = SQLiteRepository(str(database))
    repository.save_world(_world_state())
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        payload["consumption_policies"] = [{"id": "consumption_stray"}]
        connection.execute(
            "UPDATE world_snapshots SET schema_version = ?, payload = ? WHERE id = 1",
            (schema_version, json.dumps(payload)),
        )
    loaded = repository.load_world()
    assert loaded.consumption_policies == {}
    repository.save_world(loaded)
    with sqlite3.connect(database) as connection:
        assert (
            connection.execute(
                "SELECT schema_version FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
            == 8
        )


@pytest.mark.parametrize(
    ("collection", "nested", "required_key", "extra"),
    [
        (collection, None, required, extra)
        for collection, required in (
            ("consumption_policies", "owner_id"),
            ("consumption_states", "food_shortage"),
            ("storage_policies", "owner_id"),
            ("storage_states", "overflowing"),
            ("maintenance_policies", "label"),
            ("maintenance_states", "condition"),
        )
        for extra in (False, True)
    ]
    + [
        (collection, nested, required, extra)
        for collection, nested, required in (
            ("storage_policies", "resources", "spoilage_per_tick"),
            ("maintenance_policies", "upkeep", "amount"),
        )
        for extra in (False, True)
    ],
)
def test_schema_eight_rejects_missing_and_additional_nested_keys(
    tmp_path: Path,
    collection: str,
    nested: str | None,
    required_key: str,
    extra: bool,
) -> None:
    database = tmp_path / f"malformed-{collection}.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = _consequence_engine(repository)
    engine.save_world()
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        record = payload[collection][0]
        target = record if nested is None else record[nested][0]
        if extra:
            target["extra"] = 1
        else:
            target.pop(required_key)
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(payload),),
        )
    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


@pytest.mark.parametrize("case", ("owner", "unprocessed", "terminal", "partial"))
def test_schema_eight_rejects_malformed_consequence_invariants(
    tmp_path: Path, case: str
) -> None:
    database = tmp_path / f"bad-invariant-{case}.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = _consequence_engine(repository)
    engine.save_world()
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        if case == "owner":
            payload["consumption_policies"][0]["owner_id"] = "missing"
        elif case == "unprocessed":
            payload["consumption_states"][0]["food_shortage"] = True
        elif case == "terminal":
            payload["maintenance_states"][0]["condition"] = 0
        else:
            payload["consumption_states"][0]["last_processed_tick"] = payload["tick"]
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(payload),),
        )
    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


@pytest.mark.parametrize(
    ("destroyed_tick", "last_processed_tick", "world_tick"),
    ((-1, 1, 2), (True, 1, 2), (3, 3, 2), (2, 1, 3)),
)
def test_schema_eight_rejects_invalid_terminal_destruction_ticks(
    tmp_path: Path,
    destroyed_tick: object,
    last_processed_tick: int,
    world_tick: int,
) -> None:
    database = tmp_path / f"bad-terminal-{destroyed_tick}-{last_processed_tick}.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = _consequence_engine(repository)
    engine.save_world()
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        payload["tick"] = world_tick
        payload["entities"][1]["destroyed_tick"] = destroyed_tick
        payload["maintenance_states"][0].update(
            {
                "condition": 0,
                "last_processed_tick": last_processed_tick,
                "upkeep_shortage": True,
            }
        )
        connection.execute(
            "UPDATE world_snapshots SET payload = ? WHERE id = 1",
            (json.dumps(payload),),
        )
    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


def test_uninterrupted_and_save_resume_consequence_results_match(
    tmp_path: Path,
) -> None:
    left_repo = SQLiteRepository(str(tmp_path / "left.sqlite3"))
    right_repo = SQLiteRepository(str(tmp_path / "right.sqlite3"))
    left = _consequence_engine(left_repo)
    right = _consequence_engine(right_repo)
    left.step()
    right.step()
    right.save_world()
    resumed = SimulationEngine(right_repo)
    resumed.definitions.register(Definition("thing"))
    left.step()
    resumed.step()
    assert left.state.tick == resumed.state.tick
    assert [e.attributes for e in left.state.entities.values()] == [
        e.attributes for e in resumed.state.entities.values()
    ]
    assert left.state.consumption_states == resumed.state.consumption_states
    assert left.state.storage_states == resumed.state.storage_states
    assert left.state.maintenance_states == resumed.state.maintenance_states
    assert left.state.need_states == resumed.state.need_states
    assert left.state.goal_states == resumed.state.goal_states
    assert left.state.objective_states == resumed.state.objective_states
    assert [
        (e.tick, e.kind, e.subject_id, e.attributes) for e in left.state.events.values()
    ] == [
        (e.tick, e.kind, e.subject_id, e.attributes)
        for e in resumed.state.events.values()
    ]


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
