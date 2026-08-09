from living_world.core.belief import BeliefStatus
from living_world.managers.belief_manager import BeliefManager
from living_world.managers.experience_manager import ExperienceManager
from living_world.state.world_state import WorldState


def test_record_creates_and_registers_experience() -> None:
    state = WorldState(tick=11)
    manager = ExperienceManager(state)

    experience = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        summary="The miller was patient and reliable during the harvest.",
        supporting_observations=("observation_000001",),
        supporting_memories=("memory_000001",),
        supporting_beliefs=("belief_000001",),
        metadata={"source": "manual"},
    )

    assert experience.id == "experience_000001"
    assert experience.tick == 11
    assert manager.get("experience_000001") is experience
    assert state.experiences["experience_000001"] is experience


def test_experiences_for_returns_holder_history() -> None:
    manager = ExperienceManager(WorldState())

    first = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        summary="The path became slick after rain.",
    )
    second = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000003",
        summary="The mill was quieter during the off-season.",
    )

    assert manager.experiences_for("entity_000001") == (first, second)


def test_experiences_about_returns_subject_history() -> None:
    manager = ExperienceManager(WorldState())

    first = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        summary="The path became slick after rain.",
    )
    second = manager.record(
        holder_id="entity_000003",
        subject_id="entity_000002",
        summary="The path stayed crowded near evening.",
    )

    assert manager.experiences_about("entity_000002") == (first, second)


def test_experience_links_supporting_beliefs() -> None:
    manager = ExperienceManager(WorldState())

    experience = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        summary="The path was treacherous at dusk.",
        supporting_beliefs=("belief_000001", "belief_000002"),
    )

    assert experience.supporting_beliefs == ("belief_000001", "belief_000002")
    assert manager.experiences_supporting_belief("belief_000002") == (experience,)


def test_generate_from_observations_creates_experience() -> None:
    manager = ExperienceManager(WorldState(tick=15))

    experience = manager.generate_from_observations(
        holder_id="entity_000001",
        subject_id="entity_000002",
        observations=("observation_000001", "observation_000002", "observation_000003"),
        summary="The path was consistently dangerous in the wet season.",
        supporting_memories=("memory_000001",),
        supporting_beliefs=("belief_000001",),
        metadata={"source": "consolidation"},
    )

    assert experience.id == "experience_000001"
    assert experience.tick == 15
    assert experience.supporting_observations == (
        "observation_000001",
        "observation_000002",
        "observation_000003",
    )
    assert experience.supporting_memories == ("memory_000001",)
    assert experience.supporting_beliefs == ("belief_000001",)
    assert manager.get("experience_000001") is experience


def test_belief_manager_can_create_candidate_from_experience() -> None:
    experience_manager = ExperienceManager(WorldState(tick=21))
    belief_manager = BeliefManager(WorldState(tick=21))

    experience = experience_manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        summary="The western path is dangerous in wet weather.",
        supporting_observations=("observation_000001", "observation_000002"),
    )

    belief = belief_manager.record_from_experience(
        experience=experience,
        proposition="The western path becomes treacherous in wet weather.",
        confidence=0.81,
        importance=0.7,
        status=BeliefStatus.ACTIVE,
    )

    assert belief.id == "belief_000001"
    assert belief.supporting_experiences == (experience.id,)
    assert belief.subject_id == experience.subject_id
    assert belief.holder_id == experience.holder_id
    assert belief_manager.get("belief_000001") is belief


def test_consolidate_repeated_observations_creates_summary_when_threshold_is_met() -> (
    None
):
    manager = ExperienceManager(WorldState(tick=21))

    experience = manager.consolidate_repeated_observations(
        holder_id="entity_000001",
        subject_id="entity_000002",
        observations=(
            "observation_000001",
            "observation_000002",
            "observation_000003",
        ),
        threshold=2,
    )

    assert experience.id == "experience_000001"
    assert experience.tick == 21
    assert experience.supporting_observations == (
        "observation_000001",
        "observation_000002",
        "observation_000003",
    )
    assert "Repeated observations" in experience.summary
    assert "entity_000002" in experience.summary
