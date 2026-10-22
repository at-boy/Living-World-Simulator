# LN07c parent-aware setup report

Status: review-round-1 correction delivered for independent root re-review. Root acceptance,
full repository gates, integration and task completion remain pending.

## Scope and behavior

Changed only the four allowed worker paths:

- `src/living_world/archives/catalog.py`
- `src/living_world/archives/assets.py`
- `tests/test_run_archive_fork_setup.py`
- this report

`reserve_fork_setup` reserves same-lineage child identity and immutable closed fork
intent, then retains the exact source inputs under the brief child lease before
returning. One `fork_point` selects checkpoint and visible journal horizon. The
intent pins the full source configuration, retained input hashes and exact snapshot
payload plus both cursors; requested configuration can change only provider/limits.
An allocated reservation failure preserves its safe exception reference and attempts
to record `setup_failed` when a valid intent exists and publication is still pending.

`complete_setup` validates the captured source configuration, input hashes, selected
checkpoint and exact journal prefix, allowing later source advancement. It publishes
ordinary effective config/lineage metadata, then commits the captured snapshot and
cursors as child revision zero with no copied journal entries. The existing immutable
completion marker is published only after checkpoint commit and archive close.

Pending/failed/partial discovery preserves captured parent linkage and exposes no
invented checkpoint or tick. Retained-input reads bind hashes to intent, rejecting
self-consistent manifest/byte replacement. Completed child opens validate exact cp0
hash even after later child revisions and require no parent availability. Reads do
not repair files. Parentless setup and ordinary fork behavior remain unchanged.

No runtime/provider/CLI/domain/store/schema/config-rewrite changes; no dependencies,
model downloads, source mutations, VCS/index operations or other-checkout writes.

## TDD and verification

All pytest commands used `PYTHONPATH=src` and the explicit interpreter:
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.

- Initial new API RED: `-m pytest tests/test_run_archive_fork_setup.py -q`:
  4 failed because `RunCatalog.reserve_fork_setup` did not exist. Invalid initial
  test fixture data was corrected before this genuine missing-API RED.
- First GREEN: `-m pytest tests/test_run_archive_fork_setup.py tests/test_run_archive_catalog.py -q`:
  100 passed.
- Failure-window RED: `-m pytest tests/test_run_archive_fork_setup.py -q`:
  1 failed, 49 passed; an exception after successful intent write lacked the
  best-effort failure marker. Moved allocated-failure handling outside the lease
  publication block; subsequent run: 50 passed.
- Final focused command: `-m pytest tests/test_run_archive_fork_setup.py tests/test_run_archive_catalog.py tests/test_run_archive_store.py tests/test_runtime_ollama_driver.py -q`:
  **302 passed** (70 new fork-setup cases). No warnings reported.
- Same explicit interpreter, `-m ruff check src/living_world/archives/catalog.py src/living_world/archives/assets.py tests/test_run_archive_fork_setup.py`:
  passed.
- Same explicit interpreter, `-m black --check src/living_world/archives/catalog.py src/living_world/archives/assets.py tests/test_run_archive_fork_setup.py`:
  passed; three files unchanged.
- Local Python trailing-whitespace/final-newline assertions across the four allowed
  worker files: passed. Root owns authoritative `git diff --check`.

## Coverage and self-review

Reviewed the implementation against the exact task contract. Tests cover unchanged
and changed-model configuration; absent old digest and later normalized model/digest;
exact older/latest selection, one fork-point call, source checkpoint/journal advance;
strict closed fork fields/types/digests/UUIDs/boundaries/self-parent rejection;
invalid transition/revision/catalog/lease/thread and repeated/failure completion;
source configuration/cursor/snapshot/input/prefix tampering and missing source;
self-consistent child input/cp0 replacement; exact snapshot whitespace, optional tape,
source request evidence preservation and empty child journal/lifecycle; reservation
parity; retention and post-intent-write faults; before-SQLite/empty/schema/valid-no-cp0/
committed-cp0-before-marker interruption; marked corruption; actual killed lease owner;
read-only byte/mtime checks; parent unavailable and later child progress.

Initial self-review missed the early allocated failure windows subsequently identified
by independent review; correction evidence follows below. Existing catalog,
store and Ollama driver tests are included in the focused result. Full `make`,
`make examples`, independent review, canonical matrices and integration validation
were deliberately left to the root as assigned. This report does not certify the
service/CLI stages or completion of original LN07.


