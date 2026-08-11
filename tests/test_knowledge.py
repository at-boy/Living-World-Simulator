from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from living_world.core.knowledge import Knowledge
from living_world.core.memory import CognitiveSalience


def test_knowledge_is_immutable_and_defensively_freezes_metadata() -> None:
    metadata = {
        "heard_at": {"location": "the market"},
        "witnesses": ["miller"],
    }
    knowledge = Knowledge(
        id="knowledge_000001",
        tick=24,
        holder_id="npc_1",
        subject_id="east_bridge",
        statement="The east bridge is closed.",
        source_description="The miller told me.",
        salience=CognitiveSalience(importance=0.7),
        supporting_observations=("observation_000001",),
        supporting_memories=("memory_000001",),
        supporting_experiences=("experience_000001",),
        metadata=metadata,
    )
    metadata["heard_at"]["location"] = "somewhere else"
    metadata["witnesses"].append("traveller")

    assert knowledge.metadata == {
        "heard_at": {"location": "the market"},
        "witnesses": ("miller",),
    }
    with pytest.raises(FrozenInstanceError):
        knowledge.statement = "The bridge is open."
    with pytest.raises(TypeError):
        cast(MutableMapping[str, object], knowledge.metadata)["heard_at"] = "changed"
    with pytest.raises(TypeError):
        cast(MutableMapping[str, object], knowledge.metadata["heard_at"])[
            "location"
        ] = "changed"


@pytest.mark.parametrize(
    ("field_name", "value", "exception"),
    [
        ("holder_id", "", ValueError),
        ("subject_id", "", ValueError),
        ("statement", "", ValueError),
        ("source_description", "", ValueError),
        ("holder_id", 1, TypeError),
    ],
)
def test_knowledge_requires_non_empty_visible_text_and_identity(
    field_name: str,
    value: object,
    exception: type[Exception],
) -> None:
    values: dict[str, object] = {
        "id": "knowledge_000001",
        "tick": 24,
        "holder_id": "npc_1",
        "subject_id": "east_bridge",
        "statement": "The east bridge is closed.",
        "source_description": "The miller told me.",
        "salience": CognitiveSalience(importance=0.7),
    }
    values[field_name] = value

    with pytest.raises(exception):
        Knowledge(**values)  # type: ignore[arg-type]


def test_knowledge_keeps_internal_provenance_out_of_visible_attribution() -> None:
    knowledge = Knowledge(
        id="knowledge_000001",
        tick=24,
        holder_id="npc_1",
        subject_id="east_bridge",
        statement="The east bridge is closed.",
        source_description="The miller told me.",
        salience=CognitiveSalience(importance=0.7),
        supporting_observations=("observation_000001",),
    )

    assert knowledge.supporting_observations == ("observation_000001",)
    assert "observation_000001" not in knowledge.statement
    assert "observation_000001" not in knowledge.source_description


def test_knowledge_rejects_duplicate_or_non_tuple_provenance() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        Knowledge(
            id="knowledge_000001",
            tick=24,
            holder_id="npc_1",
            subject_id="east_bridge",
            statement="The east bridge is closed.",
            source_description="The miller told me.",
            salience=CognitiveSalience(importance=0.7),
            supporting_observations=("observation_000001", "observation_000001"),
        )
    with pytest.raises(TypeError, match="must be a tuple"):
        Knowledge(
            id="knowledge_000001",
            tick=24,
            holder_id="npc_1",
            subject_id="east_bridge",
            statement="The east bridge is closed.",
            source_description="The miller told me.",
            salience=CognitiveSalience(importance=0.7),
            supporting_observations="observation_000001",  # type: ignore[arg-type]
        )
    for invalid_provenance in (
        ["observation_000001"],
        {"observation_000001"},
    ):
        with pytest.raises(TypeError, match="must be a tuple"):
            Knowledge(
                id="knowledge_000001",
                tick=24,
                holder_id="npc_1",
                subject_id="east_bridge",
                statement="The east bridge is closed.",
                source_description="The miller told me.",
                salience=CognitiveSalience(importance=0.7),
                supporting_observations=invalid_provenance,  # type: ignore[arg-type]
            )


@pytest.mark.parametrize("field_name", ["statement", "source_description"])
def test_knowledge_rejects_provenance_identifiers_in_visible_text(
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "id": "knowledge_000001",
        "tick": 24,
        "holder_id": "npc_1",
        "subject_id": "east_bridge",
        "statement": "The east bridge is closed.",
        "source_description": "The miller told me.",
        "salience": CognitiveSalience(importance=0.7),
        "supporting_observations": ("observation_000001",),
    }
    values[field_name] = "This references observation_000001."

    with pytest.raises(ValueError, match="internal provenance"):
        Knowledge(**values)  # type: ignore[arg-type]
