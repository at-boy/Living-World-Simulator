# Task 20 report — work orders and reservations

## Delivered

- Added frozen typed work, target, requirement, state, reservation, and safe
  interpretation records plus manager-owned lifecycle and immutable events.
- Added aggregate non-deducting labor/tool/resource locks, deterministic query
  order, release history, rollback, spatial/lifecycle guards, and engine wiring.
- Advanced SQLite snapshots to schema 9 with legacy empty defaults and strict
  work deserialization/loaded validation.
- Added detached work inspection, summary counts, GET-only HTTP access, final
  NPC ID/number filtering, focused tests, and example 034.
- Independent review corrections tightened canonical persisted keys/IDs,
  lifecycle and reservation tick/status matrices, active-reservation graph and
  historical labor validation, settlement/maintenance creation predicates,
  and containment-ancestor lifecycle guards. Example 034 now demonstrates a
  prerequisite plus privileged inspection separately from selected safe prose.
- Second review bound chronological reservation history: only blocked releases
  may precede reassignment, histories cannot overlap, terminal releases are
  unique/last and match terminal state/tick, and completion requires its
  terminal release. Added concrete work-history, schema-8 migration, tagged
  detached inspection, GET-only, NPC filtering/non-injection, and scheduler
  non-registration regressions.
- Third review made coverage explicit in every relevant named subsystem suite:
  work prerequisites, locks, progress/priority/terminal behavior, rollback and
  resume IDs in `test_work_orders`; forever-removal and released-labor lifecycle
  in `test_entity_manager`; authoritative undercollateralization in
  `test_consumption_maintenance`; objective nonmutation/terminal rejection in
  `test_goals`; schema-8 work migration in `test_sqlite_repository`; terminal
  location/released-labor movement in `test_spatial_domain`; and the existing
  inspection, NPC-boundary/context, and scheduler regressions.
- Final literal matrix adds all six valid categories/four target families,
  every invalid family cell plus resource-name rules, full-value payload checks
  for all twelve event kinds, every schema-9 top-level and nested target/tool/
  resource missing/extra-key shape, maintenance live-positive creation versus
  destroyed/zero-condition loaded history, and resumed reservation/work ID
  allocation. The ten parameterized skips are deliberately the valid-family
  cells in the invalid-pairing Cartesian matrix, not uncovered cases.
  Blocked, cancelled, and failed transitions and each associated reservation
  release now assert exact full attribute dictionaries and values; all twelve
  distinct work event kinds therefore have full-value payload coverage.

## Boundaries

No proposal handler, scheduler system, automatic selection/progress, resource
charging, domain effect, goal mutation, YAML, prompt, or LLM behavior was added.

## Validation

Final all-named-file focused matrix: **301 passed, 10 deliberate valid-cell
skips**; final work-order matrix: **66 passed, 10 deliberate valid-cell skips**.
Required `make` passed Ruff, Black, **826 passed / 10 deliberate skips** across
836 collected tests, and examples
001–034. Separate `make examples` passed examples 001–034. `git diff --check`
passed.

## Limitations

Task 20 records and locks work only. Task 20a must validate offered proposals;
Task 20b must handle selection, undercollateralization, charging, and effects.
