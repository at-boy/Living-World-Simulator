# LN08e implementation report — shared prepared archived launch

Status: independently reviewed and root task-validated; delivery commit follows.
Feature integration and repeated merged gates remain pending.

## Worker changes

- `src/living_world/runtime/entrypoints.py`: frozen `ArchivedLaunch`, defensive
  namespace preparation, guarded one-shot launch, extracted live/source launch
  paths, canonical recorded founders preparation, and exact root-amended
  preparation-ownership cancellation/close handling.
- `tests/test_runtime_launch_request.py`: 33 adapter cases covering preparation,
  mutable caller namespaces, invalid paused values, sequential/concurrent launch,
  cooperative provider cancellation, canonical outcomes, stall limits/continuous
  behavior, checkpoint-only settings, retention handoff/failures, source config,
  checkpoint/cursors/cadence and source bytes, and preparation cancellation/close.
- This report. Existing `tests/test_runtime_cli.py` needed no edits; its existing
  live success/error/stop, replay cadence and final-mirror regressions are included.

Root-owned task/prompt amendments are preserved. No VCS/index operations, other
checkout writes, full make/examples, installations, downloads or real model calls
were performed by this worker. Temporary archives were unit-test/reproduction
fixtures only.

## Architecture and lifecycle

Preparation constructs the existing service before any blocking launch, copies the
parser namespace, and preserves `_requested` equality/model rules and inherited
mirror cadence. It reserves nothing, retains nothing and starts no threads or
provider requests. A private Lock atomically consumes the first valid launch before
any effects; invalid paused types do not consume it. The guard is released before
blocking owner setup. The adapter exposes no mutable public launch state.

Live setup uses the existing materialization/reserve/lease/retain/fail path. Source
resume/fork/replay delegates to the existing service. `run_archived` now obtains its
service from preparation and launches after starting its existing stop watcher;
its error normalization, polling, final settlement and join policy stay intact.

Recorded preparation uses canonical scenario/tapes, the approved settings and stall
limit, and public `LegacyArchiveSession` methods. The preparation handle closes
without successful `__exit__`; service ownership receives an unsettled attempt with
no premature lifecycle/checkpoint/journal writes. RuntimeService remains the sole
world owner; domain state, events, persistence schema, NPC filtering and gateway
trust boundaries are unchanged. Legacy headless founders routing is unchanged.

Root-amended pre-owner cancellation settles only a ref-less `service_closed` from
`service.start`, retaining the exact already allocated identity. Live uses
AttemptLease/fail_setup; recorded reenters the same closed session and directly
closes it. Exceptions carrying an owner ref are untouched. Settlement/close failure
reports `archive_failed` with the local ref and makes no repair/re-reservation.
The initial recorded close failure also preserves identity as `archive_failed`,
including when it overrides retention failure. A close exception is not evidence
that cleanup succeeded.

## RED/GREEN evidence

Python used for all worker checks:
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
All pytest commands used `PYTHONPATH=src` in the LN08e task worktree.

- `python -m pytest tests/test_runtime_launch_request.py -q`: initial RED, 14
  failures asserting the missing shared preparation factory before production edits.
- Initial implementation run: 11 passed, 3 failed because the test initially
  assumed outcome labels rather than established `settlement_success`,
  `founding_failure`, and null at tick limit. Assertions were corrected; canonical
  final-world digests already matched. Expanded validation also corrected one
  expected provider model name from `tiny` to canonical `tiny:latest`.
- Adapter suite before root amendments: GREEN, 22 passed; subsequently expanded
  recorded/config/continuous coverage: 24 passed.
- Requested six-file focused baseline before amendment: GREEN, 168 passed.
- `python -m pytest tests/test_runtime_launch_request.py -k preowner -q`: RED,
  4 failed/24 deselected, reproducing lost refs for both modes before launch and
  during event-synchronized retention. After the root-approved correction: GREEN,
  4 passed/24 deselected.
- Expanded cancellation/settlement/close coverage: adapter GREEN, 31 passed.
- `python -m pytest tests/test_runtime_launch_request.py -k initial_recorded_close
  -q`: RED, 2 failed/31 deselected, reproducing first-close exceptions without refs
  after successful retention and masking retention failure. After the root-approved
  correction: GREEN, 2 passed/31 deselected.
- Scoped Ruff initially found one import-order violation in the new test file;
  corrected. Subsequent scoped Ruff passed. Black formatted the two changed Python
  files; subsequent scoped check passed before the final close amendment.

Final focused command:
`python -m pytest tests/test_runtime_launch_request.py tests/test_runtime_cli.py tests/test_runtime_service.py tests/test_runner_cli.py tests/test_founders_cli.py tests/test_runtime_preflight.py -q`.
Result: GREEN, 179 passed in 77.00 seconds; no warnings reported.

Final scoped style commands:
`python -m ruff check src/living_world/runtime/entrypoints.py tests/test_runtime_launch_request.py tests/test_runtime_cli.py`
and
`python -m black --check src/living_world/runtime/entrypoints.py tests/test_runtime_launch_request.py tests/test_runtime_cli.py`.
Result: both passed after the final close amendment; Black checked three files.
No meaningful warnings reported.

## Limitations and root gates

No HTTP/CLI serve command, signal/token implementation, browser serving, dependency,
package exports or installed-Ollama acceptance is included. Providers in tests are
local fake HTTP fixtures. No live operational acceptance is claimed.

Root retains independent read-only review and disposition, `make`, separate
`make examples`, `git diff --check`/VCS boundary checks, retained canonical 26/new CLI
7/wheel 11 checks on task and merged trees, common status-document updates, commit
and integration. No worker completion claim substitutes for those gates.

## Root review and task validation — October26,2026

Independent review SPEC/QUALITYPASS, NO SUBSTANTIVE FINDINGS, open0; reviewer ran
33adaptertests/13.65s. Stable reviewed staged diff SHA256
d5b3e6ae4bc2c17f9211965de1b6b7422e7d858ff26a9e35d4bd8d65da992894.
Root validation after review:
- make VENV=shared absolutevenv: PASS2173,10existing deliberate skips,318.21s;
  actualChrome plus39examples, no new warnings.
- Separate make examples after make closed: PASS39.
- git diff --check/cached equivalent: PASS; source/tests/pyproject exactly reviewed.
- recorded_matrix.py: PASS exact historical hashes, outcomes, twofresh/resume1/3/4/
  terminalzero-step;26retained normalCLIarchives, latestcomplete checkpoints readable
  readonly; exact comparison to LN08d merged results.
- archived_cli_acceptance.py: PASS7retainedcases including2expectedfaileduninitialized;
  exactchildinitialworld/driver/feedbackcursors, resume/forkparity, sourcebytesunchanged.
- wheel_runtime_check.py: PASS offlineisolated build/extractedimport,11resourcebytes,
  runtime/inspector/authstatus/CLIhelp;0normal simulations.
Evidence in rootignoredworkspace ln08e-task-{make,examples,matrix,cli,wheel} and review.
Root task/prombt amendments preceded respective corrections. Three worker paths used;
existingtest_runtime_cli unchanged. No source changes during rootgates. CLIserve and
installedOllama remain incomplete. Feature integration will repeat required gates.
