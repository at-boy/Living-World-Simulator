# LN02 archive store implementation report

Status: independently reviewed; root task gates passed; delivery/integration pending.

## Scope and behavior

Created only `src/living_world/archives/__init__.py`, `model.py`, `store.py`
and `tests/test_run_archive_store.py`; this report is the only worker documentation
write. Root's task/prompt amendments are pre-existing edits and were preserved.
No staging, commits, dependency changes, full-suite execution or subagents.

Archive format1 stores immutable reference/configuration/parent/UTC metadata,
exact LN01 snapshot schema/payload/digest, complete cursors, canonical ordered
commit fingerprints, journal rows, command envelopes/results and lifecycle rows.
Writes use per-operation SQLite connections, foreign keys, DELETE journaling and
explicit BEGIN IMMEDIATE transactions. Creation reserves a new database without
overwriting; open never initializes or repairs missing schema.

Closed frozen dataclasses deeply freeze finite JSON mappings/arrays. Configuration
uses the contract's nonsecret allowlist; request/decision records reuse existing
cognition constructors and offered-vocabulary validation. Loaded documents reject
duplicate keys, malformed shapes, bad hashes, unknown formats and inconsistent
checkpoint/current-world/journal/command references. Read-only opens use mode=ro.
Writer calls reject foreign threads. Directory/database symlinks are rejected.

Checkpoint revision compare-and-swap occurs before mutations. Exact old commit
retries return their original checkpoint without rewinding current world. Identity
bearing audit duplicates return their prior sequence; divergent reuse fails.
Commands retain canonical envelope hashes and immutable settled results. Applied
step resolution requires its checkpoint transaction. Root-confirmed revision_context
preserves latest-revision queued admissions across reopen (revision0 before initial).
Recorded-only compatibility save preserves cursors; live/replay saves fail closed.

## Focused verification

Interpreter: `/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
All pytest invocations used `PYTHONPATH=src` in the isolated LN02 checkout.

- Initial RED: `-m pytest tests/test_run_archive_store.py -q`: expected missing
  `living_world.archives` import, one collection error before implementation.
- Initial GREEN: same command, six tests passed.
- Subsequent focused RED identified deleted checkpoint audit, live metadata
  corruption, invalid lifecycle type wrapping, post-checkpoint queued receipt
  revision and compatibility save error wrapping. Corrected and rerun to GREEN.
- Final archive run: `-m pytest tests/test_run_archive_store.py -q`: 43 passed;
  no skipped tests or warnings.
- Combined codec/repository regression run: `-m pytest tests/test_run_archive_store.py
  tests/test_world_snapshot.py tests/test_sqlite_repository.py -q`: 167 passed;
  no skipped tests or warnings (rerun after final formatting recorded below).
- Scoped Ruff and Black: imports/style findings corrected; final checks pass.
- `git diff --check`: passed. Root owns complete repository gates and examples.

Tests use a real SQLite trigger abort after current-world mutation to verify
rollback, plus deterministic real subprocess termination before and after COMMIT.
A test-only Connection subclass reports the exact boundary over a pipe and blocks
on stdin; the parent kills it without timing sleeps. Before-COMMIT termination
occurs after world-row mutation and checkpoint insertion; after-COMMIT termination
occurs immediately after SQLite commit returns. Writer reopen permits native
SQLite recovery, then assertions compare world, both distinct cursors, revision,
command receipt and action/audit entries as a complete old or new transaction.
No production test hooks were added.

Read-only tests compare database bytes/mtime on clean closed archives, use actual
file mode0444 under nonprivileged UID1000, reject every writer entry point, and
prove missing/future/corrupt schema is not created/repaired. Writable reopen is
used for crash recovery; mode=ro is not claimed to recover a hot SQLite journal.
The subprocess tests establish process-crash transaction atomicity, not power-loss
or filesystem/hardware durability guarantees.

## Self-review and limits

Reviewed allowed-file compliance, frozen records, legacy snapshot byte retention,
strict integer checks, optimistic/idempotent commits, transaction rollback,
closed journal/config data, command settlement, revision context and read-only
behavior. Self-review added load-time checkpoint-operation/audit correspondence
validation and public validation-error wrapping. No known omitted LN02 behavior.
No catalog, runtime controller, provider, HTTP/browser control or live acceptance
is implemented by this task. State transition legality and contextual hidden-world
filtering remain explicitly owned by later tasks. Independent review and full
root validation are still required before claiming task completion.

## Independent review correction round 1

Root supplied two load-bearing findings from independent SPEC/QUALITY review.
Both were reproduced before implementation with five failing focused cases:
`-m pytest tests/test_run_archive_store.py -q -k 'settled_receipt_cannot or
persisted_operation_cannot or terminal_journal_requires'` reported five failed,
43 deselected, all because the required rejection was absent.

