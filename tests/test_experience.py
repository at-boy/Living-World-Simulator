import pytest

from living_world.core.experience import Experience, ExperienceHistoryEntry


def test_experience_is_created_with_supporting_links() -> None:
    experience = Experience(
        id="experience_000001",
        tick=42,
        holder_id="entity_000001",
        subject_id="entity_000002",
        summary="The oak near the mill was mature and useful for building.",
        supporting_observations=("observation_000001", "observation_000003"),
        supporting_memories=("memory_000001",),
        supporting_beliefs=("belief_000001",),
        metadata={"source": "repeated_observation"},
    )

    assert experience.id == "experience_000001"
    assert experience.holder_id == "entity_000001"
    assert experience.subject_id == "entity_000002"
    assert (
        experience.summary
        == "The oak near the mill was mature and useful for building."
    )
    assert experience.supporting_observations == (
        "observation_000001",
        "observation_000003",
    )
    assert experience.supporting_memories == ("memory_000001",)
    assert experience.supporting_beliefs == ("belief_000001",)
    assert experience.metadata["source"] == "repeated_observation"


def test_experience_rejects_empty_holder() -> None:
    with pytest.raises(ValueError, match="Experience holder_id cannot be empty."):
        Experience(
            id="experience_000001",
            tick=1,
            holder_id="",
            subject_id="entity_000002",
            summary="The path was muddy after rain.",
        )


def test_experience_history_entry_tracks_change() -> None:
    original = Experience(
        id="experience_000001",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        summary="The path was muddy after rain.",
    )

    revised = original.update(
        tick=2,
        reason="Repeated trips showed the path stayed impassable in the wet season.",
        new_summary="The path remains difficult during the wet season and requires caution.",
    )

    assert isinstance(revised.history[0], ExperienceHistoryEntry)
    assert revised.history[0].tick == 2
    assert (
        revised.history[0].reason
        == "Repeated trips showed the path stayed impassable in the wet season."
    )
    assert (
        revised.summary
        == "The path remains difficult during the wet season and requires caution."
    )
    assert revised.history[0].old_summary == "The path was muddy after rain."
    assert (
        revised.history[0].new_summary
        == "The path remains difficult during the wet season and requires caution."
    )
