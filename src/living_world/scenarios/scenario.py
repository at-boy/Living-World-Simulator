from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

import yaml

from living_world.core.run_metadata import RunMetadata

_INTERNAL_ID = re.compile(
    r"(?:entity|relationship|event|observation|belief|experience|memory|"
    r"knowledge|npc_relationship)_\d+"
)


class ScenarioLoadError(ValueError):
    """Raised when a scenario document is invalid."""


class ScenarioCompatibilityError(ValueError):
    """Raised when a scenario does not match a persisted run."""


@dataclass(frozen=True, slots=True)
class ScenarioEntity:
    label: str
    definition_key: str
    name: str
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _freeze_mapping(self.attributes))


@dataclass(frozen=True, slots=True)
class ScenarioRelationship:
    kind: str
    source_label: str
    target_label: str
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _freeze_mapping(self.attributes))


@dataclass(frozen=True, slots=True)
class LoadedScenario:
    source_path: Path
    key: str
    schema_version: int
    seed: int
    definition_path: Path
    default_max_ticks: int
    terminal_conditions: tuple[str, ...]
    entities: tuple[ScenarioEntity, ...]
    relationships: tuple[ScenarioRelationship, ...]
    configuration_fingerprint: str

    @property
    def run_metadata(self) -> RunMetadata:
        return RunMetadata(
            self.key, self.schema_version, self.seed, self.configuration_fingerprint
        )


class ScenarioLoader(Protocol):
    def load(self, path: Path) -> LoadedScenario: ...


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            if key in result:
                raise ScenarioLoadError(f"Duplicate YAML key {key!r}.")
        except TypeError as exc:
            raise ScenarioLoadError("YAML mapping keys must be scalars.") from exc
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


class YAMLScenarioLoader:
    """Load a strict version-one scenario document."""

    def load(self, path: Path) -> LoadedScenario:
        source = path.resolve()
        try:
            document = _mapping(
                yaml.load(source.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader),
                "scenario",
            )
        except (OSError, yaml.YAMLError, ScenarioLoadError) as exc:
            raise ScenarioLoadError(f"Unable to load scenario '{path}': {exc}") from exc
        _fields(
            document,
            {
                "schema_version",
                "key",
                "seed",
                "definitions",
                "run",
                "entities",
                "relationships",
            },
            "scenario",
        )
        version = _integer(document.get("schema_version"), "schema_version")
        if version != 1:
            raise ScenarioLoadError(f"Unsupported scenario schema version {version!r}.")
        key = _text(document.get("key"), "key")
        seed = _integer(document.get("seed"), "seed")
        definitions = self._relative_path(
            source.parent,
            _text(document.get("definitions"), "definitions"),
        )
        run = _mapping(document.get("run", {}), "run")
        _fields(run, {"max_ticks", "terminal_conditions"}, "run")
        max_ticks = _integer(run.get("max_ticks", 0), "run.max_ticks")
        if max_ticks < 0:
            raise ScenarioLoadError("run.max_ticks must be non-negative.")
        conditions = _texts(
            run.get("terminal_conditions", []), "run.terminal_conditions"
        )
        entities = self._entities(document.get("entities", []))
        relationships = self._relationships(document.get("relationships", []), entities)
        normalized = {
            "schema_version": version,
            "key": key,
            "seed": seed,
            "definitions": definitions.read_text(encoding="utf-8"),
            "run": {"max_ticks": max_ticks, "terminal_conditions": conditions},
            "entities": [
                {
                    "label": item.label,
                    "definition": item.definition_key,
                    "name": item.name,
                    "attributes": mutable_attributes(item.attributes),
                }
                for item in entities
            ],
            "relationships": [
                {
                    "kind": item.kind,
                    "source": item.source_label,
                    "target": item.target_label,
                    "attributes": mutable_attributes(item.attributes),
                }
                for item in relationships
            ],
        }
        serialized = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        fingerprint = hashlib.sha256(serialized.encode()).hexdigest()
        return LoadedScenario(
            source,
            key,
            version,
            seed,
            definitions,
            max_ticks,
            conditions,
            entities,
            relationships,
            fingerprint,
        )

    @staticmethod
    def _relative_path(parent: Path, value: str) -> Path:
        candidate = Path(value)
        if candidate.is_absolute():
            raise ScenarioLoadError(
                "definitions must be relative to the scenario directory."
            )
        result = (parent / candidate).resolve()
        if not result.is_relative_to(parent.resolve()):
            raise ScenarioLoadError("definitions cannot escape the scenario directory.")
        try:
            result.read_text(encoding="utf-8")
        except OSError as exc:
            raise ScenarioLoadError(f"Unable to read definitions '{value}'.") from exc
        return result

    @staticmethod
    def _entities(value: object) -> tuple[ScenarioEntity, ...]:
        result: list[ScenarioEntity] = []
        labels: set[str] = set()
        for index, raw in enumerate(_list(value, "entities")):
            item = _mapping(raw, f"entities[{index}]")
            _fields(
                item,
                {"label", "definition", "name", "attributes"},
                f"entities[{index}]",
            )
            label = _text(item.get("label"), f"entities[{index}].label")
            if label in labels:
                raise ScenarioLoadError(f"Duplicate entity label '{label}'.")
            labels.add(label)
            attributes = _mapping(
                item.get("attributes", {}), f"entities[{index}].attributes"
            )
            _json_value(attributes, f"entities[{index}].attributes")
            result.append(
                ScenarioEntity(
                    label,
                    _text(item.get("definition"), "definition"),
                    _text(item.get("name"), "name"),
                    deepcopy(dict(attributes)),
                )
            )
        return tuple(result)

    @staticmethod
    def _relationships(
        value: object, entities: tuple[ScenarioEntity, ...]
    ) -> tuple[ScenarioRelationship, ...]:
        labels = {entity.label for entity in entities}
        result: list[ScenarioRelationship] = []
        for index, raw in enumerate(_list(value, "relationships")):
            item = _mapping(raw, f"relationships[{index}]")
            _fields(
                item,
                {"kind", "source", "target", "attributes"},
                f"relationships[{index}]",
            )
            source = _text(item.get("source"), "source")
            target = _text(item.get("target"), "target")
            if source not in labels or target not in labels:
                raise ScenarioLoadError(
                    "Scenario relationships must reference entity labels."
                )
            attributes = _mapping(item.get("attributes", {}), "relationship attributes")
            _json_value(attributes, "relationship attributes")
            result.append(
                ScenarioRelationship(
                    _text(item.get("kind"), "kind"),
                    source,
                    target,
                    deepcopy(dict(attributes)),
                )
            )
        return tuple(result)


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ScenarioLoadError(f"{name} must be a mapping with string keys.")
    return value


