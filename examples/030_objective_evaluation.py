"""Demonstrate deterministic engine-owned objective evaluation."""

from living_world.core.definition import Definition
from living_world.goals import (
    GoalDefinition,
    GoalOwnerKind,
    ObjectiveDefinition,
    ResourceMinimumCriterion,
)
from living_world.simulation.simulation_engine import SimulationEngine

engine = SimulationEngine()
engine.definitions.register(Definition("settlement"))
settlement = engine.entities.create(definition_key="settlement", name="Oakford")
settlement.attributes["resources"] = {"water": 12}

objective = ObjectiveDefinition(
    id="secure_water",
    label="Secure water",
    purpose="Maintain a minimum authoritative water reserve.",
    npc_interpretation="Keep dependable water available.",
    completion_criteria=(ResourceMinimumCriterion("water", 10),),
    authorized_action_categories=("gather_water",),
)
goal = GoalDefinition(
    id="found_oakford",
    owner_kind=GoalOwnerKind.SETTLEMENT,
    owner_id=settlement.id,
    label="Found Oakford",
    purpose="Establish a durable settlement.",
    npc_interpretation="Help establish a lasting home.",
    objective_ids=(objective.id,),
    authorized_action_categories=("settlement_work",),
)
engine.goals.create(goal, (objective,))

# Eligible records activate on the first evaluation. The next derives
# completion from authoritative state; no NPC or model declares the result.
engine.run(2)

print(engine.state.objective_states[objective.id].status.value)
print(engine.state.goal_states[goal.id].status.value)
print(engine.state.objective_states[objective.id].evidence[-1].description)