1. A new checkpoint could include an already-settled receipt from an older
   checkpoint: duplicate suppression skipped ownership validation, and load-time
   operation/audit correspondence accepted the earlier entry. Writes now reject
   cross-checkpoint settlement reuse with ArchiveRevisionConflict, rolling back
   world/checkpoint/audit changes. Load-time validation rejects a correctly hashed
   forged later operation that reuses the earlier settlement. Exact whole-operation
   retries still return their original checkpoint, and standalone exact audit
   repeats retain their existing sequence.
2. Terminal journal effects were not cross-checked against lifecycle rows. With
   root's prior contract/prompt amendment, lifecycle now stores an internal nullable
   unique `journal_sequence` foreign key. Ordinary transitions have null links;
   every attempt_finished entry must have exactly one linked lifecycle row with
   matching state/reason. Missing, null, orphaned or mismatched links fail closed
   during open/read, with no repairs. Public lifecycle output remains exactly
   sequence/state/reason/timestamp.

Focused correction GREEN: the five original regression cases passed after fixes.
Additional cases cover cleared/orphaned links, repeated terminal entries with
separate effects, null ordinary-transition links and the unchanged public shape.
The malformed-operation and lifecycle-corruption tests compare database bytes
before/after failed read-only opening to establish no repair writes.

Final correction validation:

- `PYTHONPATH=src <task24 interpreter> -m pytest tests/test_run_archive_store.py
  tests/test_world_snapshot.py tests/test_sqlite_repository.py -q`: 175 passed
  (51 archive cases); no skips or warnings.
- Scoped `-m ruff check src/living_world/archives tests/test_run_archive_store.py`:
  passed.
- Scoped `-m black --check src/living_world/archives tests/test_run_archive_store.py`:
  passed, four files unchanged.
- `git diff --check`: passed.

Stable uncommitted correction diff is ready for independent re-review. No other
files were edited, no VCS mutations/full gates/subagents were used, and root's
contract/prompt amendments remain preserved. Root retains completion authority.

## Root independent review and task gates

Independent /root/ln02_review initially found P1 cross-checkpoint Step receipt reuse
and P2 missing required terminal lifecycle effects on read. Original worker corrected
both with5RED regressions and175GREEN focused tests. Scoped re-review: both ADDRESSED,
SPEC PASS / QUALITY PASS, NO SUBSTANTIVE FINDINGS. No deferred or parked findings.
Root approved internal lifecycle journal linkage in task/prompt before implementation.

Final task tree uses dependency-only Python3.13.5 from task24/.venv with PYTHONPATH=src:

- `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`:
  passed **1503 tests / 10 existing deliberate skips**, including actual Chrome;
  lint/format and **39 examples** passed; no new warnings.
- Public CLI matrix passed all3pinned schema12 hashes, two fresh runs/outcome,
  resume1/3/4 complete row equality and success/failure terminal zero-step saves.
  Outcomes remain success10/stall5/failure13.

Raw logs/retained inputs/databases are in current-plan ignored SDD workspace under
integration checkout: ln02-task-make.log and ln02-task-matrix/results.json.
Separate examples, final whitespace and merged gates recorded after completion.
No normal CLI/browser archive entrypoints, live inference or controls claimed.

Separate task `make examples` with same VENV: **39 passed**. Final staged/unstaged
`git diff --check`: passed. Evidence ln02-task-examples.log. No schema/world-codec/
dependency changes; exact authorized source/document boundary preserved.
