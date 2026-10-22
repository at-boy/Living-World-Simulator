# LN08a — Reusable read-only revision inspection

Status: authorized bounded LN08 inspection stage after reviewed LN07e integration
`bca7e0b`; implementation independently reviewed and task-validated; delivery and
feature integration complete by the merge containing this status. Deliverybcbff33;
task/merged2087/10,39examples/exactacceptance PASS.

**Goal:** share the existing GET-only world routes and reconstruct exact, pinned
archived checkpoints without a runner, provider or source write.
**Architecture:** `create_app(engine)` keeps its public behavior, mounting one
reusable router. `RevisionSource` uses the reviewed pure archived-inspection helper
and an eight-entry LRU; every loaded inspector is detached and immutable by convention.
**Tech Stack:** existing Python/FastAPI/SQLite stack; no new dependencies.
**Spec:** `docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md`, approved LN08.
**Execution:** bounded worker, independent SPEC/QUALITY review, root integration.

## Global constraints and scope

Python>=3.11, strict types, no dependencies, formats or SQL/world schema changes.
Managers mutate, systems behave, events immutable. This is privileged operator
inspection only: no new NPC-visible data, model context, mutation, gateway or inference.
Original LN08 remains incomplete; auth/control API, browser assets/prefix wiring and
CLI serve lifecycle follow as separate bounded stages, then LN09 real-model acceptance.
Do not implement placeholders or expose new operator routes in this stage.

Exactly seven worker-owned paths:
- `src/living_world/api/inspection_routes.py` (new reusable router)
- `src/living_world/api/revision_source.py` (new detached revision cache)
- `src/living_world/api/server.py` (replace world handler definitions with router)
- `tests/test_runtime_revision_source.py` (new)
- `tests/test_inspection_api.py` (router compatibility coverage)
- `docs/http_inspection_api.md` (shared router/source behavior and remaining work)
- `docs/subagent_execution_plan/live_npc_runtime/08a_revision_inspection-report.md`

Root owns this plan, saved -prombt, common docs and architecture. Original LN08
bounded test coverage is split here into a dedicated revision-source test file;
no worker may expand the above boundary. CLI/service/catalog/archives, browser assets,
packaging, domain, provider and existing browser tests remain unchanged.

## Exact interfaces and dependencies

`create_inspection_router(resolve_inspector: Callable[[Request], WorldInspector])
 -> APIRouter` in inspection_routes.py. Import WorldInspector from existing
api.inspection. Consume the same DTO methods and return annotations as current server.
No health/static routes in this router; those remain in server.create_app unchanged.

Every world handler resolves one inspector exactly once per request through a
synchronous FastAPI dependency (run in its worker thread) rather than synchronous
archive IO directly on the async event loop. Resolve Request.path_params in the
caller resolver; the router has no knowledge of attempt/revision/auth/controller.
This allows mounting under arbitrary trusted server-chosen path prefixes later.
Keep root world route paths, names, ordering, response shapes and existing entity/
holder/run metadata 404 behavior. No methods other than existing GET behavior.
Existing create_app(engine: SimulationEngine)->FastAPI signature, title, health,
/inspector, /inspector/assets allowlist and packaged bytes/default API base unchanged.
Capture one EngineWorldInspector(engine) in create_app's resolver. Preserve module app.

`RevisionSource(catalog: RunCatalog, *, controller: RunController|None=None)`
`RevisionSource.open(attempt_id: str, revision: int)->WorldInspector`
`RevisionSourceError(LookupError)` with `.code: Literal['not_found','archive_invalid']`.
Error messages are those fixed codes only; no raw exceptions/paths/contents. Constructor
validates catalog and optional controller types (bad collaborator TypeError). Optional
controller is an inspection association only: no mutating calls, owner access or
publication-cache fast path in this task. Archive is authoritative for every miss.
No other public API needed; next operator stage maps safe errors to HTTP404/409.