def _list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ScenarioLoadError(f"{name} must be a list.")
    return value


def _fields(value: Mapping[str, object], allowed: set[str], name: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ScenarioLoadError(f"Unknown {name} field(s): {names}.")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioLoadError(f"{name} must be a non-empty string.")
    if _INTERNAL_ID.search(value):
        raise ScenarioLoadError(f"{name} cannot contain an internal record ID.")
    return value


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ScenarioLoadError(f"{name} must be an integer.")
    return value


def _texts(value: object, name: str) -> tuple[str, ...]:
    result = tuple(_text(item, name) for item in _list(value, name))
    if len(result) != len(set(result)):
        raise ScenarioLoadError(f"{name} must not contain duplicates.")
    return result


def _json_value(value: object, name: str) -> None:
    _validate_json_mapping_keys(value, name)
    try:
        serialized = json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ScenarioLoadError(f"{name} must contain JSON-compatible values.") from exc
    if _INTERNAL_ID.search(serialized):
        raise ScenarioLoadError(f"{name} cannot contain an internal record ID.")


def _validate_json_mapping_keys(value: object, name: str) -> None:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ScenarioLoadError(f"{name} must contain mappings with string keys.")
        for item in value.values():
            _validate_json_mapping_keys(item, name)
    elif isinstance(value, list | tuple):
        for item in value:
            _validate_json_mapping_keys(item, name)


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def mutable_attributes(value: Mapping[str, object]) -> dict[str, object]:
    """Return a detached mutable JSON tree for manager-owned runtime state."""

    return {key: _mutable_value(item) for key, item in value.items()}


def _mutable_value(value: object) -> object:
    if isinstance(value, Mapping):
        return mutable_attributes(value)
    if isinstance(value, tuple):
        return [_mutable_value(item) for item in value]
    return value
