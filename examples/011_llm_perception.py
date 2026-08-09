from living_world.core.entity import Entity
from living_world.perception.llm_perception_client import (
    LLMPerceptionRequest,
    LLMPerceptionResponse,
)
from living_world.perception.llm_perception_engine import LLMPerceptionEngine
from living_world.perception.perception_context import PerceptionContext
from living_world.state.world_state import WorldState


class ExampleLocalPerceptionClient:
    """Stand-in for a future Ollama or llama.cpp HTTP adapter."""

    provider_name = "example-local"

    def perceive(self, request: LLMPerceptionRequest) -> LLMPerceptionResponse:
        return LLMPerceptionResponse(
            description=(f"The {request.subject_name} appears mature and healthy."),
            confidence=0.85,
        )


def main() -> None:
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
    context = PerceptionContext(
        observer=observer,
        subject=subject,
        world_state=WorldState(),
        capabilities={"woodcraft": 80},
        relationships=(),
        tick=42,
    )

    observation = LLMPerceptionEngine(ExampleLocalPerceptionClient()).perceive(context)

    print("LLM Perception")
    print(f"Description: {observation.description}")
    print(f"Confidence: {observation.confidence}")
    print(f"Metadata: {observation.metadata}")


if __name__ == "__main__":
    main()
