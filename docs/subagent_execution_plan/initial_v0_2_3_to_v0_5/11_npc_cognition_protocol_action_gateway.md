# 11 — NPC Cognition Protocol and action gateway

## Task Description

Connect filtered cognition to offered action proposals, then require
simulation-owned validation and manager-owned application for every action.

## Context Needed

- Create: `docs/subagent_execution_plan/11_npc_cognition_protocol_action_gateway-report.md`.
- Create: `src/living_world/cognition/decision_engine.py`,
  `src/living_world/cognition/action_resolution.py`,
  `tests/test_decision_engine.py`, `tests/test_action_resolution.py`,
  `tests/test_simulation_engine_actions.py`.
- Edit: `src/living_world/simulation/simulation_engine.py`,
  `src/living_world/cognition/__init__.py`, `CHANGELOG.md`,
  `docs/project_journal.md`, `docs/backlog.md`, `docs/core_model.md`,
  `docs/engine_glossary.md`, and create an ADR describing the proposal-to-
  application authority boundary.
- Know: `NPCContext`, `NPCCognitionClient`, `ActionOption`, `ActionRequest`,
  and `NPCDecision` from Task 10; also `EventManager`, all managers, and the
  manager-owned mutation rule.

## Interface Contract

```python
class DecisionEngine:
    def __init__(self, client: NPCCognitionClient) -> None: ...
    def decide(self, context: NPCContext, actions: tuple[ActionOption, ...]) -> NPCDecision: ...

@dataclass(frozen=True, slots=True)
class ActionResolution:
    accepted: bool
    reason: str

class NPCActionResolver:
    def __init__(
        self,
        actions: tuple[ActionOption, ...],
        handlers: tuple[NPCActionHandler, ...] = (),
    ) -> None: ...
    def resolve(
        self, *, actor_id: str, request: ActionRequest
    ) -> ActionResolution: ...

class NPCActionHandler(Protocol):
    def supports(self, action_key: str) -> bool: ...
    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution: ...
    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution: ...
```

- `ActionResolution.reason` is non-empty explanatory prose. `accepted=False`
  means no handler application happened. A handler may return only an accepted
  resolution from `apply()`; a rejected result from `apply()` is a contract
  violation.
- The decision engine accepts only offered actions and target labels, including
  when a deliberately untrusted/fake client returns a directly constructed
  `NPCDecision` rather than one parsed by Task 10's client format.
- The resolver repeats that vocabulary validation before handler dispatch,
  validates first, and invokes `apply()` only if validation returns an accepted
  resolution. It returns a rejected resolution for invalid or unsupported
  proposals; it must not raise an untrusted request into a mutation path.
  `actor_id` is an engine-only resolver input and never reaches an LLM.
- The generic resolver owns no domain mutation rules and does not record a
  generic event. Only a successful handler `apply()` may use managers and
  record its single domain event. No default handler invents construction,
  trade, or occupation rules.
- Add `SimulationEngine.resolve_npc_action(*, resolver: NPCActionResolver,
  actor_id: str, request: ActionRequest) -> ActionResolution` as the thin
  engine-owned entry point. It delegates to the supplied resolver; it does not
  expose `WorldState`, managers, or actor IDs to `DecisionEngine`/LLM code.

## Test Criteria

- A rejected request changes no state and records no event.
- A valid stub handler mutates only through a manager and records one event.
- Unknown keys, undeclared targets, IDs, and malformed arguments are rejected.
- A malicious direct client decision outside the offered vocabulary is
  rejected by `DecisionEngine`; LLM output has no success/result field and
  cannot apply an action.
- Calling `apply()` after a rejected validation result, or returning a rejected
  result from `apply()`, is rejected as a handler-contract violation with no
  gateway-created event.
- The engine entry point delegates without letting the LLM see `actor_id`.
- `make` passes.

## Orchestrator Report

Create `docs/subagent_execution_plan/11_npc_cognition_protocol_action_gateway-report.md`.
Report proposal validation, rejected-action non-mutation evidence, accepted
handler/event evidence, public interfaces, and validation results.

## Boundary

- Touch only stated cognition/action/engine files, tests, and docs.
- The approved report artifact is also allowed.
- Do not add domain action behavior; later domain modules register handlers.
- Strictly preserve “LLMs reason and propose; simulation validates and applies.”
