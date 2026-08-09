from living_world.core.definition import Definition


class DefinitionManager:
    """Registry of loaded definitions."""

    def __init__(self) -> None:
        self._definitions: dict[str, Definition] = {}

    def register(self, definition: Definition) -> None:
        self.register_many((definition,))

    def register_many(self, definitions: tuple[Definition, ...]) -> None:
        """Register a complete definition set without partial updates."""

        staged_definitions: dict[str, Definition] = {}

        for definition in definitions:
            if definition.key in staged_definitions:
                raise ValueError(f"Duplicate definition key '{definition.key}'.")

            staged_definitions[definition.key] = definition

        self._definitions.update(staged_definitions)

    def get(self, key: str) -> Definition:
        return self._definitions[key]

    def exists(self, key: str) -> bool:
        return key in self._definitions

    def all(self) -> tuple[Definition, ...]:
        """Return definitions in their registration order."""

        return tuple(self._definitions.values())
