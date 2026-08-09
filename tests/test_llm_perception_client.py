from collections.abc import MutableMapping
from typing import cast

import pytest

from living_world.perception.llm_perception_client import (
    LLMPerceptionRequest,
    LLMPerceptionResponse,
)


def test_request_preserves_only_curated_perception_data() -> None:
    request = LLMPerceptionRequest(
        observer_name="Erik",
        capabilities={"woodcraft": 80},
        subject_name="Old Oak",
        subject_attributes={"growth": 87, "health": 92, "wood": 120},
    )

    assert request.observer_name == "Erik"
    assert request.capabilities == {"woodcraft": 80}
    assert request.subject_name == "Old Oak"
    assert request.subject_attributes == {
        "growth": 87,
        "health": 92,
        "wood": 120,
    }
    assert not hasattr(request, "world_state")
    assert not hasattr(request, "observer_id")
    assert not hasattr(request, "subject_id")


def test_request_mappings_are_immutable() -> None:
    request = LLMPerceptionRequest(
        observer_name="Erik",
        capabilities={"woodcraft": 80},
        subject_name="Old Oak",
        subject_attributes={"growth": 87},
    )

    with pytest.raises(TypeError):
        capabilities = cast(MutableMapping[str, object], request.capabilities)
        capabilities["woodcraft"] = 100

    with pytest.raises(TypeError):
        subject_attributes = cast(
            MutableMapping[str, object],
            request.subject_attributes,
        )
        subject_attributes["growth"] = 100


def test_response_contains_only_perception_values() -> None:
    response = LLMPerceptionResponse(
        description="The Old Oak appears mature and healthy.",
        confidence=0.85,
    )

    assert response.description == "The Old Oak appears mature and healthy."
    assert response.confidence == 0.85
    assert not hasattr(response, "observer")
    assert not hasattr(response, "subject")
    assert not hasattr(response, "evidence")
