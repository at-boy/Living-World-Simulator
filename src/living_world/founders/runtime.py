"""Fixed canonical composition through ordinary replay and domain gateways."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType

from living_world.api.inspection import WorldInspector
from living_world.cognition.action_resolution import NPCActionHandler
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.external_world.dispatch import DispatchDirection, DispatchStatus
from living_world.external_world.dispatch_action import (
    DispatchOffer,
    ExternalDispatchActionHandler,
)
from living_world.external_world.model import ContactState
from living_world.goals.model import GoalStatus
from living_world.managers.definition_manager import DefinitionManager
from living_world.replay.model import ProposalTape
from living_world.replay.runtime import ReplayPreparation
from living_world.replay.system import ReplayActionOffers
from living_world.repositories.sqlite_repository import (
    RepositoryLoadError,
    SQLiteRepository,
)
from living_world.running import RunResult
from living_world.scenarios.scenario import LoadedScenario
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.stages.model import SettlementStage
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem
from living_world.work.action import WorkActionHandler, WorkCreationOffer
from living_world.work.model import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    ResourceRequirement,
    ResourceWorkTarget,
    WorkCategory,
)

from .model import FoundersConfigurationError, FoundersPolicy, canonical_policy
from .setup import FoundersSetupManager


class FoundersCompositionSystem(SimulationSystem):
    def __init__(
        self, state: WorldState, definitions: DefinitionManager, policy: FoundersPolicy
    ) -> None:
        self._state, self._manager, self._policy = (
            state,
            FoundersSetupManager(state, definitions),
            policy,
        )

    def step(self, state: WorldState) -> None:
        if state is not self._state:
            raise FoundersConfigurationError("setup_mismatch")
        self._manager.compose(self._policy)


class FoundersOfferProvider:
    def __init__(self, engine: SimulationEngine, policy: FoundersPolicy) -> None:
        self._engine, self._policy = engine, policy

    def offers(self, *, actor_id: str, inspector: WorldInspector) -> ReplayActionOffers:
        engine, policy = self._engine, self._policy
        FoundersSetupManager(engine.state, engine.definitions).validate_existing(policy)
        r = policy.rules
        camp = engine.state.scenario_entity_bindings["camp"]
        reference = next(iter(engine.state.external_world_references.values()))
        candidates: list[WorkCreationOffer] = []
        specifications = (
            (
                "water",
                "Gather water",
                WorkCategory.GATHER_WATER,
                ResourceWorkTarget("water", r.water_work_quantity),
                r.normal_labor,
                (),
            ),
            (
                "food",
                "Produce food",
                WorkCategory.PRODUCE_FOOD,
                ResourceWorkTarget("food", r.food_work_quantity),
                r.normal_labor,
                (),
            ),
            (
                "shelter",
                "Build a modest shelter",
                WorkCategory.BUILD_SHELTER,
                CapabilityWorkTarget("shelter", r.modest_shelter_count),
                r.normal_labor,
                (ResourceRequirement("timber", r.modest_shelter_timber),),
            ),
            (
                "shelter",
                "Build a larger shelter group",
                WorkCategory.BUILD_SHELTER,
                CapabilityWorkTarget("shelter", r.large_shelter_count),
                r.large_shelter_labor,
                (ResourceRequirement("timber", r.large_shelter_timber),),
            ),
            (
                "storage",
                "Build storage",
                WorkCategory.BUILD_STORAGE,
                CapabilityWorkTarget("storage", r.storage_count),
                r.normal_labor,
                (ResourceRequirement("timber", r.storage_timber),),
            ),
            (
                "connection",
                "Contact the homeland",
                WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION,
                ExternalConnectionWorkTarget(reference.id),
                r.normal_labor,
                (),
            ),
        )
        for role, label, category, target, labor, resources in specifications:
            offer = WorkCreationOffer(
                label,
                category,
                target,
                camp,
                "objective_founders_" + role,
                camp,
                labor_required=labor,
                resources=resources,
                required_progress=r.required_progress,
            )
            try:
                WorkActionHandler(
                    engine.state, engine.definitions, engine.work, actor_id, (offer,)
                )
            except ValueError:
                continue
            candidates.append(offer)
        handlers: list[NPCActionHandler] = []
        options: list[ActionOption] = []
        if candidates:
            handler = WorkActionHandler(
                engine.state,
                engine.definitions,
                engine.work,
                actor_id,
                tuple(candidates),
            )
            handlers.append(handler)
            options.extend(handler.action_options)
        if (
            reference.contact_state is ContactState.CONTACTABLE
            and not engine.state.external_dispatches
        ):
            try:
                engine.external_dispatches.validate_create(
                    source_entity_id=actor_id,
                    reference_id=reference.id,
                    direction=DispatchDirection.INBOUND,
                    good="food",
                    quantity=r.dispatch_quantity,
                )
            except ValueError:
                pass
            else:
                dispatch = ExternalDispatchActionHandler(
                    engine.external_dispatches,
                    (
                        DispatchOffer(
                            "Request homeland supplies",
                            reference.id,
                            DispatchDirection.INBOUND,
                            "food",
                            r.dispatch_quantity,
                        ),
                    ),
                )
                handlers.append(dispatch)
                options.append(dispatch.action_option)
        return ReplayActionOffers(
            actor_id,
            tuple(sorted(options, key=lambda option: option.key)),
            tuple(handlers),
        )


class FoundersPreparation:
    def __init__(self, tape: ProposalTape) -> None:
        if tape is None:
            raise FoundersConfigurationError("missing_tape")
        if not isinstance(tape, ProposalTape):
            raise FoundersConfigurationError("invalid_policy")
        self._tape = tape
        self._replay: ReplayPreparation | None = None

    def prepare(self, engine: SimulationEngine, scenario: LoadedScenario) -> None:
        policy = FoundersPolicy.from_scenario(scenario)
        manager = FoundersSetupManager(engine.state, engine.definitions)
        manager.initialize_or_validate(policy)
        manager.restore_resource_vocabulary(policy, engine.resource_definitions)
        engine.register_system(
            FoundersCompositionSystem(engine.state, engine.definitions, policy),
            key="canonical_founders",
        )
        replay = ReplayPreparation(self._tape, FoundersOfferProvider(engine, policy))
        replay.prepare(engine, scenario)
        self._replay = replay

    def finish(
        self, engine: SimulationEngine, result: RunResult, *, finalize_proposals: bool
    ) -> None:
        if self._replay is None:
            raise FoundersConfigurationError("missing_tape")
        self._replay.finish(engine, result, finalize_proposals=finalize_proposals)


def _failure(engine: SimulationEngine) -> bool:
    return engine.state.goal_states["goal_founding"].status is GoalStatus.FAILED


def _success(engine: SimulationEngine) -> bool:
    state = engine.state
    camp = state.scenario_entity_bindings["camp"]
    if state.goal_states["goal_founding"].status is not GoalStatus.COMPLETED:
        return False
    if state.settlement_stage_states[camp].current_stage not in (
        SettlementStage.SETTLEMENT,
        SettlementStage.TOWN,
    ):
        return False
    if any(
        item.current is None or item.current.pressure != 0
        for item in state.need_states.values()
    ):
        return False
    # Immutable configured maintenance policy provides the fixed minimum via the manifest.
    rules = canonical_policy().rules
    if not any(
        s.condition >= rules.maintenance_minimum_condition
        and not s.upkeep_shortage
        and state.entities[state.maintenance_policies[key].capability_id].destroyed_tick
        is None
        for key, s in state.maintenance_states.items()
    ):
        return False
    actors = {state.scenario_entity_bindings[x] for x in ("ada", "bryn")}
    reference = next(iter(state.external_world_references.values()))
    return any(
        d.status is DispatchStatus.ARRIVED
        and d.direction is DispatchDirection.INBOUND
        and d.good == "food"
        and d.quantity == rules.dispatch_quantity
        and d.reference_id == reference.id
        and d.source_entity_id in actors
        for d in state.external_dispatches.values()
    )


def founders_terminal_conditions() -> Mapping[str, Callable[[SimulationEngine], bool]]:
    return MappingProxyType(
        {"founding_failure": _failure, "settlement_success": _success}
    )


def load_inspection_engine(
    scenario_path: Path, database_path: Path
) -> SimulationEngine:
    engine = SimulationEngine(SQLiteRepository(str(database_path), read_only=True))
    if engine.state.run_metadata is None:
        raise RepositoryLoadError("Saved scenario metadata is required.")
    scenario = engine.load_scenario(scenario_path)
    reserved = any("founders_policy" in item.attributes for item in scenario.entities)
    if reserved or scenario.key == "canonical_founders_v1":
        policy = FoundersPolicy.from_scenario(scenario)
        FoundersSetupManager(
            engine.state, engine.definitions
        ).restore_resource_vocabulary(policy, engine.resource_definitions)
    return engine
