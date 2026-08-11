# Task 11 — NPC Cognition Protocol and Action Gateway Report

## Status

Ready for orchestrator review. No commit was created.

## Implementation

- Added `DecisionEngine`, which calls an `NPCCognitionClient` only with a
  filtered `NPCContext` and offered `ActionOption` vocabulary, then validates
  the returned `NPCDecision` again.
- Added frozen, slots-based `ActionResolution`, the `NPCActionHandler`
  protocol, and `NPCActionResolver`.
- Added the thin engine-owned
  `SimulationEngine.resolve_npc_action(*, resolver, actor_id, request)`
  delegation path.
- The generic resolver has no domain handler, manager mutation, or generic
  event behavior. It validates offered action keys/targets and request shape,
  invokes `validate()` before `apply()`, and returns rejected resolutions for
  untrusted or unsupported proposals. A handler contract violation raises a
  dedicated error rather than falsely returning a rejected applied resolution.

## Public Interfaces

```python
class DecisionEngine:
    def __init__(self, client: NPCCognitionClient) -> None: ...
    def decide(
        self,
        context: NPCContext,
        actions: tuple[ActionOption, ...],
    ) -> NPCDecision: ...

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
        self,
        *,
        actor_id: str,
        request: ActionRequest,
    ) -> ActionResolution: ...

class NPCActionHandler(Protocol):
    def supports(self, action_key: str) -> bool: ...
    def validate(
        self, *, actor_id: str, request: ActionRequest
    ) -> ActionResolution: ...
    def apply(
        self, *, actor_id: str, request: ActionRequest
    ) -> ActionResolution: ...

class NPCActionHandlerContractError(RuntimeError): ...
```

## Evidence

- Decision-engine tests prove that a fake client returning a directly
  constructed decision with an unknown key, undeclared target, or target for a
  targetless action is rejected.
- Resolver tests prove rejected validation does not call `apply()`, mutate an
  entity, or record an event.
- A test-only domain handler mutates only through `EntityManager` and records
  exactly one event through `EventManager` after successful validation.
- Unknown action keys, undeclared targets, an internal entity ID supplied as a
  target, malformed arguments, and a non-`ActionRequest` object all return a
  rejected resolution with no mutation or event.
- The engine entry-point test delegates to the resolver without involving a
  cognition client or exposing its actor ID to one.

## Files Changed

Implementation and tests:

- `src/living_world/cognition/decision_engine.py`
- `src/living_world/cognition/action_resolution.py`
- `src/living_world/cognition/__init__.py`
- `src/living_world/simulation/simulation_engine.py`
- `tests/test_decision_engine.py`
- `tests/test_action_resolution.py`
- `tests/test_simulation_engine_actions.py`

Documentation:

- `docs/adr/ADR-0010-npc-action-authority-gateway.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/backlog.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- this report

The task plan and saved subagent prompt are approved plan artifacts in the
same directory and were already present in the working tree for this task.

## Authority and Boundary Compliance

The LLM receives no actor ID, `WorldState`, manager, event interface, success
field, or action-result interface. `NPCDecision` remains an untrusted proposal.
Only a domain handler may mutate through managers and record a domain event
after successful validation. No construction, trade, occupation, conversation,
or other domain action behavior was added.

Only Task 11's permitted cognition, engine, test, documentation, ADR, and
report files were created or edited for the implementation.

## Validation

Executed successfully from the repository root:

```text
make
  Ruff: passed
  Black: passed
  pytest: 275 passed
  examples/001 through examples/019: passed

make examples
  examples/001 through examples/019: passed

git diff --check
  passed (no output)
```

## Blockers and Deferred Work

None. Domain actions remain intentionally deferred: a future module must
provide an explicit `NPCActionHandler` with its own manager-owned mutation and
domain event policy.