RevisionSource must reuse existing
runtime.entrypoints.load_archived_inspection(catalog, attempt_id, revision), then
EngineWorldInspector(engine). This pure helper already reads retained inputs, uses
SnapshotRepository+SimulationEngine.load_scenario and checks full encode_world equality.
Do not duplicate its reconstruction block, import cli.py, call mode compositions,
ReplayPreparation, RunController construction, provider/broker, or initialize/step.
Do not change helper behavior or its CLI error contract in this task.

## Lookup, failures and cache semantics

- Validate attempt_id with existing identifier (valid UUID4 identity) and revision
  with existing integer(minimum=0); bool/noninteger/negative or malformed/traversal
  identity becomes not_found, without unsafe lookup or storage allocation.
- Before a cache miss load, use public catalog.attempts() to establish identity.
  No match ->not_found; multiple matches ->archive_invalid. No private `_find` or
  filesystem enumeration/guessed paths in this layer. Do not introduce a catalog API.
- Catalog summary failure archive_invalid/archive_incomplete ->archive_invalid.
  Never reject a readable failed/stopped/interrupted attempt merely for its lifecycle
  or provider/operation failure code: historical unsuccessful worlds are valuable.
  An unrelated corrupt catalog entry must not prevent loading a valid selected one.
- A safely identified pending/failed-uninitialized attempt without a complete world
  has no inspectable revision ->not_found. No invented world/checkpoint or repair.
- On readable identified archive, open readonly and inspect latest_revision to check
  requested revision exists. None/out-of-range ->not_found. Validate actual archive,
  not a guessed digest or summary-only checkpoint. Do not retain open archive handles.
- Any actual archive/input/format/schema/definition/load/exact-reconstruction error
  for an identified attempt ->archive_invalid, including RuntimeCLIError3/4 from
  the shared loader. An inaccessible catalog root ->archive_invalid; missing root
  without attempt ->not_found. Suppress raw causes at this boundary.
- An owner-probe diagnostic alone does not invalidate a readable complete world.
  Never label an active attempt interrupted here; catalog existing read semantics own
  discovery. No leases or read-side writes, initialization/migration/manifest repairs.

Use a per-instance lock to serialize cache lookup/miss reconstruction/update. Cache
key is exact (attempt_id,revision), LRU with at most eight loaded inspectors. Same key
returns the cached inspector and marks it recent; ninth distinct successful key evicts
least-recent. Reopening evicted key reloads archive identically. Failed loads do not
populate cache or evict a valid entry. No open DB/lease/controller/runner retained by
cached inspector. A cached entry is the previously validated immutable selected
revision; external tampering is detected on subsequent cache-miss load, no automatic
repair or source rewriting. No latest/default revision guessing in .open.

## Review focus and required regression tests

1. Refactor preserves ALL existing GET endpoints and JSON/404/default static behavior.
2. Pinned multi-panel calls cannot read another checkpoint when owner advances.
3. Cache eviction/concurrent requests never share or advance a mutable live engine.
4. Failed/uninitialized/corrupt/unknown archives receive truthful safe classification.
5. Historical reads preserve exact payload and all source bytes/mtime, including failure.

- [ ] Pin existing inspection tests, then genuine RED for missing router/source.
- [ ] `test_reusable_router_preserves_all_world_routes`: compare full root/prefixed
  route inventory and JSON for a representative populated engine, methods POST/PUT/
  PATCH/DELETE rejected, metadata/entity/holder missing404 unchanged. Existing ASGIClient
  in test_inspection_api avoids unavailable httpx; no installs. Resolver call count
  exactly one/request; Request.path_params arrives intact. Keep old browser tests.
- [ ] `test_source_pins_complete_revision`: recorded generic no-tape, generic taped,
  canonical recorded, live and journal-replay retained worlds reconstruct exact saved
  payload and match world/definition/manager inspection. Use existing unit fixture
  producers only where needed; no real model. Read-only source while owner commits:
  old revision unchanged, new revision independently correct, no pending candidate.
- [ ] `test_source_lru_eviction_and_concurrent_readers`: same key cached, ninth unique
  evicts oldest, recently used survives, evicted reload identical, max8; failed load
  preserves valid cache; concurrent misses are safe and no duplicate mutable builder.
  Test outcomes/reload calls, avoid asserting incidental private OrderedDict layout.
