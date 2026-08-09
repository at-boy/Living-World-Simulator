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
  `src/living_world/cognition/__init__.py`, and standard docs/ADR.
- Know: `NPCContext`, `NPCCognitionClient`, `ActionOption`, `ActionRequest`,
  and `NPCDecision` from Task 10; also `EventManager`, all managers, and the
  manager-owned mutation rule.

## Interface Contract

```python
class DecisionEngine:
    def __init__(self, client: NPCCognitionClient) -> None: ...
    def decide(self, context: NPCContext, actions: tuple[ActionOption, ...]) -> NPCDecision: ...

class NPCActionHandler(Protocol):
    def supports(self, action_key: str) -> bool: ...
    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution: ...
    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution: ...
```

- The decision engine accepts only offered actions and target labels.
- `NPCActionResolver.resolve(actor_id: str, request: ActionRequest) -> ActionResolution`
  validates before applying. `actor_id` is engine-only and never reaches the
  LLM.
- Only a successful handler `apply()` may use managers and record an event.
  No default handler invents construction, trade, or occupation rules.

## Test Criteria

- A rejected request changes no state and records no event.
- A valid stub handler mutates only through a manager and records one event.
- Unknown keys, undeclared targets, IDs, and malformed arguments are rejected.
- LLM output cannot claim success or set an authoritative result.
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
