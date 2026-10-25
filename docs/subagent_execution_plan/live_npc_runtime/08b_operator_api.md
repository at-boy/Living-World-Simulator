# LN08b — Local authenticated operator API

Status: independently reviewed and integrated after task/merged root validation.
Delivery8731bbf; base LN08a integrationc6640b5; contract52da486.
**Goal:** authenticate local administrative reads and queue durable runtime commands
without moving simulation ownership into HTTP handlers.
**Architecture:** in-memory AdminSession guards a separate operator app. RuntimeService
remains the only controller writer; readonly archives and RevisionSource provide
historical DTOs. No browser assets, CLI serve or remote/player API in this stage.
**Tech Stack:** existing Python/FastAPI/SQLite and standard-library secrets/asyncio.
**Spec:** approved live runtime design, operator section and original LN08.

## Scope and global constraints

Python>=3.11, strict types, no dependencies/format/SQL/world changes. Managers mutate,
systems behave, immutable events, filtered NPC cognition/proposals unchanged. This
is privileged operator access only; no operator DTO becomes NPC context. Existing
create_app GET-only behavior/static/default URLs remain unchanged. No new start/fork/
resume HTTP endpoint; explicit run construction remains application/CLI composition.

Exactly nine worker paths (root correction amendment below):
- src/living_world/api/auth.py (new session/HTTP authorization)
- src/living_world/api/operator.py (new app/DTO/routes)
- src/living_world/api/inspection_routes.py (synchronous DTO worker dispatch only)
- src/living_world/runtime/service.py (readonly controller association getter only)
- tests/test_runtime_operator_api.py (new)
- tests/test_runtime_service.py (getter/readiness/shutdown association tests only)
- tests/test_inspection_api.py (backward-compatible ASGIClient headers/body support only)
- docs/http_inspection_api.md
- docs/subagent_execution_plan/live_npc_runtime/08b_operator_api-report.md
Root owns task/prompt/common docs; no source outside these paths. No browser/static,
CLI, packaging, catalog/store/source/domain/provider changes. Important missing
producer or architectural ambiguity ->root before implementing/expanding.

## Session and authorization

Frozen AdminSession record: token:str and csrf_nonce:str excluded from repr, origin:str.
AdminSession.issue(*,origin:str='http://127.0.0.1:8000')->AdminSession uses two independent
secrets.token_urlsafe(32) values. Validate origin as an exact credential-free loopback
HTTP(S) origin with hostname localhost/127.0.0.1/::1, valid optional positive port,
no path (including slash), query, fragment, whitespace or control characters; reject
empty ports and dangling ?/# delimiters. Canonicalize configured origin to lowercase
known loopback host and scheme, bracket IPv6 and omit default80/443 ports. Store that
canonical origin; incoming Origin must match it exactly without normalization. CLI later supplies its
actual canonical loopback origin/port. Session remains memory-only, never archived,
logged, put in URLs, query parameters, cookies, local/session storage or JSON DTOs.

AdminSession.authorize(request:Request,*,mutation:bool=False)->None raises fixed
HTTPException: missing/malformed/wrong Bearer ->401 detail unauthorized (static
WWW-Authenticate:Bearer); wrong/present foreign Origin on any route ->403 forbidden;
POST additionally requires Origin present/exact and X-CSRF-Token matching nonce.
Check Bearer first, then Origin/nonce. Use compare_digest safely for arbitrary header
strings (non-ASCII/malformed input must produce401/403, never500). No credentials or
raw header/exception text in errors. Do not expose mutation flag as a query parameter:
fixed read/write dependency wrappers call authorize with the server-chosen boolean.

Every operator JSON/world/archive GET requires Bearer. Same-origin GET may omit
Origin; if present it must match. Every control POST also needs exact Origin and
nonce. No CORS middleware/permissive headers, alternate mutation method or token URL.
GET /runtime/status returns X-CSRF-Token ONLY after successful authentication, so
later browser can keep it in memory. All operator responses including errors use
Cache-Control:no-store. Health/version may be public and contains no world/session
secrets. No placeholder runtime page/static route in this task.

## Service association and lifecycle

Add readonly RuntimeService.controller property ->RunController|None under existing
_lock, returning its current controller without owner-thread mutation or resource
exposure. Observe None before ready and the same final closed-controller publication
after shutdown. No changes to start/poll/commands/cancellation/construction algorithms.

create_operator_app(service:RuntimeService,controller:RunController|None,*,auth:AdminSession)
 ->FastAPI validates collaborators. If nonNone controller is supplied it MUST be
