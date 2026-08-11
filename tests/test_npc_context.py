import pytest

from living_world.cognition.npc_context import NPCContextAssembler
from living_world.cognition.retrieval import RetrievalQuery
from living_world.core.entity import Entity
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.observation import Observation
from living_world.state.world_state import WorldState


class RecordingPerceptionBoundary:
    def __init__(self) -> None:
        self.contexts: list[object] = []

    def visible_description(
        self,
        observation: Observation,
        *,
        context: object | None = None,
    ) -> str:
        self.contexts.append(context)
        return observation.description


def make_state() -> WorldState:
    state = WorldState()
    state.entities["npc_1"] = Entity(
        id="npc_1",
        definition_key="npc",
        name="Erik",
        attributes={"woodcraft": 80},
    )
    state.entities["npc_2"] = Entity(
        id="npc_2",
        definition_key="npc",
        name="Mira",
        attributes={},
    )
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="tree_1",
        description="The old oak looks healthy.",
        confidence=0.8,
        evidence={"health": 92},
        metadata={},
    )
    state.observations["observation_2"] = Observation(
        id="observation_2",
        tick=3,
        observer="npc_2",
        subject="tree_1",
        description="Another NPC's perception.",
        confidence=0.8,
        evidence={},
        metadata={},
    )
    state.memories["memory_1"] = Memory(
        id="memory_1",
        tick=3,
        holder_id="npc_1",
        subject_id="tree_1",
        summary="I remember the old oak seemed sturdy.",
        salience=CognitiveSalience(importance=0.8, is_core=True),
    )
    return state


def test_assembler_returns_only_holder_scoped_npc_context() -> None:
    context = NPCContextAssembler(make_state()).assemble(
        holder_id="npc_1",
        capability_descriptions=("I know how to judge timber.",),
    )

    assert context.identity == "Erik"
    assert context.self_knowledge == ("I know how to judge timber.",)
    assert context.current_perceptions == ("The old oak looks healthy.",)
    assert tuple(item.text for item in context.core_cognition) == (
        "I remember the old oak seemed sturdy.",
    )
    assert context.retrieved_information == ()
    assert not hasattr(context, "holder_id")


def test_assembler_rejects_unknown_or_mismatched_holder() -> None:
    assembler = NPCContextAssembler(make_state())

    with pytest.raises(ValueError, match="known entity"):
        assembler.assemble(holder_id="unknown", capability_descriptions=())
    with pytest.raises(ValueError, match="must match"):
        assembler.assemble(
            holder_id="npc_1",
            query=RetrievalQuery(holder_id="npc_2", topic="oak"),
        )


def test_assembler_requires_prose_capabilities_and_applies_perception_limit() -> None:
    assembler = NPCContextAssembler(make_state())

    with pytest.raises(TypeError, match="tuple"):
        assembler.assemble(holder_id="npc_1", capability_descriptions=["prose"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="empty prose"):
        assembler.assemble(holder_id="npc_1", capability_descriptions=("",))

    context = assembler.assemble(
        holder_id="npc_1",
        capability_descriptions=("I work with timber.",),
        max_perceptions=0,
    )

    assert context.current_perceptions == ()


def test_assembler_projects_perceptions_without_engine_context_or_evidence() -> None:
    boundary = RecordingPerceptionBoundary()
    state = make_state()

    context = NPCContextAssembler(
        state,
        perception_boundary=boundary,
    ).assemble(holder_id="npc_1")

    assert context.current_perceptions == ("The old oak looks healthy.",)
    assert boundary.contexts == [None]
    assert "92" not in context.current_perceptions[0]


def test_assembler_rejects_unsafe_direct_observation_descriptions() -> None:
    state = make_state()
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="tree_1",
        description="The oak has wood=120.",
        confidence=0.8,
        evidence={"wood": 120},
        metadata={},
    )

    with pytest.raises(ValueError, match="raw attribute"):
        NPCContextAssembler(state).assemble(holder_id="npc_1")


def test_assembler_includes_only_validated_conversation_history() -> None:
    state = make_state()
    assembler = NPCContextAssembler(state)

    context = assembler.assemble(
        holder_id="npc_1",
        conversation_history=("Conversation topic: the old oak.", "It seems calm."),
    )

    assert context.conversation_history == (
        "Conversation topic: the old oak.",
        "It seems calm.",
    )
    with pytest.raises(ValueError, match="internal IDs"):
        assembler.assemble(
            holder_id="npc_1",
            conversation_history=("I saw observation_1.",),
        )
    with pytest.raises(ValueError, match="numeric values"):
        assembler.assemble(
            holder_id="npc_1",
            conversation_history=("The skill is 80.",),
        )
