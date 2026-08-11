# Task 13k — Settlement-wide council scenario report

## Delivery

Added `examples/manual/council_scenarios.py`, a manual-example-only catalog
whose `CouncilParticipant` and `ManualCouncilScenario` records are frozen
dataclasses. `SCENARIOS` and `SCENARIO_NAMES` provide deterministic ordered
discovery, while `get_scenario()` selects a named immutable setup. This module
is intentionally not part of the production package or council API.

Both Ollama and llama.cpp entry points now accept `--scenario` with identical
choices. `journey` preserves the Task 13j default data and existing run
commands; `settlement` selects the new setup. Imports, pytest collection, and
argument-parser construction do not construct or contact a provider. Provider
clients remain constructed only in `main()` after argument parsing.

## Settlement and action behavior

The settlement setup contains five NPCs behind opaque `entity_` identifiers,
three qualitative public-well responses, 20 bounded turns, and turn offset 3.
Its NPC-visible agenda says a visible shared condition requires a decision and
explicitly separates that condition from Alma's engine-appointed role as
meeting coordinator. It says neither that Alma originated the issue nor that
Alma represents agreement on an action; it also states that no action has
unanimous support. The caller receives no additional authority.

All alternatives remain cognition proposals. Each example configures the
existing manual handler with the selected scenario vocabulary; accepted
proposals still report that world state is unchanged. This delivery adds no
collective agenda discovery, institutional governance, persistence, council
policy, or simulation mutation.

## Information boundary

Only opaque IDs enter engine construction. NPC-facing scenario prose contains
names and qualitative positions but no internal identifiers, raw attributes,
`WorldState`, hidden cognition, or arbitrary runtime objects. `--show-context`
continues to serialize only the recorded, already-filtered `NPCContext` and
offered actions. Normal result rendering and the fixed safe diagnostics remain
provider independent and unchanged.

## Tests and validation

Offline tests cover the shared provider names and selection, journey default,
frozen scenario state, unknown-name rejection, five opaque settlement members,
three meaningful actions, bounded multi-round scheduling, nonzero rotation,
and the shared-condition/coordinator distinction. Existing tests continue to
cover safe normal output, safe context tracing, and accepted no-mutation
resolution.

Commands run:

- `.venv/bin/pytest tests/test_manual_council_scenarios.py tests/test_manual_council_examples.py`
- `make`
- `make examples`
- `git diff --check`

## Files changed

- `examples/manual/council_scenarios.py`
- `examples/manual/ollama_council_meeting.py`
- `examples/manual/llama_cpp_council_meeting.py`
- `tests/test_manual_council_scenarios.py`
- `tests/test_manual_council_examples.py`
- `docs/local_llm_setup.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/13k_settlement_council_scenario-report.md`
