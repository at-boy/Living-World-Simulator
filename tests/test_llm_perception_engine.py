import pytest

from living_world.core.entity import Entity
from living_world.core.observation import Observation
from living_world.perception.llm_perception_client import (
    LLMPerceptionClientError,
    LLMPerceptionRequest,
    LLMPerceptionResponse,
)
from living_world.perception.llm_perception_engine import (
    LLMPerceptionEngine,
    LLMPerceptionFallbackError,
)
from living_world.perception.perception_context import PerceptionContext
from living_world.state.world_state import WorldState


class StubLLMPerceptionClient:
    provider_name = "stub"

    def __init__(self, response: LLMPerceptionResponse) -> None:
        self.response = response
        self.requests: list[LLMPerceptionRequest] = []

    def perceive(self, request: LLMPerceptionRequest) -> LLMPerceptionResponse:
        self.requests.append(request)
        return self.response


class FailingLLMPerceptionClient:
    provider_name = "stub"

    def perceive(self, request: LLMPerceptionRequest) -> LLMPerceptionResponse:
        raise LLMPerceptionClientError("The local model is unavailable.")


class StubFallbackEngine:
    def perceive(self, context: PerceptionContext) -> Observation:
        return Observation(
            id="",
            tick=context.tick,
            observer=context.observer.id,
            subject=context.subject.id,
            description="The Old Oak is a tree.",
            confidence=0.3,
            evidence={"fallback": True},
            metadata={"engine": "stub-fallback"},
        )


class FailingFallbackEngine:
    def perceive(self, context: PerceptionContext) -> Observation:
        raise RuntimeError("Fallback failure.")


def make_context() -> PerceptionContext:
    observer = Entity(
        id="entity_000001",
        definition_key="npc",
        name="Erik",
        attributes={},
        created_tick=0,
    )
    subject = Entity(
        id="entity_000002",
        definition_key="tree",
        name="Old Oak",
        attributes={"growth": 87, "health": 92, "wood": 120},
        created_tick=0,
    )

    return PerceptionContext(
        observer=observer,
        subject=subject,
        world_state=WorldState(),
        capabilities={"woodcraft": 80},
        relationships=(),
        tick=42,
    )


def test_produces_observation_from_valid_provider_response() -> None:
    client = StubLLMPerceptionClient(
        LLMPerceptionResponse(
            description="The Old Oak appears mature and healthy.",
            confidence=0.85,
        )
    )
    engine = LLMPerceptionEngine(client)

    observation = engine.perceive(make_context())

    assert observation.tick == 42
    assert observation.observer == "entity_000001"
    assert observation.subject == "entity_000002"
    assert observation.description == "The Old Oak appears mature and healthy."
    assert observation.confidence == 0.85
    assert observation.evidence == {
        "subject_attributes": {"growth": 87, "health": 92, "wood": 120},
        "observer_capabilities": {"woodcraft": 80},
    }
    assert observation.metadata == {
        "engine": "llm",
        "provider": "stub",
        "fallback_used": False,
    }


def test_client_receives_curated_data_not_runtime_objects_or_identifiers() -> None:
    client = StubLLMPerceptionClient(
        LLMPerceptionResponse(
            description="The Old Oak appears mature.",
            confidence=0.8,
        )
    )
    engine = LLMPerceptionEngine(client)

    engine.perceive(make_context())

    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.observer_name == "Erik"
    assert request.subject_name == "Old Oak"
    assert request.capabilities == {"woodcraft": 80}
    assert request.subject_attributes == {"growth": 87, "health": 92, "wood": 120}
    assert not hasattr(request, "world_state")
    assert not hasattr(request, "observer_id")
    assert not hasattr(request, "subject_id")


@pytest.mark.parametrize(
    "response",
    [
        LLMPerceptionResponse(description="", confidence=0.8),
        LLMPerceptionResponse(
            description="The Old Oak appears mature.", confidence=-0.1
        ),
        LLMPerceptionResponse(
            description="entity_000002 appears mature.",
            confidence=0.8,
        ),
        LLMPerceptionResponse(
            description="The Old Oak has 120 units of wood.",
            confidence=0.8,
        ),
    ],
)
def test_invalid_or_unsafe_provider_response_uses_fallback(
    response: LLMPerceptionResponse,
) -> None:
    client = StubLLMPerceptionClient(response)
    engine = LLMPerceptionEngine(client, fallback_engine=StubFallbackEngine())

    observation = engine.perceive(make_context())

    assert observation.description == "The Old Oak is a tree."
    assert observation.confidence == 0.3
    assert observation.evidence == {"fallback": True}
    assert observation.metadata == {
        "engine": "llm",
        "provider": "stub",
        "fallback_used": True,
        "failure": "invalid_response",
    }


def test_provider_failure_uses_fallback_without_leaking_error_details() -> None:
    engine = LLMPerceptionEngine(
        FailingLLMPerceptionClient(),
        fallback_engine=StubFallbackEngine(),
    )

    observation = engine.perceive(make_context())

    assert observation.description == "The Old Oak is a tree."
    assert observation.metadata == {
        "engine": "llm",
        "provider": "stub",
        "fallback_used": True,
        "failure": "provider_error",
    }
    assert "unavailable" not in str(observation.metadata)


def test_provider_failure_uses_deterministic_fallback_by_default() -> None:
    observation = LLMPerceptionEngine(FailingLLMPerceptionClient()).perceive(
        make_context()
    )

    assert observation.description == (
        "The Old Oak appears mature and healthy " "and looks suitable for harvesting."
    )
    assert observation.evidence["subject_attributes"] == {
        "growth": 87,
        "health": 92,
        "wood": 120,
    }
    assert observation.metadata == {
        "engine": "llm",
        "provider": "stub",
        "fallback_used": True,
        "failure": "provider_error",
    }


def test_raises_dedicated_error_when_fallback_cannot_produce_an_observation() -> None:
    engine = LLMPerceptionEngine(
        FailingLLMPerceptionClient(),
        fallback_engine=FailingFallbackEngine(),
    )

    with pytest.raises(
        LLMPerceptionFallbackError,
        match="deterministic fallback could not run",
    ):
        engine.perceive(make_context())
