from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Definition:
    """Definition loaded by DefinitionManager.

    Definitions currently originate in Python.
    A repository may later load them from YAML without changing the engine API.
    """

    name: str
    properties: dict[str, object] = field(default_factory=dict)
    systems: tuple[str, ...] = ()
