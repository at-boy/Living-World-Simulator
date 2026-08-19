from living_world.core.definition import Definition
from living_world.goals import (
    GoalDefinition,
    GoalOwnerKind,
    GoalStatus,
    ObjectiveDefinition,
    ResourceMinimumCriterion,
)
from living_world.simulation.simulation_engine import SimulationEngine


def main() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement"))
    settlement = engine.entities.create(definition_key="settlement", name="Oakford")
    objective = ObjectiveDefinition(
        "water",
        "Secure water",
        "Maintain water",
        "Seek dependable water.",
        (ResourceMinimumCriterion("water", 10),),
        authorized_action_categories=("gather_water",),
    )
    goal = GoalDefinition(
        "found_oakford",
        GoalOwnerKind.SETTLEMENT,
        settlement.id,
        "Found Oakford",
        "Establish a settlement",
        "Help establish a lasting home.",
        (objective.id,),
        authorized_action_categories=("settlement_work",),
    )
    engine.goals.create(goal, (objective,))
    engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)
    safe = engine.goals.npc_interpretation(goal.id)
    print(f"{safe.label}: {safe.description}")


if __name__ == "__main__":
    main()
