"""Explicit objective-backed founding camp, settlement, and town development."""

from living_world.api.inspection import EngineWorldInspector
from living_world.core.definition import Definition
from living_world.goals import (
    CapacityCriterion,
    GoalDefinition,
    GoalOwnerKind,
    ObjectiveDefinition,
    PopulationMinimumCriterion,
)
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.stages import (
    SettlementStage,
    SettlementStageDefinition,
    SettlementStageProgram,
    StageObjectiveRequirement,
    StageRequirementKind,
)


def main() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    owner = engine.entities.create(
        definition_key="settlement",
        name="Oakford",
        attributes={"population": 4, "housing_capacity": 4},
    )
    housing = ObjectiveDefinition(
        "objective_housing",
        "Lasting homes",
        "Provide homes",
        "Build lasting homes.",
        (CapacityCriterion("housing", 4),),
        authorized_action_categories=("work",),
    )
    population = ObjectiveDefinition(
        "objective_population",
        "Growing community",
        "Support inhabitants",
        "Support our community.",
        (PopulationMinimumCriterion(4),),
        authorized_action_categories=("work",),
    )
    engine.goals.create(
        GoalDefinition(
            "goal_community",
            GoalOwnerKind.SETTLEMENT,
            owner.id,
            "Community",
            "Develop the community",
            "Help establish a lasting home.",
            (housing.id, population.id),
            authorized_action_categories=("work",),
        ),
        (housing, population),
    )
    homes = StageObjectiveRequirement(StageRequirementKind.CAPABILITY, housing.id)
    people = StageObjectiveRequirement(StageRequirementKind.POPULATION, population.id)
    engine.settlement_stages.configure(
        SettlementStageProgram(
            owner.id,
            (
                SettlementStageDefinition(SettlementStage.FOUNDING_CAMP, ()),
                SettlementStageDefinition(SettlementStage.SETTLEMENT, (homes,)),
                SettlementStageDefinition(SettlementStage.TOWN, (homes, people)),
            ),
        )
    )
    assert (
        engine.settlement_stages.state_for(owner.id).current_stage
        is SettlementStage.FOUNDING_CAMP
    )
    engine.run(2)
    assert (
        engine.settlement_stages.state_for(owner.id).current_stage
        is SettlementStage.SETTLEMENT
    )
    engine.step()
    assert (
        engine.settlement_stages.state_for(owner.id).current_stage
        is SettlementStage.TOWN
    )
    transitions = [
        event
        for event in engine.state.events.values()
        if event.kind == "settlement_stage_transitioned"
    ]
    assert len(transitions) == 2
    print(
        "Privileged operator inspection:",
        EngineWorldInspector(engine).settlement_stages(),
    )
    projection = engine.settlement_stages.npc_interpretation(owner.id)
    print("Explicitly selected NPC prose:", projection.label, projection.description)


if __name__ == "__main__":
    main()
