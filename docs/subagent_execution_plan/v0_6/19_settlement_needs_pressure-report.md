# Task 19 report — settlement needs and pressure

## Delivered

- Added frozen, slotted need definitions, assessments, state, enums, and safe NPC
  interpretations under `living_world.needs`.
- Added deterministic arithmetic, bounded histories, atomic events/pass rollback,
  owner-kind uniqueness, and entity removal protection.
- Scheduled needs after ordinary systems and before goal evaluation, and added the
  concrete consecutive-history sustained-need evaluator.
- Advanced SQLite persistence to schema 7 with legacy empty collections and
  strict need load validation.
- Added privileged inspection, safe qualitative interpretation, final NPC-boundary
  filtering, example 032, ADR-0020, documentation, and regression tests.
- Corrected direct self-ownership capacity aggregation so the already-included
  owner is never counted twice for shelter or storage.
- Added binding regressions for same-level pressure evidence/idempotence, maxima
  above one, every sustained-evaluator unavailable reason, event provenance,
  manager event rollback, legacy schemas 1–6, and malformed schema-7 records,
  history, arithmetic, references, enums, and numbers.

## Boundaries

No consumption, maintenance, work selection, settlement stages, NPC action, or
automatic NPC-context injection was added. Changes stayed inside Task 19's
allowed-file list.

## Validation

- Expanded focused suite: **126 passed**.
- `make`: **passed** (Ruff, Black, and **655 pytest tests passed**; its example
  gate also passed examples 001–032).
- Separate `make examples`: **passed** for examples 001–032.
- `git diff --check`: **passed**.
