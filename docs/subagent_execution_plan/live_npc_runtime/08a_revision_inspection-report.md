# LN08a revision inspection implementation report

Status: bounded implementation ready for independent root review; root validation,
integration and completion decision remain pending. Original LN08 remains incomplete.

## Delivered behavior

Extracted the existing 25 ordered world GET handlers into
`create_inspection_router(resolve_inspector)`. Every handler resolves one inspector
through a synchronous FastAPI dependency, off the async request thread. The router
accepts arbitrary trusted prefixes and preserves path parameters, response DTOs,
names, ordering and missing metadata/entity/holder 404 responses. Health, packaged
inspector/static allowlist/bytes and module application remain in `server.py`.

Applied the root-approved compatibility clarification: installed FastAPI 0.143.3
uses lazy router inclusion without a flat `.path` inventory. `create_app` attaches
the reusable router's concrete routes before startup; no private FastAPI API,
dependency modification or duplicate handlers were introduced. Prefixed consumers
use ordinary `include_router`. Existing flat-inventory regression remains intact.

Added `RevisionSource` with validated collaborators and explicit identity/revision,
public catalog discovery, safe fixed `not_found`/`archive_invalid` errors, readonly
archive validation and reuse of `runtime.entrypoints.load_archived_inspection`.
The source creates no runner/provider/lease/controller and does not use live-owner
publication shortcuts. It retains only detached inspectors, under a per-source
lock and eight-entry LRU; failed misses preserve valid cached views. Readable failed,
stopped and interrupted worlds remain inspectable. Setup-only and metadata-only
attempts without worlds have no inspectable checkpoint. Cached validated views
remain pinned; later misses detect external corruption without repair.

HTTP documentation describes these Python producer interfaces and deferred
operator/auth/control/browser-prefix/serve work. No new HTTP operator route or
NPC-visible pathway was added.

## TDD and focused validation

