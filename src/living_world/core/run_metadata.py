from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """Immutable identity binding a persisted world to its scenario input."""

    scenario_key: str
    schema_version: int
    seed: int
    configuration_fingerprint: str

    def __post_init__(self) -> None:
        if not self.scenario_key.strip():
            raise ValueError("Scenario key cannot be empty.")
        if self.schema_version < 1:
            raise ValueError("Scenario schema version must be positive.")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise TypeError("Scenario seed must be an integer.")
        if not self.configuration_fingerprint.strip():
            raise ValueError("Configuration fingerprint cannot be empty.")
