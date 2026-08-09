"""Run a real local llama.cpp perception request.

Start llama-server as described in docs/local_llm_setup.md first. This manual
example is intentionally not part of ``make examples``.
"""

from living_world.core.entity import Entity
from living_world.perception.llama_cpp_perception_client import (
    LlamaCppPerceptionClient,
)
from living_world.perception.llm_perception_engine import LLMPerceptionEngine
from living_world.perception.perception_context import PerceptionContext
from living_world.state.world_state import WorldState


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
    client = LlamaCppPerceptionClient(model="qwen3-4b-q4-k-m")

    observation = LLMPerceptionEngine(client).perceive(context)

    if observation.metadata["fallback_used"]:
        raise SystemExit(
            "llama.cpp did not produce a valid perception "
            f"({observation.metadata['failure']})."
        )

    print(observation.description)
    print(f"Confidence: {observation.confidence}")
    print(observation.metadata)


if __name__ == "__main__":
    main()
