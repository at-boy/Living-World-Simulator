from __future__ import annotations

from copy import deepcopy
from dataclasses import fields

from living_world.external_world.manager import ExternalWorldReferenceManager
from living_world.external_world.model import ContactState
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.managers.relationship_manager import RelationshipManager
from living_world.needs.consequence import ConsequenceManager
from living_world.spatial.manager import SpatialManager
from living_world.spatial.model import Point
from living_world.state.world_state import WorldState
from living_world.systems.resource_system import ResourceSystem
from living_world.systems.simulation_system import SimulationSystem
from living_world.work.manager import WorkManager
from living_world.work.model import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    MaintenanceWorkTarget,
    ResourceWorkTarget,
    WorkDefinition,
    WorkState,
    WorkStatus,
)

_WAIT_LABOR = "Waiting for eligible labor."
_WAIT_TOOLS = "Reserved tools are unavailable."
_WAIT_RESOURCES = "Required consumables are unavailable."


class WorkExecutionSystem(SimulationSystem):
    """Execute authorized work deterministically in one atomic shadow phase."""

    def __init__(self, definitions: DefinitionManager) -> None:
        self._definitions = definitions

    def step(self, state: WorldState) -> None:
        if not state.work_definitions:
            return
        shadow = WorldState()
        for item in fields(WorldState):
            value = getattr(state, item.name)
            if item.name in {"entities", "relationships"}:
                value = deepcopy(value)
            elif isinstance(value, dict):
                value = dict(value)
            setattr(shadow, item.name, value)
        self._execute(shadow)
        for item in fields(WorldState):
            setattr(state, item.name, getattr(shadow, item.name))

    def _execute(self, state: WorldState) -> None:
        events = EventManager(state)
        work = WorkManager(state, events)
        spatial = SpatialManager(state, events, work)
        entities = EntityManager(state, self._definitions, spatial, work)
        relationships = RelationshipManager(state, entities)
        resources = ResourceSystem()
        consequences = ConsequenceManager(state, resources, entities, events, work)
        external = ExternalWorldReferenceManager(state, events)
        used_labor: set[str] = set()
        locked_tools: dict[tuple[str, str], int] = {}

        for definition in work.all():
            current = state.work_states[definition.id]
            if current.status in {
                WorkStatus.COMPLETED,
                WorkStatus.CANCELLED,
                WorkStatus.FAILED,
            }:
                continue
            if (
                definition.deadline_tick is not None
                and state.tick >= definition.deadline_tick
            ):
                work.fail(definition.id, "The work deadline expired.")
                continue
            prerequisite_states = [
                state.work_states[x].status for x in definition.prerequisite_work_ids
            ]
            if any(
                x in {WorkStatus.CANCELLED, WorkStatus.FAILED}
                for x in prerequisite_states
            ):
                work.fail(definition.id, "A prerequisite cannot complete.")
                continue
            if any(x is not WorkStatus.COMPLETED for x in prerequisite_states):
                continue
            permanent = self._permanent_target_failure(state, definition)
            if permanent:
                work.fail(definition.id, "The work target is permanently unavailable.")
                continue
            if current.status is WorkStatus.PROPOSED:
                current = work.mark_ready(definition.id)
            if current.status in {WorkStatus.ASSIGNED, WorkStatus.ACTIVE}:
                reason = self._reservation_problem(
                    state, definition, current, used_labor, locked_tools, resources
                )
                if reason is not None:
                    work.block(definition.id, reason)
                    current = state.work_states[definition.id]
                else:
                    reservation = state.work_reservations[current.reservation_id]  # type: ignore[index]
                    used_labor.update(reservation.labor_entity_ids)
                    for requirement in reservation.tools:
                        key = (definition.settlement_id, requirement.tool)
                        locked_tools[key] = (
                            locked_tools.get(key, 0) + requirement.quantity
                        )
            if current.status in {WorkStatus.READY, WorkStatus.BLOCKED}:
                labor = self._available_labor(state, definition, used_labor)
                reason = self._preflight(
                    state, definition, current, labor, locked_tools, resources
                )
                if reason is not None:
                    if current.status is not WorkStatus.BLOCKED:
                        work.block(definition.id, reason)
                    continue
                if current.status is WorkStatus.BLOCKED:
                    work.mark_ready(definition.id)
                current = work.assign_and_reserve(definition.id, labor)
                used_labor.update(labor)
                for requirement in definition.tools:
                    key = (definition.settlement_id, requirement.tool)
                    locked_tools[key] = locked_tools.get(key, 0) + requirement.quantity
            if current.status is WorkStatus.ASSIGNED:
                if current.inputs_charged_tick is None:
                    current = self._charge(state, work, resources, definition, current)
                current = work.activate(definition.id)
            elif (
                current.status is WorkStatus.ACTIVE
                and current.inputs_charged_tick is None
            ):
                current = self._charge(state, work, resources, definition, current)
            previous = current.progress
            amount = min(
                max(1, definition.labor_required),
                definition.required_progress - previous,
            )
            if amount:
                current = work.record_progress(definition.id, amount)
                for threshold in (25, 50, 75):
                    if (
                        previous * 100
                        < definition.required_progress * threshold
                        <= current.progress * 100
                    ):
                        events.record(
                            kind="work_progress_threshold_reached",
                            subject_id=definition.id,
                            attributes={
                                "threshold_percent": threshold,
                                "previous_progress": previous,
                                "current_progress": current.progress,
                                "required_progress": definition.required_progress,
                            },
                        )
            if current.progress == definition.required_progress:
                self._effect(
                    state,
                    events,
                    entities,
                    relationships,
                    spatial,
                    resources,
                    consequences,
                    external,
                    definition,
                )
                work.complete(definition.id)

    def _available_labor(
        self, state: WorldState, definition: WorkDefinition, used: set[str]
    ) -> tuple[str, ...]:
        result = []
        for entity_id in sorted(state.entities):
            if self._labor_is_eligible(
                state, entity_id, definition.settlement_id, used
            ):
                result.append(entity_id)
        return tuple(result[: definition.labor_required])

    def _labor_is_eligible(
        self,
        state: WorldState,
        entity_id: str,
        settlement_id: str,
        used: set[str],
    ) -> bool:
        entity = state.entities[entity_id]
        schedule = entity.attributes.get("schedule", [])
        return (
            entity.destroyed_tick is None
            and "npc_identity" in entity.attributes
            and entity_id not in used
            and self._inside(state, entity_id, settlement_id)
            and (not schedule or entity.attributes.get("active_activity") == "working")
        )

    def _inside(self, state: WorldState, entity_id: str, settlement_id: str) -> bool:
        current: str | None = entity_id
        while current is not None:
            if current == settlement_id:
                return True
            placement = state.placements.get(current)
            current = None if placement is None else placement.containing_entity_id
        return False

    def _preflight(
        self,
        state: WorldState,
        d: WorkDefinition,
        s: WorkState,
        labor: tuple[str, ...],
        locks: dict[tuple[str, str], int],
        resources: ResourceSystem,
    ) -> str | None:
        if len(labor) != d.labor_required:
            return _WAIT_LABOR
        owner = state.entities[d.settlement_id]
        for item in d.tools:
            if (
                resources.get(owner, item.tool)
                - locks.get((d.settlement_id, item.tool), 0)
                < item.quantity
            ):
                return _WAIT_TOOLS
        if s.inputs_charged_tick is None:
            for item in d.resources:
                if resources.get(owner, item.resource) < item.quantity:
                    return _WAIT_RESOURCES
        return None

    def _reservation_problem(
        self,
        state: WorldState,
        d: WorkDefinition,
        s: WorkState,
        used: set[str],
        locks: dict[tuple[str, str], int],
        resources: ResourceSystem,
    ) -> str | None:
        reservation = state.work_reservations[s.reservation_id]  # type: ignore[index]
        if any(
            not self._labor_is_eligible(state, entity_id, d.settlement_id, used)
            for entity_id in reservation.labor_entity_ids
        ):
            return _WAIT_LABOR
        return self._preflight(
            state, d, s, reservation.labor_entity_ids, locks, resources
        )

    def _charge(
        self,
        state: WorldState,
        work: WorkManager,
        resources: ResourceSystem,
        d: WorkDefinition,
        s: WorkState,
    ) -> WorkState:
        owner = state.entities[d.settlement_id]
        for item in d.resources:
            resources.remove(owner, item.resource, item.quantity)
        return work.record_inputs_charged(d.id)

    def _permanent_target_failure(self, state: WorldState, d: WorkDefinition) -> bool:
        if isinstance(d.target, MaintenanceWorkTarget):
            policy = state.maintenance_policies.get(d.target.policy_id)
            condition = state.maintenance_states.get(d.target.policy_id)
            entity = (
                None if policy is None else state.entities.get(policy.capability_id)
            )
            return (
                policy is None
                or condition is None
                or condition.condition <= 0
                or entity is None
                or entity.destroyed_tick is not None
            )
        if isinstance(d.target, ExternalConnectionWorkTarget):
            ref = state.external_world_references.get(d.target.reference_id)
            return ref is None or ref.contact_state is ContactState.UNKNOWN
        return (
            d.location_id not in state.entities
            or state.entities[d.location_id].destroyed_tick is not None
        )

    def _effect(
        self,
        state: WorldState,
        events: EventManager,
        entities: EntityManager,
        relationships: RelationshipManager,
        spatial: SpatialManager,
        resources: ResourceSystem,
        consequences: ConsequenceManager,
        external: ExternalWorldReferenceManager,
        d: WorkDefinition,
    ) -> None:
        if isinstance(d.target, ResourceWorkTarget):
            resources.add(
                state.entities[d.settlement_id], d.target.resource, d.target.quantity
            )
            events.record(
                kind="work_resource_produced",
                subject_id=d.settlement_id,
                attributes={
                    "work_id": d.id,
                    "category": d.category.value,
                    "resource": d.target.resource,
                    "quantity": d.target.quantity,
                },
            )
        elif isinstance(d.target, CapabilityWorkTarget):
            placement = state.placements[d.location_id]
            geometry = placement.geometry
            point = geometry if isinstance(geometry, Point) else Point(geometry.x + (geometry.width - 1) // 2, geometry.y + (geometry.height - 1) // 2)  # type: ignore[union-attr]
            parent_id = (
                placement.containing_entity_id
                if isinstance(geometry, Point)
                else d.location_id
            )
            for ordinal in range(1, d.target.count + 1):
                entity = entities.create(
                    definition_key=d.target.definition_key,
                    name=f"{d.target.definition_key.replace('_', ' ').title()} {ordinal}",
                    attributes={"is_constructed": True},
                )
                relationships.create(
                    kind="owns", source_id=d.settlement_id, target_id=entity.id
                )
                spatial.place(
                    entity_id=entity.id,
                    geometry=point,
                    containing_entity_id=parent_id,
                )
                events.record(
                    kind="work_capability_constructed",
                    subject_id=entity.id,
                    attributes={
                        "work_id": d.id,
                        "settlement_id": d.settlement_id,
                        "definition_key": d.target.definition_key,
                        "ordinal": ordinal,
                        "location_id": d.location_id,
                    },
                )
        elif isinstance(d.target, MaintenanceWorkTarget):
            policy = state.maintenance_policies[d.target.policy_id]
            consequences.restore(d.target.policy_id, policy.recovery_per_paid_tick)
        elif isinstance(d.target, ExternalConnectionWorkTarget):
            ref = state.external_world_references[d.target.reference_id]
            if ref.contact_state is not ContactState.CONTACTABLE:
                external.transition_contact(ref.id, ContactState.CONTACTABLE)