Interpreter for all checks:
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`;
tests use `PYTHONPATH=src` from the LN08a task checkout.

- Initial router RED: `python -m pytest tests/test_inspection_api.py -q`:
  12 existing tests passed, one new test failed because the router module was absent.
- Router integration exposed two failures caused by FastAPI lazy router inventory;
  root approved and amended the exact plan/prompt before the compatibility fix.
- Initial source RED: `python -m pytest tests/test_runtime_revision_source.py -q`:
  collection failed because the source module was absent.
- Initial source GREEN: the initial safe-selection test passed. Subsequent
  regressions expanded pinning/cache/mode/error/readonly coverage during implementation.
- Intermediate test authoring failures: incorrect broker class name and an invalid
  schema fixture rejected by the archive writer. Corrected the fixture imports and
  used deliberate stored-schema tampering; neither required production scope changes.
- Combined source/router intermediate GREEN: 17 passed.
- Focused three-file suite before final added diagnostics/invalid selections:
  `python -m pytest tests/test_runtime_revision_source.py tests/test_inspection_api.py tests/test_runtime_cli.py -q`:
  66 passed, no skips or warnings.
- Expanded source-only check: `python -m pytest tests/test_runtime_revision_source.py -q`:
  29 passed, no skips or warnings.
- Final three-file suite: `python -m pytest tests/test_runtime_revision_source.py tests/test_inspection_api.py tests/test_runtime_cli.py -q`: 75 passed, no skips or warnings.
- `python -m ruff check` on all five allowed Python paths: passed. Initial lint
  identified FastAPI dependency-default call warnings and import ordering; fixed
  by constructing one dependency object per router and sorting imports.
- `python -m black --check` on the same five paths: passed, five unchanged.
- Worker whitespace scan over seven worker-owned files: passed (trailing whitespace and final newlines). Root `git diff --check` remains pending.

Regression evidence includes exact saved `encode_world` equality for generic no-tape,
generic taped, canonical recorded, live fixture and journal-replay retained worlds;
world/definition/manager inspection; separate old/new owner revisions; request path
parameters, once-per-request resolver and worker-thread execution; explicit 25-route
inventory, root/prefixed OpenAPI and actual JSON/method responses; cache reload,
LRU recency/eviction and concurrent same-key misses; setup/no-world/unknown identities,
missing checkpoints, corruption, duplicate IDs, unsupported stored schema, inaccessible
catalog diagnostics and CLI loader error mapping. Owner-probe failures alone do not
invalidate a complete world. Successful and failing reads preserve file bytes/mtime
and directory entries, including absent lock files; forbidden step/controller/service/
broker/provider/lease entry calls fail the readonly test if invoked.

All simulation producers were unit-test fixtures using temporary retained archives.
No ad-hoc normal simulation, real-model call, installation, VCS/index operation,
full `make`, `make examples`, subagent or other-checkout write was performed.

## Boundary and self-review

Only the seven worker paths in the exact task were edited. Root independently owns
plan/prompt clarification changes. CLI, service, catalog, domain, assets, packaging,
existing browser tests, schemas, serialization and dependencies were not changed.

Self-review checked route parity and source error ordering, collaborator validation,
lock coverage, failed-miss cache preservation, explicit revision handling, archive
closure before return, absence of provider/runner/ownership calls and privileged-only
inspection. The cache is immutable by convention through the inspector interface;
external archive changes are intentionally revalidated only on misses.

Independent SPEC/QUALITY review, correction/re-review as needed, authoritative task
and merged-tree `make`, separate `make examples`, `git diff --check`, retained exact
acceptance and all VCS/integration transitions remain root responsibilities.

## Independent review correction 1

Root supplied the sole substantive SPEC/QUALITY P2: a typed ordinary failed
reservation with `archive_initialization_failed`, no complete world and no revision
was incorrectly classified `archive_invalid` because `open_attempt` rejects the
intentional reservation failure marker. Read the root's amended exact task and
saved prompt before changing the source.

Added two regressions using the public `catalog.reserve` producer: archive creation
raises before DB publication; archive creation creates/closes an empty valid DB,
then raises. Both assert `ArchiveReservationError.ref`, matching validated public
summary (`recorded`, `failed`, no revision/tick, exact reservation failure code),
fixed safe `not_found`, no reconstruction/provider/service/controller/step/lease
entry, preservation of all eight valid cached inspectors, and unchanged source
bytes/mtime/directory entries across the failed inspection.

Genuine RED: `PYTHONPATH=src python -m pytest tests/test_runtime_revision_source.py -q -k failed_reservation_without_world`
failed both new cases with `archive_invalid` instead of `not_found` (29 deselected).
The narrow source fix recognizes only the validated failed/no-revision/exact
`archive_initialization_failed` summary after existing physical corruption checks.
It does not broadly reinterpret failed/no-revision worlds or change catalog behavior.
GREEN: same command passed both new cases (29 deselected).

Final correction checks use the same task24 interpreter and LN08a checkout as above:

- `PYTHONPATH=src python -m pytest tests/test_runtime_revision_source.py tests/test_inspection_api.py tests/test_runtime_cli.py -q`: 77 passed, no skips or warnings.
- Scoped `python -m black --check` over the five allowed Python files: passed.
- Scoped `python -m ruff check` over the five allowed Python files: passed.
- Whitespace scan over seven worker files: passed; root's VCS whitespace gate remains pending.

Only revision source, its dedicated tests and this report changed in this correction. No VCS/index operations or other-checkout writes.


## Root task acceptance — October 23, 2026

Initial independent review found one P2 failed-uninitialized reservation misclassified
as archive_invalid. Root amended contract/prompt before producer-based correction.
Scoped re-review: P2 ADDRESSED, SPEC/QUALITY PASS, zero open, NO SUBSTANTIVE FINDINGS.
Final focused77passed, scopedRuff/Black/whitespace passed. Nine reviewed changed paths
(seven worker plus two root contract/prompt amendments); no reviewed source changes
from formatting/gates. Root owns common documentation changes below.

- Full `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`: PASS,2087passed/10existing deliberate skips,39examples including actualChrome regressions.
- Separate `make examples` sameVENV: PASS,39examples. Whitespace PASS.
- Exact schema12 canonical success/stall/failure fresh/resume1/3/4/terminal-zero-step
  matrix: PASS, matches LN07e;26retained readable normalCLI checkpoints.
- NewCLI acceptance: PASS,7normal attempts retained including2failed/uninitialized,
  exact childworld/cursors/referenceequality/parentbytes/readonlyinspection.
- `git diff --exit-code -- src tests`: PASS, reviewed source unchanged by gates.

Evidence ignored current-plan SDD: ln08a-review-1.diff,ln08a-fix-1.diff,
ln08a-review-final.md,ln08a-task-make.log,ln08a-task-examples.log,
ln08a-task-matrix and ln08a-task-cli. Source supports privileged readonly inspection
only; auth/control/browser/serve and real-model acceptance remain later stages.
Delivery and repeated merged gates follow; branches/checkouts/owner edits preserved.


## Root merged acceptance — October 23, 2026

Deliverybcbff33 pushed on preserved codex/live-npc-ln08a-revision-inspection. Feature
merge clean; reviewed source exactdelivery (`git diff bcbff33 --exit-code -- src tests`).
Mergedmake sameabsoluteVENV: PASS,2087passed/10existing skips,39examples/actualChrome.
Separatemakeexamples PASS39; whitespace PASS; source unchanged after review/gates.
Canonical schema12 exactmatrix matches task,26normalCLIarchives retained/readable.
NewCLI7cases PASS, allattempts including2failed/uninitialized retained. Evidence:
ln08a-merged-make.log,ln08a-merged-examples.log,ln08a-merged-matrix,ln08a-merged-cli.
Integration is the merge containing this report. LN08a complete; auth/controlAPI,
browser/serve and installed-model gates remain pending. Owner-local patch/protected
refs and every task branch/worktree preserved.
