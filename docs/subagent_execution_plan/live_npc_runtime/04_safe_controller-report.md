# LN04 worker report — safe controller and recorded adapter

Status: independent SPEC/QUALITY PASS; root task validation passed. Delivery and
merged-tree evidence follow below. Historical worker checkpoint statements remain
as evidence of their respective stage, rather than current completion claims.

## Scope and behavior

Added the five authorized runtime modules and two test modules. The controller owns
command admission/dispatch, detached candidate engines, durable Step settlement,
nonblocking preparation polls, pause/stop/retry intent and complete immutable
publication. Operational state_version advances independently of checkpoint revision.
Read-side status/history uses a lock-protected eight-checkpoint cache with no archive
IO; mutation methods enforce the creating thread. Construction validates arguments
without initializing simulation or accessing storage.

Initial driver cursors are committed explicitly before control acknowledgement.
Restoration verifies canonical world equality and preserves saved source bytes. Failed
candidates never publish. Successful SQL commit followed by operational/audit failure
publishes the committed checkpoint with failed/audit_failed status, retaining its
applied Step receipt. Terminal saved attempts remain terminal, including setup failures
without a checkpoint. Each poll dispatches at most one queued command before new work;
queued commands are revalidated without accumulating Step credits.

Recorded composition uses existing FoundersPreparation/ReplayPreparation and retained
inputs, validates captured hashes, restores per-engine ephemeral systems, and evaluates
terminal predicates in configured order. It performs no extra observations or model
calls. SnapshotRepository returns detached decoded state and rejects candidate saves.
Recorded cursor/world identity is checked before installation and updated from exact
replay progress after the existing engine tick. Finalization preserves legacy
finalize_proposals and operator-stop semantics.

The only existing producer changes are the authorized optional actual
admitted_state_version in control_requested/load-side replay, and recorded max_ticks=0
configuration support. Existing assertions and runner/replay/founders source remain
unchanged. Root-owned task/prompt edits were present independently; the worker did not
edit those artifacts or any other common documentation.

## Verification

