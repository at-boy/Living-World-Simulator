"""Typed, manual-only scenarios shared by the local council examples."""

from __future__ import annotations

from dataclasses import dataclass

from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.retrieval import (
    CognitiveRetriever,
    DeterministicCognitiveRetriever,
    RetrievalQuery,
    RetrievedCognition,
)
from living_world.core.definition import Definition
from living_world.core.memory import CognitiveSalience
from living_world.simulation.simulation_engine import SimulationEngine


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


@dataclass(frozen=True)
class PreparedCouncilRuntime:
    """Manager-created runtime state and opaque IDs for one manual council."""

    engine: SimulationEngine
    organization_id: str
    participant_ids: tuple[str, ...]
    participant_self_knowledge: dict[str, tuple[str, ...]]
    cognitive_retriever: CognitiveRetriever | None


@dataclass(frozen=True)
class _ManualTopicRetriever:
    """Apply a scenario topic through the production retrieval protocol."""

    retriever: CognitiveRetriever
    topic: str

    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievedCognition, ...]:
        return self.retriever.retrieve(
            RetrievalQuery(
                holder_id=query.holder_id,
                topic=self.topic if query.topic is None else query.topic,
                limit=query.limit,
            )
        )


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

OPPOSING_INTERESTS = ManualCouncilScenario(
    name="opposing-interests",
    organization_id="organization_303",
    organization_name="Town Council",
    participants=(
        CouncilParticipant(
            "entity_421",
            "Fara",
            "I work with the riverside traders, who need dependable wagon access "
            "to the market.",
        ),
        CouncilParticipant(
            "entity_422",
            "Galen",
            "I belong to the hillside growers, who want scarce communal labour "
            "kept available for the coming harvest.",
        ),
        CouncilParticipant(
            "entity_423",
            "Hesta",
            "I trade produce from the hillside growers at the riverside market, "
            "so both reliable access and harvest readiness matter to me.",
        ),
        CouncilParticipant(
            "entity_424",
            "Ivo",
            "I work with the riverside carriers and favour repairing the damaged "
            "market road before trade is disrupted further.",
        ),
        CouncilParticipant(
            "entity_425",
            "Jora",
            "I am an independent healer who needs market deliveries but worries "
            "about exhausting the town's workers before harvest.",
        ),
    ),
    agenda=(
        "The damaged market road is slowing riverside trade while the hillside "
        "growers need communal labour for the approaching harvest. The council "
        "must choose how the town should balance these opposed and overlapping "
        "interests; no group has special voting authority."
    ),
    actions=(
        ActionOption(
            "repair_market_road_now",
            "Commit communal labour to repair the market road immediately.",
        ),
        ActionOption(
            "prioritize_harvest",
            "Keep communal labour on harvest preparations and defer the road repair.",
        ),
        ActionOption(
            "split_work_crews",
            "Divide available work crews between a limited road repair and harvest preparations.",
        ),
    ),
    max_rounds=20,
    turn_order_offset=1,
)

COGNITION_SHAPED = ManualCouncilScenario(
    name="cognition-shaped",
    organization_id="organization_304",
    organization_name="Town Council",
    participants=(
        CouncilParticipant(
            "entity_431", "Nessa", "I maintain shared buildings for the town."
        ),
        CouncilParticipant(
            "entity_432", "Orin", "I coordinate water deliveries between households."
        ),
        CouncilParticipant(
            "entity_433", "Pella", "I account for the town's repair materials."
        ),
        CouncilParticipant(
            "entity_434", "Quin", "I carry urgent goods along the well road."
        ),
        CouncilParticipant(
            "entity_435", "Rhea", "I help neighbours organize shared work."
        ),
    ),
    agenda=(
        "The public well is failing and the council must choose a response. Each "
        "member may weigh the same condition and choices differently."
    ),
    actions=(
        ActionOption(
            "repair_well_now", "Organize an immediate repair with available materials."
        ),
        ActionOption(
            "secure_water_first",
            "Establish temporary water deliveries before beginning repairs.",
        ),
        ActionOption(
            "inspect_then_repair", "Inspect the failure and prepare a staged repair."
        ),
    ),
    max_rounds=20,
    turn_order_offset=4,
)

SCENARIOS: tuple[ManualCouncilScenario, ...] = (
    JOURNEY,
    SETTLEMENT,
    OPPOSING_INTERESTS,
    COGNITION_SHAPED,
)
SCENARIO_NAMES: tuple[str, ...] = tuple(scenario.name for scenario in SCENARIOS)
DEFAULT_SCENARIO_NAME = JOURNEY.name


