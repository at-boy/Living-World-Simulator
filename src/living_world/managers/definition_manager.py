from living_world.core.definition import Definition


class DefinitionManager:
    """Owns loaded definitions, not their storage."""

    def __init__(self) -> None:
        self._definitions: dict[str, Definition] = {}

    def register(self, definition: Definition) -> None:
        self._definitions[definition.key] = definition

    def get(self, key: str) -> Definition:
        return self._definitions[key]

    def exists(self, key: str) -> bool:
        return key in self._definitions
