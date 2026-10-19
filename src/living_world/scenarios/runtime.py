from collections.abc import Mapping
from dataclasses import fields
from types import MappingProxyType

from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.relationship_manager import RelationshipManager
from living_world.scenarios.scenario import (
    LoadedScenario,
    ScenarioCompatibilityError,
    mutable_attributes,
)
from living_world.state.world_state import WorldState


class ScenarioRuntimeManager:
    """Own atomic initial-world binding and persisted run identity mutation."""

    def __init__(self, state: WorldState, definitions: DefinitionManager) -> None:
        self._state = state
        self._definitions = definitions

    def bind(
        self,
        scenario: LoadedScenario,
        definitions: tuple[Definition, ...],
    ) -> bool:
        """Bind a fresh world, or validate and reload an existing binding."""

        metadata = self._state.run_metadata
        if metadata is not None and metadata != scenario.run_metadata:
            raise ScenarioCompatibilityError(
                "Scenario identity, seed, or configuration does not match "
                "the saved run."
            )
        if metadata is None and self._world_has_records():
            raise ScenarioCompatibilityError(
                "A populated legacy world cannot be bound to a scenario implicitly."
            )
        self._validate_definitions(scenario, definitions)
        if metadata is not None:
            self._validate_bindings(scenario)
            self._definitions.register_many(definitions)
            return False

        staged_state = WorldState()
        staged_definitions = DefinitionManager()
        staged_definitions.register_many(definitions)
        entities = EntityManager(staged_state, staged_definitions)
        relationships = RelationshipManager(staged_state, entities)
        labels: dict[str, str] = {}
        for item in scenario.entities:
            entity = entities.create(
                definition_key=item.definition_key,
                name=item.name,
                attributes=mutable_attributes(item.attributes),
            )
            if item.label in labels:
                raise ScenarioCompatibilityError(
                    "Scenario entity labels must be unique."
                )
            labels[item.label] = entity.id
        for item in scenario.relationships:
            relationships.create(
                kind=item.kind,
                source_id=labels[item.source_label],
                target_id=labels[item.target_label],
                attributes=mutable_attributes(item.attributes),
            )

        self._definitions.register_many(definitions)
        self._state.entities.update(staged_state.entities)
        self._state.relationships.update(staged_state.relationships)
        self._state.scenario_entity_bindings.update(labels)
        self._state.run_metadata = scenario.run_metadata
        return True

    @staticmethod
    def _validate_definitions(
        scenario: LoadedScenario, definitions: tuple[Definition, ...]
    ) -> None:
        known = {definition.key for definition in definitions}
        unknown = sorted(
            {
                item.definition_key
                for item in scenario.entities
                if item.definition_key not in known
            }
        )
        if unknown:
            raise ScenarioCompatibilityError(
                f"Scenario uses unknown definition(s): {', '.join(unknown)}."
            )

    def entity_bindings(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self._state.scenario_entity_bindings))

    def validate_entity_removal(self, entity_id: str) -> None:
        if entity_id in self._state.scenario_entity_bindings.values():
            raise ScenarioCompatibilityError(
                "Scenario entity history must be retained."
            )

    def _validate_bindings(self, scenario: LoadedScenario) -> None:
        labels = self._state.scenario_entity_bindings
        if not labels:  # Legacy snapshots remain usable without replay.
            return
        if set(labels) != {item.label for item in scenario.entities} or len(
            set(labels.values())
        ) != len(labels):
            raise ScenarioCompatibilityError("Scenario entity bindings do not match.")
        for item in scenario.entities:
            entity = self._state.entities.get(labels[item.label])
            if entity is None or entity.definition_key != item.definition_key:
                raise ScenarioCompatibilityError(
                    "Scenario entity bindings do not match."
                )

    def _world_has_records(self) -> bool:
        return any(getattr(self._state, item.name) for item in fields(self._state))
