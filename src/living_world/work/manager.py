from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import replace

from living_world.goals.model import GoalOwnerKind, GoalStatus
from living_world.managers.event_manager import EventManager
from living_world.npc.identity import NPCIdentity
from living_world.state.world_state import WorldState
from living_world.work.model import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    MaintenanceWorkTarget,
    NPCWorkInterpretation,
    ResourceRequirement,
    ResourceWorkTarget,
    ToolRequirement,
    WorkCategory,
    WorkDefinition,
    WorkReservation,
    WorkState,
    WorkStatus,
    WorkTarget,
    integer,
    text,
    visible_text,
)

_TERMINAL = frozenset({WorkStatus.COMPLETED, WorkStatus.CANCELLED, WorkStatus.FAILED})
_RELEASING = frozenset({WorkStatus.BLOCKED, *_TERMINAL})
_DESCRIPTIONS = {
    WorkStatus.PROPOSED: "This work is being considered.",
    WorkStatus.READY: "This work is ready to begin.",
    WorkStatus.ASSIGNED: "People and supplies have been set aside for this work.",
    WorkStatus.ACTIVE: "This work is underway.",
    WorkStatus.BLOCKED: "This work cannot currently proceed.",
    WorkStatus.COMPLETED: "This work is complete.",
    WorkStatus.CANCELLED: "This work will not proceed.",
    WorkStatus.FAILED: "This work could not be completed.",
}
_WORK_ID = re.compile(r"work_\d{6}")
_RESERVATION_ID = re.compile(r"work_reservation_\d{6}")


