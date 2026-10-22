# LN08b local operator API report

Status: independently reviewed and root task-validated delivery; feature integration
and repeated merged gates remain pending at the owner-requested pause.

## Delivered behavior and ownership

Added separate `create_operator_app` and frozen memory-only `AdminSession` with
independent hidden-repr secrets, canonical configured loopback origins, exact incoming
Origin and CSRF enforcement, arbitrary non-ASCII header safety, fixed failures,
no-store responses, and no CORS permissions. Authentication precedes command body
parsing and protected archive/source access. Fixed read/write wrappers prevent query
parameters from changing mutation authorization.

The readonly locked service controller getter preserves association before readiness
and after shutdown. The operator app rejects a mismatched controller, reads current
service publications, captures one immutable status snapshot, and caches immutable
nonsecret metadata or its safe error per attempt. Catalog work runs in worker threads.
Only `service.submit` admits commands; its Future is awaited asynchronously, with
queued/applied/rejected receipt distinctions, stable ID deduplication, stale/lifecycle
rejections, safe submission failures, and explicit Retry. Lifespan joins the service
through a worker thread. Browser request completion does not stop it.

Archive DTOs use public catalog/reservation/setup/config/archive methods. Failed,
setup-only, uninitialized and corrupt discoveries remain visible in listings;
valid no-world details/checkpoint lists preserve their actual meaning. Details expose
total typed journal count and only the last 50 entries. Existing inspection router
and shared RevisionSource supply exact pinned historical/live worlds and eviction
reload without reconstruction duplication, model invocation, or writes.

Only the nine authorized paths were written after the root scope amendment: new auth/operator modules, controller
getter in service, new operator tests, appended service getter test, backward-compatible
shared ASGIClient optional headers/body and query separation, HTTP documentation,
this report, and the shared inspection router correction described below. No source outside scope, domain/store/catalog/provider/CLI/assets/
packaging/dependencies/VCS/index/worktree changes were made by the worker.

## TDD and validation evidence

Interpreter for all pytest/style commands:
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
Pytest uses `PYTHONPATH=src`.

- RED session/getter slice: `-m pytest tests/test_runtime_operator_api.py tests/test_runtime_service.py::test_controller_readonly_publication_before_ready_and_after_shutdown -q`
  failed 4 tests for missing auth module/controller getter. After implementation,
  the same slice passed 4 tests.
- RED operator slice: `-m pytest tests/test_runtime_operator_api.py -q` failed 2
  new tests for missing operator module, with the 3 session cases passing. Real
  command/status/archive routes were then implemented and exercised.
- Final focused gate: `-m pytest tests/test_runtime_operator_api.py tests/test_runtime_service.py tests/test_inspection_api.py tests/test_runtime_revision_source.py -q`
  PASS after review correction, 88 tests, 24.70 seconds, no warnings. Earlier
  focused runs passed 87 and 82 tests before final coverage/correction.
- Additional malformed IPv6-origin cases: `-m pytest tests/test_runtime_operator_api.py::test_session_secrets_and_origins -q`
  PASS, 1 test before the review correction; included in the post-correction final focused run.
- Scoped `-m ruff check` on the seven authorized Python paths: PASS.
- Scoped `-m black --check` on the same seven paths: PASS, 7 unchanged.
- Local trailing-whitespace scan on all nine authorized paths: PASS.
  Root retains authoritative `git diff --check` including this report.

Seventeen operator cases include real service durable step/duplicate/stale/conflict,
concurrent duplicate admission, provider-error explicit Retry, Stop/terminal rejection,
queued Pause remaining pending until durable applied receipt, owner-thread identity,
last-complete status during delayed fake inference, real uvicorn loopback status/
auth/control and lifespan owner join, metadata-error caching, no-world configuration
source labels, physical corruption, completed/failed/stopped/interrupted outcomes,
latest-50 journal truncation, all collection world DTO panels, exact revision eviction
reload, fixed body/submission errors, auth-before-access and query-bypass denial,
no CORS/no-store, and secret absence from archive bytes and captured server logs.
Readonly archive assertions compare bytes and mtimes before/after successful reads
and missing-revision failures. All simulation fixtures are unit-test temporary
archives; no normal manual simulations or real model calls occurred.

Meaningful intermediate failures were corrected: test fixtures initially omitted
required writer leases; an initial test incorrectly expected stopped outcome text
and one checkpoint after shutdown, although authoritative behavior is null outcome
and a final same-tick settlement checkpoint; the retried original step correctly
ends applied, not rejected. These test expectations were fixed to preserve existing
producer semantics. Initial Ruff found formatting/import/unused-variable issues and
long suppression placement; all final style gates pass. A helper edit command first
used unavailable `python`; rerun with `python3` completed the intended bounded edit.

