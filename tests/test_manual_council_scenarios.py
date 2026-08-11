"""Offline coverage for the shared manual council scenario catalog."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import ModuleType

import pytest

from living_world.cognition.local_llm_cognition_format import serialize_decision_request
from living_world.cognition.npc_context import NPCContextAssembler

_SCENARIO_PATH = Path("examples/manual/council_scenarios.py")
_SCENARIO_SPEC = importlib.util.spec_from_file_location(
    "council_scenarios", _SCENARIO_PATH
)
assert _SCENARIO_SPEC is not None
assert _SCENARIO_SPEC.loader is not None
_SCENARIO_MODULE = importlib.util.module_from_spec(_SCENARIO_SPEC)
sys.modules[_SCENARIO_SPEC.name] = _SCENARIO_MODULE
_SCENARIO_SPEC.loader.exec_module(_SCENARIO_MODULE)

DEFAULT_SCENARIO_NAME = _SCENARIO_MODULE.DEFAULT_SCENARIO_NAME
COGNITION_SHAPED = _SCENARIO_MODULE.COGNITION_SHAPED
JOURNEY = _SCENARIO_MODULE.JOURNEY
OPPOSING_INTERESTS = _SCENARIO_MODULE.OPPOSING_INTERESTS
SCENARIO_NAMES = _SCENARIO_MODULE.SCENARIO_NAMES
SETTLEMENT = _SCENARIO_MODULE.SETTLEMENT
get_scenario = _SCENARIO_MODULE.get_scenario
prepare_council_runtime = _SCENARIO_MODULE.prepare_council_runtime

_EXAMPLE_PATHS = (
    Path("examples/manual/ollama_council_meeting.py"),
    Path("examples/manual/llama_cpp_council_meeting.py"),
)


def _load_example(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_preserves_journey_default_and_is_immutable() -> None:
    assert DEFAULT_SCENARIO_NAME == "journey"
    assert get_scenario(DEFAULT_SCENARIO_NAME) is JOURNEY

    with pytest.raises(FrozenInstanceError):
        JOURNEY.agenda = "replacement"  # type: ignore[misc]


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_providers_expose_same_offline_scenario_selection(path: Path) -> None:
    module = _load_example(path)

    assert module.SCENARIO_NAMES == SCENARIO_NAMES
    assert module.get_scenario("settlement") is SETTLEMENT
    assert module.JOURNEY is JOURNEY


@pytest.mark.parametrize(
    ("path", "provider_name"),
    (
        (_EXAMPLE_PATHS[0], "OllamaCognitionClient"),
        (_EXAMPLE_PATHS[1], "LlamaCppCognitionClient"),
    ),
)
def test_argument_help_does_not_construct_or_contact_provider(
    path: Path,
    provider_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_example(path)

    def fail_provider_construction(*args: object, **kwargs: object) -> None:
        raise AssertionError("provider must not be constructed for --help")

    monkeypatch.setattr(module, provider_name, fail_provider_construction)
    monkeypatch.setattr(sys, "argv", [path.name, "--help"])

    with pytest.raises(SystemExit) as exit_info:
        module.main()

    assert exit_info.value.code == 0
    assert (
        "--scenario {journey,settlement,opposing-interests,cognition-shaped}"
        in capsys.readouterr().out
    )


def test_settlement_scenario_is_opaque_long_rotated_and_qualitative() -> None:
    assert len(SETTLEMENT.participants) == 5
    assert SETTLEMENT.max_rounds > len(SETTLEMENT.participants)
    assert SETTLEMENT.turn_order_offset > 0
    assert SETTLEMENT.organization_id.startswith("organization_")
    assert all(
        participant.identifier.startswith("entity_")
        for participant in SETTLEMENT.participants
    )
    assert all(
        participant.name.casefold() not in participant.identifier.casefold()
        for participant in SETTLEMENT.participants
    )
    assert len(SETTLEMENT.actions) >= 3
    assert len({action.key for action in SETTLEMENT.actions}) == len(SETTLEMENT.actions)
    assert all(action.description.strip() for action in SETTLEMENT.actions)


def test_settlement_text_separates_shared_condition_from_coordinator() -> None:
    visible_text = " ".join(
        (
            SETTLEMENT.agenda,
            *(participant.self_knowledge for participant in SETTLEMENT.participants),
        )
    ).casefold()

    assert "visible failure" in visible_text
    assert "requires a decision" in visible_text
    assert "only to coordinate" in visible_text
    assert "not introduced by alma" in visible_text
    assert "no action has unanimous support" in visible_text
    assert "speak for everyone" in visible_text


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_providers_select_opposing_interests_without_provider_access(
    path: Path,
) -> None:
    module = _load_example(path)

    assert module.get_scenario("opposing-interests") is OPPOSING_INTERESTS
    assert module.SCENARIO_NAMES == (
        "journey",
        "settlement",
        "opposing-interests",
        "cognition-shaped",
    )


def test_opposing_interests_has_five_independently_eligible_members() -> None:
    assert len(OPPOSING_INTERESTS.participants) == 5
    assert len(set(OPPOSING_INTERESTS.participant_ids)) == 5
    assert OPPOSING_INTERESTS.organization_name == "Town Council"
    assert all(
        participant.identifier.startswith("entity_")
        for participant in OPPOSING_INTERESTS.participants
    )

    # Both entry points use the shared manager-owned preparation path.
    for path in _EXAMPLE_PATHS:
        source = path.read_text(encoding="utf-8")
        assert "prepare_council_runtime(scenario)" in source
        assert "state.entities[" not in source
        assert "state.relationships[" not in source


def test_opposing_interests_context_is_opposed_cross_cutting_and_safe() -> None:
    visible_text = " ".join(
        (
            OPPOSING_INTERESTS.agenda,
            *(
                participant.self_knowledge
                for participant in OPPOSING_INTERESTS.participants
            ),
        )
    ).casefold()

    assert "riverside traders" in visible_text
    assert "hillside growers" in visible_text
    assert "both reliable access and harvest readiness" in visible_text
    assert "independent healer" in visible_text
    assert "opposed and overlapping interests" in visible_text
    assert "special voting authority" in visible_text
    assert "entity_" not in visible_text
    assert "organization_" not in visible_text
    assert "relationship" not in visible_text
    assert "score" not in visible_text


def test_opposing_interests_offers_choices_without_preselected_result() -> None:
    assert len(OPPOSING_INTERESTS.actions) >= 3
    assert len({action.key for action in OPPOSING_INTERESTS.actions}) == len(
        OPPOSING_INTERESTS.actions
    )
    assert all(action.description.strip() for action in OPPOSING_INTERESTS.actions)

    participant_text = " ".join(
        participant.self_knowledge for participant in OPPOSING_INTERESTS.participants
    )
    assert all(
        action.key not in participant_text for action in OPPOSING_INTERESTS.actions
    )
    assert not hasattr(OPPOSING_INTERESTS, "proposal")
    assert not hasattr(OPPOSING_INTERESTS, "majority")


def test_unknown_scenario_is_rejected_without_provider_access() -> None:
    with pytest.raises(ValueError, match="Unknown manual council scenario"):
        get_scenario("missing")


@pytest.mark.parametrize("scenario_name", SCENARIO_NAMES)
def test_shared_runtime_uses_manager_generated_entities_and_membership(
    scenario_name: str,
) -> None:
    scenario = get_scenario(scenario_name)
    runtime = prepare_council_runtime(scenario)

    assert runtime.organization_id == "entity_000001"
    assert runtime.participant_ids == tuple(
        f"entity_{index:06d}" for index in range(2, 7)
    )
    assert runtime.participant_ids != scenario.participant_ids
    assert set(runtime.participant_self_knowledge) == set(runtime.participant_ids)
    assert {
        (relationship.source_id, relationship.target_id)
        for relationship in runtime.engine.state.relationships.values()
    } == {
        (participant_id, runtime.organization_id)
        for participant_id in runtime.participant_ids
    }


def test_cognition_shaped_history_is_holder_scoped_and_interpretive() -> None:
    runtime = prepare_council_runtime(COGNITION_SHAPED)
    engine = runtime.engine
    participant_ids = runtime.participant_ids

    assert all(engine.observations.observations_for(item) for item in participant_ids)
    assert engine.memories.memories_for(participant_ids[0])
    assert engine.experiences.experiences_for(participant_ids[1])
    pella_belief = engine.beliefs.beliefs_for(participant_ids[2])[0]
    quin_belief = engine.beliefs.beliefs_for(participant_ids[3])[0]
    assert "inspection first" in pella_belief.proposition
    assert "immediate repair" in quin_belief.proposition
    assert engine.npc_relationships.relationships_for(participant_ids[4])

    # Conflicting beliefs remain interpretations, not authoritative entity state.
    assert not any(entity.name == "public well" for entity in engine.entities.all())
    assert not hasattr(COGNITION_SHAPED, "proposal")
    assert not hasattr(COGNITION_SHAPED, "majority")


def test_every_cognition_shaped_context_excludes_other_holders_and_internals() -> None:
    runtime = prepare_council_runtime(COGNITION_SHAPED)
    assembler = NPCContextAssembler(
        runtime.engine.state, retriever=runtime.cognitive_retriever
    )
    expected_private_text = (
        "hidden damage was missed",
        "handle a water emergency calmly",
        "prevent wasting scarce stone",
        "allowing the disruption to continue",
        "trust nessa's caution but know quin values urgency",
    )
    forbidden_engine_text = (
        "private_measurement",
        "private_route_count",
        "private_inventory",
        "private_schedule",
        "private_names",
        "internal_note",
        "private_source",
        "private_basis",
    )

    for index, holder_id in enumerate(runtime.participant_ids):
        context = assembler.assemble(
            holder_id=holder_id,
            capability_descriptions=runtime.participant_self_knowledge[holder_id],
        )
        rendered = serialize_decision_request(context, COGNITION_SHAPED.actions)

        assert expected_private_text[index] in rendered.casefold()
        assert all(
            text not in rendered.casefold()
            for other_index, text in enumerate(expected_private_text)
            if other_index != index
        )
        assert all(identifier not in rendered for identifier in runtime.participant_ids)
        assert runtime.organization_id not in rendered
        assert all(
            prefix not in rendered
            for prefix in (
                "observation_",
                "memory_",
                "belief_",
                "experience_",
                "npc_relationship_",
            )
        )
        assert all(text not in rendered for text in forbidden_engine_text)
        assert "evidence" not in rendered
        assert "metadata" not in rendered
        assert "WorldState" not in rendered
        relationship_records = tuple(
            record
            for record in (*context.core_cognition, *context.retrieved_information)
            if record.kind == "relationship"
        )
        if index == 4:
            assert tuple(record.text for record in relationship_records) == (
                "On public well work, I trust Nessa's caution but know Quin values urgency.",
            )
        else:
            assert relationship_records == ()


def test_cognition_shaped_scenario_offers_one_common_unforced_agenda() -> None:
    runtime = prepare_council_runtime(COGNITION_SHAPED)

    assert len(runtime.participant_ids) == 5
    assert len(COGNITION_SHAPED.actions) == 3
    participant_text = " ".join(
        participant.self_knowledge for participant in COGNITION_SHAPED.participants
    )
    assert all(
        action.key not in participant_text for action in COGNITION_SHAPED.actions
    )
    assert "majority" not in COGNITION_SHAPED.agenda.casefold()
    assert "must choose" not in participant_text.casefold()
