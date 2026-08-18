from __future__ import annotations

from dataclasses import replace

from living_world.external_world.model import (
    ContactState,
    ExternalWorldReference,
    NPCExternalReference,
)
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState

_TRANSITIONS: dict[ContactState, frozenset[ContactState]] = {
    ContactState.UNKNOWN: frozenset({ContactState.KNOWN}),
    ContactState.KNOWN: frozenset({ContactState.CONTACTABLE, ContactState.UNAVAILABLE}),
    ContactState.CONTACTABLE: frozenset({ContactState.UNAVAILABLE}),
    ContactState.UNAVAILABLE: frozenset({ContactState.CONTACTABLE}),
}

_CONTACT_PROSE = {
    ContactState.UNKNOWN: "No direct knowledge of contact is available.",
    ContactState.KNOWN: "This external contact is known but not yet reachable.",
    ContactState.CONTACTABLE: "This external contact can currently be reached.",
    ContactState.UNAVAILABLE: "This external contact is currently unavailable.",
}


class ExternalWorldReferenceManager:
    """Own deliberately partial off-map reference state and contact lifecycle."""

    def __init__(self, state: WorldState, events: EventManager) -> None:
        self._state = state
        self._events = events
        self._next_id = 1

    def create(
        self,
        *,
        name: str,
        role: str,
        allowed_imports: tuple[str, ...] = (),
        allowed_exports: tuple[str, ...] = (),
        capacity: int,
        delay_ticks: int,
        cost_per_unit: int,
        reliability: float,
        contact_state: ContactState = ContactState.UNKNOWN,
    ) -> ExternalWorldReference:
        reference = ExternalWorldReference(
            id=self._candidate_id(),
            name=name,
            role=role,
            allowed_imports=allowed_imports,
            allowed_exports=allowed_exports,
            capacity=capacity,
            delay_ticks=delay_ticks,
            cost_per_unit=cost_per_unit,
            reliability=reliability,
            contact_state=contact_state,
            created_tick=self._state.tick,
        )
        if any(
            item.name.strip().casefold() == reference.name.strip().casefold()
            for item in self._state.external_world_references.values()
        ):
            raise ValueError(
                f"External reference name '{reference.name}' must be unique."
            )
        event_ids = frozenset(self._state.events)
        try:
            self._events.record(
                kind="external_world_reference_created",
                subject_id=reference.id,
                attributes={"name": reference.name, "role": reference.role},
            )
            self._state.external_world_references[reference.id] = reference
            self._next_id += 1
        except Exception:
            for event_id in set(self._state.events) - event_ids:
                self._state.events.pop(event_id, None)
            self._state.external_world_references.pop(reference.id, None)
            raise
        return reference

    def transition_contact(
        self, reference_id: str, contact_state: ContactState
    ) -> ExternalWorldReference:
        reference = self.get(reference_id)
        if reference is None:
            raise ValueError(f"Unknown external reference '{reference_id}'.")
        if not isinstance(contact_state, ContactState):
            raise TypeError("contact_state must be a ContactState.")
        if contact_state not in _TRANSITIONS[reference.contact_state]:
            raise ValueError(
                f"Invalid contact transition from {reference.contact_state.value} "
                f"to {contact_state.value}."
            )
        updated = replace(reference, contact_state=contact_state)
        event_ids = frozenset(self._state.events)
        try:
            self._events.record(
                kind="external_contact_state_changed",
                subject_id=reference.id,
                attributes={
                    "previous": reference.contact_state.value,
                    "current": contact_state.value,
                },
            )
            self._state.external_world_references[reference.id] = updated
        except Exception:
            for event_id in set(self._state.events) - event_ids:
                self._state.events.pop(event_id, None)
            self._state.external_world_references[reference.id] = reference
            raise
        return updated

    def get(self, reference_id: str) -> ExternalWorldReference | None:
        return self._state.external_world_references.get(reference_id)

    def all(self) -> tuple[ExternalWorldReference, ...]:
        return tuple(
            sorted(
                self._state.external_world_references.values(), key=lambda item: item.id
            )
        )

    def npc_interpretation(self, reference_id: str) -> NPCExternalReference:
        reference = self.get(reference_id)
        if reference is None:
            raise ValueError(f"Unknown external reference '{reference_id}'.")
        return NPCExternalReference(
            name=reference.name,
            role=reference.role,
            contact_description=_CONTACT_PROSE[reference.contact_state],
        )

    def npc_interpretations(self) -> tuple[NPCExternalReference, ...]:
        return tuple(self.npc_interpretation(item.id) for item in self.all())

    def _candidate_id(self) -> str:
        while True:
            reference_id = f"external_reference_{self._next_id:06d}"
            if reference_id not in self._state.external_world_references:
                return reference_id
            self._next_id += 1
