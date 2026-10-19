from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest


def test_packaged_policy_is_exact_detached_and_portable() -> None:
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        materialize_founders_assets,
    )
    from living_world.scenarios.scenario import (
        ScenarioEntity,
        YAMLScenarioLoader,
        mutable_attributes,
    )

    with materialize_founders_assets() as assets:
        scenario = YAMLScenarioLoader().load(assets.scenario)
        policy = FoundersPolicy.from_scenario(scenario)
        assert policy.rules.deadline_tick == 12
        assert len(policy.fingerprint) == 64
        manifest = policy.to_manifest()
        manifest["version"] = True
        entities = list(scenario.entities)
        camp = entities[1]
        attrs = mutable_attributes(camp.attributes)
        attrs["founders_policy"] = manifest
        entities[1] = ScenarioEntity(camp.label, camp.definition_key, camp.name, attrs)
        with pytest.raises(FoundersConfigurationError, match="invalid_policy"):
            FoundersPolicy.from_scenario(replace(scenario, entities=tuple(entities)))
        assert policy.to_manifest()["version"] == 1
        path = assets.scenario
    assert not path.exists()


def test_setup_is_atomic_retryable_idempotent_and_rejects_partial(
    tmp_path: Path,
) -> None:
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import _serialize_world
    from living_world.simulation.simulation_engine import SimulationEngine

    with materialize_founders_assets() as assets:
        engine = SimulationEngine()
        scenario = engine.load_scenario(assets.scenario)
        policy = FoundersPolicy.from_scenario(scenario)
        manager = FoundersSetupManager(engine.state, engine.definitions)
        manager.initialize_or_validate(policy)
        before = _serialize_world(engine.state)
        manager.initialize_or_validate(policy)
        manager.validate_existing(policy)
        assert _serialize_world(engine.state) == before
        assert len(engine.state.need_definitions) == 4
        assert len(engine.state.objective_definitions) == 7
        assert not engine.state.work_definitions
        assert (
            len(
                [
                    event
                    for event in engine.state.events.values()
                    if event.kind == "canonical_setup_completed"
                ]
            )
            == 1
        )
        del engine.state.need_states["need_founders_food"]
        with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
            manager.initialize_or_validate(policy)


@pytest.mark.parametrize(
    ("outcome", "tick", "terminal"),
    [
        ("success", 10, "settlement_success"),
        ("stall", 5, None),
        ("failure", 13, "founding_failure"),
    ],
)
def test_canonical_outcomes_use_real_gateway(
    tmp_path: Path, outcome: str, tick: int, terminal: str | None
) -> None:
    from living_world.founders import (
        FoundersOutcome,
        FoundersPreparation,
        founders_terminal_conditions,
        materialize_founders_assets,
    )
    from living_world.replay.loader import YAMLProposalTapeLoader
    from living_world.repositories.sqlite_repository import SQLiteRepository
    from living_world.running import RunConfiguration, ScenarioRunner
    from living_world.simulation.simulation_engine import SimulationEngine

    with materialize_founders_assets() as assets:
        engine = SimulationEngine(SQLiteRepository(str(tmp_path / "world.sqlite3")))
        tape = YAMLProposalTapeLoader().load(assets.tape_for(FoundersOutcome(outcome)))
        result = ScenarioRunner(
            engine,
            FoundersPreparation(tape),
            terminal_conditions=founders_terminal_conditions(),
        ).run(
            assets.scenario, RunConfiguration(max_ticks=5 if outcome == "stall" else 16)
        )
        assert (result.end_tick, result.terminal_condition) == (tick, terminal)
        assert engine.state.replay_state.next_index == tick
        receipts = [
            event
            for event in engine.state.events.values()
            if event.kind == "replay_proposal_resolved"
        ]
        assert [event.attributes["sequence"] for event in receipts] == list(
            range(1, tick + 1)
        )
        charged = [
            event.subject_id
            for event in engine.state.events.values()
            if event.kind == "work_inputs_charged"
        ]
        assert len(charged) == len(set(charged))
        if outcome == "success":
            camp = engine.entities.get(engine.state.scenario_entity_bindings["camp"])
            assert camp is not None
            assert camp.attributes["resources"]["timber"] == 6
            assert len(charged) == 5
        assert (
            len(
                [
                    e
                    for e in engine.state.events.values()
                    if e.kind == "replay_proposal_resolved"
                ]
            )
            == tick
        )


