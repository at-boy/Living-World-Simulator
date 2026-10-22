# LN07d runtime service implementation report

Status: correction round 1 handed off for independent re-review; root validation,
acceptance, integration and commit remain pending. No VCS/index mutation, full
`make`, examples, dependency installation or writes to other checkouts performed.
Root owns the amended task contract/prompt and common milestone documents.

## Delivered behavior

- `RuntimeService` claims one non-daemon owner thread. That owner constructs and
  closes leases, archives, compositions, brokers and controllers. Caller reads use
  existing immutable controller publications; commands use a FIFO queue and
  `Future[CommandReceipt]`. A queued Future result is admission, while archive
  `command()` remains the durable applied/rejected acknowledgment.
- `_LaunchFactory` in private `launch.py` owns mode construction and startup
  settlement. New start consumes the same exact retained-input reservation, checks
  identity/configuration before accepting ownership for failure settlement, calls
  `on_reserved` on owner before GET, and preserves mismatched existing attempts.
- New live setup and linked live restart/fork use the existing preflight and
  reserve/complete setup producers. Source checkpoint/cursors validate before
  semantic terminal checks. Pure driver/feedback validation does not stage
  observations, memories, candidates or provider requests. Historical operational
  completed/stopped/failed outcomes do not seal valid saved worlds; child-relative
  budgets renew. Pinned semantic terminal plain resume skips discovery/generation.
- Generic recorded composition supports no tape, generic replay tape and strict
  canonical founders policy/tape. Existing strict wrapper payloads remain exact.
  Saved `recorded` versus `legacy_recorded` cursor kind is preserved. Unknown
  terminals, malformed closed cursors and world mismatch fail before readiness,
  retaining linked child cp0 evidence.
- `limits.continuous` is a strict recorded-only boolean metadata extension. Missing
  or false means archived numeric max or scenario default for missing/null max;
  true requires missing/null max and means unbounded. No archive/world format bump.
  Old raw-null limits did not encode continuous intent: that historical preference
  cannot be recovered; exact saved world/cursors are preserved without inventing it.
- Shared bounded poll loop automatically stops request-budget exhaustion normally
  with `request_budget_exhausted` in attempt finish and final lifecycle. Other
  provider failures remain paused for explicit Retry/Stop. Initial recorded Stop
  can precede terminal/max-zero evaluation without advancing a tick.
- Root-authorized `settle_shutdown()` factors existing owner shutdown settlement,
  leaving the archive open for final mirror publication/failure audit; `close()`
  still settles and closes. Mirrors follow archive commits at initial/final and
  configured child-relative tick cadence. Mirror failure records archive-ahead
  truth at the latest committed checkpoint.
- Replay uses no HTTP, one shared captured ForkPoint/horizon for composition and
  driver, and original sealed live ancestry on replay resume/fork. Source and child
  snapshot/cursors, config fingerprint, retained inputs and ancestor chain validate.
- Shutdown cancels preflight, wakes owner and joins up to five seconds; timeout
  retains thread/ref/stop intent for later join. Pending Futures settle, cancelled
  Futures are skipped, conflicts remain local to their Future, and terminal owner
  remains available until shutdown. Unexpected admission errors fail safely; failure
  settlement recovers durably accepted requests even if IO raised before queue insert.

## Test-driven evidence and validation

Genuine RED/GREEN slices observed for continuous metadata/cursor selection,
generic composition, feedback validation, initial Stop/budget stopping, absent
service API, earlier source-revision validation, startup cancellation before first
poll, final mirror failure, after-archive constructor/publication failure,
unexpected admission error sanitization, invalid replay cursor classification, and
durable admission write-then-error receipt settlement. Fixture errors were corrected
separately from production behavior; no failed command is claimed successful.

Runtime tests cover real archive ownership, command FIFO/idempotence/conflict,
cancelled Future and shutdown drain, callback failure/order, missing model,
hung/trickle preflight timeout/cancellation, callback join timeout and later join,
request budget versus provider Retry, mirror failure/cadence, semantic-terminal
zero-HTTP live resume, changed provider fork and pinned digest failure, generic tape
and continuous fork, both cursor kinds, zero-limit terminal tamper rejection, and
all three canonical service world digest pins.

