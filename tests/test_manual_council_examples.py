"""Offline rendering coverage for the opt-in local council examples."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from living_world.cognition.action_resolution import ActionResolution
from living_world.cognition.conversation import (
    ConversationProposal,
    ConversationResult,
    ConversationTurn,
)
from living_world.cognition.council import CouncilAttendance, CouncilResult
from living_world.cognition.npc_cognition_client import ActionRequest

_EXAMPLE_PATHS = (
    Path("examples/manual/ollama_council_meeting.py"),
    Path("examples/manual/llama_cpp_council_meeting.py"),
)


def _load_example(path: Path) -> ModuleType:
    """Load an example module without calling its opt-in ``main`` function."""

    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_caller_only_result_is_rendered_offline_and_accurately(path: Path) -> None:
    module = _load_example(path)
    result = CouncilResult(
        (
            CouncilAttendance("Aster", True, False),
            CouncilAttendance("Bryn", False, False),
        ),
        ConversationResult((), ()),
        None,
        (),
    )

    output = module.format_council_result(result)

    assert "- Aster (caller): attending" in output
    assert "- Bryn (invitee): not attending" in output
    assert "Only the caller attended; no invited NPC joined." in output
    assert "No debate was held because no invited NPC joined." in output


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_invited_attendee_dialogue_and_proposal_remain_visible(path: Path) -> None:
    module = _load_example(path)
    proposal = ActionRequest("wait", None, "Waiting preserves supplies.")
    result = CouncilResult(
        (
            CouncilAttendance("Aster", True, False),
            CouncilAttendance("Bryn", True, False),
        ),
        ConversationResult(
            (ConversationTurn("Bryn", "Let us wait until daylight."),),
            (),
            (ConversationProposal("Bryn", proposal),),
        ),
        proposal,
        (ActionResolution(False, "No handler supports the requested action."),),
    )

    output = module.format_council_result(result)

    assert "- Aster (caller): attending" in output
    assert "- Bryn (invitee): attending" in output
    assert "Bryn: Let us wait until daylight." in output
    assert "- Bryn: wait (Waiting preserves supplies.)" in output
    assert "Majority proposal: ActionRequest(" in output
    assert "Gateway resolution: ActionResolution(" in output


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_formatter_rejects_non_council_result(path: Path) -> None:
    module = _load_example(path)

    with pytest.raises(TypeError, match="CouncilResult"):
        module.format_council_result(object())