def test_setup_late_failure_leaves_bound_graph_and_retry_matches_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from living_world.core.event import Event
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.managers.event_manager import EventManager
    from living_world.repositories.sqlite_repository import _serialize_world
    from living_world.simulation.simulation_engine import SimulationEngine

    with materialize_founders_assets() as assets:
        engine = SimulationEngine()
        scenario = engine.load_scenario(assets.scenario)
        policy = FoundersPolicy.from_scenario(scenario)
        manager = FoundersSetupManager(engine.state, engine.definitions)
        before = _serialize_world(engine.state)
        record = EventManager.record

        def fail_marker(
            self: EventManager,
            *,
            kind: str,
            subject_id: str | None = None,
            attributes: dict[str, object] | None = None,
        ) -> Event:
            if kind == "canonical_setup_completed":
                raise ValueError("injected late failure")
            return record(self, kind=kind, subject_id=subject_id, attributes=attributes)

        monkeypatch.setattr(EventManager, "record", fail_marker)
        with pytest.raises(FoundersConfigurationError):
            manager.initialize_or_validate(policy)
        assert _serialize_world(engine.state) == before
        monkeypatch.setattr(EventManager, "record", record)
        manager.initialize_or_validate(policy)
        clean = SimulationEngine()
        clean.load_scenario(assets.scenario)
        FoundersSetupManager(clean.state, clean.definitions).initialize_or_validate(
            policy
        )
        assert _serialize_world(engine.state) == _serialize_world(clean.state)
        assert (
            engine.entities.create(definition_key="founder", name="Visitor").id
            == "entity_000005"
        )
        existing_events = set(engine.state.events)
        event = engine.events.record(kind="visitor_arrived", subject_id="entity_000005")
        assert event.id not in existing_events
        assert len(engine.state.events) == len(existing_events) + 1
        existing_references = set(engine.state.external_world_references)
        reference = engine.external_world_references.create(
            name="Visitor",
            role="visitor",
            capacity=1,
            delay_ticks=0,
            cost_per_unit=0,
            reliability=1.0,
        )
        assert reference.id not in existing_references
        assert len(engine.state.external_world_references) == 2