class WorkManager:
    """Exclusive mutation boundary for work orders and aggregate locks."""

    def __init__(self, state: WorldState, events: EventManager) -> None:
        self._state = state
        self._events = events
        self._next_work_id = self._next("work", state.work_definitions)
        self._next_reservation_id = self._next(
            "work_reservation", state.work_reservations
        )

    def create(
        self,
        *,
        category: WorkCategory,
        target: WorkTarget,
        public_label: str,
        settlement_id: str,
        objective_id: str,
        location_id: str,
        prerequisite_work_ids: tuple[str, ...] = (),
        labor_required: int = 0,
        tools: tuple[ToolRequirement, ...] = (),
        resources: tuple[ResourceRequirement, ...] = (),
        required_progress: int = 1,
        priority: int = 0,
        deadline_tick: int | None = None,
    ) -> WorkDefinition:
        self.validate_create(
            category=category,
            target=target,
            public_label=public_label,
            settlement_id=settlement_id,
            objective_id=objective_id,
            location_id=location_id,
            prerequisite_work_ids=prerequisite_work_ids,
            labor_required=labor_required,
            tools=tools,
            resources=resources,
            required_progress=required_progress,
            priority=priority,
            deadline_tick=deadline_tick,
        )
        definition = self._candidate_definition(
            category,
            target,
            public_label,
            settlement_id,
            objective_id,
            location_id,
            prerequisite_work_ids,
            labor_required,
            tools,
            resources,
            required_progress,
            priority,
            deadline_tick,
        )
        wid = definition.id
        state = WorkState(wid)
        snapshot = self._snapshot()
        try:
            self._state.work_definitions[wid] = definition
            self._state.work_states[wid] = state
            self._events.record(
                kind="work_order_created",
                subject_id=wid,
                attributes=self._creation_attributes(definition),
            )
            self._next_work_id += 1
        except Exception:
            self._restore(snapshot)
            raise
        return definition

    def validate_create(
        self,
        *,
        category: WorkCategory,
        target: WorkTarget,
        public_label: str,
        settlement_id: str,
        objective_id: str,
        location_id: str,
        prerequisite_work_ids: tuple[str, ...] = (),
        labor_required: int = 0,
        tools: tuple[ToolRequirement, ...] = (),
        resources: tuple[ResourceRequirement, ...] = (),
        required_progress: int = 1,
        priority: int = 0,
        deadline_tick: int | None = None,
        require_available_inputs: bool = False,
        reject_nonterminal_duplicate: bool = False,
    ) -> None:
        if not isinstance(require_available_inputs, bool):
            raise TypeError("require_available_inputs must be a bool.")
        if not isinstance(reject_nonterminal_duplicate, bool):
            raise TypeError("reject_nonterminal_duplicate must be a bool.")
        definition = self._candidate_definition(
            category,
            target,
            public_label,
            settlement_id,
            objective_id,
            location_id,
            prerequisite_work_ids,
            labor_required,
            tools,
            resources,
            required_progress,
            priority,
            deadline_tick,
        )
        self._validate_definition(definition, creating=True)
        if reject_nonterminal_duplicate and any(
            x.settlement_id == settlement_id
            and x.objective_id == objective_id
            and x.category is category
            and x.target == definition.target
            and x.location_id == location_id
            and self._state.work_states[x.id].status not in _TERMINAL
            for x in self._state.work_definitions.values()
        ):
            raise ValueError("Duplicate nonterminal work is not allowed.")
        if require_available_inputs:
            quantities = self._settlement_resources(settlement_id)
            locked: dict[str, int] = {}
            for reservation in self.active_reservations():
                for requirement in (*reservation.tools, *reservation.resources):
                    name = (
                        requirement.tool
                        if isinstance(requirement, ToolRequirement)
                        else requirement.resource
                    )
                    locked[name] = locked.get(name, 0) + requirement.quantity
            for requirement in (*definition.tools, *definition.resources):
                name = (
                    requirement.tool
                    if isinstance(requirement, ToolRequirement)
                    else requirement.resource
                )
                if quantities.get(name, 0) - locked.get(name, 0) < requirement.quantity:
                    raise ValueError(f"Insufficient unreserved '{name}'.")

    def _candidate_definition(
        self,
        category: WorkCategory,
        target: WorkTarget,
        public_label: str,
        settlement_id: str,
        objective_id: str,
        location_id: str,
        prerequisite_work_ids: tuple[str, ...],
        labor_required: int,
        tools: tuple[ToolRequirement, ...],
        resources: tuple[ResourceRequirement, ...],
        required_progress: int,
        priority: int,
        deadline_tick: int | None,
    ) -> WorkDefinition:
        return WorkDefinition(
            self._candidate_work_id(),
            category,
            target,
            public_label,
            settlement_id,
            objective_id,
            location_id,
            tuple(sorted(prerequisite_work_ids)),
            labor_required,
            tuple(sorted(tools, key=lambda x: x.tool)),
            tuple(sorted(resources, key=lambda x: x.resource)),
            required_progress,
            priority,
            deadline_tick,
            self._state.tick,
        )

    def mark_ready(self, work_id: str) -> WorkState:
        definition, current = self._required(work_id)
        if current.status not in {WorkStatus.PROPOSED, WorkStatus.BLOCKED}:
            raise ValueError("Only proposed or blocked work can become ready.")
        if any(
            self._state.work_states[x].status is not WorkStatus.COMPLETED
            for x in definition.prerequisite_work_ids
        ):
            raise ValueError("Every prerequisite must be completed.")
        return self._simple_transition(
            current,
            replace(current, status=WorkStatus.READY, status_reason=None),
            "work_order_ready",
        )

    def assign_and_reserve(
        self, work_id: str, labor_entity_ids: tuple[str, ...]
    ) -> WorkState:
        self.validate_assign_and_reserve(work_id, labor_entity_ids)
        definition, current = self._required(work_id)
        labor = tuple(sorted(labor_entity_ids))

        rid = self._candidate_reservation_id()
        reservation = WorkReservation(
            rid,
            work_id,
            labor,
            definition.tools,
            definition.resources,
            self._state.tick,
        )
        updated = replace(current, status=WorkStatus.ASSIGNED, reservation_id=rid)
        snapshot = self._snapshot()
        try:
            self._state.work_reservations[rid] = reservation
            self._events.record(
                kind="work_reservation_created",
                subject_id=rid,
                attributes={
                    "work_id": work_id,
                    "labor_entity_ids": labor,
                    "tools": self._tools(definition.tools),
                    "resources": self._resources(definition.resources),
                },
            )
            self._events.record(
                kind="work_order_assigned",
                subject_id=work_id,
                attributes={
                    "previous_status": current.status.value,
                    "current_status": updated.status.value,
                    "reservation_id": rid,
                },
            )
            self._state.work_states[work_id] = updated
            self._next_reservation_id += 1
        except Exception:
            self._restore(snapshot)
            raise
        return updated

    def validate_assign_and_reserve(
        self, work_id: str, labor_entity_ids: tuple[str, ...]
    ) -> None:
        definition, current = self._required(work_id)
        if current.status is not WorkStatus.READY:
            raise ValueError("Only ready work can be assigned.")
        if not isinstance(labor_entity_ids, tuple):
            raise TypeError("labor_entity_ids must be a tuple.")
        labor = tuple(sorted(labor_entity_ids))
        if len(labor) != definition.labor_required or len(set(labor)) != len(labor):
            raise ValueError(
                "Assignment must contain exactly the required unique laborers."
            )
        for entity_id in labor:
            self._validate_labor(entity_id, definition.settlement_id)
        used = {x for r in self.active_reservations() for x in r.labor_entity_ids}
        if used.intersection(labor):
            raise ValueError("A laborer cannot be reserved by multiple work orders.")
        quantities = self._settlement_resources(definition.settlement_id)
        locked: dict[str, int] = {}
        for reservation in self.active_reservations():
            for requirement in (*reservation.tools, *reservation.resources):
                name = (
                    requirement.tool
                    if isinstance(requirement, ToolRequirement)
                    else requirement.resource
                )
                locked[name] = locked.get(name, 0) + requirement.quantity
        for requirement in (*definition.tools, *definition.resources):
            name = (
                requirement.tool
                if isinstance(requirement, ToolRequirement)
                else requirement.resource
            )
            if quantities.get(name, 0) - locked.get(name, 0) < requirement.quantity:
                raise ValueError(f"Insufficient unreserved '{name}'.")
            locked[name] = locked.get(name, 0) + requirement.quantity

    def activate(self, work_id: str) -> WorkState:
        _, current = self._required(work_id)
        if current.status is not WorkStatus.ASSIGNED or current.reservation_id is None:
            raise ValueError(
                "Only assigned work with an active reservation can activate."
            )
        reservation = self._state.work_reservations.get(current.reservation_id)
        if reservation is None or reservation.released_tick is not None:
            raise ValueError("Work reservation is not active.")
        return self._simple_transition(
            current,
            replace(
                current,
                status=WorkStatus.ACTIVE,
                started_tick=(
                    current.started_tick
                    if current.started_tick is not None
                    else self._state.tick
                ),
            ),
            "work_order_activated",
        )

    def record_progress(self, work_id: str, amount: int) -> WorkState:
        definition, current = self._required(work_id)
        if current.status is not WorkStatus.ACTIVE:
            raise ValueError("Only active work can progress.")
        integer(amount, "amount", 1)
        if current.progress + amount > definition.required_progress:
            raise ValueError("Progress cannot exceed required progress.")
        updated = replace(current, progress=current.progress + amount)
        return self._event_update(
            current,
            updated,
            "work_order_progressed",
            {
                "previous_progress": current.progress,
                "current_progress": updated.progress,
            },
        )

    def set_priority(self, work_id: str, priority: int) -> WorkDefinition:
        self.validate_set_priority(work_id, priority)
        definition, _ = self._required(work_id)
        updated = replace(definition, priority=priority)
        snapshot = self._snapshot()
        try:
            self._events.record(
                kind="work_order_priority_changed",
                subject_id=work_id,
                attributes={
                    "previous_priority": definition.priority,
                    "current_priority": priority,
                },
            )
            self._state.work_definitions[work_id] = updated
        except Exception:
            self._restore(snapshot)
            raise
        return updated

    def validate_set_priority(self, work_id: str, priority: int) -> None:
        definition, state = self._required(work_id)
        if state.status in _TERMINAL:
            raise ValueError("Terminal work priority cannot change.")
        integer(priority, "priority")
        if priority == definition.priority:
            raise ValueError("Priority must change.")

    def block(self, work_id: str, reason: str) -> WorkState:
        return self._finish(work_id, WorkStatus.BLOCKED, reason)

    def cancel(self, work_id: str, reason: str) -> WorkState:
        return self._finish(work_id, WorkStatus.CANCELLED, reason)

    def fail(self, work_id: str, reason: str) -> WorkState:
        return self._finish(work_id, WorkStatus.FAILED, reason)

    def complete(self, work_id: str) -> WorkState:
        definition, state = self._required(work_id)
        if (
            state.status is not WorkStatus.ACTIVE
            or state.progress != definition.required_progress
        ):
            raise ValueError("Only fully progressed active work can complete.")
        return self._finish(work_id, WorkStatus.COMPLETED, None)

    def get(self, work_id: str) -> WorkDefinition | None:
        return self._state.work_definitions.get(work_id)

    def all(self) -> tuple[WorkDefinition, ...]:
        return tuple(
            sorted(
                self._state.work_definitions.values(),
                key=lambda x: (-x.priority, x.created_tick, x.id),
            )
        )

    def reservations_for(self, work_id: str) -> tuple[WorkReservation, ...]:
        return tuple(
            sorted(
                (
                    x
                    for x in self._state.work_reservations.values()
                    if x.work_id == work_id
                ),
                key=lambda x: x.id,
            )
        )

    def active_reservations(self) -> tuple[WorkReservation, ...]:
        return tuple(
            x
            for x in sorted(self._state.work_reservations.values(), key=lambda x: x.id)
            if x.released_tick is None
        )

    def npc_interpretation(self, work_id: str) -> NPCWorkInterpretation:
        definition, state = self._required(work_id)
        return NPCWorkInterpretation(
            definition.public_label, _DESCRIPTIONS[state.status]
        )

    def validate_loaded_state(self) -> None:
        if set(self._state.work_definitions) != set(self._state.work_states):
            raise ValueError("Persisted work definitions and states must correspond.")
        for key, definition in self._state.work_definitions.items():
            if type(definition) is not WorkDefinition:
                raise TypeError(
                    "Persisted work definitions must be WorkDefinition records."
                )
            if key != definition.id or _WORK_ID.fullmatch(key) is None:
                raise ValueError("Persisted work keys and canonical IDs must match.")
            self._validate_definition(definition, creating=False)
            self._validate_state(definition, self._state.work_states[definition.id])
        for key, reservation in self._state.work_reservations.items():
            if key != reservation.id or _RESERVATION_ID.fullmatch(key) is None:
                raise ValueError(
                    "Persisted reservation keys and canonical IDs must match."
                )
            self._validate_reservation(reservation)
        labor: set[str] = set()
        for reservation in self.active_reservations():
            if labor.intersection(reservation.labor_entity_ids):
                raise ValueError("Persisted labor reservations cannot overlap.")
            labor.update(reservation.labor_entity_ids)
            for entity_id in reservation.labor_entity_ids:
                self._validate_labor(
                    entity_id,
                    self._state.work_definitions[reservation.work_id].settlement_id,
                )
        for definition in self._state.work_definitions.values():
            current = self._state.work_states[definition.id]
            history = self.reservations_for(definition.id)
            self._validate_reservation_history(current, history)
            active = [x for x in history if x.released_tick is None]
            if len(active) > 1:
                raise ValueError("Work may have at most one active reservation.")
            if current.status in {WorkStatus.ASSIGNED, WorkStatus.ACTIVE}:
                if len(active) != 1 or current.reservation_id != active[0].id:
                    raise ValueError(
                        "Assigned work must reference its sole active reservation."
                    )
            elif active:
                raise ValueError(
                    "Only assigned or active work may retain a reservation."
                )

    def _validate_reservation_history(
        self, state: WorkState, history: tuple[WorkReservation, ...]
    ) -> None:
        terminal_releases: list[WorkReservation] = []
        previous: WorkReservation | None = None
        for reservation in history:
            if previous is not None:
                if (previous.created_tick, previous.id) >= (
                    reservation.created_tick,
                    reservation.id,
                ):
                    raise ValueError("Reservation history is not chronological.")
                if previous.released_tick is None:
                    raise ValueError("An active reservation must be last.")
                if previous.released_tick > reservation.created_tick:
                    raise ValueError("Reservation histories cannot overlap.")
                if previous.release_status is not WorkStatus.BLOCKED:
                    raise ValueError("Only a blocked release may precede reassignment.")
            if reservation.release_status in _TERMINAL:
                terminal_releases.append(reservation)
            previous = reservation
        if len(terminal_releases) > 1:
            raise ValueError("Work history cannot contain multiple terminal releases.")
        terminal_release = terminal_releases[0] if terminal_releases else None
        if terminal_release is not None:
            if not history or terminal_release is not history[-1]:
                raise ValueError("A terminal release must be last.")
            if state.status not in _TERMINAL:
                raise ValueError("Nonterminal work cannot have a terminal release.")
            if (
                terminal_release.release_status is not state.status
                or terminal_release.released_tick != state.resolution_tick
            ):
                raise ValueError("Terminal release must match terminal work state.")
        if state.status is WorkStatus.COMPLETED and terminal_release is None:
            raise ValueError("Completed work requires its matching terminal release.")
        if state.status not in _TERMINAL and any(
            item.release_status is not WorkStatus.BLOCKED
            for item in history
            if item.release_status is not None
        ):
            raise ValueError(
                "Nonterminal work history may contain only blocked releases."
            )

    def validate_entity_removal(self, entity_id: str) -> None:
        if any(
            x.settlement_id == entity_id or x.location_id == entity_id
            for x in self._state.work_definitions.values()
        ) or any(
            entity_id in x.labor_entity_ids
            for x in self._state.work_reservations.values()
        ):
            raise ValueError(
                f"Entity '{entity_id}' cannot be removed while work history refers to it."
            )

    def validate_entity_destruction(self, entity_id: str) -> None:
        if (
            any(
                x.settlement_id == entity_id
                for x in self._state.work_definitions.values()
            )
            or any(
                self._spatial_dependency(entity_id, x.location_id)
                and self._state.work_states[x.id].status not in _TERMINAL
                for x in self._state.work_definitions.values()
            )
            or any(
                self._spatial_dependency(entity_id, labor_id)
                for x in self.active_reservations()
                for labor_id in x.labor_entity_ids
            )
        ):
            raise ValueError("Entity is required by nonterminal work.")

    def validate_spatial_change(self, entity_id: str) -> None:
        self.validate_entity_destruction(entity_id)

    def validate_maintenance_target(self, entity_id: str) -> None:
        self.validate_entity_destruction(entity_id)

    def _finish(
        self, work_id: str, status: WorkStatus, reason: str | None
    ) -> WorkState:
        _, current = self._required(work_id)
        allowed = {
            WorkStatus.BLOCKED: {
                WorkStatus.READY,
                WorkStatus.ASSIGNED,
                WorkStatus.ACTIVE,
            },
            WorkStatus.COMPLETED: {WorkStatus.ACTIVE},
            WorkStatus.CANCELLED: set(WorkStatus) - _TERMINAL,
            WorkStatus.FAILED: set(WorkStatus) - _TERMINAL,
        }
        if current.status not in allowed[status]:
            raise ValueError("Invalid work transition.")
        if status is not WorkStatus.COMPLETED:
            text(reason, "reason")
        snapshot = self._snapshot()
        try:
            if current.reservation_id is not None:
                reservation = self._state.work_reservations[current.reservation_id]
                released = replace(
                    reservation, released_tick=self._state.tick, release_status=status
                )
                self._events.record(
                    kind="work_reservation_released",
                    subject_id=reservation.id,
                    attributes={"work_id": work_id, "release_status": status.value},
                )
                self._state.work_reservations[reservation.id] = released
            terminal = status in _TERMINAL
            updated = replace(
                current,
                status=status,
                reservation_id=None,
                status_reason=reason,
                resolution_tick=self._state.tick if terminal else None,
            )
            attrs = {
                "previous_status": current.status.value,
                "current_status": status.value,
            }
            if reason is not None:
                attrs["reason"] = reason
            self._events.record(
                kind=f"work_order_{status.value}", subject_id=work_id, attributes=attrs
            )
            self._state.work_states[work_id] = updated
        except Exception:
            self._restore(snapshot)
            raise
        return updated

    def _simple_transition(
        self, previous: WorkState, current: WorkState, kind: str
    ) -> WorkState:
        return self._event_update(
            previous,
            current,
            kind,
            {
                "previous_status": previous.status.value,
                "current_status": current.status.value,
            },
        )

    def _event_update(
        self,
        previous: WorkState,
        current: WorkState,
        kind: str,
        attrs: dict[str, object],
    ) -> WorkState:
        snapshot = self._snapshot()
        try:
            self._events.record(kind=kind, subject_id=current.work_id, attributes=attrs)
            self._state.work_states[current.work_id] = current
        except Exception:
            self._restore(snapshot)
            raise
        return current

    def _validate_definition(self, d: WorkDefinition, *, creating: bool) -> None:
        text(d.id, "work id")
        visible_text(d.public_label, "public label")
        if not isinstance(d.category, WorkCategory):
            raise TypeError("category must be WorkCategory.")
        for value, name in (
            (d.settlement_id, "settlement_id"),
            (d.objective_id, "objective_id"),
            (d.location_id, "location_id"),
        ):
            text(value, name)
        integer(d.labor_required, "labor_required")
        integer(d.required_progress, "required_progress", 1)
        integer(d.priority, "priority")
        integer(d.created_tick, "created_tick")
        if d.deadline_tick is not None:
            integer(d.deadline_tick, "deadline_tick")
            if creating and d.deadline_tick <= self._state.tick:
                raise ValueError("Deadline must be in the future.")
            if not creating and d.deadline_tick < d.created_tick:
                raise ValueError("Deadline cannot predate creation.")
        if d.prerequisite_work_ids != tuple(sorted(d.prerequisite_work_ids)) or len(
            set(d.prerequisite_work_ids)
        ) != len(d.prerequisite_work_ids):
            raise ValueError("Prerequisites must be unique and sorted.")
        if d.tools != tuple(
            sorted(d.tools, key=lambda x: x.tool)
        ) or d.resources != tuple(sorted(d.resources, key=lambda x: x.resource)):
            raise ValueError("Requirements must be sorted.")
        tool_names = self._requirements(d.tools, ToolRequirement)
        resource_names = self._requirements(d.resources, ResourceRequirement)
        if tool_names & resource_names:
            raise ValueError("Tool and resource names cannot overlap.")
        self._validate_target(d, creating=creating)
        settlement = self._state.entities.get(d.settlement_id)
        if (
            settlement is None
            or settlement.destroyed_tick is not None
            or settlement.definition_key != "settlement"
        ):
            raise ValueError("Settlement must be live.")
        goals = [
            g
            for g in self._state.goal_definitions.values()
            if d.objective_id in g.objective_ids
        ]
        if (
            len(goals) != 1
            or goals[0].owner_kind is not GoalOwnerKind.SETTLEMENT
            or goals[0].owner_id != d.settlement_id
        ):
            raise ValueError("Objective must belong to the settlement's goal.")
        if d.objective_id not in self._state.objective_states:
            raise ValueError("Objective state is missing.")
        if creating and (
            self._state.goal_states[goals[0].id].status
            in {GoalStatus.COMPLETED, GoalStatus.FAILED}
            or self._state.objective_states[d.objective_id].status
            in {GoalStatus.COMPLETED, GoalStatus.FAILED}
        ):
            raise ValueError("Terminal goals cannot receive new work.")
        location = self._state.entities.get(d.location_id)
        if location is None or (creating and location.destroyed_tick is not None):
            raise ValueError("Work location must exist and be live.")
        if (
            creating
            or self._state.work_states.get(d.id, WorkState(d.id)).status
            not in _TERMINAL
        ) and not self._inside(d.location_id, d.settlement_id):
            raise ValueError("Work location must be within its settlement.")
        for key in d.prerequisite_work_ids:
            p = self._state.work_definitions.get(key)
            if (
                p is None
                or p.settlement_id != d.settlement_id
                or (p.created_tick, p.id) >= (d.created_tick, d.id)
            ):
                raise ValueError("Invalid work prerequisite.")

    def _validate_target(self, d: WorkDefinition, *, creating: bool) -> None:
        pairs = {
            WorkCategory.GATHER_WATER: ResourceWorkTarget,
            WorkCategory.PRODUCE_FOOD: ResourceWorkTarget,
            WorkCategory.BUILD_SHELTER: CapabilityWorkTarget,
            WorkCategory.BUILD_STORAGE: CapabilityWorkTarget,
            WorkCategory.MAINTAIN_CAPABILITY: MaintenanceWorkTarget,
            WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION: ExternalConnectionWorkTarget,
        }
        if type(d.target) is not pairs[d.category]:
            raise ValueError("Work category and target type do not match.")
        if isinstance(d.target, ResourceWorkTarget):
            text(d.target.resource, "target resource")
            integer(d.target.quantity, "target quantity", 1)
            expected = "water" if d.category is WorkCategory.GATHER_WATER else "food"
            if d.target.resource != expected:
                raise ValueError("Resource target does not match category.")
        elif isinstance(d.target, CapabilityWorkTarget):
            text(d.target.definition_key, "definition_key")
            integer(d.target.count, "count", 1)
        elif isinstance(d.target, MaintenanceWorkTarget):
            policy = self._state.maintenance_policies.get(d.target.policy_id)
            state = self._state.maintenance_states.get(d.target.policy_id)
            if policy is None or state is None or policy.owner_id != d.settlement_id:
                raise ValueError("Maintenance target is invalid.")
            capability = (
                None
                if policy is None
                else self._state.entities.get(policy.capability_id)
            )
            if capability is None:
                raise ValueError("Maintenance capability history is missing.")
            if creating and (
                state.condition <= 0 or capability.destroyed_tick is not None
            ):
                raise ValueError(
                    "New maintenance work requires a live positive-condition capability."
                )
        elif isinstance(d.target, ExternalConnectionWorkTarget):
            if d.target.reference_id not in self._state.external_world_references:
                raise ValueError("External reference is unknown.")

    def _validate_state(self, d: WorkDefinition, s: WorkState) -> None:
        if (
            type(s) is not WorkState
            or s.work_id != d.id
            or not isinstance(s.status, WorkStatus)
        ):
            raise ValueError("Persisted work state is invalid.")
        integer(s.progress, "progress")
        if s.progress > d.required_progress:
            raise ValueError("Progress exceeds requirement.")
        for tick in (s.started_tick, s.resolution_tick):
            if tick is not None:
                integer(tick, "lifecycle tick")
                if tick < d.created_tick or tick > self._state.tick:
                    raise ValueError("Work lifecycle ticks are out of bounds.")
        if (
            s.started_tick is not None
            and s.resolution_tick is not None
            and s.started_tick > s.resolution_tick
        ):
            raise ValueError("Work start cannot follow resolution.")
        if s.status in {WorkStatus.ASSIGNED, WorkStatus.ACTIVE}:
            if (
                s.reservation_id is None
                or self._state.work_reservations.get(s.reservation_id, None) is None
            ):
                raise ValueError("Assigned work needs a reservation.")
        elif s.reservation_id is not None:
            raise ValueError("Only assigned/active work may reference a reservation.")
        if s.status in {WorkStatus.BLOCKED, WorkStatus.CANCELLED, WorkStatus.FAILED}:
            text(s.status_reason, "status_reason")
        elif s.status_reason is not None:
            raise ValueError("Status reason is not valid here.")
        if (s.status in _TERMINAL) != (s.resolution_tick is not None):
            raise ValueError("Resolution tick/status mismatch.")
        if s.status is WorkStatus.COMPLETED and s.progress != d.required_progress:
            raise ValueError("Completed work must have exact progress.")
        if s.status is WorkStatus.PROPOSED and (
            s.progress != 0
            or any(
                x is not None
                for x in (
                    s.reservation_id,
                    s.status_reason,
                    s.started_tick,
                    s.resolution_tick,
                )
            )
        ):
            raise ValueError("Proposed work has invalid state fields.")
        if (
            s.status in {WorkStatus.READY, WorkStatus.ASSIGNED}
            and s.started_tick is None
            and s.progress != 0
        ):
            raise ValueError("Unstarted work cannot have progress.")
        if s.status is WorkStatus.ACTIVE and s.started_tick is None:
            raise ValueError("Active work requires a start tick.")
        if s.status is WorkStatus.COMPLETED and s.started_tick is None:
            raise ValueError("Completed work requires a start tick.")
        if (
            s.status
            not in {WorkStatus.ACTIVE, WorkStatus.BLOCKED, WorkStatus.COMPLETED}
            and s.progress == d.required_progress
        ):
            raise ValueError("This status cannot retain complete progress.")

    def _validate_reservation(self, r: WorkReservation) -> None:
        if (
            type(r) is not WorkReservation
            or r.work_id not in self._state.work_definitions
        ):
            raise ValueError("Persisted reservation is invalid.")
        d = self._state.work_definitions[r.work_id]
        if (
            r.tools != d.tools
            or r.resources != d.resources
            or r.labor_entity_ids != tuple(sorted(r.labor_entity_ids))
            or len(r.labor_entity_ids) != d.labor_required
            or len(set(r.labor_entity_ids)) != len(r.labor_entity_ids)
        ):
            raise ValueError("Reservation does not match its work definition.")
        if (r.released_tick is None) != (r.release_status is None):
            raise ValueError("Reservation release fields must correspond.")
        if r.release_status is not None and r.release_status not in _RELEASING:
            raise ValueError("Invalid release status.")
        integer(r.created_tick, "reservation created_tick")
        if r.created_tick < d.created_tick or r.created_tick > self._state.tick:
            raise ValueError("Reservation creation tick is out of bounds.")
        if r.released_tick is not None:
            integer(r.released_tick, "reservation released_tick")
            if r.released_tick < r.created_tick or r.released_tick > self._state.tick:
                raise ValueError("Reservation release tick is out of bounds.")
        for entity_id in r.labor_entity_ids:
            if entity_id not in self._state.entities:
                raise ValueError("Reservation labor history must reference an entity.")

    def _spatial_dependency(self, ancestor_id: str, subject_id: str) -> bool:
        current: str | None = subject_id
        seen: set[str] = set()
        while current is not None and current not in seen:
            if current == ancestor_id:
                return True
            seen.add(current)
            placement = self._state.placements.get(current)
            current = None if placement is None else placement.containing_entity_id
        return False

    def _validate_labor(self, entity_id: str, settlement_id: str) -> None:
        entity = self._state.entities.get(entity_id)
        if entity is None or entity.destroyed_tick is not None:
            raise ValueError("Laborer must be live.")
        NPCIdentity.from_attribute(entity.attributes.get("npc_identity"))
        if any(
            p.capability_id == entity_id
            for p in self._state.maintenance_policies.values()
        ):
            raise ValueError("Maintenance capability cannot provide labor.")
        if not self._inside(entity_id, settlement_id):
            raise ValueError("Laborer must be placed within the settlement.")

    def _inside(self, entity_id: str, settlement_id: str) -> bool:
        current: str | None = entity_id
        seen: set[str] = set()
        while current is not None and current not in seen:
            if current == settlement_id:
                return current in self._state.placements
            seen.add(current)
            placement = self._state.placements.get(current)
            if placement is None or placement.geometry is None:
                return False
            current = placement.containing_entity_id
        return False

    def _settlement_resources(self, settlement_id: str) -> dict[str, int]:
        raw = self._state.entities[settlement_id].attributes.get("resources", {})
        if not isinstance(raw, dict):
            raise TypeError("resources must be a dictionary.")
        result: dict[str, int] = {}
        for key, value in raw.items():
            text(key, "resource name")
            result[key] = integer(value, f"resource '{key}'")
        return result

    @staticmethod
    def _requirements(values: tuple[object, ...], expected: type) -> set[str]:
        names: list[str] = []
        for value in values:
            if type(value) is not expected:
                raise TypeError("Requirement has an invalid type.")
            name = value.tool if isinstance(value, ToolRequirement) else value.resource
            text(name, "requirement name")
            integer(value.quantity, "requirement quantity", 1)
            names.append(name)
        if len(set(names)) != len(names):
            raise ValueError("Requirement names must be unique.")
        return set(names)

    def _required(self, work_id: str) -> tuple[WorkDefinition, WorkState]:
        definition = self._state.work_definitions.get(work_id)
        state = self._state.work_states.get(work_id)
        if definition is None or state is None:
            raise ValueError("Work order is unknown.")
        return definition, state

    def _snapshot(self):
        return (
            deepcopy(self._state.work_definitions),
            deepcopy(self._state.work_states),
            deepcopy(self._state.work_reservations),
            set(self._state.events),
            self._next_work_id,
            self._next_reservation_id,
        )

    def _restore(self, snapshot) -> None:
        (
            definitions,
            states,
            reservations,
            events,
            self._next_work_id,
            self._next_reservation_id,
        ) = snapshot
        self._state.work_definitions = definitions
        self._state.work_states = states
        self._state.work_reservations = reservations
        for key in set(self._state.events) - events:
            self._state.events.pop(key, None)

    @staticmethod
    def _next(prefix: str, records: dict[str, object]) -> int:
        values = [
            int(x[len(prefix) + 1 :])
            for x in records
            if x.startswith(prefix + "_") and x[len(prefix) + 1 :].isdigit()
        ]
        return max(values, default=0) + 1

    def _candidate_work_id(self) -> str:
        return f"work_{self._next_work_id:06d}"

    def _candidate_reservation_id(self) -> str:
        return f"work_reservation_{self._next_reservation_id:06d}"

    @staticmethod
    def _tools(values):
        return tuple({"tool": x.tool, "quantity": x.quantity} for x in values)

    @staticmethod
    def _resources(values):
        return tuple({"resource": x.resource, "quantity": x.quantity} for x in values)

    def _creation_attributes(self, d: WorkDefinition) -> dict[str, object]:
        if isinstance(d.target, ResourceWorkTarget):
            target = {
                "kind": "resource",
                "resource": d.target.resource,
                "quantity": d.target.quantity,
            }
        elif isinstance(d.target, CapabilityWorkTarget):
            target = {
                "kind": "capability",
                "definition_key": d.target.definition_key,
                "count": d.target.count,
            }
        elif isinstance(d.target, MaintenanceWorkTarget):
            target = {"kind": "maintenance", "policy_id": d.target.policy_id}
        else:
            target = {
                "kind": "external_connection",
                "reference_id": d.target.reference_id,
            }
        return {
            "category": d.category.value,
            "target": target,
            "public_label": d.public_label,
            "settlement_id": d.settlement_id,
            "objective_id": d.objective_id,
            "location_id": d.location_id,
            "prerequisite_work_ids": d.prerequisite_work_ids,
            "labor_required": d.labor_required,
            "tools": self._tools(d.tools),
            "resources": self._resources(d.resources),
            "required_progress": d.required_progress,
            "priority": d.priority,
            "deadline_tick": d.deadline_tick,
        }
