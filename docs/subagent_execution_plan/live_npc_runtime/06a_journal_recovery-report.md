# LN06a recovery-journal report

Status: complete bounded LN06a stage; independent SPEC/QUALITY PASS and root task/
merged gates passed. Delivery6469a38; integrated by the merge containing this report. LN06 as a whole is
not complete; provider/broker/live/replay consumers belong to LN06b.

## Scope and behavior

Changed only the four permitted archive modules, the two archive test modules,
and this report. No world schema, SQLite schema/table/column, configuration
fingerprint, dependency, provider, runtime, feedback or HTTP changes.

- Added frozen validated `JournalRecord`, `JournalBoundary` and `ForkPoint`, with
  package exports. Prefix accessors preserve original sequences/linkage and hash
  canonical closed row documents. Zero selects empty, missing/noninteger/boolean
  or negative bounds fail safely. Existing `entries()` is unchanged.
- `fork_point()` reads checkpoint and journal horizon in one existing readonly
  transaction. Catalog forks publish that seal with an exact revision-zero child
  snapshot/cursors; parent bytes remain untouched. Later source rows are outside
  the seal. A real concurrent WAL writer regression pins snapshot consistency.
- Optional nullable `parent_journal` is parsed through shared boundary validation;
  reservation parsing is factored once, preserving `read_reservation()`'s four
  return values. Catalog opening checks reservation/archive seal parity. Missing
  legacy fields remain readable without repair writes. Existing parent tuple and
  AttemptConfig contracts are unchanged. The existing factory is `create()`;
  root corrected the task's initial `initialize` spelling before implementation.
- Action outcomes require a preceding validated local response/import and their
  own complete checkpoint advancing base revision by one. Base/committed ticks,
  local request slot, no-action/decision agreement and duplicate ownership are
  enforced on writes and loads. Invalid batches roll back world, cursors, journal
  and command settlement together; exact whole-commit retries stay idempotent.
- `response_reused` establishes a local request plus validated safe decision in
  the request identity namespace, distinct from network-start rows. Source IDs,
  sealed boundary and safe offered vocabulary are validated without source IO.
  Imports are idempotent only when byte-equivalent; conflicting starts, imports
  or subsequent response rows fail. Safe optional digest/elapsed provenance is
  supported on validated responses/imports, including finite-number checks.

## Validation evidence

`TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
All pytest commands below used `PYTHONPATH=src "$TASK_PY" -m pytest`.

| Stage | Command arguments | Result |
| --- | --- | --- |
| Baseline | `tests/test_run_archive_store.py tests/test_run_archive_catalog.py tests/test_runtime_recorded.py -q` | 99 passed |
| Initial RED | `tests/test_run_archive_store.py tests/test_run_archive_catalog.py -q` | 30 failed, 91 passed; missing records/accessors/seals and acceptance of standalone pending/failed actions. Some response-fixture failures were invalid speech/action setup, corrected below; those failures are not claimed as behavior proof. |
| First correction pass | `tests/test_run_archive_store.py tests/test_run_archive_catalog.py -q --tb=short` | 21 failed, 100 passed; invalid new speech-only helper and existing closed-key expectation surfaced. |
| Corrected store fixtures | `tests/test_run_archive_store.py -q --tb=short` | 82 passed |
| Additional edge RED | `tests/test_run_archive_store.py tests/test_run_archive_catalog.py -q --tb=short` | 1 failed, 150 passed; huge elapsed integer leaked OverflowError instead of ArchiveFormatError. |
| GREEN | `tests/test_run_archive_store.py tests/test_run_archive_catalog.py tests/test_runtime_recorded.py -q --tb=short` | 160 passed |
| Expanded final focused | same three files, `-q --tb=short` | 167 passed; no skips or warnings |

Scoped Ruff initially reported seven import/export sorting issues; scoped
`ruff check --fix` corrected them. Black formatting was applied only to the six
permitted Python files. Final `ruff check` passed for all six files; final
`black --check` passed with six unchanged files. A direct trailing-whitespace
and final-newline check passed for all seven worker files (no VCS invocation).
An initial edit command used unavailable `python` and exited 127 before making
changes; rerun with available `python3` succeeded. No dependencies were installed.

Regression coverage includes original crash/checkpoint, Step receipt, lifecycle,
lease/catalog and recorded-resume tests; new prefix/gap/immutability/read-only
checks, source seal append/tamper/missing-sequence checks, single-snapshot source
activity, legacy/malformed/parity metadata, imports/identity/offers/provenance,
raw SQL action corruption, invalid action slots/ticks/outcomes, duplicate actor
slots, atomic command rollback and exact checkpoint retry behavior.

## Intentional existing fixture changes

Root explicitly approved both changes before editing expectations:

1. `test_process_termination_keeps_complete_transaction` previously recorded a
   timeout then committed a no-action outcome. Its precursor is now a validated
   safe speech decision with no action. Every process boundary, row-count,
   world/cursor, receipt and action-presence assertion is preserved. Dedicated
   pending/failed-resolution rejection tests preserve timeout failure coverage.
2. `test_reservation_is_unique_closed_and_pre_world_failure_discoverable` extends
   its exact closed-key set by the required normalized `parent_journal` field.
   Equality and unknown-field rejection remain strict.

A newly introduced helper initially used no speech and no action, invalid under
existing NPCDecision rules. It was corrected to nonempty safe speech; production
NPCDecision validation was not relaxed.

## Self-review and remaining work

Reviewed factory validation before publication, shared metadata parser reuse,
identity conflicts in both directions, checkpoint operation ownership, readonly
corruption checks and transaction rollback. No known substantive issue remains
in this bounded producer stage. Storage intentionally does not verify external
source prefixes: LN06b consumers must compare the sealed prefix and decision/
input/config before import, and must decline unsealed provenance. No runtime
recovery/provider/replay capability is claimed here.

Per worker assignment, no VCS operations, commits, full `make`, examples,
dependency changes or subagents were performed. Root owns independent review,
`git diff --check`, full validation and integration. All prior branches/checkouts
were left alone.


## Independent review fix round 1 (2026-10-22)

Independent review found one important contract failure: `_record()` used Python
record equality for repeated identities, so `elapsed_seconds=0` and `0.0` were
accepted as an idempotent import despite differing canonical JSON bytes. Root
confirmed and authorized this bounded correction.

Changed `_record()` to compare both kind and canonical payload for all existing
identity-bearing entry kinds. Ownership checks remain in their existing order.
Added a parameterized import regression for integer-to-float and float-to-integer
provenance changes. Each case preserves exact-repeat idempotence, rejects the
canonical divergence and verifies whole-batch rollback (including an earlier new
candidate row), unchanged journal boundary/records, checkpoint and world tick.

Validation using the same TASK_PY and PYTHONPATH as above:

- RED: `pytest tests/test_run_archive_store.py::test_import_identity_requires_identical_canonical_numeric_provenance -q --tb=short`:
  2 failed because the divergent repeat did not raise ArchiveRevisionConflict.
- GREEN: same smallest command: 2 passed.
- Focused: `pytest tests/test_run_archive_store.py tests/test_run_archive_catalog.py tests/test_runtime_recorded.py -q --tb=short`:
  169 passed, no warnings/skips.
- Scoped Ruff initially found two redundant `int | float` parameter annotations;
  corrected to `float`, which also admits integer inputs under Python typing.
- Final scoped `ruff check`: passed for six Python files. Final scoped
  `black --check`: passed, six unchanged files. Direct whitespace/final-newline
  check: passed for all seven worker files.

Only store.py, its test file and this report changed in this correction round.
No VCS, subagents, full make/examples or out-of-boundary changes were performed.
Independent re-review and root gates remain pending; the earlier self-review
claim did not catch the numeric-equivalence issue and is superseded by this
review finding and correction evidence.

## Root review and task acceptance — October 22, 2026

Independent review identified the canonical numeric identity issue above. Root
confirmed it, the original worker corrected it, and scoped independent re-review
returned SPEC PASS / QUALITY PASS, NO SUBSTANTIVE FINDINGS (one addressed, zero
open). No other source changes followed review.

- Full `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`:
  passed, 1,722 tests / 10 existing deliberate skips; Ruff, Black, actual Chrome
  coverage and all 39 examples passed.
- Separate `make examples` with the same VENV: passed, 39 examples.
- `recorded_matrix.py` against this task checkout: passed all three canonical
  complete-payload hashes, two fresh runs per outcome, resume ticks 1/3/4 and
  zero additional ticks after success/failure termination.
- `git diff --check`: passed before delivery staging/commit.

Ignored evidence is retained in the integration checkout's current-plan SDD
workspace: `ln06a-task-make.log`, `ln06a-task-examples.log`,
`ln06a-task-matrix/results.json` and `ln06a-review-final.md`.
No actual model inference is claimed; LN06b and public entrypoints remain pending.

## Root integration acceptance

Delivery `6469a38` is pushed on preserved `codex/live-npc-ln06a-journal-recovery`.
Merged into `codex/live-npc-runtime` with only root-owned checkpoint-documentation
conflicts; no source conflict or source correction was required.

- Merged full `make` with the same VENV: passed, 1,722 tests / 10 existing skips,
  lint/format, actual Chrome coverage and 39 examples.
- Separate merged `make examples`: passed, 39 examples.
- Merged canonical `recorded_matrix.py`: passed all three exact payload hashes,
  duplicate fresh runs, resume ticks 1/3/4 and success/failure zero-step termination.
- Staged and unstaged `git diff --check`: passed.
- Owner-local master-plan patch remains byte-identical and unstaged. All task
  branches/worktrees are retained; main, milestone and release tag are unchanged.

Merged evidence: `ln06a-merged-make.log`, `ln06a-merged-examples.log` and
`ln06a-merged-matrix/results.json` in the current-plan ignored workspace.
LN06a is complete; LN06 as a whole remains incomplete pending LN06b and aggregate
acceptance. Next step is the exact bounded provider/live/replay contract.
