import re

from living_world.cognition.local_llm_cognition_format import SYSTEM_INSTRUCTIONS


def test_opening_guidance_distinguishes_an_agenda_from_visible_dialogue() -> None:
    guidance = " ".join(SYSTEM_INSTRUCTIONS.split())

    assert "topic or agenda by itself as context" in guidance
    assert "not as something a prior speaker said" in guidance
    assert "begin with your own direct position" in guidance
    assert 'such as "I see" or "I agree"' in guidance


def test_dialogue_guidance_limits_replies_to_visible_history() -> None:
    guidance = " ".join(SYSTEM_INSTRUCTIONS.split())

    assert "When labelled prior dialogue is present" in guidance
    assert "respond only to that visible dialogue" in guidance
    assert "Never invent unseen speakers" in guidance
    assert "supplied NPC-readable context" in guidance


def test_opening_guidance_contains_no_concrete_world_or_internal_data() -> None:
    guidance = SYSTEM_INSTRUCTIONS.split("Treat a topic or agenda", maxsplit=1)[1]
    guidance = guidance.split("Return exactly one JSON object", maxsplit=1)[0]

    for forbidden_text in ("action_key", "target_label", "oak", "Erik", "0.8"):
        assert forbidden_text not in guidance
    assert re.search(r"\b\w+_\d+\b", guidance) is None