exactly service.controller; mismatched service/controller raises safe ValueError.
Live operations use current service.controller, allowing None before readiness or
an archive-only session; no HTTP handler starts/polls/steps/builds a controller.
This prevents showing one controller while service.submit mutates a different one.

App lifespan finally calls service.shutdown via asyncio.to_thread, joining owner/
provider resources even after server stop; no raw exception/session logging. Service
owns final settlement/mirror/audit. CLI later also guards cleanup idempotently. Browser
disconnect/GET does not stop a world. Existing source and independent app behavior
are unaffected. Do not auto-Retry or turn provider failure into a successful state.

## Status and control routes

GET /runtime/status JSON exactly {'live':None|LIVE}. LIVE keys:
attempt_id,lineage_id,state,state_version,revision,tick,activity,error_code,mode,
scenario,model,configuration_error,inspection_prefix. State/version/revision/tick/
activity/error come from one immutable controller.status snapshot. Revision/tick mean
last durable complete world, not pending candidate. inspection_prefix is None without
revision, otherwise server-generated `/live/checkpoints/{revision}`. model is None or
{'name':str,'digest':str|None}; use immutable nonsecret config for mode/scenario/model.

Load metadata once per ready attempt using readonly catalog APIs off the event loop;
cache plain immutable metadata, not archive handles. On metadata failure keep status
responsive with mode/scenario/model None and configuration_error='archive_invalid';
otherwise configuration_error None. No repeated failing DB scan on every status poll.
None controller ->liveNone, no invented initialization/world/attempt. All synchronous
catalog/DTO work runs in worker threads; control admission awaits a Future asynchronously.

POST /runtime/commands accepts EXACT existing CommandEnvelope keys command_id,action,
expected_state_version via existing model.envelope; no missing/extra/coerced fields.
Authentication precedes body parsing/lookup/submission. Invalid JSON/schema ->422
fixed invalid_command. Version is operational state_version, NOT checkpoint revision.
Call only service.submit and await asyncio.wrap_future for durable admission; never
controller.submit/step/manager mutation, event-loop blocking Future.result or fabricated
202 before admission. queued receipt ->202, applied ->200, rejected ->409. Same-envelope
duplicates retain durable receipt/effect; reused ID/different envelope ->409
command_conflict. Stale/lifecycle rejection includes existing nonsecret receipt/reason.
Closed/not-ready/no-live ->409 fixed runtime_unavailable; audit/archive submission
failure ->409 archive_invalid. No automatic Retry. Methods other than POST do not act.

Response is existing receipt fields only, using safe JSON primitives. A queued
receipt is NOT a durable pause/step effect ACK; later applied result owns its checkpoint.
GET /runtime/commands/{command_id:path} uses readonly current-attempt archive.command:
known receipt ->200, unknown/no live ->404 not_found, archive error ->409 archive_invalid.
Opaque command ID is parameterized archive lookup, never a filesystem identity.
No auth headers/nonce enter command envelope/audit. Future/client cancellation must
not invent applied effects; repeated stable ID safely discovers or resubmits outcome.

## Archive and revision routes

GET /archives returns {'attempts':[SUMMARY,...]} in catalog order. SUMMARY keys:
attempt_id,lineage_id,mode,scenario,parent,started_at,ended_at,lifecycle,last_revision,
tick,error_code. Parent is None or {'attempt_id':str,'revision':int}. Use public
catalog summaries, include unsuccessful/setup/incomplete/corrupt discoveries; no
Path/ref/runtime object serialization. Inaccessible catalog ->409 archive_invalid.

GET /archives/{attempt_id} returns {'attempt':SUMMARY,'configuration':JSON|None,
'configuration_source': 'archive'|'reservation'|'requested'|None,'outcome':str|None,
'journal_total':int,'recent_journal':[{'kind':str,'payload':JSON},...]}.
Use public config_document for config; readonly archive.config/entries when readable.
Recent journal is the last50 typed validated entries in order, with journal_total
explicitly showing truncation; no raw unsafe response, headers or new persistence.
Outcome is latest attempt_finished outcome, not an invented game-success boolean.
Valid pending/setup-failed/failed-uninitialized no-world attempts still return known
metadata/config using public read_reservation/setup_config; no fake checkpoint or
successful provider validation, journal_total0/recent[] when no archive exists.
Physical archive_invalid/archive_incomplete/duplicate identities or corrupt metadata
->409 fixed archive_invalid; unknown/malformed identity ->404 not_found. Listing
still retains those bad rows; viewing must not repair them or relabel active owners.