Restart proofs include:

- A real process commits a paused generic tick, exits normally or is hard-killed;
  a later process/owner child starts with exact world and both cursors and completes
  one turn. Source files remain byte-identical and lease is reacquirable.
- An action-bearing live source checkpoint contains work definitions and memories.
  A later subprocess resumes from it and completes exactly one turn; its entire
  snapshot and driver/feedback cursors match an independently advanced uninterrupted
  reference, covering resources, work charges/progress and cognition. Child records
  exactly two action outcomes; source files remain byte-identical.
- Replay and replay resume from an earlier checkpoint reproduce complete source
  snapshot/cursors; the existing replay regression also covers concurrent source
  advance between composition/driver construction and shared horizon.

Final focused command (explicit interpreter; `PYTHONPATH=src`):

```sh
/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python -m pytest tests/test_runtime_service.py tests/test_runtime_restart.py tests/test_runtime_recorded.py tests/test_runtime_ollama_driver.py tests/test_runtime_controller.py tests/test_runtime_founders_feedback.py tests/test_runtime_journal_replay.py -q
```

Initial handoff result (historical): **172 passed** in **61.19 seconds**, after the
durable-admission regression/fix. No warnings or failures in that focused run.
Current correction-round validation is recorded below.

Initial handoff scoped Ruff: pass over all 16 allowed Python paths. Initial scoped
Black `--check`: pass, 16 files unchanged. `git diff --check`: pass. No successful command output pasted.
Worker self-review inspected actual adapter/controller diff, launch ownership,
source/child selection, queue teardown and mirror order. Root review remains required.

## Interrupted test command and cleanup

During the genuine RED test for unexpected admission failure, its first version
omitted `finally: shutdown()` and left its recorded service owner alive after the
assertion failed. Tool command session **73076** was explicitly interrupted with
Ctrl-C and returned **exit 130**, ending that test process and its owner thread.
The fixture was recorded-only and launched no provider subprocess. The test now
always shuts down in `finally`; its corrected regression and later focused suite
pass. A later cleanup check found that pytest had already pruned that temporary
attempt directory, so no stale lease path remains to reacquire. Other cleanup tests
explicitly reacquire their attempt leases after failures/cancellation/hard kill and
confirm callback-timeout owner eventually joins. No command from that interrupted
session remains running.

## Boundaries and remaining responsibility

Initial implementation used the then-authorized 17 paths (including this report).
Correction round 1 expands the allowed boundary to 19 paths: catalog.py and its
existing tests, only for post-allocation ordinary-fork error identity. Task/prompt
amendments are root-owned. No CLI/runner/hooks/domain/protocol/SQL/schema,
assets/store/lease/packaging changes were made. Existing direct controller
and strict recorded adapter behavior is covered by focused regression tests.

Full task and merged-tree `make`, separate `make examples`, retained CLI matrices,
independent review/corrections, common docs, integration and commits are root work.
This report does not certify those gates or the later LN07e consumer/serve stages.


## Independent review correction round 1

Root authorized this bounded correction after review reported two P2 findings.
The exact task/prompt amendment was read before correction. Both findings are
addressed; independent re-review and root gates remain required.

1. Ordinary `RunCatalog.fork` now wraps only post-`_reserve` ordinary Exception
   failures in existing `ArchiveReservationError(ref)`, preserving original cause
   and allocated evidence. Pre-allocation validation and successful clone/seal
   behavior remain unchanged. No catalog enumeration/diffing, duplicate fork loop,
   child repair/deletion, or BaseException/control-flow remapping was introduced.
   The linked launch path validates the supplied ref's catalog root, lineage,
   distinct child identity, requested config and exact selected parent pair, then
   acquires the normal owner lease and accepts that child for existing failure
   settlement. Failure is recorded at actual latest revision: None before copy,
   zero when commit succeeded before raising. Source bytes remain unchanged.
