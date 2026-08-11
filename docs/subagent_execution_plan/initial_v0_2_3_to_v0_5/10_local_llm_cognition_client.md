# 10 — Local LLM cognition client

## Task Description

Provide loopback-only Ollama and llama.cpp adapters for structured NPC
reasoning proposals, with no authority or raw-world-data access.

## Context Needed

- Create: `docs/subagent_execution_plan/10_local_llm_cognition_client-report.md`.
- Create: `src/living_world/cognition/npc_cognition_client.py`,
  `src/living_world/cognition/local_llm_cognition_format.py`,
  `src/living_world/cognition/ollama_cognition_client.py`,
  `src/living_world/cognition/llama_cpp_cognition_client.py`.
- Create tests: `tests/test_npc_cognition_client.py`,
  `tests/test_ollama_cognition_client.py`, `tests/test_llama_cpp_cognition_client.py`.
- Edit: `src/living_world/cognition/__init__.py`, `docs/local_llm_setup.md`,
  `CHANGELOG.md`, `docs/project_journal.md`.
- Reuse unchanged: `perception/local_llm_http.py` and its loopback validation
  design. Know the filtered `NPCContext` from Task 09. This task establishes
  the model-facing proposal types consumed by Task 11.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class ActionOption:
    key: str
    description: str
    target_labels: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class ActionRequest:
    action_key: str
    target_label: str | None
    rationale: str
    arguments: Mapping[str, str] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class NPCDecision:
    spoken_text: str | None
    action_request: ActionRequest | None

class NPCCognitionClient(Protocol):
    @property
    def provider_name(self) -> str: ...
    def decide(self, context: NPCContext, actions: tuple[ActionOption, ...]) -> NPCDecision: ...

class OllamaCognitionClient:
    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 30.0,
        transport: JsonHttpTransport | None = None,
    ) -> None: ...
    @property
    def provider_name(self) -> str: ...
    def decide(self, context: NPCContext, actions: tuple[ActionOption, ...]) -> NPCDecision: ...

class LlamaCppCognitionClient:
    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:8080",
        timeout_seconds: float = 30.0,
        transport: JsonHttpTransport | None = None,
    ) -> None: ...
    @property
    def provider_name(self) -> str: ...
    def decide(self, context: NPCContext, actions: tuple[ActionOption, ...]) -> NPCDecision: ...

class NPCCognitionClientError(Exception): ...
class NPCCognitionInvalidResponseError(NPCCognitionClientError): ...

def serialize_decision_request(
    context: NPCContext,
    actions: tuple[ActionOption, ...],
) -> str: ...
def parse_decision_response(
    content: object,
    actions: tuple[ActionOption, ...],
) -> NPCDecision: ...
```

- Ollama and llama.cpp clients are loopback HTTP adapters only and return
  structured JSON. No cloud endpoint, API key, model-side tool call, or
  runtime object is allowed.
- The serializer accepts only `NPCContext` plus offered `ActionOption`s.
- Client output is untrusted and contains no claim of action success.
- Action keys and target labels are proposal vocabulary, never engine IDs.
- All client-facing `ActionOption`, `ActionRequest`, and `NPCDecision` text
  rejects conventional internal record IDs (for example `entity_000001`,
  `observation_000001`, and `memory_000001`). This is a format-level safeguard
  because cognition clients deliberately have no `WorldState` from which to
  resolve arbitrary engine IDs.
- All public value objects validate non-empty visible strings; action target
  labels and `ActionOption.target_labels` are tuples of unique non-empty
  strings, and `ActionRequest.arguments` is a defensively copied read-only
  mapping of non-empty string keys and values. `NPCDecision` must contain at
  least one of spoken text or an action request.
- `serialize_decision_request()` accepts exactly the safe `NPCContext` fields
  and offered action vocabulary. It includes neither runtime objects nor
  internal IDs, raw attributes, evidence, metadata, or raw numerical
  capabilities. `parse_decision_response()` accepts either `null` or an action
  object, rejects extra/malformed fields, and rejects an action key or target
  label not offered in its `actions` argument. It performs proposal-vocabulary
  validation only; Task 11 remains the sole engine authority for action
  validation/application.

## Test Criteria

- Request serialization excludes IDs, raw attributes, evidence, metadata,
  `WorldState`, and raw numerical capabilities.
- Invalid JSON/schema/network output produces a dedicated client error.
- Non-loopback URLs are rejected.
- Valid structured response round-trips without side effects.

## Orchestrator Report

Create `docs/subagent_execution_plan/10_local_llm_cognition_client-report.md`.
Report provider request/response contracts, loopback enforcement, prompt-boundary
evidence, error handling, and validation results.

## Boundary

- Touch only stated cognition-client modules/tests and local-LLM docs.
- The approved report artifact is also allowed.
- Do not modify existing perception clients or action application code.
- Adhere to the distinction between the perception LLM (engine subsystem) and
  cognition LLM (NPC reasoning endpoint).
