import pytest

from living_world.cognition.npc_context import NPCContextAssembler
from living_world.cognition.retrieval import RetrievalQuery
from living_world.core.entity import Entity
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.observation import Observation
from living_world.needs import (
    NeedAssessment,
    NeedDefinition,
    NeedKind,
    NeedLevel,
    NeedState,
)
from living_world.spatial import Bounds, BoundsKind, Placement, Point
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


@pytest.mark.parametrize(
    "description",
    (
        "The well is at 47, 83.",
        "The well is 47 steps east.",
        "The well is at x 47.0 and y 83.00.",
    ),
)
def test_assembler_revalidates_stored_spatial_observations(
    description: str,
) -> None:
    state = make_state()
    state.placements["npc_1"] = Placement("npc_1", Point(47, 83))
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="well_1",
        description=description,
        confidence=0.8,
        evidence={},
        metadata={},
    )

    with pytest.raises(ValueError):
        NPCContextAssembler(state).assemble(holder_id="npc_1")


def test_assembler_keeps_spatial_observations_holder_scoped() -> None:
    state = make_state()
    state.placements["npc_1"] = Placement("npc_1", Point(47, 83))
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="well_1",
        description="The well is north-east of Erik.",
        confidence=1.0,
        evidence={"spatial_relations": ("north_east",)},
        metadata={"engine": "spatial_perception"},
    )

    erik = NPCContextAssembler(state).assemble(holder_id="npc_1")
    mira = NPCContextAssembler(state).assemble(holder_id="npc_2")

    assert erik.current_perceptions == ("The well is north-east of Erik.",)
    assert mira.current_perceptions == ("Another NPC's perception.",)
    assert "spatial_relations" not in erik.current_perceptions[0]


def test_assembler_numeric_equivalence_preserves_token_boundaries() -> None:
    state = make_state()
    state.placements["npc_1"] = Placement("npc_1", Point(47, 83))
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="route_1",
        description="Route47.0 remains open.",
        confidence=0.8,
        evidence={},
        metadata={},
    )

    context = NPCContextAssembler(state).assemble(holder_id="npc_1")

    assert context.current_perceptions == ("Route47.0 remains open.",)


@pytest.mark.parametrize(
    "description",
    (
        "The well is at x-47.0 and y-83.0.",
        "The well is at x-4.7e1 and y-8.3e1.",
    ),
)
def test_assembler_rejects_stored_attached_signed_coordinate_equivalents(
    description: str,
) -> None:
    state = make_state()
    state.placements["npc_1"] = Placement("npc_1", Point(-47, -83))
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="well_1",
        description=description,
        confidence=0.8,
        evidence={},
        metadata={},
    )

    with pytest.raises(ValueError, match="coordinate notation"):
        NPCContextAssembler(state).assemble(holder_id="npc_1")


@pytest.mark.parametrize(
    "description",
    (
        "The width+20.0 is known.",
        "The height+3e1 is known.",
    ),
)
def test_assembler_rejects_stored_attached_signed_dimension_equivalents(
    description: str,
) -> None:
    state = make_state()
    state.placements["npc_1"] = Placement(
        "npc_1",
        Bounds(40, 80, 20, 30),
        bounds_kind=BoundsKind.STRUCTURE,
    )
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="well_1",
        description=description,
        confidence=0.8,
        evidence={},
        metadata={},
    )

    with pytest.raises(ValueError, match="coordinate notation"):
        NPCContextAssembler(state).assemble(holder_id="npc_1")


@pytest.mark.parametrize(
    "description",
    (
        "The well is at x47.0 and y8.3e1.",
        "The width20.0 and height3e1 are known.",
    ),
)
def test_assembler_rejects_stored_attached_unsigned_spatial_equivalents(
    description: str,
) -> None:
    state = make_state()
    state.placements["npc_1"] = Placement(
        "npc_1",
        Bounds(47, 83, 20, 30),
        bounds_kind=BoundsKind.STRUCTURE,
    )
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="well_1",
        description=description,
        confidence=0.8,
        evidence={},
        metadata={},
    )

    with pytest.raises(ValueError, match="coordinate notation"):
        NPCContextAssembler(state).assemble(holder_id="npc_1")


@pytest.mark.parametrize(
    "description",
    ("The record need_food changed.", "Pressure is 0.25.", "Pressure0.25 remains."),
)
def test_assembler_rejects_need_ids_and_authoritative_numbers(description: str) -> None:
    state = make_state()
    definition = NeedDefinition("need_food", "npc_1", NeedKind.FOOD, 2, 0.25, 0.5, 3)
    assessment = NeedAssessment(2, NeedLevel.CRITICAL, 1, 4, -3, 0.75)
    state.need_definitions[definition.id] = definition
    state.need_states[definition.id] = NeedState(
        definition.id, assessment, (assessment,)
    )
    state.observations["observation_1"] = Observation(
        id="observation_1",
        tick=2,
        observer="npc_1",
        subject="tree_1",
        description=description,
        confidence=0.8,
        evidence={},
        metadata={},
    )

    with pytest.raises(ValueError, match="internal IDs|numeric values"):
        NPCContextAssembler(state).assemble(holder_id="npc_1")


def test_assembler_does_not_auto_inject_consequence_interpretations() -> None:
    from living_world.needs import ConsumptionPolicy, ConsumptionState

    state = make_state()
    state.consumption_policies["consumption_town"] = ConsumptionPolicy(
        "consumption_town", "npc_1", 1, 1
    )
    state.consumption_states["consumption_town"] = ConsumptionState("consumption_town")
    context = NPCContextAssembler(state).assemble(holder_id="npc_1")
    assert "consumption_town" not in repr(context)
    assert "Food and water use" not in repr(context)
