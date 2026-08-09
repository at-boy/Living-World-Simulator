from living_world.core.observation import Observation
from living_world.state.world_state import WorldState


class ObservationManager:
    """Records immutable observations of the world."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._next_observation_id = 1

    def add(self, observation: Observation) -> None:
        self._state.observations[observation.id] = observation

    def record(
        self,
        *,
        observer: str,
        subject: str,
        description: str,
        confidence: float,
        evidence: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Observation:
        """Record a new immutable observation."""

        if not observer.strip():
            raise ValueError("Observation observer cannot be empty.")

        if not subject.strip():
            raise ValueError("Observation subject cannot be empty.")

        if not description.strip():
            raise ValueError("Observation description cannot be empty.")

        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Observation confidence must be between 0.0 and 1.0.")

        observation = Observation(
            id=self._generate_id(),
            tick=self._state.tick,
            observer=observer,
            subject=subject,
            description=description,
            confidence=confidence,
            evidence=evidence or {},
            metadata=metadata or {},
        )

        self.add(observation)

        return observation

    def get(self, observation_id: str) -> Observation | None:
        return self._state.observations.get(observation_id)

    def observations_for(
        self,
        observer: str,
    ) -> tuple[Observation, ...]:
        return tuple(
            observation
            for observation in self._state.observations.values()
            if observation.observer == observer
        )

    def _generate_id(self) -> str:
        while True:
            observation_id = f"observation_{self._next_observation_id:06d}"
            self._next_observation_id += 1

            if observation_id not in self._state.observations:
                return observation_id

    def all(self) -> tuple[Observation, ...]:
        return tuple(self._state.observations.values())