All commands ran from `.worktrees/live-npc-ln04`, with `PYTHONPATH=src` and
`TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.

- Baseline: `$TASK_PY -m pytest tests/test_runner_cli.py tests/test_recorded_proposal_tapes.py tests/test_run_archive_store.py -q` — passed, 196 tests.
- Initial controller RED: new controller collection failed because living_world.runtime
  did not exist, identifying the absent required API.
- Producer RED: `$TASK_PY -m pytest tests/test_run_archive_store.py -q` — 2 failed,
  51 passed; unsupported admitted_state_version and rejected recorded zero-tick config.
- Additional observed RED regressions: reopening stopped attempts became running;
  failed Stop remained queued; unbounded poll drained all queued controls; reopening a
  setup-failed attempt initialized a new world. Each was corrected in authorized scope.
- One expanded intermediate run had a test-fixture error from a missing child temporary
  directory; corrected the fixture without changing any existing assertion.
- Final focused GREEN: `$TASK_PY -m pytest tests/test_runtime_controller.py tests/test_runtime_recorded.py tests/test_runner_cli.py tests/test_recorded_proposal_tapes.py tests/test_run_archive_store.py -q` — passed, 231 tests in 7.59 seconds; no skips/warnings.
- Scoped Ruff check over all changed/new Python files — passed.
- Scoped Black check over all changed/new Python files — passed, 10 files unchanged.
- `git diff --check` — passed.

No full make/examples, VCS mutation, dependencies, provider or infrastructure actions
were performed by the worker, as assigned. Root must perform independent review and
current full gates before completion claims.

## Recorded parity evidence

Old runner outputs were measured before recorded adapter implementation. Initial
exploration used default-bound stall and reached domain failure at tick13; this is not
the canonical stall row. The required canonical stall row explicitly uses max_ticks=5.
All three required rows now assert schema12, complete payload hash, snapshot digest,
tick, immutable event count and replay cursor progress. Full hash pins are in the test.

| Mode | Tick | Payload SHA256 prefix | Snapshot digest prefix | Events |
| --- | ---: | --- | --- | ---: |
| success | 10 | ec4a908de25253fa | 08e45db464eeec34 | 152 |
| stall, max_ticks=5 | 5 | 6fcb0e0003c59faa | 1ac4b3d42faab269 | 77 |
| failure | 13 | fd80996bb1e122cd | 1bf0b8f37ff43a13 | 56 |

Catalog/lease integration covers paused parent fork, exact restored snapshot/cursors,
and final canonical success parity. A real subprocess commits a paused Step and exits;
parent read-only reopen and a linked child fork retain the applied receipt and complete
world, then the child reaches the same canonical success payload/history.

## Self-review and remaining concerns

Reviewed owner-thread guards, immutable records, version/revision distinction,
idempotent/conflicting IDs, truthful stale/future rejections, dispatch revalidation,
pause versus synchronous tick boundaries, interrupted Step/paused retry intent,
precommit quarantine, postcommit audit failure, terminal persistence, zero-tick
finalization, child-relative tick limits and cache eviction. Focused tests cover these
paths using real engines/archive transactions and deterministic test-only preparations.

No unresolved architectural or scope choice is known. Controller construction checks
existing private archive ownership flags because AttemptArchive has no public
read-only/owner status accessor; this avoids unauthorized archive API expansion or
constructor IO. Preparation/provider-specific staged-response reuse remains the driver's
journal-backed responsibility through the amended protocol; no live driver is part of
LN04. Future/evicted history lookup remains a read-only catalog concern for LN08.

## Independent review correction round 1

The independent review found two Important issues in the first submitted diff. Both
were reproduced before correction and are ready for root re-review:

1. `close()` before initial publication could call bounded `poll()` only once, leaving
   another admitted initializing control queued, then fail safe stop without a world.
   Shutdown now dispatches/revalidates outstanding initializing controls and directly
   establishes the initial boundary before stopping. This behavior is confined to close;
   ordinary poll still dispatches at most one control. No preparation/model IO or tick
   begins. The first same-version Pause is applied after healthy initialization; the
   following Stop is truthfully rejected stale_state_version, and close performs its
   own safe stop. A genuine initialization failure remains initialization_failed and
   settles the latched Pause without inventing a checkpoint.
2. Weak-key preparation values indirectly retained their engine through the existing
   founders replay offer provider, retaining discarded worlds. Existing preparation now
   receives a weak engine proxy during ephemeral composition, breaking the value-to-key
   strong reference without changing founders/replay source, patching private fields,
   duplicating replay logic or dropping supported candidate mappings. A real weakref/GC
   regression proves discarded candidate collection while the composition lives and
   verifies the remaining live candidate can still step and finalize.

Round-1 verification (same checkout/interpreter/environment as above):

- Smallest new regressions before fixes — 3 failed as expected (healthy close, genuine
  setup-failure close classification, and discarded-candidate retention).
- Smallest new regressions after fixes — 3 passed in 0.38 seconds.
- Full focused command listed above — 234 passed in 7.71 seconds; no skips/warnings.
- Scoped Ruff — passed. Scoped Black check — passed, 10 files unchanged.
- `git diff --check` — passed.

Only controller.py, recorded.py, their two test modules and this report changed in the
correction. No VCS mutation, broad gates or source changes outside the existing file
boundary were performed. Root re-review/full gates remain outstanding.

## Root independent review and task gates

Independent reviewer /root/ln04_review found two Important issues: preinitialization
close with multiple queued controls and recorded preparation retention of discarded
engines. Both were reproduced and corrected within the original boundary. Scoped
re-review returned **SPEC PASS / QUALITY PASS**, two addressed and zero open findings.
Root inspected the correction diff and accepted the disposition.

Final task tree using dependency-only Python3.13.5 and PYTHONPATH=src:

- `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`: **1589 passed / 10 existing deliberate skips**, including actual Chrome, lint/format and **39 examples**; no new warnings.
- Public CLI canonical matrix: all three pinned schema12 payload hashes, two fresh
  runs per outcome, complete row equality on resume1/3/4, and success/failure
  terminal zero-step passed. Outcomes remain success10/stall5/failure13.

Evidence: ln04-review-1.diff, ln04-review-1-findings.md, ln04-fix-1.diff,
ln04-review-final.md, ln04-task-make.log and ln04-task-matrix/results.json in
the ignored current-plan SDD workspace under the integration checkout.
Public CLI/browser controls and actual model decisions remain later tasks. LN05/LN06
must consume the amended driver initialize/paused/activity/error protocol.

Separate task `make examples` with the same VENV: **39 passed**. Final staged
and unstaged whitespace checks passed. Evidence ln04-task-examples.log.
