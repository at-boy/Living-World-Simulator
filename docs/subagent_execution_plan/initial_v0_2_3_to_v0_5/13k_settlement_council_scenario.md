# 13k — Settlement-wide council scenario

## Task Description

Add a reusable manual council-scenario catalog and a scenario where a
settlement-wide problem requires a decision even though no NPC personally
introduced the issue. The current council API still has one engine-selected
caller who coordinates the meeting; NPC-facing prose must distinguish that
procedural role from ownership of the concern or a preferred outcome.

## Context Needed

- Create: `examples/manual/council_scenarios.py`,
  `tests/test_manual_council_scenarios.py`, and
  `docs/subagent_execution_plan/13k_settlement_council_scenario-report.md`.
- Edit: both manual council examples, `tests/test_manual_council_examples.py`,
  `docs/local_llm_setup.md`, `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: Task 13j's opaque-ID scenario, safe context trace, manual-only gateway
  handler, `CouncilCall`, `CouncilAgenda`, and local client construction.

## Interface Contract

- Provide a manual-example-only, typed scenario description/factory shared by
  the Ollama and llama.cpp entry points. It must use immutable dataclasses or
  another existing typed domain pattern and must not become a production API.
- Both entry points accept a deterministic `--scenario` selection without
  contacting a provider during import, argument help, or pytest collection.
- Preserve the Task 13j scenario as the default so existing run commands keep
  working. Add a named settlement scenario with five eligible NPCs, at least
  three qualitative actions, a longer bounded discussion, and a nonzero turn
  offset.
- The settlement scenario states that a visible shared condition requires a
  decision. The engine appoints one eligible NPC as caller/meeting coordinator,
  but neither context nor output may claim that caller originated the issue,
  represents unanimous support for an action, or has special decision
  authority.
- The offered actions remain proposals handled by the existing manual-only,
  accepted no-mutation gateway path. This task does not implement collective
  agenda discovery, institutional governance, persistence, or world mutation.

## Test Criteria

- Offline tests prove both providers expose the same scenario names and select
  the same deterministic settlement setup without making network calls.
- Tests prove the scenario has opaque IDs, five eligible members, at least
  three meaningful alternatives, a bounded multi-round schedule, and a
  nonzero turn offset.
- Tests prove NPC-visible text frames the condition as settlement-wide while
  keeping the caller a coordinator rather than the issue's author or an
  authoritative representative of consensus.
- Existing normal and `--show-context` rendering remains safe and provider
  independent.
- `make`, `make examples`, and `git diff --check` pass. Live local-model runs
  remain opt-in and excluded from `make`.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13k_settlement_council_scenario-report.md`.
Report the scenario catalog interface, CLI behavior, settlement/caller
distinction, action alternatives, tests and commands, exact files changed,
information-boundary compliance, and deferred collective agenda/governance
policy.

## Boundary

- Touch only the listed manual-example, test, documentation, and report files.
- Do not change production council/cognition APIs, council eligibility or vote
  policy, persistence, HTTP APIs, provider clients, numbered examples, or the
  Makefile.
- Do not model broad recognition of a problem as unanimous agreement on an
  action, give the caller extra authority, expose raw world state/IDs, or apply
  a real world mutation.
