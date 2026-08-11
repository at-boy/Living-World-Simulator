"""Offline coverage for the shared manual council scenario catalog."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import ModuleType

import pytest

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
JOURNEY = _SCENARIO_MODULE.JOURNEY
OPPOSING_INTERESTS = _SCENARIO_MODULE.OPPOSING_INTERESTS
SCENARIO_NAMES = _SCENARIO_MODULE.SCENARIO_NAMES
SETTLEMENT = _SCENARIO_MODULE.SETTLEMENT
get_scenario = _SCENARIO_MODULE.get_scenario

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
        "--scenario {journey,settlement,opposing-interests}" in capsys.readouterr().out
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
    )


def test_opposing_interests_has_five_independently_eligible_members() -> None:
    assert len(OPPOSING_INTERESTS.participants) == 5
    assert len(set(OPPOSING_INTERESTS.participant_ids)) == 5
    assert OPPOSING_INTERESTS.organization_name == "Town Council"
    assert all(
        participant.identifier.startswith("entity_")
        for participant in OPPOSING_INTERESTS.participants
    )

    # Both manual entry points create one member_of relationship per participant;
    # no affiliation grants or substitutes for council eligibility.
    for path in _EXAMPLE_PATHS:
        source = path.read_text(encoding="utf-8")
        assert "for index, participant in enumerate(scenario.participants" in source
        assert '"member_of"' in source
        assert "participant.identifier" in source
        assert "scenario.organization_id" in source


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