def get_scenario(name: str) -> ManualCouncilScenario:
    """Select a named scenario deterministically without provider access."""

    for scenario in SCENARIOS:
        if scenario.name == name:
            return scenario
    raise ValueError(f"Unknown manual council scenario: {name}")


def prepare_council_runtime(
    scenario: ManualCouncilScenario,
) -> PreparedCouncilRuntime:
    """Create one scenario solely through manager-owned runtime lifecycles."""

    engine = SimulationEngine()
    engine.definitions.register_many(
        (Definition(key="organization"), Definition(key="npc"))
    )
    organization = engine.entities.create(
        definition_key="organization", name=scenario.organization_name
    )
    participants = tuple(
        engine.entities.create(definition_key="npc", name=participant.name)
        for participant in scenario.participants
    )
    for participant in participants:
        engine.relationships.create(
            kind="member_of",
            source_id=participant.id,
            target_id=organization.id,
        )

    if scenario is COGNITION_SHAPED:
        _seed_cognition_shaped_history(engine, tuple(item.id for item in participants))

    cognitive_retriever = (
        _ManualTopicRetriever(
            DeterministicCognitiveRetriever(engine.state), "public well"
        )
        if scenario is COGNITION_SHAPED
        else None
    )

    return PreparedCouncilRuntime(
        engine=engine,
        organization_id=organization.id,
        participant_ids=tuple(participant.id for participant in participants),
        participant_self_knowledge={
            runtime.id: (catalog.self_knowledge,)
            for runtime, catalog in zip(
                participants, scenario.participants, strict=True
            )
        },
        cognitive_retriever=cognitive_retriever,
    )


def _seed_cognition_shaped_history(
    engine: SimulationEngine, participant_ids: tuple[str, ...]
) -> None:
    """Seed private interpretations without selecting a council response."""

    nessa_id, orin_id, pella_id, quin_id, rhea_id = participant_ids
    observations = (
        engine.observations.record(
            observer=nessa_id,
            subject="well_record",
            description="Fresh cracks are spreading beside the public well's old repair.",
            confidence=0.9,
            evidence={"private_measurement": "north seam widened"},
            metadata={"internal_note": "maintenance round"},
        ),
        engine.observations.record(
            observer=orin_id,
            subject="well_record",
            description="Several households are already rationing their remaining water.",
            confidence=0.8,
            evidence={"private_route_count": 7},
            metadata={"internal_note": "delivery route"},
        ),
        engine.observations.record(
            observer=pella_id,
            subject="well_record",
            description="The available stone looks sufficient only if damaged sections are identified first.",
            confidence=0.75,
            evidence={"private_inventory": "limited"},
            metadata={"internal_note": "store ledger"},
        ),
        engine.observations.record(
            observer=quin_id,
            subject="well_record",
            description="Queues around the failing well are blocking the road used for urgent deliveries.",
            confidence=0.85,
            evidence={"private_schedule": "missed route"},
            metadata={"internal_note": "courier round"},
        ),
        engine.observations.record(
            observer=rhea_id,
            subject="well_record",
            description="Neighbours are volunteering, but they disagree about whether to inspect or repair first.",
            confidence=0.8,
            evidence={"private_names": "volunteer list"},
            metadata={"internal_note": "work gathering"},
        ),
    )
    core = CognitiveSalience(importance=0.9, is_core=True)
    engine.memories.record(
        holder_id=nessa_id,
        subject_id="public well",
        summary="I remember a rushed repair failing because hidden damage was missed.",
        salience=core,
        source_observation_ids=(observations[0].id,),
    )
    engine.experiences.record(
        holder_id=orin_id,
        subject_id="public well",
        summary="Temporary deliveries once gave households time to handle a water emergency calmly.",
        supporting_observations=(observations[1].id,),
        metadata={"private_source": "earlier shortage"},
        salience=core,
    )
    engine.beliefs.record(
        holder_id=pella_id,
        subject_id="public well",
        proposition="I believe inspection first is most likely to prevent wasting scarce stone.",
        confidence=0.75,
        importance=0.9,
        status="core",
        supporting_observations=(observations[2].id,),
        metadata={"private_basis": "material estimate"},
        salience=core,
    )
    engine.beliefs.record(
        holder_id=quin_id,
        subject_id="public well",
        proposition="I believe immediate repair is safer than allowing the disruption to continue.",
        confidence=0.75,
        importance=0.9,
        status="core",
        supporting_observations=(observations[3].id,),
        metadata={"private_basis": "delivery delays"},
        salience=core,
    )
    engine.npc_relationships.record(
        holder_id=rhea_id,
        subject_id=nessa_id,
        summary="On public well work, I trust Nessa's caution but know Quin values urgency.",
        salience=CognitiveSalience(importance=0.7),
        source_observation_ids=(observations[4].id,),
    )