2. Mirror state/helper now exists before pre-poll cancellation. Normal exit,
   cancellation and failure share one owner-finally settlement -> final mirror /
   failure audit -> close sequence with the archive open for audit. If no initial
   poll occurred, mirror cadence derives its initial tick from the settled complete
   publication. Failed mirror publication is not retried during final cleanup.
   `mirror_failed` overrides a pending cancelled startup error and is recorded at
   the actual complete stopped checkpoint. Successful early cancellation writes
   the exact stopped cp0 mirror, advances zero ticks, and remains safely rejoinable.

Focused RED/GREEN evidence:

- Catalog retention, before-cp0 clone and commit-then-raise cases, plus the recorded /
  replay resume / explicit fork matrix: **15 expected RED failures**, then **15
  passed**, 108 deselected, 4.80 seconds. Cases assert allocated ref/parent, actual
  revision, failed lifecycle and attempt_finished outcome, exact copied checkpoint
  when present, unchanged source bytes and released lease.
- Controlled-constructor shutdown with valid and failing mirror: **2 expected RED
  failures** (missing valid mirror; cancelled instead of mirror_failed), then the
  early-cancel/mirror focused selection **6 passed**, 20 deselected, 0.64 seconds.
  Cases compare exported snapshot to archive, verify archive-ahead failed outcome
  on mirror error and repeated shutdown/lease cleanup.
- Ref-adoption guards: **3 passed**, 25 deselected, 0.49 seconds, preserving source,
  foreign-catalog and wrong-parent attempt bytes on rejected adoption.

Current exact focused command (`PYTHONPATH=src`, explicit assigned interpreter):

```sh
/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python -m pytest tests/test_runtime_service.py tests/test_runtime_restart.py tests/test_runtime_recorded.py tests/test_runtime_ollama_driver.py tests/test_runtime_controller.py tests/test_runtime_founders_feedback.py tests/test_runtime_journal_replay.py tests/test_run_archive_catalog.py -q
```

Current focused result: **286 passed** in **68.51 seconds**, no warnings/failures.
Current scoped Ruff: pass over all 18 authorized Python paths. Black `--check`:
pass, 18 files unchanged. Final `git diff --check`: pass after report update.

Only correction source/tests/report changes are unstaged relative to the root's
staged baseline. No index/commit/branch mutation, full make/examples, installs,
subagents, or other-checkout writes were performed. No new interrupted/hung test
command occurred in this correction round. All targeted and final focused commands completed. No active validation command,
task-owned service owner or provider subprocess remains; the regressions explicitly
reacquire failed-child leases and join controlled-constructor shutdown owners.


## Root task acceptance — October 22, 2026

Independent reviewer ln07d_review (gpt-6.1-sol/high): initial SPEC/QUALITY FAIL with
two P2 findings; narrowly amended contract/prompt before correction. Scoped final
SPEC PASS / QUALITY PASS, both addressed, zero open, NO SUBSTANTIVE FINDINGS.
Root inspected the actual staged source and boundary: 19 changed paths, including
two root-owned contract/prompt amendments; 19 permitted worker paths with two
permitted test files unchanged. No source changed after final review.

- `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`: PASS, 2018 tests passed / 10 existing deliberate skips, 39 examples.
- Separate `make examples` with the same VENV: PASS, 39 examples.
- `git diff --check` and staged whitespace check: PASS.
- Root canonical recorded matrix: PASS, full schema-12 payloads identical to LN07c
  for success/stall/failure; two fresh runs, resume at ticks 1/3/4 and terminal
  zero-step checks. All 26 normal CLI invocations retain readable complete archive
  checkpoints in ignored `ln07d-task-matrix/state/living-world/runs`.
- `git diff --exit-code -- src tests`: PASS; make did not alter reviewed source.

Evidence: ignored current-plan SDD workspace `ln07d-review-1.diff`,
`ln07d-fix-1.diff`, `ln07d-task-make.log`, `ln07d-task-examples.log`,
`ln07d-task-matrix/results.json` and invocation logs. Delivery/merged gates follow;
this does not certify CLI/browser or actual installed-model acceptance.
