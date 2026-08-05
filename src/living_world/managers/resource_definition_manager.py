from living_world.core.resource_definition import ResourceDefinition


class ResourceDefinitionManager:
    """Registry of loaded resource definitions."""

    def __init__(self) -> None:
        self._definitions: dict[str, ResourceDefinition] = {}

    def register(
        self,
        definition: ResourceDefinition,
    ) -> None:
        self._definitions[definition.key] = definition

    def get(
        self,
        key: str,
    ) -> ResourceDefinition:
        return self._definitions[key]

    def exists(
        self,
        key: str,
    ) -> bool:
        return key in self._definitions
