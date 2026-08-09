from collections.abc import MutableMapping
from typing import cast

import pytest

from living_world.core.observation import Observation


def make_observation() -> Observation:
    return Observation(
        id="observation_000001",
        tick=42,
        observer="entity_000001",
        subject="entity_000002",
        description="The oak appears mature and healthy.",
        confidence=0.91,
        evidence={
            "growth": 87,
            "health": 92,
            "wood": 120,
        },
        metadata={
            "perception_type": "visual",
            "engine": "deterministic",
        },
    )


def test_observation_stores_expected_values() -> None:
    observation = make_observation()

    assert observation.id == "observation_000001"
    assert observation.tick == 42
    assert observation.observer == "entity_000001"
    assert observation.subject == "entity_000002"
    assert observation.description == "The oak appears mature and healthy."
    assert observation.confidence == 0.91

    assert observation.evidence["growth"] == 87
    assert observation.evidence["health"] == 92
    assert observation.evidence["wood"] == 120

    assert observation.metadata["perception_type"] == "visual"
    assert observation.metadata["engine"] == "deterministic"


def test_observation_is_immutable() -> None:
    observation = make_observation()

    with pytest.raises(AttributeError):
        observation.description = "Something else"


def test_observation_evidence_is_immutable() -> None:
    observation = make_observation()

    with pytest.raises(TypeError):
        evidence = cast(MutableMapping[str, object], observation.evidence)
        evidence["growth"] = 100


def test_observation_metadata_is_immutable() -> None:
    observation = make_observation()

    with pytest.raises(TypeError):
        metadata = cast(MutableMapping[str, object], observation.metadata)
        metadata["engine"] = "llm"
