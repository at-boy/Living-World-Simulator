"""Tape-free founders and holder-safe runtime feedback contracts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from living_world.archives import JournalEntry
    from living_world.cognition.npc_cognition_client import ActionOption
    from living_world.cognition.npc_context import NPCContext
    from living_world.runtime.feedback import FoundersFeedback
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.simulation.simulation_engine import SimulationEngine
    from living_world.state.world_state import WorldState
    from living_world.work.model import WorkDefinition

from living_world.archives import AttemptConfig, Checkpoint, RunCatalog, retain_inputs
from living_world.founders.assets import materialize_founders_assets
from living_world.repositories.world_snapshot import decode_world, encode_world


def composition(tmp_path: Path) -> FoundersLiveComposition:
    from living_world.runtime.founders import FoundersLiveComposition

    catalog = RunCatalog(tmp_path)
    with materialize_founders_assets() as assets:
        from living_world.scenarios.scenario import YAMLScenarioLoader

        scenario = YAMLScenarioLoader().load(assets.scenario)
        ref = catalog.reserve(
            AttemptConfig("ollama", scenario.key, scenario.seed, "test", {})
        )
        inputs = retain_inputs(ref, assets.scenario, tape_path=None)
    return FoundersLiveComposition(inputs)


def test_tape_free_world_and_byte_exact_restore(tmp_path: Path) -> None:
    live = composition(tmp_path)
    engine = live.initialize()
    before = encode_world(engine.state)
    assert engine.state.replay_binding is None
    assert engine.state.replay_state is None
    assert encode_world(live.restore(before).state) == before
    live.finalize(engine, stopped=True)
    assert encode_world(engine.state) == before


def test_initial_feedback_is_holder_scoped_and_reconstruction_is_exact(
    tmp_path: Path,
) -> None:
    from living_world.cognition.local_llm_cognition_format import (
        serialize_decision_request,
    )
    from living_world.runtime.feedback import FoundersFeedback

    live = composition(tmp_path)
    engine = live.initialize()
    feedback = FoundersFeedback(
        lambda context, options: len(serialize_decision_request(context, options))
    )
    cursor = feedback.initialize(engine)
    base = Checkpoint(0, encode_world(engine.state), {}, cursor)
    first = feedback.prepare(live.restore(base.snapshot), base)
    second = FoundersFeedback(feedback._request_size).prepare(
        live.restore(base.snapshot), base
    )
    assert tuple(item.actor_label for item in first) == ("ada", "bryn")
    assert tuple(item.input_fingerprint for item in first) == tuple(
        item.input_fingerprint for item in second
    )
    for item in first:
        assert item.context.core_cognition[0].text.startswith(
            "You were asked to help the camp: "
        )
        assert (
            len(item.context.core_cognition) + len(item.context.retrieved_information)
            <= 8
        )
        assert len(item.context.current_perceptions) <= 8
        payload = serialize_decision_request(item.context, item.options)
        assert item.actor_id not in payload
        assert "goal_founding" not in payload
        memories = engine.memories.memories_for(item.actor_id)
        assert memories and all(memory.source_observation_ids for memory in memories)
        assert all(memory.holder_id == item.actor_id for memory in memories)


import pytest


@pytest.mark.parametrize("change", ["relocate", "unplace", "destroy"])
def test_live_dynamic_founder_restore_step_and_offers(
    tmp_path: Path, change: str
) -> None:
    from living_world.founders import FoundersConfigurationError, FoundersSetupManager
    from living_world.founders.model import canonical_policy
    from living_world.runtime.feedback import FoundersFeedback
    from living_world.spatial.model import Point

    live = composition(tmp_path)
    engine = live.initialize()
    ada = engine.state.scenario_entity_bindings["ada"]
    valley = engine.state.scenario_entity_bindings["valley"]
    if change == "relocate":
        engine.spatial.replace(
            entity_id=ada, geometry=Point(20, 20), containing_entity_id=valley
        )
    elif change == "unplace":
        engine.spatial.unplace(ada)
    elif change == "destroy":
        engine.entities.mark_destroyed(ada, engine.state.tick)
    else:
        engine.entities.set_attribute(entity_id=ada, key="npc_identity", value={})
    with pytest.raises(FoundersConfigurationError):
        FoundersSetupManager(engine.state, engine.definitions).validate_existing(
            canonical_policy()
        )
    saved = encode_world(engine.state)
    candidate = live.restore(saved)
    assert encode_world(candidate.state) == saved
    live.finalize(candidate, stopped=True)
    live.finalize(candidate, stopped=False)
    assert encode_world(candidate.state) == saved
    feedback = FoundersFeedback(lambda _context, _options: 100)
    cursor = feedback.initialize(candidate)
    base = Checkpoint(0, encode_world(candidate.state), {}, cursor)
    decisions = feedback.prepare(candidate, base)
    assert tuple(item.actor_label for item in decisions) == ("bryn",)
    candidate.step()
    assert candidate.state.tick == 1


def ready(
    tmp_path: Path,
) -> tuple[FoundersLiveComposition, SimulationEngine, FoundersFeedback, Checkpoint]:
    from living_world.runtime.feedback import FoundersFeedback

    live = composition(tmp_path)
    engine = live.initialize()
    feedback = FoundersFeedback(lambda _context, _options: 100)
    cursor = feedback.initialize(engine)
    return live, engine, feedback, Checkpoint(0, encode_world(engine.state), {}, cursor)


def resolved(
    base: Checkpoint, label: str, outcome: str = "no_action", refs: tuple[str, ...] = ()
) -> JournalEntry:
    from living_world.archives import JournalEntry

    return JournalEntry(
        "action_resolved",
        {
            "base_revision": base.revision,
            "source_tick": decode_world(base.snapshot).tick,
            "actor_label": label,
            "request_id": "operational-request",
            "outcome": outcome,
            "event_references": refs,
        },
    )


@pytest.mark.parametrize(
    "outcome,prose",
    [
        ("accepted", "Your proposal was accepted."),
        ("rejected", "Your proposal could not be carried out."),
        ("no_action", "You chose not to propose an action."),
    ],
)
def test_actor_result_is_observed_on_next_decision(
    tmp_path: Path, outcome: str, prose: str
) -> None:
    live, engine, feedback, base = ready(tmp_path)
    decisions = feedback.prepare(engine, base)
    assert all(prose not in item.context.current_perceptions for item in decisions)
    engine.step()
    cursor = feedback.after_tick(
        engine, (resolved(base, "ada", outcome), resolved(base, "bryn"))
    )
    assert all(prose != item.description for item in engine.state.observations.values())
    next_base = Checkpoint(1, encode_world(engine.state), {}, cursor)
    candidate = live.restore(next_base.snapshot)
    first = feedback.prepare(candidate, next_base)
    assert prose in first[0].context.current_perceptions
    if outcome != "no_action":
        assert prose not in first[1].context.current_perceptions
    state = encode_world(candidate.state)
    again = feedback.prepare(candidate, next_base)
    assert encode_world(candidate.state) == state
    assert tuple((item.context, item.input_fingerprint) for item in first) == tuple(
        (item.context, item.input_fingerprint) for item in again
    )
    fresh_candidate = live.restore(next_base.snapshot)
    fresh = type(feedback)(lambda _context, _options: 100).prepare(
        fresh_candidate, next_base
    )
    assert encode_world(fresh_candidate.state) == state
    assert tuple(item.input_fingerprint for item in fresh) == tuple(
        item.input_fingerprint for item in first
    )


@pytest.mark.parametrize("damage", ["future_result", "foreign_provenance", "bad_hash"])
def test_cursor_requires_real_holder_provenance(tmp_path: Path, damage: str) -> None:
    import json

    from living_world.archives.model import canonical
    from living_world.runtime.feedback import RuntimePreparationError

    live, engine, feedback, base = ready(tmp_path)
    cursor = json.loads(canonical(base.feedback_cursor))
    if damage == "future_result":
        cursor["pending_results"] = [
            {"actor_label": "ada", "source_tick": 0, "outcome": "accepted"}
        ]
    elif damage == "bad_hash":
        cursor["holders"]["ada"]["sources"]["mandate"]["goal_founding"] = "0" * 64
    else:
        ada = engine.state.scenario_entity_bindings["ada"]
        for key, item in tuple(engine.state.observations.items()):
            if item.observer == ada and item.evidence.get("source_kind") == "mandate":
                from dataclasses import replace

                engine.state.observations[key] = replace(
                    item, observer=engine.state.scenario_entity_bindings["bryn"]
                )
    corrupt = Checkpoint(0, encode_world(engine.state), {}, cursor)
    with pytest.raises(RuntimePreparationError):
        feedback.prepare(live.restore(corrupt.snapshot), corrupt)


def test_after_tick_rejects_old_event_references(tmp_path: Path) -> None:
    from living_world.runtime.feedback import RuntimePreparationError

    _live, engine, feedback, base = ready(tmp_path)
    # First tick makes tick-zero setup events historical.
    feedback.prepare(engine, base)
    engine.step()
    cursor = feedback.after_tick(
        engine, (resolved(base, "ada"), resolved(base, "bryn"))
    )
    base = Checkpoint(1, encode_world(engine.state), {}, cursor)
    feedback.prepare(engine, base)
    engine.step()
    old = next(key for key, event in engine.state.events.items() if event.tick == 0)
    with pytest.raises(RuntimePreparationError):
        feedback.after_tick(
            engine, (resolved(base, "ada", refs=(old,)), resolved(base, "bryn"))
        )


def test_private_cognition_and_hidden_goal_values_never_enter_requests(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from living_world.cognition.local_llm_cognition_format import (
        serialize_decision_request,
    )
    from living_world.core.memory import CognitiveSalience
    from living_world.goals.model import GoalOwnerKind
    from living_world.needs.model import NeedDefinition, NeedKind

    live, engine, feedback, _base = ready(tmp_path)
    visitor = engine.entities.create(definition_key="founder", name="Visitor")
    camp = engine.state.scenario_entity_bindings["camp"]
    engine.needs.create(
        NeedDefinition("need_private_food", visitor.id, NeedKind.FOOD, 1, 0.0, 0.5, 3)
    )
    goal = engine.state.goal_definitions["goal_founding"]
    objective = engine.state.objective_definitions["objective_founders_water"]
    engine.goals.create(
        replace(
            goal,
            id="goal_private",
            owner_kind=GoalOwnerKind.NPC,
            owner_id=visitor.id,
            label="Secret aim",
            purpose="hidden-secret-purpose",
            npc_interpretation="hidden-secret-instruction",
            objective_ids=("objective_private",),
        ),
        (
            replace(
                objective,
                id="objective_private",
                label="Secret objective",
                npc_interpretation="hidden-secret-objective",
            ),
        ),
    )
    observation = engine.observations.record(
        observer=visitor.id,
        subject=camp,
        description="hidden-secret-memory",
        confidence=1.0,
    )
    engine.memories.record(
        holder_id=visitor.id,
        subject_id=camp,
        summary="hidden-secret-memory",
        salience=CognitiveSalience(0.9, True),
        source_observation_ids=(observation.id,),
    )
    engine.events.record(
        kind="unobserved_model_speech",
        subject_id=visitor.id,
        attributes={"speech": "hidden-secret-speech"},
    )
    engine.events.record(
        kind="unseen_dispatch_result",
        subject_id=camp,
        attributes={"description": "hidden-secret-dispatch"},
    )
    snapshot = encode_world(engine.state)
    candidate = live.restore(snapshot)
    assert encode_world(candidate.state) == snapshot
    cursor = feedback.initialize(candidate)
    base = Checkpoint(0, encode_world(candidate.state), {}, cursor)
    decisions = feedback.prepare(candidate, base)
    assert tuple(item.actor_label for item in decisions) == ("ada", "bryn")
    for item in decisions:
        payload = serialize_decision_request(item.context, item.options)
        assert "hidden-secret" not in payload
        assert str(goal.deadline_tick) not in payload
        for marker in (
            item.actor_id,
            "source_kind",
            "source_id",
            "qualitative_hash",
            "handlers",
            "input_fingerprint",
            "goal_founding",
        ):
            assert marker not in payload


@pytest.mark.parametrize(
    "damage",
    [
        "identity",
        "canonical_need",
        "canonical_goal",
        "canonical_objective",
        "extra_need",
        "extra_goal",
        "extra_objective",
        "camp_placement",
        "valley_placement",
        "camp_dead",
        "valley_dead",
    ],
)
def test_live_rejects_structural_corruption(tmp_path: Path, damage: str) -> None:
    from dataclasses import replace

    from living_world.founders import FoundersConfigurationError, FoundersSetupManager
    from living_world.founders.model import canonical_policy
    from living_world.runtime.feedback import RuntimePreparationError
    from living_world.spatial.model import Point

    live, engine, feedback, _base = ready(tmp_path)
    bindings = engine.state.scenario_entity_bindings
    if damage == "identity":
        engine.entities.set_attribute(
            entity_id=bindings["ada"], key="npc_identity", value={}
        )
    elif damage in ("camp_dead", "valley_dead"):
        # Deliberately corrupt a protected entity: normal lifecycle manager forbids camp destruction.
        engine.state.entities[bindings[damage.removesuffix("_dead")]].destroyed_tick = 0
    elif damage.endswith("_placement"):
        engine.state.placements[bindings[damage.removesuffix("_placement")]] = replace(
            engine.state.placements[bindings[damage.removesuffix("_placement")]],
            geometry=Point(0, 0),
            bounds_kind=None,
        )
    elif damage.startswith("canonical_"):
        kind = damage.removeprefix("canonical_")
        collection = getattr(engine.state, kind + "_definitions")
        key = next(iter(collection))
        field = "requirement_per_person" if kind == "need" else "purpose"
        collection[key] = replace(
            collection[key],
            **{field: 91 if kind == "need" else "changed canonical purpose"},
        )
    else:
        kind = damage.removeprefix("extra_")
        collection = getattr(engine.state, kind + "_definitions")
        collection[kind + "_invalid"] = object()
    with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
        FoundersSetupManager(engine.state, engine.definitions).validate_live(
            canonical_policy()
        )
    # Bad world objects need not be serializable, but feedback always classifies safely.
    with pytest.raises(RuntimePreparationError, match="invalid_feedback"):
        feedback.initialize(engine)
    if damage == "identity":
        with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
            live.restore(encode_world(engine.state))


def test_transitive_placement_and_fixed_scenario_roster(tmp_path: Path) -> None:
    from living_world.spatial.model import Bounds, BoundsKind, Point

    live, engine, feedback, _base = ready(tmp_path)
    camp = engine.state.scenario_entity_bindings["camp"]
    ada = engine.state.scenario_entity_bindings["ada"]
    area = engine.entities.create(definition_key="area", name="Tent area")
    engine.spatial.place(
        entity_id=area.id,
        geometry=Bounds(0, 0, 4, 4),
        bounds_kind=BoundsKind.AREA,
        containing_entity_id=camp,
    )
    engine.spatial.replace(
        entity_id=ada, geometry=Point(1, 1), containing_entity_id=area.id
    )
    visitor = engine.entities.create(
        definition_key="founder",
        name="Visitor",
        attributes=dict(engine.state.entities[ada].attributes),
    )
    engine.spatial.place(
        entity_id=visitor.id, geometry=Point(3, 3), containing_entity_id=camp
    )
    cursor = feedback.initialize(engine)
    base = Checkpoint(0, encode_world(engine.state), {}, cursor)
    decisions = feedback.prepare(live.restore(base.snapshot), base)
    assert tuple(item.actor_label for item in decisions) == ("ada", "bryn")
    assert decisions[0].actor_id == ada


def test_feedback_and_live_candidate_caches_do_not_retain_engine(
    tmp_path: Path,
) -> None:
    import gc
    import weakref

    live, engine, feedback, base = ready(tmp_path)
    candidate = live.restore(base.snapshot)
    decisions = feedback.prepare(candidate, base)
    reference = weakref.ref(candidate)
    del candidate, decisions
    gc.collect()
    assert reference() is None
    assert engine.state.tick == 0


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {
            "format": True,
            "mode": "founders_feedback",
            "holders": {},
            "pending_results": [],
        },
        {
            "format": 1,
            "mode": "founders_feedback",
            "holders": {"stranger": {"sources": {}}},
            "pending_results": [],
        },
        {
            "format": 1,
            "mode": "founders_feedback",
            "holders": {},
            "pending_results": [
                {"actor_label": "ada", "source_tick": True, "outcome": "accepted"}
            ],
        },
    ],
)
def test_closed_cursor_rejects_corruption(
    tmp_path: Path, bad: dict[str, object]
) -> None:
    from living_world.runtime.feedback import RuntimePreparationError

    _live, engine, feedback, base = ready(tmp_path)
    with pytest.raises(RuntimePreparationError, match="invalid_cursor"):
        feedback.prepare(engine, Checkpoint(0, base.snapshot, {}, bad))


def test_initial_exact_templates_salience_and_provenance(tmp_path: Path) -> None:
    _live, engine, feedback, base = ready(tmp_path)
    expected = {
        "You were asked to help the camp: Help the settlement become secure.",
        *(
            f"{label}: This need cannot yet be assessed."
            for label in ("Food", "Water", "Shelter", "Storage")
        ),
    }
    for decision in feedback.prepare(engine, base):
        memories = engine.memories.memories_for(decision.actor_id)
        assert len(memories) == 5
        assert {item.summary for item in memories} == expected
        for memory in memories:
            observation = engine.state.observations[memory.source_observation_ids[0]]
            assert observation.observer == memory.holder_id == decision.actor_id
            assert (
                observation.subject
                == memory.subject_id
                == engine.state.scenario_entity_bindings["camp"]
            )
            assert observation.confidence == 1.0
            assert set(observation.evidence) == {
                "source_kind",
                "source_id",
                "qualitative_hash",
            }
            assert not observation.metadata
            assert memory.salience.importance == (
                0.8 if observation.evidence["source_kind"] == "mandate" else 0.6
            )
            assert memory.salience.is_core == (
                observation.evidence["source_kind"] == "mandate"
            )


def test_context_budget_is_deterministic_and_includes_complete_body(
    tmp_path: Path,
) -> None:
    import json

    from living_world.cognition.local_llm_cognition_format import (
        serialize_decision_request,
    )
    from living_world.core.memory import CognitiveSalience
    from living_world.runtime.feedback import FoundersFeedback, RuntimePreparationError

    live, engine, _feedback, base = ready(tmp_path)
    ada = engine.state.scenario_entity_bindings["ada"]
    for word in (
        "First",
        "Second",
        "Third",
        "Fourth",
        "Fifth",
        "Sixth",
        "Seventh",
        "Eighth",
        "Ninth",
    ):
        engine.memories.record(
            holder_id=ada,
            subject_id=ada,
            summary=word + " personal recollection.",
            salience=CognitiveSalience(0.7),
        )
    snapshot = encode_world(engine.state)
    base = Checkpoint(0, snapshot, {}, base.feedback_cursor)

    # Real complete-body encoder adds substantial model/system/schema material.
    def body_size(context: NPCContext, options: tuple[ActionOption, ...]) -> int:
        body = json.dumps(
            {
                "model": "test-local-model",
                "system": "s" * 14700,
                "format": {"type": "object"},
                "prompt": serialize_decision_request(context, options),
            },
            sort_keys=True,
        )
        return len(body)

    feedback = FoundersFeedback(body_size)
    first = feedback.prepare(live.restore(snapshot), base)
    second = FoundersFeedback(body_size).prepare(
        live.restore(snapshot), Checkpoint(23, snapshot, {}, base.feedback_cursor)
    )
    assert tuple(item.input_fingerprint for item in first) == tuple(
        item.input_fingerprint for item in second
    )
    for item in first:
        assert body_size(item.context, item.options) <= 16000
        assert (
            item.context.core_cognition[0].text
            == "You were asked to help the camp: Help the settlement become secure."
        )
    # Oldest selected memory is removed first; records outside initial top eight
    # selection must not be backfilled during pruning.
    texts = tuple(record.text for record in first[0].context.retrieved_information)
    assert "First personal recollection." not in texts
    assert "Ninth personal recollection." not in texts
    with pytest.raises(RuntimePreparationError, match="context_budget_exceeded"):
        FoundersFeedback(lambda _context, _options: 16001).prepare(
            live.restore(snapshot), base
        )


@pytest.mark.parametrize("size", [True, -1, 1.5, None])
def test_request_size_requires_exact_nonnegative_integer(
    tmp_path: Path, size: object
) -> None:
    from living_world.runtime.feedback import FoundersFeedback, RuntimePreparationError

    live, _engine, _feedback, base = ready(tmp_path)
    with pytest.raises(RuntimePreparationError, match="invalid_request_size"):
        FoundersFeedback(lambda _context, _options: size).prepare(
            live.restore(base.snapshot), base
        )


def create_work(
    engine: SimulationEngine,
    label: str = "Gather supplies",
    location: str | None = None,
    quantity: int = 1,
) -> WorkDefinition:
    from living_world.work.model import ResourceWorkTarget, WorkCategory

    camp = engine.state.scenario_entity_bindings["camp"]
    return engine.work.create(
        category=WorkCategory.GATHER_WATER,
        target=ResourceWorkTarget("water", quantity),
        public_label=label,
        settlement_id=camp,
        objective_id="objective_founders_water",
        location_id=location or camp,
    )


def test_local_work_replacement_changes_safe_perceptions_and_offers(
    tmp_path: Path,
) -> None:
    from living_world.runtime.feedback import FoundersFeedback

    live, engine, feedback, base = ready(tmp_path)
    feedback.prepare(engine, base)
    engine.step()
    cursor = feedback.after_tick(
        engine, (resolved(base, "ada"), resolved(base, "bryn"))
    )
    old = create_work(engine, "Old water effort", quantity=1)
    engine.work.cancel(old.id, "The plan changed.")
    new = create_work(engine, "New water effort", quantity=2)
    from dataclasses import replace

    from living_world.goals.model import GoalOwnerKind
    from living_world.spatial.model import Bounds, BoundsKind
    from living_world.work.model import ResourceWorkTarget, WorkCategory

    remote_camp = engine.entities.create(definition_key="settlement", name="Other camp")
    engine.spatial.place(
        entity_id=remote_camp.id,
        geometry=Bounds(15, 15, 5, 5),
        bounds_kind=BoundsKind.AREA,
        containing_entity_id=engine.state.scenario_entity_bindings["valley"],
    )
    objective = engine.state.objective_definitions["objective_founders_water"]
    goal = engine.state.goal_definitions["goal_founding"]
    engine.goals.create(
        replace(
            goal,
            id="goal_remote",
            owner_kind=GoalOwnerKind.SETTLEMENT,
            owner_id=remote_camp.id,
            objective_ids=("objective_remote",),
        ),
        (replace(objective, id="objective_remote"),),
    )
    remote = engine.work.create(
        category=WorkCategory.GATHER_WATER,
        target=ResourceWorkTarget("water", 1),
        public_label="Unseen water effort",
        settlement_id=remote_camp.id,
        objective_id="objective_remote",
        location_id=remote_camp.id,
    )
    base = Checkpoint(1, encode_world(engine.state), {}, cursor)
    candidate = live.restore(base.snapshot)
    decisions = FoundersFeedback(lambda _context, _options: 100).prepare(
        candidate, base
    )
    for item in decisions:
        assert (
            "Old water effort: This work will not proceed."
            in item.context.current_perceptions
        )
        assert (
            "New water effort: This work is being considered."
            in item.context.current_perceptions
        )
        assert all(
            "Unseen water effort" not in prose
            for prose in item.context.current_perceptions
        )
        observations = candidate.observations.observations_for(item.actor_id)
        assert any(
            record.evidence.get("source_id") == new.id for record in observations
        )
        assert all(
            record.evidence.get("source_id") != remote.id for record in observations
        )
        assert item.options
        assert all(new.id not in option.description for option in item.options)


@pytest.mark.parametrize("label", ["coordinates 4, 7", "work_123456", "available 123"])
def test_malicious_work_projection_fails_with_safe_code(
    tmp_path: Path, label: str
) -> None:
    from living_world.runtime.feedback import RuntimePreparationError

    _live, engine, feedback, _base = ready(tmp_path)
    try:
        create_work(engine, label)
    except ValueError:
        # Existing manager may reject an unsafe label even before feedback.
        return
    with pytest.raises(RuntimePreparationError) as captured:
        feedback.initialize(engine)
    assert str(captured.value) == "invalid_feedback"
    assert captured.value.__cause__ is None


def test_eight_perceptions_and_eight_distinct_holder_memories(tmp_path: Path) -> None:
    from living_world.core.memory import CognitiveSalience

    _live, engine, feedback, base = ready(tmp_path)
    for label in (
        "A useful effort",
        "Another effort",
        "A third effort",
        "A fourth effort",
        "A fifth effort",
        "A sixth effort",
    ):
        create_work(engine, label)
    ada = engine.state.scenario_entity_bindings["ada"]
    for word in (
        "First",
        "Second",
        "Third",
        "Fourth",
        "Fifth",
        "Sixth",
        "Seventh",
        "Eighth",
        "Ninth",
    ):
        engine.memories.record(
            holder_id=ada,
            subject_id=ada,
            summary=word + " personal recollection.",
            salience=CognitiveSalience(0.7),
        )
    cursor = feedback.initialize(engine)
    base = Checkpoint(0, encode_world(engine.state), {}, cursor)
    first = feedback.prepare(engine, base)[0]
    assert len(first.context.current_perceptions) == 8
    assert len(first.context.core_cognition) == 1
    assert len(first.context.retrieved_information) == 7
    assert (
        len(
            {
                item.text
                for item in first.context.core_cognition
                + first.context.retrieved_information
            }
        )
        == 8
    )
    assert all(not item.is_core for item in first.context.retrieved_information)
    assert first.context.retrieved_information[0].text == "First personal recollection."


def test_pending_result_waits_for_returning_holder_and_is_consumed_once(
    tmp_path: Path,
) -> None:
    from living_world.spatial.model import Point

    live, engine, feedback, base = ready(tmp_path)
    feedback.prepare(engine, base)
    engine.step()
    ada = engine.state.scenario_entity_bindings["ada"]
    engine.spatial.replace(
        entity_id=ada,
        geometry=Point(20, 20),
        containing_entity_id=engine.state.scenario_entity_bindings["valley"],
    )
    cursor = feedback.after_tick(
        engine, (resolved(base, "ada", "accepted"), resolved(base, "bryn"))
    )
    base = Checkpoint(1, encode_world(engine.state), {}, cursor)
    candidate = live.restore(base.snapshot)
    decisions = feedback.prepare(candidate, base)
    assert tuple(item.actor_label for item in decisions) == ("bryn",)
    assert all(
        item.description != "Your proposal was accepted."
        for item in candidate.state.observations.values()
    )
    candidate.step()
    cursor = feedback.after_tick(candidate, (resolved(base, "bryn"),))
    assert cursor["pending_results"][0]["actor_label"] == "ada"
    candidate.spatial.replace(
        entity_id=ada,
        geometry=Point(1, 1),
        containing_entity_id=candidate.state.scenario_entity_bindings["camp"],
    )
    base = Checkpoint(2, encode_world(candidate.state), {}, cursor)
    feedback.prepare(candidate, base)
    accepted = [
        item
        for item in candidate.observations.observations_for(ada)
        if item.description == "Your proposal was accepted."
    ]
    assert len(accepted) == 1
    candidate.step()
    cursor = feedback.after_tick(
        candidate, (resolved(base, "ada"), resolved(base, "bryn"))
    )
    assert all(item["source_tick"] != 0 for item in cursor["pending_results"])


@pytest.mark.parametrize(
    "damage",
    [
        "without_prepare",
        "no_tick",
        "wrong_revision",
        "wrong_actor",
        "duplicate_actor",
        "missing_actor",
        "missing_event",
        "wrong_source_tick",
    ],
)
def test_staged_continuity_and_outcome_validation(tmp_path: Path, damage: str) -> None:
    from living_world.archives import JournalEntry
    from living_world.runtime.feedback import RuntimePreparationError

    _live, engine, feedback, base = ready(tmp_path)
    if damage != "without_prepare":
        feedback.prepare(engine, base)
    if damage != "no_tick":
        engine.step()
    outcomes = (resolved(base, "ada"), resolved(base, "bryn"))
    if damage in (
        "wrong_revision",
        "wrong_actor",
        "missing_event",
        "wrong_source_tick",
    ):
        p = dict(outcomes[0].payload)
        field, value = {
            "wrong_revision": ("base_revision", 8),
            "wrong_actor": ("actor_label", "stranger"),
            "missing_event": ("event_references", ("event_999999",)),
            "wrong_source_tick": ("source_tick", 8),
        }[damage]
        p[field] = value
        outcomes = (JournalEntry("action_resolved", p), outcomes[1])
    elif damage == "duplicate_actor":
        outcomes = (outcomes[0], outcomes[0])
    elif damage == "missing_actor":
        outcomes = outcomes[:1]
    with pytest.raises(RuntimePreparationError, match="invalid_outcomes"):
        feedback.after_tick(engine, outcomes)


def test_cursor_cannot_drop_or_rewind_prior_sources(tmp_path: Path) -> None:
    import json

    from living_world.archives.model import canonical
    from living_world.runtime.feedback import RuntimePreparationError

    live, _engine, feedback, base = ready(tmp_path)
    cursor = json.loads(canonical(base.feedback_cursor))
    cursor["holders"].pop("ada")
    with pytest.raises(RuntimePreparationError, match="invalid_cursor"):
        feedback.prepare(
            live.restore(base.snapshot), Checkpoint(0, base.snapshot, {}, cursor)
        )


def test_changed_local_need_a_b_a_is_new_and_restart_deduplicates(
    tmp_path: Path,
) -> None:
    from living_world.runtime.feedback import FoundersFeedback

    live, engine, feedback, base = ready(tmp_path)
    camp = engine.state.scenario_entity_bindings["camp"]
    ada = engine.state.scenario_entity_bindings["ada"]
    counts = []
    observed = []
    for quantity in (0, 100, 0):
        feedback.prepare(engine, base)
        engine.entities.set_attribute(
            entity_id=camp,
            key="resources",
            value={"food": quantity, "water": quantity, "timber": 10},
        )
        engine.step()
        cursor = feedback.after_tick(
            engine, (resolved(base, "ada"), resolved(base, "bryn"))
        )
        base = Checkpoint(base.revision + 1, encode_world(engine.state), {}, cursor)
        candidate = live.restore(base.snapshot)
        decisions = FoundersFeedback(lambda _context, _options: 100).prepare(
            candidate, base
        )
        observed.append(
            tuple(
                text
                for text in decisions[0].context.current_perceptions
                if text.startswith("Water:")
            )
        )
        counts.append(
            len(
                [
                    item
                    for item in candidate.observations.observations_for(ada)
                    if item.evidence.get("source_id") == "need_founders_water"
                ]
            )
        )
        # Checkpoint is before feedback preparation, so each fresh reconstruction
        # must allocate exactly the same new observations/memories.
        restarted = live.restore(base.snapshot)
        FoundersFeedback(lambda _context, _options: 100).prepare(
            restarted, Checkpoint(0, base.snapshot, {}, cursor)
        )
        assert encode_world(restarted.state) == encode_world(candidate.state)
        engine = live.restore(base.snapshot)
    assert observed[0] == observed[2] != observed[1]
    assert counts == [2, 3, 4]


@pytest.mark.parametrize("timing", ["before", "after"])
def test_destroyed_founder_preserves_historical_shelter_attachments(
    tmp_path: Path, timing: str
) -> None:
    from living_world.founders import FoundersSetupManager
    from living_world.founders.model import canonical_policy

    live = composition(tmp_path)
    engine = live.initialize()
    camp = engine.state.scenario_entity_bindings["camp"]
    ada = engine.state.scenario_entity_bindings["ada"]
    from living_world.systems.simulation_system import SimulationSystem

    class ConstructShelter(SimulationSystem):
        def step(self, state: WorldState) -> None:
            if not any(
                entity.definition_key == "shelter" for entity in state.entities.values()
            ):
                created = engine.entities.create(
                    definition_key="shelter",
                    name="Modest shelter",
                    attributes={"is_constructed": True},
                )
                engine.relationships.create(
                    kind="owns", source_id=camp, target_id=created.id
                )

    engine.register_system(ConstructShelter(), key="test_construction")
    engine.step()
    shelter = next(
        entity
        for entity in engine.state.entities.values()
        if entity.definition_key == "shelter"
    )
    if timing == "before":
        engine.entities.mark_destroyed(ada, engine.state.tick)
    engine.step()
    if timing == "after":
        engine.entities.mark_destroyed(ada, engine.state.tick)
    manager = FoundersSetupManager(engine.state, engine.definitions)
    manager.validate_live(canonical_policy())
    occupants = {
        rel.source_id
        for rel in engine.state.relationships.values()
        if rel.kind == "housed_in" and rel.target_id == shelter.id
    }
    assert occupants == {
        engine.state.scenario_entity_bindings[label] for label in ("ada", "bryn")
    }
    snapshot = encode_world(engine.state)
    restored = live.restore(snapshot)
    live.finalize(restored, stopped=False)
    assert encode_world(restored.state) == snapshot


def test_semantic_cursor_affects_fingerprint_but_revision_does_not(
    tmp_path: Path,
) -> None:
    live, _engine, feedback, base = ready(tmp_path)
    first = feedback.prepare(live.restore(base.snapshot), base)
    renamed = Checkpoint(99, base.snapshot, base.driver_cursor, base.feedback_cursor)
    second = feedback.prepare(live.restore(base.snapshot), renamed)
    changed = Checkpoint(
        0, base.snapshot, {"semantic_position": "changed"}, base.feedback_cursor
    )
    third = feedback.prepare(live.restore(base.snapshot), changed)
    assert tuple(item.input_fingerprint for item in first) == tuple(
        item.input_fingerprint for item in second
    )
    assert tuple(item.input_fingerprint for item in first) != tuple(
        item.input_fingerprint for item in third
    )


def test_absent_local_source_leaves_history_without_stale_perception(
    tmp_path: Path,
) -> None:
    from living_world.spatial.model import Bounds, BoundsKind

    live, engine, feedback, _base = ready(tmp_path)
    camp = engine.state.scenario_entity_bindings["camp"]
    area = engine.entities.create(definition_key="area", name="Work clearing")
    engine.spatial.place(
        entity_id=area.id,
        geometry=Bounds(5, 3, 2, 2),
        bounds_kind=BoundsKind.AREA,
        containing_entity_id=camp,
    )
    work = create_work(engine, "Local water effort", location=area.id)
    engine.work.cancel(work.id, "The plan changed.")
    cursor = feedback.initialize(engine)
    base = Checkpoint(0, encode_world(engine.state), {}, cursor)
    first = feedback.prepare(engine, base)
    assert (
        "Local water effort: This work will not proceed."
        in first[0].context.current_perceptions
    )
    engine.spatial.replace(
        entity_id=area.id,
        geometry=Bounds(20, 20, 2, 2),
        bounds_kind=BoundsKind.AREA,
        containing_entity_id=engine.state.scenario_entity_bindings["valley"],
    )
    engine.step()
    cursor = feedback.after_tick(
        engine, (resolved(base, "ada"), resolved(base, "bryn"))
    )
    base = Checkpoint(1, encode_world(engine.state), {}, cursor)
    candidate = live.restore(base.snapshot)
    second = feedback.prepare(candidate, base)
    assert all(
        "Local water effort" not in text
        for text in second[0].context.current_perceptions
    )
    memories = candidate.memories.memories_for(second[0].actor_id)
    assert any(
        memory.summary == "Local water effort: This work will not proceed."
        for memory in memories
    )


def test_broken_placement_chains_fail_closed_without_looping(tmp_path: Path) -> None:
    from dataclasses import replace

    from living_world.runtime.feedback import RuntimePreparationError

    _live, engine, feedback, _base = ready(tmp_path)
    ada = engine.state.scenario_entity_bindings["ada"]
    engine.state.placements[ada] = replace(
        engine.state.placements[ada], containing_entity_id=ada
    )
    with pytest.raises(RuntimePreparationError, match="invalid_feedback"):
        feedback.initialize(engine)


def test_consumed_result_cannot_be_reintroduced(tmp_path: Path) -> None:
    import json

    from living_world.archives.model import canonical
    from living_world.runtime.feedback import RuntimePreparationError

    _live, engine, feedback, base = ready(tmp_path)
    feedback.prepare(engine, base)
    engine.step()
    cursor = feedback.after_tick(
        engine, (resolved(base, "ada", "accepted"), resolved(base, "bryn"))
    )
    next_base = Checkpoint(1, encode_world(engine.state), {}, cursor)
    feedback.prepare(engine, next_base)
    engine.step()
    cursor = feedback.after_tick(
        engine, (resolved(next_base, "ada"), resolved(next_base, "bryn"))
    )
    bad = json.loads(canonical(cursor))
    bad["pending_results"].append(
        {"actor_label": "ada", "source_tick": 0, "outcome": "accepted"}
    )
    bad_base = Checkpoint(2, encode_world(engine.state), {}, bad)
    with pytest.raises(RuntimePreparationError, match="invalid_cursor"):
        feedback.prepare(engine, bad_base)


def test_candidate_mismatch_and_failure_leave_base_unchanged(tmp_path: Path) -> None:
    from living_world.runtime.feedback import FoundersFeedback, RuntimePreparationError

    live, engine, feedback, base = ready(tmp_path)
    before = base.snapshot
    candidate = live.restore(before)
    candidate.entities.set_attribute(
        entity_id=candidate.state.scenario_entity_bindings["ada"],
        key="private_note",
        value="changed engine fact",
    )
    with pytest.raises(RuntimePreparationError, match="candidate_mismatch"):
        feedback.prepare(candidate, base)
    assert encode_world(engine.state) == before == base.snapshot
    with pytest.raises(RuntimePreparationError, match="context_budget_exceeded"):
        FoundersFeedback(lambda _context, _options: 16001).prepare(
            live.restore(before), base
        )
    assert encode_world(engine.state) == before == base.snapshot


@pytest.mark.parametrize("bad_tick", [True, -1, 99])
def test_live_rejects_invalid_founder_destruction_ticks(
    tmp_path: Path, bad_tick: object
) -> None:
    from living_world.founders import FoundersConfigurationError, FoundersSetupManager
    from living_world.founders.model import canonical_policy

    _live, engine, _feedback, _base = ready(tmp_path)
    engine.state.entities[
        engine.state.scenario_entity_bindings["ada"]
    ].destroyed_tick = bad_tick
    with pytest.raises(FoundersConfigurationError, match="setup_mismatch"):
        FoundersSetupManager(engine.state, engine.definitions).validate_live(
            canonical_policy()
        )


def test_live_offers_refresh_after_cancelling_and_replacing_work_target(
    tmp_path: Path,
) -> None:
    from living_world.api.inspection import EngineWorldInspector
    from living_world.founders.model import canonical_policy
    from living_world.founders.runtime import FoundersLiveOfferProvider
    from living_world.work.model import ResourceWorkTarget, WorkCategory

    live = composition(tmp_path)
    engine = live.initialize()
    engine.step()
    camp = engine.state.scenario_entity_bindings["camp"]
    actor = engine.state.scenario_entity_bindings["ada"]
    policy = canonical_policy()
    old = engine.work.create(
        category=WorkCategory.GATHER_WATER,
        target=ResourceWorkTarget("water", policy.rules.water_work_quantity),
        public_label="Old water effort",
        settlement_id=camp,
        objective_id="objective_founders_water",
        location_id=camp,
        labor_required=policy.rules.normal_labor,
        required_progress=policy.rules.required_progress,
    )
    provider = FoundersLiveOfferProvider(engine, policy)
    before = provider.offers(
        actor_id=actor, inspector=EngineWorldInspector(engine)
    ).options
    assert all("Gather water" not in option.target_labels for option in before)
    engine.work.cancel(old.id, "The plan changed.")
    replacement = create_work(engine, "Replacement water effort", quantity=2)
    after = provider.offers(
        actor_id=actor, inspector=EngineWorldInspector(engine)
    ).options
    assert any("Gather water" in option.target_labels for option in after)
    assert replacement.id != old.id
    assert before != after
