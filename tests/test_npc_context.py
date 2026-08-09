from living_world.cognition.npc_context import NPCContextAssembler
from living_world.core.belief import Belief, BeliefStatus
from living_world.core.entity import Entity
from living_world.core.experience import Experience
from living_world.core.observation import Observation
from living_world.state.world_state import WorldState


def make_state() -> WorldState:
    world = WorldState(tick=42)

    world.entities["entity_000001"] = Entity(
        id="entity_000001",
        definition_key="npc",
        name="Erik",
        attributes={"role": "woodcutter"},
        created_tick=0,
    )
    world.entities["entity_000002"] = Entity(
        id="entity_000002",
        definition_key="tree",
        name="Old Oak",
        attributes={
            "growth": 87,
            "health": 92,
            "wood": 120,
        },
        created_tick=0,
    )

    world.observations["observation_000001"] = Observation(
        id="observation_000001",
        tick=42,
        observer="entity_000001",
        subject="entity_000002",
        description="The Old Oak appears mature and healthy.",
        confidence=0.9,
        evidence={"subject_attributes": {"growth": 87, "health": 92}},
        metadata={"source": "perception"},
    )

    world.observations["observation_000002"] = Observation(
        id="observation_000002",
        tick=43,
        observer="entity_000003",
        subject="entity_000002",
        description="The Old Oak is a tree.",
        confidence=0.4,
        evidence={"subject_attributes": {"growth": 30}},
        metadata={"source": "perception"},
    )

    world.beliefs["belief_000001"] = Belief(
        id="belief_000001",
        tick=42,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The Old Oak is suitable for harvesting.",
        confidence=0.88,
        importance=0.8,
        status=BeliefStatus.IMPORTANT,
        supporting_observations=("observation_000001",),
    )

    world.experiences["experience_000001"] = Experience(
        id="experience_000001",
        tick=42,
        holder_id="entity_000001",
        subject_id="entity_000002",
        summary="The grove provides strong timber after a dry season.",
        supporting_observations=("observation_000001",),
    )

    return world


def test_npc_context_uses_only_npc_accessible_information() -> None:
    assembler = NPCContextAssembler(make_state())

    context = assembler.assemble(
        holder_id="entity_000001",
        capabilities={"woodcraft": 80},
    )

    assert context.holder_id == "entity_000001"
    assert context.identity == "Erik"
    assert context.capabilities == {"woodcraft": 80}
    assert context.current_perceptions == ("The Old Oak appears mature and healthy.",)
    assert context.retrieved_information == (
        "The Old Oak appears mature and healthy.",
        "The Old Oak is suitable for harvesting.",
        "The grove provides strong timber after a dry season.",
    )


def test_npc_context_excludes_raw_world_truth() -> None:
    assembler = NPCContextAssembler(make_state())

    context = assembler.assemble(
        holder_id="entity_000001",
        capabilities={"woodcraft": 80},
    )

    joined = "\n".join(context.retrieved_information)

    assert "growth=" not in joined
    assert "health=" not in joined
    assert "wood=" not in joined
    assert "87" not in joined
    assert "92" not in joined
    assert "120" not in joined
    assert "entity_000002" not in joined
    assert "WorldState" not in context.retrieved_information
