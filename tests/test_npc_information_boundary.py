import pytest

from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.retrieval import RetrievedCognition
from living_world.core.entity import Entity
from living_world.state.world_state import WorldState


def _context(text: str) -> NPCContext:
    return NPCContext(
        identity="Erik",
        self_knowledge=("I know timber.",),
        current_perceptions=(),
        core_cognition=(
            RetrievedCognition(
                kind="memory",
                text=text,
                importance=0.8,
                is_core=True,
            ),
        ),
        retrieved_information=(),
    )


def test_boundary_allows_qualitative_prose_even_when_attribute_name_matches() -> None:
    state = WorldState()
    state.entities["npc_1"] = Entity(
        id="npc_1",
        definition_key="npc",
        name="Erik",
        attributes={"woodcraft": 80, "health": 92},
    )

    NPCInformationBoundary(state).validate_context(
        _context("The oak looks healthy and my woodcraft is useful.")
    )


def test_boundary_rejects_internal_ids_and_authoritative_numbers() -> None:
    state = WorldState()
    state.entities["entity_000001"] = Entity(
        id="entity_000001",
        definition_key="tree",
        name="Old Oak",
        attributes={"wood": 120, "skills": {"woodcraft": 80}},
    )
    boundary = NPCInformationBoundary(state)

    with pytest.raises(ValueError, match="internal IDs"):
        boundary.validate_context(_context("I visited entity_000001 yesterday."))
    with pytest.raises(ValueError, match="numeric values"):
        boundary.validate_context(_context("The oak contains 120 pieces of timber."))
    with pytest.raises(ValueError, match="numeric values"):
        boundary.validate_context(_context("My skill is 80."))


def test_boundary_rejects_unsafe_conversation_history_directly() -> None:
    state = WorldState()
    state.entities["entity_000001"] = Entity(
        id="entity_000001",
        definition_key="tree",
        name="Old Oak",
        attributes={"wood": 120},
    )
    boundary = NPCInformationBoundary(state)

    internal_id_context = _context("A calm memory.")
    object.__setattr__(
        internal_id_context,
        "conversation_history",
        ("Erik: I visited entity_000001.",),
    )
    with pytest.raises(ValueError, match="internal IDs"):
        boundary.validate_context(internal_id_context)

    numeric_context = _context("A calm memory.")
    object.__setattr__(
        numeric_context,
        "conversation_history",
        ("Erik: The oak has 120 branches.",),
    )
    with pytest.raises(ValueError, match="numeric values"):
        boundary.validate_context(numeric_context)


def test_boundary_rejects_structural_engine_data() -> None:
    state = WorldState()
    context = _context("A calm memory.")
    object.__setattr__(context, "self_knowledge", ({"wood": 120},))

    with pytest.raises(TypeError, match="engine state or mappings"):
        NPCInformationBoundary(state).validate_context(context)


def test_boundary_rejects_world_state_substituted_for_npc_prose() -> None:
    state = WorldState()
    context = _context("A calm memory.")
    object.__setattr__(context, "identity", state)

    with pytest.raises(TypeError, match="engine state or mappings"):
        NPCInformationBoundary(state).validate_context(context)


def test_boundary_rejects_raw_numeric_skill_value_in_npc_prose() -> None:
    state = WorldState()
    state.entities["npc_1"] = Entity(
        id="npc_1",
        definition_key="npc",
        name="Erik",
        attributes={"skills": {"woodcraft": 80}},
    )

    with pytest.raises(ValueError, match="numeric values"):
        NPCInformationBoundary(state).validate_context(
            _context("My woodcraft skill is 80.")
        )


def test_boundary_rejects_consequence_ids_and_numbers_and_allows_fixed_prose() -> None:
    from living_world.needs import ConsumptionPolicy, ConsumptionState

    state = WorldState()
    state.consumption_policies["consumption_town"] = ConsumptionPolicy(
        "consumption_town", "town", 7, 1
    )
    state.consumption_states["consumption_town"] = ConsumptionState("consumption_town")
    boundary = NPCInformationBoundary(state)
    with pytest.raises(ValueError, match="internal IDs"):
        boundary.validate_context(_context("The policy is consumption_town."))
    with pytest.raises(ValueError, match="numeric values"):
        boundary.validate_context(_context("The hidden rate is 7."))
    boundary.validate_context(_context("Food and water use is currently supplied."))


def test_boundary_rejects_work_ids_and_authoritative_numbers() -> None:
    from living_world.work import (
        ResourceWorkTarget,
        WorkCategory,
        WorkDefinition,
        WorkState,
    )

    state = WorldState()
    definition = WorkDefinition(
        "work_000001",
        WorkCategory.PRODUCE_FOOD,
        ResourceWorkTarget("food", 17),
        "Plant crops",
        "settlement",
        "objective",
        "location",
        (),
        0,
        (),
        (),
        23,
        4,
        None,
        0,
    )
    state.work_definitions[definition.id] = definition
    state.work_states[definition.id] = WorkState(definition.id)
    boundary = NPCInformationBoundary(state)
    with pytest.raises(ValueError, match="internal IDs"):
        boundary.validate_context(_context("Review work_000001."))
    with pytest.raises(ValueError, match="numeric values"):
        boundary.validate_context(_context("Progress requires 23."))