- [ ] `test_source_safe_errors`: malformed/traversal/non-UUID4 IDs, bool/negative/
  noninteger revision, missing root/attempt/checkpoint, duplicate identity, valid
  setup/metadata-only failures without world, corrupt/incomplete/tampered inputs,
  unsupported world schema, inaccessible root. Fixed error codes, no raw path/error.
- [ ] `test_source_keeps_unsuccessful_worlds_readable`: stopped/failed/interrupted
  attempts with complete checkpoints still inspectable; no active relabeling.
- [ ] `test_source_is_read_only`: bytes/mtime of archive/input/reservation/lock files
  and directory entries unchanged before/after success and failure; no new sidecars or
  owner.lock creation. Patch runner/step/provider constructors to fail if invoked.
- [ ] GREEN focused/scoped checks; self-review and truthful own report. Source engine
  snapshot exactness, provider zero IO and read-only failures must be evidence, not
  test-name-only claims. No broad suite reruns for small corrections.

Focused final command (PYTHONPATH=src):
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python -m pytest tests/test_runtime_revision_source.py tests/test_inspection_api.py tests/test_runtime_cli.py -q`.
Scoped Ruff/Black and whitespace over allowed Python/docs. Report command/result/
counts/warnings/failures, TDD and self-review; do not paste successful output.
Worker no VCS/index/commits/worktrees/subagents/fullmake/examples/installs/othercheckout
writes. Root independently reviews/fixes/re-reviews then authoritative task and merged
make, separate examples, whitespace and retained canonical/newCLI acceptance. Preserve
all branches, task worktrees, owner edit and every normal simulation attempt archive.

## Root pre-dispatch self-review

Producer/consumer: existing CLI pure loader returns exact detached engine; source
wraps it with safe source error mapping/cache. Router consumes existing WorldInspector;
server mounts it at root now, operator later mounts it under pinned prefixes and auth.
No new HTTP endpoint, asset, provider call, owner mutation or NPC context this stage.
Original LN08 security/UI/serve acceptance is explicitly deferred, not claimed done.
Spec coverage and five review risks map to named tests. Boundary and interfaces are
complete; unresolved architectural choice must be sent to root before worker edits.


## Root router compatibility clarification

Verified installed FastAPI0.143.3 include_router stores lazy _IncludedRouter objects
without .path; this breaks the existing flat create_app route inventory. Preserve
that existing inventory without weakening its test: attach the reusable router's
concrete APIRoutes to application.router.routes during create_app construction,
before requests/OpenAPI generation. The router has no startup/lifespan handlers
and root mount needs no prefix/dependencies; reuse its handlers, no copied route
definitions. Do not call private FastAPI internals or alter installed dependencies.
Later prefixed consumers use normal include_router. Verify root and prefixed actual
GET JSON, OpenAPI world paths, names/order and readonly method behavior. Existing
root dependency behavior remains valid; no dynamic post-start route mutation.


## Root review correction1 — truthful failed reservation without world

Public catalog.reserve can raise typed ArchiveReservationError after saving valid
attempt.json with reservation_error=archive_initialization_failed, before any world.
Public catalog.attempts validates this metadata and reports failed/last_revision=None/
archive_initialization_failed. This safely identified failed-uninitialized attempt
has no complete world, so RevisionSource.open must return not_found, not classify
it as corrupted because open_attempt rejects the deliberate failure marker. Keep
physical archive_invalid/archive_incomplete handling unchanged; do not treat every
failed lifecycle/no-revision row as missing rather than corruption. Use existing
public validated catalog semantics, no source repair or private catalog production API.
Required genuine RED/GREEN producer regressions: reserve publication raises before
DB creation; and create empty valid DB then raise before reserve return. Preserve
typed ref/validated failure metadata, fixed not_found, all source bytes/mtime/entries
unchanged, no reconstruction/runner/provider call. Seven worker paths unchanged.
