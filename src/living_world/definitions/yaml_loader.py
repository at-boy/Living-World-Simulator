"""Validated YAML loading for definition vocabulary."""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import yaml

from living_world.core.definition import Definition


class WorldDefinitionLoadError(ValueError):
    """Raised when a world-definition document is invalid."""


class WorldDefinitionLoader(Protocol):
    """Loads definition vocabulary without constructing runtime state."""

    def load(self, path: Path) -> tuple[Definition, ...]:
        """Load and validate definitions from a document path."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)

        try:
            if key in mapping:
                raise WorldDefinitionLoadError(f"Duplicate YAML key '{key}'.")
        except TypeError as error:
            raise WorldDefinitionLoadError(
                "YAML mapping keys must be scalars."
            ) from error

        mapping[key] = loader.construct_object(value_node, deep=deep)

    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


class YAMLWorldDefinitionLoader:
    """Load the strict definition-only YAML document schema.

    The accepted top-level schema is ``{definitions: [...]}``.  Each definition
    contains ``key`` and optional ``initial_attributes`` and ``systems`` fields.
    """

    _TOP_LEVEL_FIELDS: frozenset[str] = frozenset({"definitions"})
    _DEFINITION_FIELDS: frozenset[str] = frozenset(
        {"key", "initial_attributes", "systems"}
    )

    def load(self, path: Path) -> tuple[Definition, ...]:
        """Return fully validated definitions in document order."""

        document = self._load_document(path)
        return self._parse_document(document)

    def _load_document(self, path: Path) -> object:
        try:
            with path.open(encoding="utf-8") as definition_file:
                return yaml.load(definition_file, Loader=_UniqueKeySafeLoader)
        except (OSError, yaml.YAMLError, WorldDefinitionLoadError) as error:
            raise WorldDefinitionLoadError(
                f"Unable to load world definitions from '{path}': {error}"
            ) from error

    def _parse_document(self, document: object) -> tuple[Definition, ...]:
        top_level = self._require_mapping(document, "The YAML document")
        self._reject_unknown_fields(top_level, self._TOP_LEVEL_FIELDS, "top-level")

        if "definitions" not in top_level:
            raise WorldDefinitionLoadError("The YAML document requires 'definitions'.")

        definitions_value = top_level["definitions"]
        if not isinstance(definitions_value, list):
            raise WorldDefinitionLoadError("'definitions' must be a list.")

        definitions = tuple(
            self._parse_definition(value, index)
            for index, value in enumerate(definitions_value)
        )
        self._validate_unique_definition_keys(definitions)
        return definitions

    def _parse_definition(self, value: object, index: int) -> Definition:
        definition_data = self._require_mapping(value, f"Definition at index {index}")
        self._reject_unknown_fields(
            definition_data,
            self._DEFINITION_FIELDS,
            f"definition at index {index}",
        )

        key = definition_data.get("key")
        if not isinstance(key, str) or not key.strip():
            raise WorldDefinitionLoadError(
                f"Definition at index {index} requires a non-empty string 'key'."
            )

        initial_attributes = definition_data.get("initial_attributes", {})
        self._validate_attributes(initial_attributes, f"definition '{key}'")

        systems = definition_data.get("systems", [])
        if not isinstance(systems, list) or any(
            not isinstance(system, str) or not system.strip() for system in systems
        ):
            raise WorldDefinitionLoadError(
                f"Definition '{key}' field 'systems' must be a list of non-empty strings."
            )

        return Definition(
            key=key,
            initial_attributes=dict(initial_attributes),
            systems=tuple(systems),
        )

    def _require_mapping(self, value: object, context: str) -> Mapping[object, object]:
        if not isinstance(value, Mapping):
            raise WorldDefinitionLoadError(f"{context} must be a mapping.")

        return value

    def _reject_unknown_fields(
        self,
        value: Mapping[object, object],
        allowed_fields: frozenset[str],
        context: str,
    ) -> None:
        unknown_fields = set(value).difference(allowed_fields)
        if unknown_fields:
            field_names = ", ".join(sorted(repr(field) for field in unknown_fields))
            raise WorldDefinitionLoadError(
                f"Unknown {context} schema field(s): {field_names}."
            )

    def _validate_attributes(self, value: object, context: str) -> None:
        if not isinstance(value, Mapping):
            raise WorldDefinitionLoadError(
                f"Definition {context} field 'initial_attributes' must be a mapping."
            )

        self._validate_attribute_value(value, context, set())

    def _validate_attribute_value(
        self,
        value: object,
        context: str,
        visited_values: set[int],
    ) -> None:
        if value is None or isinstance(value, str | int | float | bool):
            return

        value_id = id(value)
        if value_id in visited_values:
            raise WorldDefinitionLoadError(
                f"Definition {context} has recursive initial attributes."
            )

        if isinstance(value, Mapping):
            visited_values.add(value_id)
            for key, nested_value in value.items():
                if not isinstance(key, str):
                    raise WorldDefinitionLoadError(
                        f"Definition {context} initial attribute keys must be strings."
                    )
                self._validate_attribute_value(nested_value, context, visited_values)
            visited_values.remove(value_id)
            return

        if isinstance(value, list):
            visited_values.add(value_id)
            for nested_value in value:
                self._validate_attribute_value(nested_value, context, visited_values)
            visited_values.remove(value_id)
            return

        raise WorldDefinitionLoadError(
            f"Definition {context} initial attributes must contain only YAML scalar, "
            "mapping, or list values."
        )

    def _validate_unique_definition_keys(
        self,
        definitions: tuple[Definition, ...],
    ) -> None:
        seen_keys: set[str] = set()

        for definition in definitions:
            if definition.key in seen_keys:
                raise WorldDefinitionLoadError(
                    f"Duplicate definition key '{definition.key}'."
                )
            seen_keys.add(definition.key)
