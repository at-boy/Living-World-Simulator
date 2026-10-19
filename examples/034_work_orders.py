"""Demonstrate durable work intent and non-deducting aggregate reservations."""

from living_world.api.inspection import EngineWorldInspector
from living_world.core.definition import Definition
from living_world.goals import (
    GoalDefinition,
    GoalOwnerKind,
    ObjectiveDefinition,
    ResourceMinimumCriterion,
)
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial import Bounds, BoundsKind, Point
from living_world.work import ResourceRequirement, ResourceWorkTarget, WorkCategory

engine = SimulationEngine()
engine.definitions.register(Definition("settlement"))
engine.definitions.register(Definition("npc"))
settlement = engine.entities.create(
    definition_key="settlement", name="Oakford", attributes={"resources": {"seed": 3}}
)
worker = engine.entities.create(
    definition_key="npc",
    name="Mara",
    attributes={
        "npc_identity": {
            "name": "Mara",
            "description": "A farmer.",
            "capability_descriptions": [],
        }
    },
)
engine.spatial.place(
    entity_id=settlement.id, geometry=Bounds(0, 0, 8, 8), bounds_kind=BoundsKind.AREA
)
engine.spatial.place(
    entity_id=worker.id, geometry=Point(1, 1), containing_entity_id=settlement.id
)
objective = ObjectiveDefinition(
    "objective_food",
    "Produce food",
    "Produce food",
    "Secure a food supply.",
    (ResourceMinimumCriterion("food", 5),),
    authorized_action_categories=("produce_food",),
)
engine.goals.create(
    GoalDefinition(
        "goal_home",
        GoalOwnerKind.SETTLEMENT,
        settlement.id,
        "Found a home",
        "Found a home",
        "Help the settlement thrive.",
        (objective.id,),
        authorized_action_categories=("settlement_work",),
    ),
    (objective,),
)
preparation = engine.work.create(
    category=WorkCategory.PRODUCE_FOOD,
    target=ResourceWorkTarget("food", 5),
    public_label="Prepare the field",
    settlement_id=settlement.id,
    objective_id=objective.id,
    location_id=settlement.id,
    labor_required=0,
    required_progress=1,
)
engine.work.mark_ready(preparation.id)
engine.work.assign_and_reserve(preparation.id, ())
engine.work.activate(preparation.id)
engine.work.record_progress(preparation.id, 1)
engine.work.complete(preparation.id)
work = engine.work.create(
    category=WorkCategory.PRODUCE_FOOD,
    target=ResourceWorkTarget("food", 5),
    public_label="Plant the first crop",
    settlement_id=settlement.id,
    objective_id=objective.id,
    location_id=settlement.id,
    prerequisite_work_ids=(preparation.id,),
    labor_required=1,
    resources=(ResourceRequirement("seed", 2),),
    required_progress=2,
)
engine.work.mark_ready(work.id)
engine.work.assign_and_reserve(work.id, (worker.id,))
assert settlement.attributes["resources"] == {"seed": 3}
engine.work.activate(work.id)
engine.work.record_progress(work.id, 1)
engine.work.block(work.id, "The field needs attention.")
engine.work.mark_ready(work.id)
engine.work.assign_and_reserve(work.id, (worker.id,))
engine.work.activate(work.id)
engine.work.record_progress(work.id, 1)
engine.work.complete(work.id)
print("Privileged:", EngineWorldInspector(engine).work_orders())
print("NPC-safe:", engine.work.npc_interpretation(work.id).description)
