from living_world.managers.belief_manager import BeliefManager
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.managers.experience_manager import ExperienceManager
from living_world.managers.observation_manager import ObservationManager
from living_world.managers.relationship_manager import RelationshipManager
from living_world.managers.resource_definition_manager import ResourceDefinitionManager
from living_world.simulation.simulation_scheduler import SimulationScheduler
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class SimulationEngine:
    """High-level façade over the Living World runtime."""

    def __init__(self) -> None:
        self._state = WorldState()

        self._definitions = DefinitionManager()

        self._resource_definitions = ResourceDefinitionManager()

        self._entities = EntityManager(
            self._state,
            self._definitions,
        )

        self._relationships = RelationshipManager(
            self._state,
            self._entities,
        )

        self._events = EventManager(
            self._state,
        )

        self._observations = ObservationManager(
            self._state,
        )

        self._beliefs = BeliefManager(
            self._state,
        )

        self._experiences = ExperienceManager(
            self._state,
        )

        self._scheduler = SimulationScheduler(
            self._state,
        )

    @property
    def state(self) -> WorldState:
        return self._state

    @property
    def definitions(self) -> DefinitionManager:
        return self._definitions

    @property
    def entities(self) -> EntityManager:
        return self._entities

    @property
    def relationships(self) -> RelationshipManager:
        return self._relationships

    @property
    def events(self) -> EventManager:
        return self._events

    @property
    def observations(
        self,
    ) -> ObservationManager:
        return self._observations

    @property
    def beliefs(self) -> BeliefManager:
        return self._beliefs

    @property
    def experiences(self) -> ExperienceManager:
        return self._experiences

    def register_system(
        self,
        system: SimulationSystem,
    ) -> None:
        self._scheduler.register(system)

    def step(self) -> None:
        self._scheduler.step()

    def run(
        self,
        steps: int,
    ) -> None:
        self._scheduler.run(steps)

    @property
    def resource_definitions(
        self,
    ) -> ResourceDefinitionManager:
        return self._resource_definitions
