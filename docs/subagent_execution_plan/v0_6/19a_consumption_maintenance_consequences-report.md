# Task 19a report — consumption, maintenance, and consequences

## Delivered

- Added frozen/slotted consumption, storage, and maintenance policy/state records,
  canonical validation, and fixed qualitative NPC-safe interpretations.
- Added `ConsequenceManager` as the authoritative creation/application boundary and
  one ordered `ConsequenceSystem` phase after ordinary systems and before needs and
  goals. Consumption, upkeep, condition, terminal destruction, storage overflow,
  spoilage, transition events, same-tick idempotence, prevalidation, and whole-phase
  rollback are deterministic.
- Added manager-owned current-tick destruction and bidirectional live-role guards for
  consequence, need, goal, and external-dispatch ownership.
- Advanced SQLite persistence to schema 8 with legacy empty defaults, exact nested
  consequence records, loaded-state validation, and save/resume coverage.
- Added detached privileged consequence inspection and counts, GET-only HTTP access,
  consequence IDs/numbers to the final NPC boundary, example 033, and documentation.
- Independent review corrected maintenance creation so an existing maintenance
  capability cannot become another maintenance policy's owner, and expanded the
  required cross-module and schema-8 regression matrix.
- A second review pass enforced exact policy/state runtime types, strict terminal
  destruction-tick typing and ordering, repository-wide canonical-ID exclusion in
  safe consequence text, exhaustive exact-key schema-8 cases, sustained goal
  evidence flow, and needs/goals/evidence save-resume equivalence.
- Final spot-check coverage added the repository's canonical
  `external_dispatch_*` prefix to NPC-safe text rejection alongside
  `external_reference_*`.

## Files and boundaries

Changes are confined to the Task 19a allowed source, test, example, documentation,
and report paths. `ResourceSystem`, YAML configuration, work/stage/run authority,
automatic NPC-context injection, and LLM behavior were not changed.

## Validation

- Second-pass focused consequence/goal/persistence/NPC suite: **151 passed**.
- Final canonical-ID focused suite: **34 passed**.
- Full pytest suite: **729 passed**.
- Ruff and Black implementation formatting pass: passed.
- Required `make`: passed (Ruff, Black, **729 pytest tests**, examples 001–033).
- Separate `make examples`: passed for examples 001–033.
- `git diff --check`: passed.

## Limitations

Policies are configured through Python manager APIs only. Consequence interpretations
are selected explicitly and are never automatically injected into NPC context. A
terminal capability cannot recover, and positive condition does not proportionally
alter capability output or capacity.
