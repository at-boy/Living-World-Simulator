from dataclasses import FrozenInstanceError

import pytest

from living_world.core.memory import CognitiveSalience, Memory


def test_cognitive_salience_distinguishes_important_from_core() -> None:
    important = CognitiveSalience(importance=0.6)
    core = CognitiveSalience(importance=0.8, is_core=True)

    assert important.is_important is True
    assert important.is_core is False
    assert core.is_important is True
    assert core.is_core is True


def test_cognitive_salience_rejects_invalid_core_threshold() -> None:
    with pytest.raises(ValueError, match="requires importance >= 0.8"):
        CognitiveSalience(importance=0.7, is_core=True)


def test_memory_is_immutable_and_holder_scoped() -> None:
    memory = Memory(
        id="memory_000001",
        tick=24,
        holder_id="npc_1",
        subject_id="tree_1",
        summary="I remember that the old oak looked healthy.",
        salience=CognitiveSalience(importance=0.8, is_core=True),
        source_observation_ids=("observation_000001",),
    )

    assert memory.holder_id == "npc_1"
    assert memory.source_observation_ids == ("observation_000001",)
    with pytest.raises(FrozenInstanceError):
        memory.summary = "changed"


def test_memory_rejects_duplicate_provenance() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        Memory(
            id="memory_000001",
            tick=24,
            holder_id="npc_1",
            subject_id="tree_1",
            summary="I remember the tree.",
            salience=CognitiveSalience(importance=0.5),
            source_observation_ids=("observation_000001", "observation_000001"),
        )


def test_memory_rejects_string_provenance() -> None:
    with pytest.raises(TypeError, match="must be a tuple"):
        Memory(
            id="memory_000001",
            tick=24,
            holder_id="npc_1",
            subject_id="tree_1",
            summary="I remember the tree.",
            salience=CognitiveSalience(importance=0.5),
            source_observation_ids="observation_000001",  # type: ignore[arg-type]
        )
