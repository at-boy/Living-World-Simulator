# Task 13m — Cognition-shaped council scenario report

## Delivery

Added the `cognition-shaped` shared manual scenario. Every participant receives
the same public-well agenda and three action options, while private histories
provide different considerations. Journey remains the default and both local
provider entry points use one typed runtime preparation path for all scenarios.

## Manager paths and seeded cognition

`prepare_council_runtime()` registers definitions, creates the organization and
participants through `SimulationEngine.entities`, and creates `member_of`
eligibility through `SimulationEngine.relationships`. It returns the generated
opaque IDs required by `CouncilCall`.

The scenario uses `observations` for five holder-specific perceptions,
`memories` for Nessa's maintenance memory, `experiences` for Orin's delivery
experience, `beliefs` for Pella's and Quin's conflicting
interpretations, and `npc_relationships` for Rhea's private social
interpretation. No world collection is directly mutated.

## Information boundary

Offline tests assemble and serialize every participant context. Each contains
only that holder's current perception and core cognitive prose and excludes all
other seeded prose, runtime and cognitive IDs, provenance, evidence, metadata,
and raw state. A typed manual-only retriever adapter applies the public-well
topic through the existing production `CognitiveRetriever` interface for this
scenario. Both provider assemblers use it, so Rhea's exact holder-scoped
relationship projection appears as `kind="relationship"` only in Rhea's safe
context. Other scenarios retain ordinary default retrieval.

Both examples retain the request-only safe trace and the accepted no-mutation
gateway. Setup creates no authoritative well entity and forces no attendance,
speech, proposal, vote, majority, or resolution.

## Files changed

- `examples/manual/council_scenarios.py`
- `examples/manual/ollama_council_meeting.py`
- `examples/manual/llama_cpp_council_meeting.py`
- `tests/test_manual_council_scenarios.py`
- `tests/test_manual_council_examples.py`
- `docs/local_llm_setup.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/13m_cognition_shaped_council_scenario-report.md`

## Validation

- Focused manual scenario/example tests: 44 passed.
- `make`: Ruff and Black passed; 389 tests passed; all 22 numbered examples
  passed.
- `make examples`: all 22 numbered examples passed.
- `git diff --check`: passed.

## Boundary compliance and deferred work

No production API, persistence, provider client, HTTP API, numbered example, or
Makefile changed. Durable governance, forced model diversity, production
topic-selection policy, persistence, and world mutation remain deferred.
