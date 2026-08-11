from living_world.core.event import Event
from living_world.state.world_state import WorldState


class EventManager:
    """Records immutable world history."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._next_event_id = 1

    def add(self, event: Event) -> None:
        self._state.events[event.id] = event

    def record(
        self,
        *,
        kind: str,
        subject_id: str | None = None,
        attributes: dict[str, object] | None = None,
    ) -> Event:
        """Record a new immutable event."""

        if not kind.strip():
            raise ValueError("Event kind cannot be empty.")

        event = Event(
            id=self._generate_id(),
            tick=self._state.tick,
            kind=kind,
            subject_id=subject_id,
            attributes=attributes or {},
        )

        self.add(event)

        return event

    def get(self, event_id: str) -> Event | None:
        return self._state.events.get(event_id)

    def events_for(
        self,
        subject_id: str,
    ) -> tuple[Event, ...]:
        return tuple(
            event
            for event in self._state.events.values()
            if event.subject_id == subject_id
        )

    def _generate_id(self) -> str:
        while True:
            event_id = f"event_{self._next_event_id:06d}"
            self._next_event_id += 1

            if event_id not in self._state.events:
                return event_id
