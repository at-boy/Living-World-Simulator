from living_world.core.belief import BeliefStatus
from living_world.managers.belief_manager import BeliefManager
from living_world.managers.experience_manager import ExperienceManager
from living_world.state.world_state import WorldState


def main() -> None:
    state = WorldState(tick=20)
    experience_manager = ExperienceManager(state)
    belief_manager = BeliefManager(state)

    repeated_observations = (
        "observation_000001",
        "observation_000002",
        "observation_000003",
    )

    experience = experience_manager.consolidate_repeated_observations(
        holder_id="entity_000001",
        subject_id="entity_000002",
        observations=repeated_observations,
        threshold=2,
        summary="The western path becomes treacherous in the wet season and requires caution.",
        supporting_memories=("memory_000001",),
        supporting_beliefs=("belief_000001",),
        metadata={"source": "cognitive_consolidation"},
    )

    belief = belief_manager.record_from_experience(
        experience=experience,
        proposition="The western path becomes treacherous in wet weather.",
        confidence=0.81,
        importance=0.7,
        status=BeliefStatus.ACTIVE,
    )

    recorded_experience = experience_manager.get(experience.id)
    if recorded_experience is None:
        raise RuntimeError("Expected generated experience to be recorded in the world state.")

    print("Experience")
    print(f"ID: {experience.id}")
    print(f"Holder: {experience.holder_id}")
    print(f"Subject: {experience.subject_id}")
    print(f"Summary: {experience.summary}")
    print(f"Observation support: {experience.supporting_observations}")
    print(f"Memory support: {experience.supporting_memories}")
    print(f"Belief support: {experience.supporting_beliefs}")

    print()
    print("Belief created from this experience")
    print(f"ID: {belief.id}")
    print(f"Proposition: {belief.proposition}")
    print(f"Confidence: {belief.confidence}")
    print(f"Supporting experiences: {belief.supporting_experiences}")

    print()
    print("Recorded Experiences")
    for recorded in experience_manager.all():
        print(
            recorded.id,
            recorded.holder_id,
            "->",
            recorded.subject_id,
            recorded.summary,
        )

    print()
    print("This is a lived-interaction experience created from repeated observations.")
    print("A belief can then be formed from that experience while retaining the source link.")


if __name__ == "__main__":
    main()