GET /archives/{attempt_id}/checkpoints returns {'checkpoints':[{'revision':int,'tick':int},...]}
in ascending order from complete readonly checkpoints. Known valid no-world ->[];
unknown404, physical/format corruption409. No world blobs in this metadata list.
Use existing public archive methods; do not expand store/catalog APIs for optimization.
This initial bounded slice favors correctness; long-history scan cost is later work.

Mount create_inspection_router under `/archives/{attempt_id}/checkpoints/{revision}`
and `/live/checkpoints/{revision}`, with authorization before source reconstruction.
Use one shared RevisionSource per app, trusted server prefixes and Request.path_params;
8a not_found->404,archive_invalid->409. Live prefix resolves only current service
controller attempt; no controller404. Parse path revision strictly nonnegative decimal,
not bool/negative/float/arbitrary text. Exact selected revision fallback to archive
survives controller publication-cache eviction. No arbitrary query-provided API base.
Existing GET DTO responses unchanged, no runner/model or writes for history.

## Required tests, TDD and gates

- [x] Genuine RED then GREEN session and service association, no prototype code first.
- [x] Session tests token/nonce independence, hidden repr, origin validation; missing/
  wrong/non-ASCII Bearer, absent/foreign Origin, wrong/non-ASCII nonce;401/403fixed
  errors, nonce only authenticated status, no CORS/no-store, no alternate method bypass.
- [x] Readonly service getter before ready/after shutdown and wrong-controller app
  refusal; app starts no runner; lifespan shutdown joins actual owner resources.
- [x] Real command tests duplicate/concurrent/stale step exactly one complete tick,
  changed envelope conflict, queued pause stays pending until durable applied receipt,
  explicit Retry only on provider error, Stop and terminal conflict; verify durable
  archive audit/receipts and actor/world owner thread, no HTTP mutation.
- [x] During delayed fake-provider inference, actual status request remains responsive
  and reports last durable tick/revision/activity. At least one real uvicorn loopback
  status/control/auth case, not only monkeypatched route strings. No actual model.
- [x] Archive list/details/checkpoints includes success, stopped, failed, interrupted,
  setup-only and typed failed-uninitialized attempts; safe corrupt/unknown outcomes,
  configuration-source labels, bounded50recent journal/truncation count, no secret leak.
- [x] Pinned root/prefixed all-world JSON and safe errors, multiple panels same selected
  revision while owner advances, archived cache-eviction reload and historical no
  controls/steps/provider; all source bytes/mtime/entries unchanged by reads/failures.
- [x] Unauthorized requests neither submit nor reconstruct/read protected archive data;
  tokens/nonces absent from all archive files, returned error/DTO JSON and captured logs.
- [x] Extend existing test_inspection_api.ASGIClient with optional headers/body bytes and correct query
  separation from path (for real auth-bypass query tests)
  while preserving existing calls/behavior; reuse helper, no copied full client/httpx.
- [x] Final focused: PYTHONPATH=src TASK_PY -m pytest tests/test_runtime_operator_api.py
  tests/test_runtime_service.py tests/test_inspection_api.py tests/test_runtime_revision_source.py -q.
  TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python.
  Scoped Ruff/Black/whitespace, self-review/report command/result/counts/warnings only.

Worker no VCS/index/commit/worktree/subagents/fullmake/examples/installs/realmodel/
othercheckout writes. Unit temp fixtures allowed; normal manual simulation archives
must persist. Root owns exact contract/prompt/common docs, review/fix/re-review, full
task/merged make, separate examples, whitespace and retained canonical/newCLI checks.

## Root pre-dispatch review

Interfaces:8a router/source provide readonly DTOs; existing controller owns immutable
status and receipts, service.submit is only mutation gateway. Getter adds safe service
association; test-client extension preserves existing API/browser tests. Error/status/
security and metadata producer choices are explicit; UI/token-file/serve wiring remain
later stages. All nine paths and required tests correspond; no NPC boundary change.

## Root correction amendment — worker dispatch for inspection DTOs

Independent review confirmed shared async GET handlers call synchronous inspector DTO
methods on the event loop, violating this task's responsiveness contract. Root adds
inspection_routes.py to the exact worker boundary solely to change synchronous DTO
handlers from async def to def, preserving all routes, names, signatures, dependency
resolution, return DTOs and errors. FastAPI dispatches them in its worker pool; no
second router or copied handler implementation. This applies consistently to existing
standalone and prefixed consumers. Add a genuine RED/GREEN regression in the existing
operator test file: block a DTO in a worker while an actual loopback status request
remains responsive, assert DTO execution is off the event-loop thread, release/join
in finally. Existing root/prefixed inspection/browser compatibility gates still bind.
No other source expansion or scheduling/serialization architecture change authorized.
