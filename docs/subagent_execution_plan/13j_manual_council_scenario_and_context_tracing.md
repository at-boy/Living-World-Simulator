# 13j — Manual council scenario and safe context tracing

## Task Description

Turn the opt-in Ollama and llama.cpp council demonstrations into a longer,
meaningful five-NPC integration scenario. Use opaque engine IDs, several
engine-offered agenda alternatives, and a no-world-mutation manual action
handler so distinct opinions can produce distinct proposals and an accepted
gateway demonstration. Add an opt-in safe request-context trace for debugging
what each local model call received.

## Context Needed

- Create: `src/living_world/cognition/recording_cognition_client.py`,
  `tests/test_recording_cognition_client.py`,
  `docs/subagent_execution_plan/13j_manual_council_scenario_and_context_tracing-report.md`.
- Edit: `src/living_world/cognition/__init__.py`, both manual council examples,
  `tests/test_manual_council_examples.py`, `docs/local_llm_setup.md`,
  `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: Task 13h `turn_order_offset`, Task 13i dialogue guidance,
  `NPCCognitionClient`, `NPCContext`, `ActionOption`,
  `serialize_decision_request`, `NPCActionResolver`, and the Task 13 manual
  integration boundary.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class RecordedCognitionRequest:
    context: NPCContext
    actions: tuple[ActionOption, ...]

class RecordingCognitionClient:
    def __init__(self, inner: NPCCognitionClient) -> None: ...
    @property
    def provider_name(self) -> str: ...
    @property
    def recorded_requests(self) -> tuple[RecordedCognitionRequest, ...]: ...
    def decide(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> NPCDecision: ...
```

- The wrapper records only the pre-call, already-safe `NPCContext` and offered
  actions; it never records raw provider responses, exception text, transport
  payloads, `WorldState`, or internal IDs. It re-raises provider errors
  unchanged and performs no retries.
- Both manual examples accept an opt-in `--show-context` flag. With it, they
  print each recorded request using `serialize_decision_request`; without it,
  they retain normal concise output. They must never make a provider call at
  import time or during pytest collection.
- Manual engine IDs are opaque (`entity_...`/`organization_...` style) and not
  natural-language words that can collide with safe prose. Display labels remain
  Aster, Bryn, Cato, Dara, and Eris.
- Each manual scenario offers at least three qualitative alternatives matching
  the five NPC perspectives, uses a longer bounded discussion, and passes a
  nonzero `turn_order_offset`. It may encourage attendance through safe
  self-knowledge but must not force a model to attend.
- The manual-only action handler supports those alternatives through the normal
  resolver and returns an accepted no-mutation `ActionResolution`; it is not a
  world primitive, manager mutation, or production handler.

## Test Criteria

- Wrapper tests prove safe request order/immutability, transparent provider
  behavior/errors, and no response/error recording.
- Manual tests prove `--show-context` rendering serializes safe request context
  and action vocabulary but contains no raw provider output/error or world
  state; normal rendering remains concise.
- Tests verify the scenario has three alternatives, opaque IDs, a longer round
  limit, rotation offset, and a gateway handler path without asserting a live
  model's decision.
- `make`, `make examples`, and `git diff --check` pass. The local manual
  examples remain opt-in and excluded from `make`.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13j_manual_council_scenario_and_context_tracing-report.md`.
Report scenario alternatives/handler behavior, context-trace boundary proof,
opaque-ID rationale, tests/commands/results, exact run commands, changed files,
and the fact that live-model behavior remains variable.

## Boundary

- Touch only listed wrapper/export/manual/test/docs/report files.
- Do not change council policy, cognition parsing/transport, information-boundary
  rules, persistence, HTTP APIs, numbered automated examples, or Makefile.
- Do not print/provider-log raw responses or exceptions, expose world state, or
  treat the manual handler as a real simulation mutation.
