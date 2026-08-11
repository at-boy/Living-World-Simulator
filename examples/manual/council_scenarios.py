"""Typed, manual-only scenarios shared by the local council examples."""

from __future__ import annotations

from dataclasses import dataclass

from living_world.cognition.npc_cognition_client import ActionOption


@dataclass(frozen=True)
class CouncilParticipant:
    """One opaque-ID participant and their NPC-visible self-knowledge."""

    identifier: str
    name: str
    self_knowledge: str


@dataclass(frozen=True)
class ManualCouncilScenario:
    """Immutable input data for an opt-in manual council run."""

    name: str
    organization_id: str
    organization_name: str
    participants: tuple[CouncilParticipant, ...]
    agenda: str
    actions: tuple[ActionOption, ...]
    max_rounds: int
    turn_order_offset: int

    @property
    def participant_ids(self) -> tuple[str, ...]:
        """Return opaque participant identifiers in deterministic call order."""

        return tuple(participant.identifier for participant in self.participants)


JOURNEY = ManualCouncilScenario(
    name="journey",
    organization_id="organization_301",
    organization_name="Council",
    participants=(
        CouncilParticipant(
            "entity_401", "Aster", "I favour careful preparation before travel."
        ),
        CouncilParticipant(
            "entity_402", "Bryn", "I favour a swift route while daylight lasts."
        ),
        CouncilParticipant(
            "entity_403", "Cato", "I favour conserving supplies for later."
        ),
        CouncilParticipant(
            "entity_404",
            "Dara",
            "I favour preparing first so every concern can shape the plan.",
        ),
        CouncilParticipant(
            "entity_405",
            "Eris",
            "I favour the bold daybreak route that benefits the settlement.",
        ),
    ),
    agenda="how the settlement should approach a necessary risky journey",
    actions=(
        ActionOption(
            "prepare_then_travel", "Prepare supplies before taking the journey."
        ),
        ActionOption("travel_at_daybreak", "Take the quickest route at daybreak."),
        ActionOption("postpone_journey", "Postpone the journey and conserve supplies."),
    ),
    max_rounds=15,
    turn_order_offset=2,
)

SETTLEMENT = ManualCouncilScenario(
    name="settlement",
    organization_id="organization_302",
    organization_name="Town Council",
    participants=(
        CouncilParticipant(
            "entity_411",
            "Alma",
            "I was appointed only to coordinate this meeting; I do not own the issue "
            "or speak for everyone.",
        ),
        CouncilParticipant(
            "entity_412", "Bo", "I want reliable access while repairs are considered."
        ),
        CouncilParticipant(
            "entity_413", "Cyra", "I worry that a rushed repair will waste materials."
        ),
        CouncilParticipant(
            "entity_414", "Davi", "I favour sharing the immediate burden fairly."
        ),
        CouncilParticipant(
            "entity_415", "Enid", "I want a durable response to the shared condition."
        ),
    ),
    agenda=(
        "A visible failure in the settlement's public well requires a decision by "
        "the council. Alma was appointed only to coordinate the meeting; the shared "
        "condition was not introduced by Alma, and no action has unanimous support."
    ),
    actions=(
        ActionOption(
            "repair_well_now", "Organize an immediate repair using available materials."
        ),
        ActionOption(
            "secure_water_first",
            "Establish temporary water deliveries before scheduling repairs.",
        ),
        ActionOption(
            "inspect_then_repair",
            "Inspect the failure first and prepare a staged repair plan.",
        ),
    ),
    max_rounds=20,
    turn_order_offset=3,
)

SCENARIOS: tuple[ManualCouncilScenario, ...] = (JOURNEY, SETTLEMENT)
SCENARIO_NAMES: tuple[str, ...] = tuple(scenario.name for scenario in SCENARIOS)
DEFAULT_SCENARIO_NAME = JOURNEY.name


def get_scenario(name: str) -> ManualCouncilScenario:
    """Select a named scenario deterministically without provider access."""

    for scenario in SCENARIOS:
        if scenario.name == name:
            return scenario
    raise ValueError(f"Unknown manual council scenario: {name}")
