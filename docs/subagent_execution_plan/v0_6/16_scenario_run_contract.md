# 16 — Scenario and deterministic run contract

## Status and dependency

Authorized as the first v0.6 implementation task. Execute on
`task/16-scenario-run-contract` from the current `milestone/v0.6`. Task 16a
depends on its reviewed merge.

## Task description

Add a strict, versioned YAML scenario contract and durable run identity so a
world can be created reproducibly and a saved world can be checked against the
scenario used to resume it. This task loads and instantiates a scenario; it
does not add the long-running CLI loop, checkpoint policy, goals, needs, work,
external references, spatial state, or proposal tapes.

## Public contract

- Add frozen dataclasses for scenario identity/configuration and run metadata,
  plus a `ScenarioLoader` protocol and strict YAML implementation.
- Scenario version 1 contains a non-empty scenario key, integer deterministic
  seed, definition document path, initial entities with validated attributes,
  initial relationships, and bounded-run defaults/terminal-condition names
  reserved for Task 16a.
- Reject duplicate keys/labels, unknown fields, booleans used as integers,
  invalid references, unsupported schema versions, absolute definition paths,
  and relative paths that escape the scenario directory.
- Resolve entity relationships by scenario-local labels. Internal generated
  IDs must not appear in scenario prose or NPC-visible values.
- Store immutable run metadata in `WorldState`: scenario key/schema version,
  seed, and a deterministic configuration fingerprint. Initial creation is
  idempotent; resume validates metadata and does not recreate records.
- Definitions remain configuration, not snapshot records. Resume reloads the
  same definition document and verifies its fingerprint before systems run.

## Persistence and inspection

- Extend SQLite serialization to a new schema version while loading schema-v1
  v0.5 snapshots with absent run metadata as a legacy, unbound world.
- Saving a loaded legacy world writes the current schema. Do not invent a
  scenario identity for it.
- Add privileged detached run-metadata inspection to the existing world
  summary/API. Run metadata is operator data and must not enter NPC context.

## Allowed files

- New scenario/run domain and loader modules under `src/living_world/`.
- `WorldState`, `SimulationEngine`, SQLite repository, inspection API/server,
  public package exports required by the contract.
- Focused tests, one numbered executable example, scenario fixture(s), ADR,
  glossary/core-model/API docs, changelog, project journal, backlog, and the
  Task 16 report.
- Do not edit cognition, perception, action resolution, existing systems, UI
  assets, or later v0.6 task artifacts.

## Tests and validation

- Cover valid deterministic loading, strict malformed input, duplicate labels,
  reference validation, safe path handling, idempotent creation, metadata and
  definition mismatch on resume, schema-v1 loading/current-schema rewriting,
  repository round trips, inspection detachment/order, and unchanged NPC
  context.
- Run `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/16_scenario_run_contract-report.md`
with exact files/interfaces, migration behavior, boundary evidence, commands
and results, and blockers.