def test_read_only_inspection_rejects_missing_setup_without_repair(
    tmp_path: Path,
) -> None:
    from living_world.founders import (
        FoundersConfigurationError,
        load_inspection_engine,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import SQLiteRepository
    from living_world.simulation.simulation_engine import SimulationEngine

    with materialize_founders_assets() as assets:
        database = tmp_path / "graph.sqlite3"
        engine = SimulationEngine(SQLiteRepository(str(database)))
        engine.load_scenario(assets.scenario)
        engine.save_world()
        before = database.read_bytes()
        with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
            load_inspection_engine(assets.scenario, database)
        assert database.read_bytes() == before


def test_setup_rejects_changed_initial_resources_and_policy(tmp_path: Path) -> None:
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.simulation.simulation_engine import SimulationEngine

    with materialize_founders_assets() as assets:
        engine = SimulationEngine()
        scenario = engine.load_scenario(assets.scenario)
        policy = FoundersPolicy.from_scenario(scenario)
        camp = engine.state.entities[engine.state.scenario_entity_bindings["camp"]]
        camp.attributes["resources"]["food"] = 1
        with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
            FoundersSetupManager(
                engine.state, engine.definitions
            ).initialize_or_validate(policy)
        assert not engine.state.need_definitions


@pytest.mark.parametrize("outcome", ["success", "stall", "failure"])
def test_fresh_and_checkpoint_resume_payloads_are_exact(
    tmp_path: Path, outcome: str
) -> None:
    import sqlite3

    from living_world.cli import main

    def run(path: Path, *extra: str) -> None:
        assert (
            main(["run", "--founders", outcome, "--database", str(path), *extra]) == 0
        )

    def row(path: Path) -> tuple[int, str]:
        with sqlite3.connect(path) as db:
            return db.execute(
                "SELECT schema_version,payload FROM world_snapshots WHERE id=1"
            ).fetchone()

    first = tmp_path / "first.sqlite3"
    second = tmp_path / "second.sqlite3"
    run(first)
    run(second)
    expected = row(first)
    assert row(second) == expected
    for k in (1, 3, 4):
        path = tmp_path / f"checkpoint{k}.sqlite3"
        run(path, "--max-ticks", str(k), "--checkpoint-only")
        remaining = (5 - k) if outcome == "stall" else 16
        run(path, "--max-ticks", str(remaining))
        assert row(path) == expected
        if outcome != "stall":
            run(path, "--max-ticks", "0")
            assert row(path) == expected


@pytest.mark.parametrize("outcome", ["success", "stall", "failure"])
def test_every_decision_receives_filtered_context_and_provider_is_pure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    from living_world.api.inspection import EngineWorldInspector
    from living_world.cognition.npc_cognition_client import ActionOption, NPCDecision
    from living_world.cognition.npc_context import NPCContext
    from living_world.founders import (
        FoundersOutcome,
        FoundersPolicy,
        FoundersPreparation,
        founders_terminal_conditions,
        materialize_founders_assets,
    )
    from living_world.founders.runtime import FoundersOfferProvider
    from living_world.replay.client import RecordedProposalClient
    from living_world.replay.loader import YAMLProposalTapeLoader
    from living_world.repositories.sqlite_repository import (
        SQLiteRepository,
        _serialize_world,
    )
    from living_world.running import RunConfiguration, ScenarioRunner
    from living_world.simulation.simulation_engine import SimulationEngine

    observations: list[tuple[str, tuple[str, ...]]] = []
    decide = RecordedProposalClient.decide

    def audit(
        self: RecordedProposalClient,
        context: NPCContext,
        options: tuple[ActionOption, ...],
    ) -> NPCDecision:
        assert isinstance(context, NPCContext)
        rendered = repr((context, options))
        for hidden in (
            "entity_",
            "objective_",
            "goal_",
            "need_",
            "founders_policy",
            "required_progress",
            "deadline_tick",
            "labor_required",
            "timber",
        ):
            assert hidden not in rendered
        assert not any(character.isdigit() for character in rendered)
        observations.append((context.identity, tuple(option.key for option in options)))
        return decide(self, context, options)

    monkeypatch.setattr(RecordedProposalClient, "decide", audit)
    with materialize_founders_assets() as assets:
        engine = SimulationEngine(SQLiteRepository(str(tmp_path / "audit.sqlite3")))
        scenario = engine.load_scenario(assets.scenario)
        policy = FoundersPolicy.from_scenario(scenario)
        preparation = FoundersPreparation(
            YAMLProposalTapeLoader().load(assets.tape_for(FoundersOutcome(outcome)))
        )
        preparation.prepare(engine, scenario)
        provider = FoundersOfferProvider(engine, policy)
        before = _serialize_world(engine.state)
        bundle = provider.offers(
            actor_id=engine.state.scenario_entity_bindings["ada"],
            inspector=EngineWorldInspector(engine),
        )
        assert _serialize_world(engine.state) == before
        assert bundle.options == ()
        ScenarioRunner(
            engine, preparation, terminal_conditions=founders_terminal_conditions()
        ).run(
            assets.scenario, RunConfiguration(max_ticks=5 if outcome == "stall" else 16)
        )
        assert [name for name, _ in observations] == [
            "Ada" if i % 2 == 0 else "Bryn" for i in range(engine.state.tick)
        ]


def test_capabilities_attach_only_after_construction_and_keep_dynamic_state(
    tmp_path: Path,
) -> None:
    from living_world.cli import main
    from living_world.founders import (
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import (
        SQLiteRepository,
        _serialize_world,
    )
    from living_world.simulation.simulation_engine import SimulationEngine

    database = tmp_path / "composition.sqlite3"
    assert (
        main(
            [
                "run",
                "--founders",
                "success",
                "--database",
                str(database),
                "--max-ticks",
                "4",
                "--checkpoint-only",
            ]
        )
        == 0
    )
    state = SQLiteRepository(str(database), read_only=True).load_world()
    assert len(state.entities) == 5
    assert not state.maintenance_policies and not state.storage_policies
    assert (
        main(
            [
                "run",
                "--founders",
                "success",
                "--database",
                str(database),
                "--max-ticks",
                "1",
                "--checkpoint-only",
            ]
        )
        == 0
    )
    state = SQLiteRepository(str(database), read_only=True).load_world()
    assert len(state.maintenance_policies) == 1 and not state.storage_policies
    assert (
        next(
            e for e in state.events.values() if e.kind == "founders_shelter_composed"
        ).tick
        == 4
    )
    assert (
        main(
            [
                "run",
                "--founders",
                "success",
                "--database",
                str(database),
                "--max-ticks",
                "1",
                "--checkpoint-only",
            ]
        )
        == 0
    )
    engine = SimulationEngine(SQLiteRepository(str(database)))
    with materialize_founders_assets() as assets:
        scenario = engine.load_scenario(assets.scenario)
        policy = FoundersPolicy.from_scenario(scenario)
        manager = FoundersSetupManager(engine.state, engine.definitions)
        before = _serialize_world(engine.state)
        manager.compose(policy)
        assert _serialize_world(engine.state) == before
    assert (
        next(
            e
            for e in engine.state.events.values()
            if e.kind == "founders_storage_composed"
        ).tick
        == 5
    )
    camp = engine.state.entities[engine.state.scenario_entity_bindings["camp"]]
    assert camp.attributes["resources"] == {"food": 10, "water": 8, "timber": 6}
    assert next(iter(engine.state.maintenance_states.values())).condition == 3
    shelter = next(
        e for e in engine.state.entities.values() if e.definition_key == "shelter"
    )
    assert shelter.attributes["housing_allocated"] == 2
    assert engine.state.need_states["need_founders_shelter"].current.tick == 5


@pytest.mark.parametrize(
    "damage",
    [
        "missing_marker",
        "duplicate_marker",
        "marker_policy",
        "marker_tick",
        "extra_need",
        "changed_objective",
        "changed_reference",
        "missing_housing",
        "duplicate_housing",
        "missing_maintenance",
        "missing_maintenance_state",
        "missing_shelter_marker",
        "missing_storage",
        "missing_storage_state",
        "missing_storage_marker",
        "storage_marker_subject",
    ],
)
def test_resume_rejects_contradictory_setup_without_repair(
    tmp_path: Path, damage: str
) -> None:
    from living_world.cli import main
    from living_world.core.event import Event
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import (
        SQLiteRepository,
        _serialize_world,
    )
    from living_world.simulation.simulation_engine import SimulationEngine

    database = tmp_path / "complete.sqlite3"
    assert main(["run", "--founders", "success", "--database", str(database)]) == 0
    with materialize_founders_assets() as assets:
        engine = SimulationEngine(SQLiteRepository(str(database)))
        policy = FoundersPolicy.from_scenario(engine.load_scenario(assets.scenario))
        state = engine.state
        marker = next(
            e for e in state.events.values() if e.kind == "canonical_setup_completed"
        )
        if damage == "missing_marker":
            del state.events[marker.id]
        elif damage == "duplicate_marker":
            state.events["event_duplicate"] = replace(marker, id="event_duplicate")
        elif damage == "marker_policy":
            state.events[marker.id] = replace(
                marker, attributes={**marker.attributes, "policy_version": 2}
            )
        elif damage == "marker_tick":
            state.events[marker.id] = replace(marker, tick=1)
        elif damage == "extra_need":
            original = state.need_definitions["need_founders_food"]
            state.need_definitions["need_other"] = replace(original, id="need_other")
        elif damage == "changed_objective":
            original = state.objective_definitions["objective_founders_population"]
            state.objective_definitions[original.id] = replace(
                original, authorized_action_categories=("grow",)
            )
        elif damage == "changed_reference":
            original = next(iter(state.external_world_references.values()))
            state.external_world_references[original.id] = replace(original, capacity=2)
        elif damage in ("missing_housing", "duplicate_housing"):
            edge = next(
                r for r in state.relationships.values() if r.kind == "housed_in"
            )
            if damage == "missing_housing":
                del state.relationships[edge.id]
            else:
                state.relationships["relationship_duplicate"] = replace(
                    edge, id="relationship_duplicate"
                )
        elif damage == "missing_maintenance":
            state.maintenance_policies.clear()
        elif damage == "missing_maintenance_state":
            state.maintenance_states.clear()
        elif damage == "missing_storage":
            state.storage_policies.clear()
        elif damage == "missing_storage_state":
            state.storage_states.clear()
        else:
            kind = (
                "founders_shelter_composed"
                if damage == "missing_shelter_marker"
                else "founders_storage_composed"
            )
            event = next(e for e in state.events.values() if e.kind == kind)
            if damage == "storage_marker_subject":
                state.events[event.id] = Event(
                    event.id,
                    event.tick,
                    event.kind,
                    state.scenario_entity_bindings["camp"],
                    event.attributes,
                )
            else:
                del state.events[event.id]
        before = _serialize_world(state)
        manager = FoundersSetupManager(state, engine.definitions)
        for operation in (
            manager.validate_existing,
            manager.initialize_or_validate,
            manager.compose,
        ):
            with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
                operation(policy)
            assert _serialize_world(state) == before


def test_accepted_success_can_continue_with_stable_provisions_without_proposals(
    tmp_path: Path,
) -> None:
    from living_world.cli import main
    from living_world.founders import FoundersPreparation, materialize_founders_assets
    from living_world.replay.loader import YAMLProposalTapeLoader
    from living_world.repositories.sqlite_repository import SQLiteRepository
    from living_world.simulation.simulation_engine import SimulationEngine

    accepted = tmp_path / "accepted.sqlite3"
    assert main(["run", "--founders", "success", "--database", str(accepted)]) == 0
    before = accepted.read_bytes()
    continued = tmp_path / "continued.sqlite3"
    continued.write_bytes(before)
    with materialize_founders_assets() as assets:
        engine = SimulationEngine(SQLiteRepository(str(continued)))
        scenario = engine.load_scenario(assets.scenario)
        FoundersPreparation(YAMLProposalTapeLoader().load(assets.success)).prepare(
            engine, scenario
        )
        for _ in range(3):
            engine.step()  # Bypass terminal runner only on the separate evidence copy.
            assert all(
                n.current is not None and n.current.pressure == 0.0
                for n in engine.state.need_states.values()
            )
            camp = engine.entities.get(engine.state.scenario_entity_bindings["camp"])
            assert camp is not None
            assert camp.attributes["resources"] == {"food": 10, "water": 8, "timber": 6}
        assert engine.replay.current().next_index == 10
        engine.save_world()
    assert accepted.read_bytes() == before


def test_absent_shelter_attachment_is_pending_only_through_next_boundary(
    tmp_path: Path,
) -> None:
    from living_world.cli import main
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import (
        SQLiteRepository,
        _serialize_world,
    )
    from living_world.simulation.simulation_engine import SimulationEngine

    database = tmp_path / "pending.sqlite3"
    assert (
        main(
            [
                "run",
                "--founders",
                "success",
                "--database",
                str(database),
                "--max-ticks",
                "4",
                "--checkpoint-only",
            ]
        )
        == 0
    )
    with materialize_founders_assets() as assets:
        engine = SimulationEngine(SQLiteRepository(str(database)))
        policy = FoundersPolicy.from_scenario(engine.load_scenario(assets.scenario))
        manager = FoundersSetupManager(engine.state, engine.definitions)
        manager.validate_existing(policy)
        engine.state.tick = (
            5  # Missed ordinary attachment phase after construction at 3.
        )
        before = _serialize_world(engine.state)
        with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
            manager.compose(policy)
        assert _serialize_world(engine.state) == before


@pytest.mark.parametrize("ownership", ["ended", "future", "ended_attached"])
def test_review_attachments_require_current_live_ownership(
    tmp_path: Path,
    ownership: str,
) -> None:
    from living_world.cli import main
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import (
        SQLiteRepository,
        _serialize_world,
    )
    from living_world.simulation.simulation_engine import SimulationEngine

    path = tmp_path / "ownership.sqlite3"
    extra = (
        []
        if ownership == "ended_attached"
        else ["--max-ticks", "5", "--checkpoint-only"]
    )
    assert main(["run", "--founders", "success", "--database", str(path), *extra]) == 0
    with materialize_founders_assets() as assets:
        engine = SimulationEngine(SQLiteRepository(str(path)))
        policy = FoundersPolicy.from_scenario(engine.load_scenario(assets.scenario))
        storage = next(
            e for e in engine.state.entities.values() if e.definition_key == "storage"
        )
        edge = next(
            r
            for r in engine.state.relationships.values()
            if r.kind == "owns" and r.target_id == storage.id
        )
        if ownership == "future":
            edge.created_tick = engine.state.tick + 1
        else:
            edge.destroyed_tick = engine.state.tick - 1
        before = _serialize_world(engine.state)
        manager = FoundersSetupManager(engine.state, engine.definitions)
        if ownership == "ended_attached":
            with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
                manager.compose(policy)
        else:
            manager.compose(policy)
            assert not engine.state.storage_policies
        assert _serialize_world(engine.state) == before


@pytest.mark.parametrize("setup_present", [False, True])
def test_review_bound_founder_identity_rejects_without_mutation_and_retries(
    setup_present: bool,
) -> None:
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import _serialize_world
    from living_world.simulation.simulation_engine import SimulationEngine

    with materialize_founders_assets() as assets:
        engine = SimulationEngine()
        policy = FoundersPolicy.from_scenario(engine.load_scenario(assets.scenario))
        manager = FoundersSetupManager(engine.state, engine.definitions)
        if setup_present:
            manager.initialize_or_validate(policy)
        ada = engine.state.entities[engine.state.scenario_entity_bindings["ada"]]
        identity = ada.attributes.pop("npc_identity")
        before = _serialize_world(engine.state)
        with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
            manager.initialize_or_validate(policy)
        assert _serialize_world(engine.state) == before
        ada.attributes["npc_identity"] = identity
        manager.initialize_or_validate(policy)
        manager.validate_existing(policy)


@pytest.mark.parametrize("version", [True, 1.0])
def test_review_setup_marker_version_requires_exact_integer(version: object) -> None:
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import _serialize_world
    from living_world.simulation.simulation_engine import SimulationEngine

    with materialize_founders_assets() as assets:
        engine = SimulationEngine()
        policy = FoundersPolicy.from_scenario(engine.load_scenario(assets.scenario))
        manager = FoundersSetupManager(engine.state, engine.definitions)
        manager.initialize_or_validate(policy)
        marker = next(
            e
            for e in engine.state.events.values()
            if e.kind == "canonical_setup_completed"
        )
        engine.state.events[marker.id] = replace(
            marker, attributes={**marker.attributes, "policy_version": version}
        )
        before = _serialize_world(engine.state)
        with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
            manager.validate_existing(policy)
        assert _serialize_world(engine.state) == before


@pytest.mark.parametrize(
    "kind", ["founders_shelter_composed", "founders_storage_composed"]
)
@pytest.mark.parametrize("tick", [0, 3, 6, 11])
def test_review_composition_marker_requires_exact_bounded_phase_tick(
    tmp_path: Path,
    kind: str,
    tick: int,
) -> None:
    from living_world.cli import main
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        FoundersSetupManager,
        materialize_founders_assets,
    )
    from living_world.repositories.sqlite_repository import (
        SQLiteRepository,
        _serialize_world,
    )
    from living_world.simulation.simulation_engine import SimulationEngine

    path = tmp_path / "chronology.sqlite3"
    assert main(["run", "--founders", "success", "--database", str(path)]) == 0
    with materialize_founders_assets() as assets:
        engine = SimulationEngine(SQLiteRepository(str(path)))
        policy = FoundersPolicy.from_scenario(engine.load_scenario(assets.scenario))
        marker = next(e for e in engine.state.events.values() if e.kind == kind)
        engine.state.events[marker.id] = replace(marker, tick=tick)
        before = _serialize_world(engine.state)
        with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
            FoundersSetupManager(engine.state, engine.definitions).validate_existing(
                policy
            )
        assert _serialize_world(engine.state) == before


@pytest.mark.parametrize("operation", ["to_manifest", "fingerprint"])
@pytest.mark.parametrize("invalid", ["surrogate", "nonfinite", "unserializable"])
def test_review_direct_policy_serialization_has_fixed_safe_error(
    operation: str,
    invalid: str,
) -> None:
    from living_world.founders import (
        FoundersConfigurationError,
        FoundersPolicy,
        materialize_founders_assets,
    )
    from living_world.scenarios.scenario import YAMLScenarioLoader

    with materialize_founders_assets() as assets:
        policy = FoundersPolicy.from_scenario(
            YAMLScenarioLoader().load(assets.scenario)
        )
    if invalid == "surrogate":
        policy = replace(policy, area_label="private\ud800payload")
    elif invalid == "nonfinite":
        policy = replace(
            policy, rules=replace(policy.rules, homeland_reliability=float("nan"))
        )
    else:
        policy = replace(policy, version=object())
    with pytest.raises(FoundersConfigurationError) as caught:
        if operation == "to_manifest":
            policy.to_manifest()
        else:
            _ = policy.fingerprint
    assert str(caught.value) == "invalid_policy: Invalid founders policy."
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
