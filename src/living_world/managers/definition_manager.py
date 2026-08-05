from living_world.core.definition import Definition


class DefinitionManager:
    """Owns loaded definitions, not their storage."""

    def __init__(self) -> None:
        self._definitions: dict[str, Definition] = {}

    def register(self, definition: Definition) -> None:
        self._definitions[definition.name] = definition

    def get(self, name: str) -> Definition:
        return self._definitions[name]

    def exists(self, name: str) -> bool:
        return name in self._definitions
