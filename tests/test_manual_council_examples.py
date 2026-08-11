"""Offline rendering coverage for the opt-in local council examples."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from living_world.cognition.action_resolution import ActionResolution, NPCActionResolver
from living_world.cognition.conversation import (
    ConversationProposal,
    ConversationResult,
    ConversationTurn,
)
from living_world.cognition.council import (
    CouncilAttendance,
    CouncilDecisionBasis,
    CouncilInvitationDiagnostic,
    CouncilInvitationFeedback,
    CouncilInvitationStatus,
    CouncilResult,
)
from living_world.cognition.npc_cognition_client import ActionRequest
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.recording_cognition_client import RecordedCognitionRequest

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
def test_invitation_feedback_renders_each_invitee_without_caller(path: Path) -> None:
    module = _load_example(path)
    result = CouncilResult(
        (
            CouncilAttendance("Aster", True, False),
            CouncilAttendance("Bryn", False, True),
            CouncilAttendance("Cato", False, False),
        ),
        ConversationResult((), ()),
        None,
        (),
        (
            CouncilInvitationFeedback(
                "Bryn",
                CouncilInvitationStatus.DECLINED,
                "I must remain at the gate.",
                "Please count my delegation.",
            ),
            CouncilInvitationFeedback(
                "Cato",
                CouncilInvitationStatus.UNAVAILABLE,
                None,
                None,
                CouncilInvitationDiagnostic.INVALID_STRUCTURED_RESPONSE,
            ),
        ),
    )

    output = module.format_council_result(result)

    assert "Invitation feedback" in output
    assert "- Bryn: declined" in output
    assert "statement: I must remain at the gate." in output
    assert "rationale: Please count my delegation." in output
    assert "- Cato: unavailable" in output
    assert "No usable reply: invalid structured response." in output
    assert "- Aster: " not in output


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_explicit_decline_fallback_basis_renders_without_invitee_reasons(
    path: Path,
) -> None:
    module = _load_example(path)
    result = CouncilResult(
        (
            CouncilAttendance("Aster", True, False),
            CouncilAttendance("Bryn", False, True),
        ),
        ConversationResult((), ()),
        ActionRequest("wait", None, "The caller proposes waiting."),
        (ActionResolution(False, "No handler supports the requested action."),),
        (),
        CouncilDecisionBasis.EXPLICIT_DECLINE_CALLER_FALLBACK,
    )

    output = module.format_council_result(result)

    assert (
        "Every invitee explicitly declined and delegated one fallback proposal."
        in output
    )
    assert "Decision basis: explicit_decline_caller_fallback" in output
    assert "Caller fallback proposal: ActionRequest(" in output
    assert "Majority proposal: ActionRequest(" not in output


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_unavailable_feedback_renders_only_fixed_diagnostic(path: Path) -> None:
    module = _load_example(path)
    raw_provider_error = "transport timeout entity_999"
    result = CouncilResult(
        (
            CouncilAttendance("Aster", True, False),
            CouncilAttendance("Bryn", False, False),
        ),
        ConversationResult((), ()),
        None,
        (),
        (
            CouncilInvitationFeedback(
                "Bryn",
                CouncilInvitationStatus.UNAVAILABLE,
                None,
                None,
                CouncilInvitationDiagnostic.PROVIDER_UNAVAILABLE,
            ),
        ),
    )

    output = module.format_council_result(result)

    assert "No usable reply: provider unavailable." in output
    assert raw_provider_error not in output
    assert "entity_999" not in output


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_formatter_rejects_non_council_result(path: Path) -> None:
    module = _load_example(path)

    with pytest.raises(TypeError, match="CouncilResult"):
        module.format_council_result(object())


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_scenario_is_long_rotated_opaque_and_has_three_choices(path: Path) -> None:
    module = _load_example(path)

    assert len(module.ACTIONS) >= 3
    assert len({action.key for action in module.ACTIONS}) == len(module.ACTIONS)
    assert module.MAX_ROUNDS > len(module.PARTICIPANT_IDS)
    assert module.TURN_ORDER_OFFSET > 0
    assert module.ORGANIZATION_ID.startswith("organization_")
    assert all(
        identifier.startswith("entity_") for identifier in module.PARTICIPANT_IDS
    )
    assert not any(
        name.casefold() in identifier.casefold()
        for identifier, (name, _) in zip(
            module.PARTICIPANT_IDS, module.PERSPECTIVES, strict=True
        )
    )


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_manual_handler_accepts_offered_choice_without_world_mutation(
    path: Path,
) -> None:
    module = _load_example(path)
    handler = module.ManualCouncilActionHandler()
    request = ActionRequest(module.ACTIONS[0].key, None, "This best fits our needs.")
    sentinel_world = {"unchanged": True}

    assert handler.supports(request.action_key)
    resolver = NPCActionResolver(module.ACTIONS, (handler,))
    resolution = resolver.resolve(actor_id="entity_401", request=request)

    assert resolution.accepted
    assert "world state unchanged" in resolution.reason
    assert sentinel_world == {"unchanged": True}


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_context_trace_serializes_only_safe_request_and_action_vocabulary(
    path: Path,
) -> None:
    module = _load_example(path)
    context = NPCContext(
        "Aster",
        ("I favour careful preparation.",),
        ("The road looks difficult.",),
        (),
        (),
    )
    requests = (RecordedCognitionRequest(context, module.ACTIONS),)
    raw_provider_output = "RAW_PROVIDER_RESPONSE secret-token entity_999"
    raw_world_state = "WorldState(entity_999)"

    output = module.format_context_trace(requests)

    assert "Filtered cognition request context" in output
    assert '"identity":"Aster"' in output
    assert '"actions"' in output
    assert all(action.key in output for action in module.ACTIONS)
    assert raw_provider_output not in output
    assert raw_world_state not in output
    assert "secret-token" not in output
    assert "entity_999" not in output


@pytest.mark.parametrize("path", _EXAMPLE_PATHS)
def test_normal_result_rendering_remains_concise_without_context(path: Path) -> None:
    module = _load_example(path)
    result = CouncilResult(
        (CouncilAttendance("Aster", True, False),),
        ConversationResult((), ()),
        None,
        (),
    )

    output = module.format_council_result(result)

    assert "Attendance" in output
    assert "Filtered cognition request context" not in output
    assert '"identity"' not in output
