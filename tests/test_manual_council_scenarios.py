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
    assert "--scenario {journey,settlement}" in capsys.readouterr().out


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


def test_unknown_scenario_is_rejected_without_provider_access() -> None:
    with pytest.raises(ValueError, match="Unknown manual council scenario"):
        get_scenario("missing")