## Review round 1 correction

Independent SPEC/QUALITY review identified one P2: lock creation or first intent
write failure could return allocated identity without durable captured parent linkage.
Root amended the task and saved prompt before this correction. The same four-file
boundary applies; the staged baseline and VCS/index were not changed by the worker.

The complete intent, including one timestamp, is now precomputed and published
before creating owner.lock. The private unreturned-allocation failure handler makes
one bounded retry of the exact captured intent only if absent, validates existing
intent against the same canonical document, and refuses malformed/divergent evidence.
When a lock exists it uses the ordinary lease plus fail_setup; an owned or unsafe
lock cannot be bypassed. When no lock exists, only this private creation-failure path
can publish closed setup_failed evidence after checking final/failure conflicts.
Normal public setup/input/completion lease rules remain unchanged.

Added ten cases covering lock creation, pre-write intent, post-write/sync-like and
post-lock/sync-like faults; missing-lock normal lease rejection; malformed/divergent
existing intent; unsafe and independently owned locks; existing final metadata; and
persistent metadata IO failure. The successful-fallback cases retain exact intent,
config, parent, no fabricated world, and read-only discovery/source bytes.

When every metadata write remains unavailable, no durable intent or failure marker
can be claimed. The bounded retry fails, ArchiveReservationError still preserves the
allocated reference/directory, and discovery truthfully lacks unpersisted linkage.
The persistent-failure test explicitly checks this physical IO limitation.

Verification, same explicit interpreter and PYTHONPATH as above:

- RED: `-m pytest tests/test_run_archive_fork_setup.py -k 'early_allocated or allocated_failure_handler or persistent_allocated' -q`:
  6 failed, 4 passed, 70 deselected. Failures exposed ordering, absent intent and
  missing bounded-retry behavior.
- GREEN: same targeted command: 10 passed, 70 deselected.
- Final focused contract command listed above: **312 passed**, including 80 new
  fork-setup cases; no warnings. The subsequent lint-only context-manager formatting
  correction was followed by the targeted command: 10 passed, 70 deselected.
- Scoped Ruff: initial SIM117 on new nested test contexts corrected; final check
  passed. Scoped Black check: passed, three files unchanged.
- Four-file trailing-whitespace/final-newline assertions: passed.

Self-review checked the amendment against both no-lock and existing-lock paths,
immutable intent/timestamp reuse, no overwrite/repair, safe exception identity,
source preservation and bounded retry behavior. No remaining ambiguity identified.
Independent scoped re-review and all root-owned full gates remain pending.

## Root task acceptance

Independent SPEC/QUALITY review found one P2 early allocated failure linkage gap.
Root confirmed, amended exact plan/prompt before correction; scoped re-review passed,
one addressed / zero open, NO SUBSTANTIVE FINDINGS.

- Full task `make` with task24 VENV: 1,956 passed / 10 existing skips, lint/format,
  actual Chrome and 39 examples passed. Separate `make examples`: 39 passed.
- Exact canonical matrix matches previous reviewed integration: all three hashes,
  fresh duplicates, resume 1/3/4 and terminal checks. All26normalCLIattempts retain
  readable complete-checkpoint archives.
- Staged/unstaged whitespace clean; source unchanged by make after re-review.

Evidence: ln07c-review-1.diff, ln07c-fix-1.diff, ln07c-review-final.md,
ln07c-task-make.log, ln07c-task-examples.log and ln07c-task-matrix/results.json
with retainedstate in current-plan ignored SDDworkspace. Delivery/merged gates next.
Original Task7/service/CLI/browser/installed-model acceptance remains incomplete.

## Root merged acceptance

Delivery ada9b8b is integrated by the merge containing this report. No source
conflicts; source/tests byte-identical to reviewed delivery after merged gates.

- Mergedmake: 1,956 passed / 10 existing skips, lint/format, actualChrome and39examples.
- Separate mergedexamples:39passed; staged/unstaged whitespace clean.
- Exact merged canonical matrix equals task;26normalCLIattempts retain readable
  complete checkpoints. No source branches, owner edits or acceptance archives removed.

Evidence: ln07c-merged-make.log, ln07c-merged-examples.log,
ln07c-merged-matrix/results.json and retainedstate in current-plan SDDworkspace.
LN07c complete; next LN07d owner-thread service/recorded restart, then LN07e CLI.
Original Task7 and LN08/LN09 remain incomplete.