## Self-review and remaining root gates

Self-review checked explicit file scope, no private catalog access, public readonly
archive methods, immutable status/metadata handling, service-only mutation admission,
fixed errors, strict command schema, server-selected auth mode, exact prefix selection,
nonce/header-only delivery, no world construction in handlers, and final lifecycle
join. NPC cognition and simulation authority are unchanged.

No unresolved producer or architecture gap identified. Initial archive-list/detail/
checkpoint scans intentionally retain public API scan cost, as the contract specifies.
Root must independently review SPEC and QUALITY, resolve findings/re-review, run full
`make`, separate `make examples`, whitespace and retained canonical/new-CLI gates,
then decide completion and any focused commit/integration. Worker has not run those
root-owned gates or performed any VCS operation.


## Independent-review P2 correction

Root accepted the independent finding that synchronous inspector DTO methods were
called inside async shared route handlers, blocking the HTTP event loop. Root amended
the exact task and saved prompt before authorizing the ninth worker path,
`src/living_world/api/inspection_routes.py`. The correction changes exactly 24 handler
`async def` declarations to `def`; the existing synchronous settlement-stage handler
is untouched. Names, parameters, dependency resolution, URLs, returned DTOs and errors
are preserved. FastAPI now dispatches all synchronous inspector DTO work in workers
for both standalone and prefixed route consumers.

Genuine correction RED/GREEN:
`PYTHONPATH=src TASK_PY -m pytest tests/test_runtime_operator_api.py::test_blocked_inspection_dto_keeps_loopback_status_responsive -q`
failed before the source change: 1 failed, 1.50 seconds, concurrent authenticated
actual uvicorn status request timed out while the inspection DTO occupied the event
loop. Its finally block released the DTO and joined server and owner resources.
The exact command after the bounded source change passed: 1 passed, 0.62 seconds.
The regression holds a real pinned world DTO, confirms concurrent loopback status
returns last-durable revision/tick before release, and asserts DTO execution differs
from the server event-loop thread. Release and resource joins remain in finally.
Scoped Ruff and Black checks on seven Python paths pass. Root retains independent
re-review, full task/merged gates, examples and VCS integration.

Post-correction four-file focused gate: PASS, 88 tests, 24.70 seconds, no warnings.
All-nine-path trailing-whitespace scan: PASS. No VCS or index operation performed;
review corrections remain unstaged relative to the root-staged baseline.

## Root review and authoritative task validation

Independent reviewer /root/ln08b_review found one P2: shared async inspection DTO
handlers blocked the event loop. Root accepted it and amended task/prompt in both
checkouts before expanding the worker boundary to nine paths. The real loopback
regression failed before correction and passed after24 handlers changed to sync def.
Scoped independent re-review: original P2 addressed, SPEC/QUALITY PASS, NO SUBSTANTIVE
FINDINGS; reviewer reran regression1passed0.67s. Final focused88passed24.70s.

Root task commands and results (absolute VENV below):
- make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv:
  PASS2105tests/10existing deliberate skips,229.28s; actual Chrome suite and all39examples.
- Separate make examples with same VENV after make closed: PASS39examples.
- git diff --check and git diff --cached --check: PASS.
- git diff --exit-code -- src tests relative reviewed staged source: PASS; gates
  did not change source or tests after review.
- retained recorded_matrix.py: PASS exact schema12 hashes for all three outcomes,
  fresh equality/resume1,3,4/terminal zero-step;26normal CLIarchives preserved.
  Root opened each latest complete checkpoint readonly:26readable.
- retained archived_cli_acceptance.py: PASS7normal CLIattempts including2expected
  failed-uninitialized; exact child world/cursors, resumed tick2/forked tick3 equality,
  readonly inspection and unchanged source bytes.

Evidence in feature ignored .superpowers/sdd/2026-10-19-live-npc-runtime:
ln08b-review-1.diff, ln08b-fix-1.diff, ln08b-reviewed-final.diff,
ln08b-review-initial.md, ln08b-review-final.md, ln08b-task-make.log,
ln08b-task-examples.log, ln08b-task-matrix and ln08b-task-cli (including every archive).
Root approves focused task delivery only. Feature merge/repeated full gates are
pending; browser assets/serve and actual installed-model acceptance are incomplete.
Owner requested pause soon; no next task started, no main/milestone/tag movement.
