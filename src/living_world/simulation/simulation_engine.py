from pathlib import Path

from living_world.cognition.consolidation import (
    CognitiveConsolidationSystem,
    SleepCognitiveConsolidator,
)
from living_world.core.definition import Definition
from living_world.definitions.yaml_loader import YAMLWorldDefinitionLoader
from living_world.managers.belief_manager import BeliefManager
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.managers.experience_manager import ExperienceManager
from living_world.managers.knowledge_manager import KnowledgeManager
from living_world.managers.memory_manager import MemoryManager
from living_world.managers.npc_relationship_manager import NPCRelationshipManager
from living_world.managers.observation_manager import ObservationManager
from living_world.managers.relationship_manager import RelationshipManager
from living_world.managers.resource_definition_manager import ResourceDefinitionManager
from living_world.repositories.graph_repository import GraphRepository
from living_world.simulation.simulation_scheduler import SimulationScheduler
from living_world.state.world_state import WorldState
from living_world.systems.construction_system import ConstructionSystem
from living_world.systems.housing_system import HousingSystem
from living_world.systems.organization_system import OrganizationSystem
from living_world.systems.population_system import PopulationSystem
from living_world.systems.production_system import ProductionSystem
from living_world.systems.progress_system import ProgressSystem
from living_world.systems.resource_system import ResourceSystem
from living_world.systems.schedule_system import ScheduleSystem
from living_world.systems.settlement_system import SettlementSystem
from living_world.systems.simulation_system import SimulationSystem
from living_world.systems.trade_system import TradeSystem
from living_world.systems.weather_system import WeatherSystem


class SimulationEngine:
    """High-level façade over the Living World runtime."""

    def __init__(self, repository: GraphRepository | None = None) -> None:
        self._repository = repository
        self._state = WorldState() if repository is None else repository.load_world()

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

        self._memories = MemoryManager(
            self._state,
        )

        self._knowledge = KnowledgeManager(
            self._state,
        )

        self._npc_relationships = NPCRelationshipManager(
            self._state,
        )

        self._scheduler = SimulationScheduler(
            self._state,
        )

        self._resources = ResourceSystem()

        self.register_system(
            WeatherSystem(
                self._definitions,
                self._entities,
                self._events,
            )
        )
        self.register_system(
            PopulationSystem(
                self._definitions,
                self._entities,
                self._events,
            )
        )
        self.register_system(
            OrganizationSystem(
                self._definitions,
                self._entities,
                self._events,
            )
        )
        self.register_system(
            SettlementSystem(
                self._definitions,
                self._entities,
                self._events,
            )
        )
        self.register_system(
            ProgressSystem(
                self._entities,
            )
        )
        self.register_system(
            ConstructionSystem(
                self._definitions,
                self._entities,
                self._events,
                self._resources,
            )
        )
        self.register_system(
            HousingSystem(
                self._definitions,
                self._entities,
                self._events,
            )
        )
        self.register_system(
            ProductionSystem(
                self._definitions,
                self._entities,
                self._events,
                self._resources,
            )
        )
        self.register_system(
            TradeSystem(
                self._entities,
                self._events,
                self._resources,
            )
        )
        self.register_system(
            ScheduleSystem(
                self._entities,
                self._events,
            )
        )
        self.register_system(
            CognitiveConsolidationSystem(
                SleepCognitiveConsolidator(
                    entities=self._entities,
                    observations=self._observations,
                    memories=self._memories,
                    experiences=self._experiences,
                    beliefs=self._beliefs,
                ),
                self._entities,
            )
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

    @property
    def memories(self) -> MemoryManager:
        return self._memories

    @property
    def knowledge(self) -> KnowledgeManager:
        return self._knowledge

    @property
    def npc_relationships(self) -> NPCRelationshipManager:
        return self._npc_relationships

    def register_system(
        self,
        system: SimulationSystem,
    ) -> None:
        self._scheduler.register(system)

    def load_definitions(self, path: Path) -> tuple[Definition, ...]:
        """Load and atomically register definition vocabulary from YAML."""

        definitions = YAMLWorldDefinitionLoader().load(path)
        self._definitions.register_many(definitions)
        return definitions

    def step(self) -> None:
        self._scheduler.step()

    def run(
        self,
        steps: int,
    ) -> None:
        self._scheduler.run(steps)

    def save_world(self) -> None:
        """Persist the current state when this engine was composed with a repository."""

        if self._repository is None:
            return

        self._repository.save_world(self._state)

    @property
    def resource_definitions(
        self,
    ) -> ResourceDefinitionManager:
        return self._resource_definitions
