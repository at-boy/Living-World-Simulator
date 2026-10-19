# Task 1 / LN01 — World snapshot codec

Status: authorized for implementation by owner plan approval October19,2026.
Integration base8cf5855; isolated task branch codex/live-npc-ln01-world-snapshot-codec.
Root owns review, validation, VCS and integration; worker does not commit or spawn agents.

Binding design: [approved spec](../../superpowers/specs/2026-10-19-live-npc-runtime-design.md).
Milestone execution plan: [live runtime plan](../../superpowers/plans/2026-10-19-live-npc-runtime.md).

## Task-relevant global constraints

Python>=3.11, strict hints, frozen snapshot values; preserve manager/system/event and
NPC information boundaries. No world fields/schema/version/dependency changes.
Existing schema12 row equality and schemas1–12 reads remain unchanged. No model,
container, CLI/API, archive tables or main/tag changes in this task.

## Exact authorizing task text

## LN01: Extract the existing world snapshot codec

**Files:**
- Create: `src/living_world/repositories/world_snapshot.py`, `tests/test_world_snapshot.py`.
- Modify: `src/living_world/repositories/sqlite_repository.py`, `tests/test_sqlite_repository.py`.
- Slug: `world_snapshot_codec`.

**Interfaces:** produces `encode_world(state: WorldState) -> WorldSnapshot`,
`decode_world(snapshot: WorldSnapshot) -> WorldState`; consumes existing private
serialize/deserialize/validation logic. `SQLiteRepository` public constructor and
GraphRepository load/save signatures remain unchanged.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_world_snapshot.py tests/test_sqlite_repository.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** `test_codec_preserves_exact_existing_row`,
  `test_codec_roundtrip_and_detachment`, `test_codec_rejects_corrupt_and_future_schema`.
  Pin the tuple and complete payload, not selected fields:
  ```python
  encoded = encode_world(populated_world)
  repository.save_world(populated_world)
  assert (encoded.schema_version, encoded.payload) == read_world_row(database)
  assert encode_world(decode_world(encoded)) == encoded
  assert decode_world(encoded) is not populated_world
  ```
  `read_world_row` is a test-only helper; use current schema12 and legacy fixture tests.
- [ ] **Step 2 — Observe RED** run `tests/test_world_snapshot.py`; expected import/name
  failure for absent codec. Existing serialization fixtures establish the reference.
- [ ] **Step 3 — Implement** exact functions above by extracting/reusing existing
  validators and canonical JSON; no second serializer or world field changes. Preserve compatibility aliases for
  existing private _serialize_world imports used by canonical tests; do not rewrite
  those assertions to accommodate codec drift. Keep
  current error types/diagnostics by translating codec errors at repository boundary.
- [ ] **Step 4 — Observe GREEN** focused codec/repository/replay tests plus canonical
  exact fresh/resume checks. Mutation of decoded state cannot mutate source snapshot.
- [ ] **Step 5 — Review, root gates and commit** `refactor: expose compatible world snapshot codec`.
  Root verifies no schema/version/dependency delta and records exact reviewed commit.

## Ownership and exact allowed-file boundary

Worker may create src/living_world/repositories/world_snapshot.py and
 tests/test_world_snapshot.py; modify src/living_world/repositories/sqlite_repository.py,
 tests/test_sqlite_repository.py and this task's 01_world_snapshot_codec-report.md.
No other worker edits. Preserve every existing assertion unless an actual extension
requires a root-approved contract amendment. Existing _serialize_world imports
remain valid. Tests/helpers belong in tests, never product test switches.

Root common-document allowance: this task plan/prompt/report, live_npc_runtime/README.md,
CHANGELOG.md, docs/project_journal.md, docs/backlog.md and continuation_brief.md.
The owner-local master-plan edit is not part of this task and must not be staged.

## Architecture and failure semantics

Keep a single existing serialization implementation: move/reuse canonical helpers
without rewriting their domain semantics. Root permits mechanical helper extraction
into world_snapshot.py with compatibility aliases in sqlite_repository.py; preserve
imports and avoid import cycles. Return frozen WorldSnapshot(schema_version:int,
payload:str), digest SHA256 UTF8(str(schema_version)+"\n"+payload). Version exact int
(not bool), payload string; malformed/unsupported decode fails closed. Codec loading
never changes input row, loaded source schema/payload or live caller state. Schema12
encode output must be byte-identical to existing JSON serialization. Normal encode
validates existing stage/replay constraints, preserving repository errors at the SQL
boundary. decode returns detached WorldState. No archive timestamps or extra fields.

## Validation ownership

Worker: focused baseline, TDD RED/GREEN, repository/replay focused regressions, whitespace
and truthful report. Root: independent review, full make, separate make examples,
whitespace and complete canonical CLI hashes; commit only after all pass, merge into
feature branch and repeat required merged gates. Never run unrequested full suites
in a worker. No successful raw logs copied into reports.
