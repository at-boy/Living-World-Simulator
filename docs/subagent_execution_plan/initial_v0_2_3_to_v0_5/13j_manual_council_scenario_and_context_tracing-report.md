# Task 13j — Manual council scenario and safe context tracing report

## Outcome

Implemented the bounded Task 13j manual integration scenario for both Ollama
and llama.cpp. Each example now uses five display-labelled NPCs backed by
opaque `entity_...` engine IDs and an opaque `organization_...` ID, offers
three qualitative journey alternatives, permits up to fifteen discussion
turns, and starts automatic speaker rotation at offset two.

The three offered alternatives are to prepare before travelling, travel at
daybreak, or postpone and conserve supplies. The example-only action handler
supports exactly that vocabulary. It validates and returns an accepted
`ActionResolution` through `NPCActionResolver`, while its application response
explicitly states that world state is unchanged. It owns no manager, world
primitive, event recording, or production mutation.

## Context-trace boundary

`RecordingCognitionClient` records a frozen `RecordedCognitionRequest` before
each delegated call. The record contains only the already-filtered
`NPCContext` and immutable offered `ActionOption` tuple. It calls the wrapped
provider exactly once, returns decisions unchanged, re-raises the same error
object, retries nothing, and has no response or error field.

The examples expose tracing only with `--show-context`. Recorded request values
are rendered by `serialize_decision_request`; normal output does not include
the trace. No raw provider response, exception text, HTTP/transport payload,
`WorldState`, engine identifier, hidden record, or secret is captured or
printed. Opaque engine IDs ensure identifiers are not meaningful prose and are
kept entirely on the engine side; display labels remain Aster, Bryn, Cato,
Dara, and Eris.

## Tests and validation

Tests cover ordered request capture, immutable snapshots, transparent provider
identity/decisions/errors, absence of response/error recording, safe trace
serialization, concise default rendering, opaque scenario IDs, three distinct
actions, the longer round bound, nonzero rotation, and the accepted resolver
handler path.

Commands run:

```text
.venv/bin/pytest tests/test_recording_cognition_client.py tests/test_manual_council_examples.py
make
make examples
git diff --check
```

The final focused suite passed all 22 tests. `make` passed Ruff, Black, all 365
tests, and all 22 numbered examples. The explicit final `make examples` run
also passed all 22 examples, and `git diff --check` passed with no output.

Manual run commands:

```text
PYTHONPATH=src .venv/bin/python examples/manual/ollama_council_meeting.py
PYTHONPATH=src .venv/bin/python examples/manual/ollama_council_meeting.py --show-context
PYTHONPATH=src .venv/bin/python examples/manual/llama_cpp_council_meeting.py
PYTHONPATH=src .venv/bin/python examples/manual/llama_cpp_council_meeting.py --show-context
```

These remain opt-in and require a separately running loopback model server.
Live attendance, speech, proposal selection, malformed output, and provider
availability remain variable. No test asserts a live model decision.

## Changed files

- `src/living_world/cognition/recording_cognition_client.py`
- `src/living_world/cognition/__init__.py`
- `examples/manual/ollama_council_meeting.py`
- `examples/manual/llama_cpp_council_meeting.py`
- `tests/test_recording_cognition_client.py`
- `tests/test_manual_council_examples.py`
- `docs/local_llm_setup.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/13j_manual_council_scenario_and_context_tracing-report.md`
