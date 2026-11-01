# LN09f2 — Authenticated trace API and offline application factory

> Use superpowers:subagent-driven-development: one bounded worker, independent
> spec/quality review, root task + repeated feature validation.

Status: COMPLETE after R1 fixround2 independent spec/quality review, one finding addressed/zero open; task and repeatedmerged gates2691/10existing skips/allcompatibility/native/newwheelAPI checks PASS. Taskdeliveryac09081 preserved/pushed.
Root approved-design execution continues using one worker and independent review.
Goal: make saved exact call evidence available through the same protected API in
live operator and an inert offline FastAPI app. CLI/browser UI and export follow.
Spec: docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md (owner approved),
plus explicit later owner requirements for exact raw request/response/backend/timing
retention and analysis. Those requirements supersede older raw-invalid nonretention.

## Architecture / constraints

Use reviewed9f1 reader unchanged for traces and bodies. Add bounded catalog identity/
reservation discovery; do not call RunCatalog.attempts/open_attempt, AttemptArchive,
RevisionSource or load worlds just to list/read traces. Mount one shared router in
existing operator and a new standalone factory. Offline app never constructs/starts
RuntimeService/RunController, reserves an attempt, loads a GGUF or contacts a provider.
Existing unauthenticated inspect app does not receive raw-trace routes.

Python>=3.11, strict hints/frozen DTOs, no dependencies. Simulation/managers/gateways
retain authority; no NPC context/LLM prompt changes. Admin-only raw evidence never
becomes NPC knowledge. Preserve old fingerprints, schemas, recorded hashes and routes.
Read-only means recursive source bytes/mtimes unchanged; normal rollback-only reader
restriction remains explicit. No source lease/index/cache/migration or writes.

## Review focus

- Unauthenticated/hostile-Origin calls must not reach even catalog discovery.
- An invalid/no-checkpoint attempt remains listed without certifying its world.
- Oversized/unsafe metadata fails within the catalog budgets without following links.
- Body attachments/preview retain exact invalid/error bytes and sealed-prefix authority.
- An offline application startup/request/shutdown must never initialize a runtime owner.

## Exactly seven worker paths

- NEW src/living_world/archives/trace_catalog.py
- NEW src/living_world/api/trace_analysis.py
- src/living_world/api/operator.py (import/mount shared router only)
- NEW tests/test_trace_analysis_catalog.py
- NEW tests/test_trace_analysis_api.py
- NEW docs/trace_analysis.md
- docs/subagent_execution_plan/live_npc_runtime/09f2_trace_api-report.md

Root owns task/prombt/common docs/handoff/evidence/VCS/gates. Worker no VCS/index/
subagents/fullmake/examples/realservers except test-loopback/dependencies/downloads/
other checkout edits. Report missing seams BEFORE expansion. No 9f1 source edit.

## Catalog interfaces and limits

In trace_catalog.py, frozen `TraceCatalogLimits(max_entries:int=10000,
max_header_bytes:int=1048576)`, exact positive ints, no bool/unlimited mode.
Use existing TraceAnalysisLimitError for budget excess, same fixed diagnostic.

Frozen `TraceAttemptSummary` fields: `lineage_id:str`, `attempt_id:str`,
`metadata_state:Literal['available','missing','invalid']`, `has_database:bool`,
`mode:str|None`, `scenario_key:str|None`, `reserved_at:str|None`,
`parent:tuple[str,int]|None`, `reservation_error:str|None`.
Frozen `TraceAttemptPage(attempts:tuple[TraceAttemptSummary,...],
next_after:tuple[str,str]|None,
 integrity:Literal['reservation_metadata_checked']='reservation_metadata_checked')`.
Do not expose local absolute paths/config/raw request bodies in the catalog JSON.

`list_trace_attempts(catalog:RunCatalog, *, after:tuple[str,str]|None=None,
 limit:int=50, limits:TraceCatalogLimits=DEFAULT_CATALOG_LIMITS)->TraceAttemptPage`
`resolve_trace_attempt(catalog:RunCatalog, attempt_id:str, *,
 limits:TraceCatalogLimits=DEFAULT_CATALOG_LIMITS)->AttemptRef`

Safely scan only root/lineage/attempt, no recursion into objects/inputs/spools. Count
ALL inspected directory entries against max_entries, including ignored names. Validate
ID names with existing identifier; skip non-ID catalog entries and unsafe/non-directory
lineage nodes without following them. Root itself must be safe; missing root returns
empty list and unknown resolution without creating directories. Collect/sort bounded
refs by (lineage_id,attempt_id). Duplicate attempt IDs across lineages reject for
resolution; invalid ID and unknown/duplicate identity raise fixed ArchiveFormatError.
A known attempt symlink/non-directory/unsafe path must not be followed; resolver rejects.
List that attempt as invalid without reading its target. Do not use private catalog
methods (which materialize a full catalog tuple without this budget).

Validate after is exactly tuple(valid lineageID,valid attemptID); limit is exact int1..100, no bool. Return
metadata ONLY for selected page refs, ordered strictly after key. next_after is last
returned pair iff more identities remain. This is a current filesystem listing, not
a sealed catalog snapshot; a refresh discovers concurrent insertions before a cursor.
No catalog mutation or hardcoded source root. Resolve reads no header or database.
DEFAULT_CATALOG_LIMITS is one frozen shared instance; returned page containers/parent
values must be immutable tuples.

Read selected attempt.json with safe_path/regular independent no links and bounded
read(max_header_bytes+1), not stat then unbounded read_text. Missing header is missing;
invalid/oversized/unsafe header is invalid on that row, without discarding other rows.
Decode through existing loads/document/AttemptConfig, catalog.parent_pair/timestamp,
and model.parent_boundary. Exact reservation format1 structure: required format,
lineage_id,attempt_id,config,parent,reserved_at,reservation_error; optional parent_journal.
Require matching ref identity; reservation_error is None or archive_initialization_failed.
Config has mode/scenario_key/seed/software_revision/settings, no provider resolution.
This validates reservation syntax only, not setup markers/world/inputs/parent seals.
Invalid/missing rows have None descriptive fields and preserve their IDs.
has_database means a safely regular independent archive.sqlite3 exists; unsafe DB path
makes row invalid and false, without opening SQLite. Missing DB is false. Never claim
an available header means a complete/valid world. No lease probing creates owner.lock.

## Shared protected router and inert app

In api/trace_analysis.py:
`create_trace_analysis_router(catalog:RunCatalog, *, auth:AdminSession,
 mode:Literal['live','offline']='live')->APIRouter`
`create_analysis_app(catalog:RunCatalog, *, auth:AdminSession)->FastAPI`
Router prefix /analysis. Factory mounts it with offline mode and no runtime owner.
Operator mounts same router with live mode, existing behavior otherwise unchanged.
Factory disables docs/redoc/openapi and uses no-store middleware on ALL responses,
including authentication/query/error responses. Operator already has no-store.

All routes GET only, require auth.authorize BEFORE any catalog/filesystem/SQLite/body
access. Bearer/Origin policy is existing AdminSession, no new credential scheme/CORS.
Run blocking catalog/reader work in asyncio.to_thread; never hold event loop for scans.
No logs of tokens/body/path/exceptions. Fixed sanitized HTTP errors: unknown/invalid/
duplicate attempt ID404 not_found; other ArchiveFormatError409 trace_unavailable;
TraceAnalysisLimitError413 analysis_limit_exceeded; unexpected adapter failure409
trace_unavailable. Catch TraceAnalysisLimitError before ArchiveFormatError, including
resolution, so resource exhaustion is413 rather than404. Resolver invalid/unknown/
duplicate identity is404; other adapter failures are409. Invalid cursor/query pair400 invalid_query; framework scalar-type
query validation may remain422. Never return an exception string or raw traceback.

Routes and exact response shape:
- GET /analysis/status: {mode,access:'read_only',capabilities:['calls','body_download',
  'body_preview'],world_validation:'not_performed'}.
- GET /analysis/attempts: query after_lineage_id + after_attempt_id both-or-neither,
  limit default50/max100. {integrity,attempts:[summary fields],next_after:null or
  {lineage_id,attempt_id},listing:'current'}. No full archive validity claim.
- GET /analysis/attempts/{attempt_id}/traces: query through_sequence + journal_digest
  both-or-neither (test None presence, not truthiness; sequence0 is valid),
  after_sequence default0, limit default50/max100. Pass the exact
  JournalBoundary or None to reader. {archive_format,boundary:{sequence,digest},
  calls:[all TraceCall fields],next_after_sequence,integrity}. Use model.plain/manual
  DTO projection; do not deepcopy immutable mappingproxy with dataclasses.asdict.
- GET /analysis/attempts/{attempt_id}/bodies/{sha256}: require both through_sequence
  and journal_digest; reader verifies prefix/whole selected bytes before response.
  application/octet-stream, attachment filename inference-{validatedsha}.bin,
  X-Content-Type-Options:nosniff. No arbitrary path/filename or raw HTML response.
- GET /analysis/attempts/{attempt_id}/bodies/{sha256}/preview: same required boundary
  and whole-body verification. Return {sha256,byte_length,integrity,text,truncated,
  preview_byte_length,replacement_used,preview_kind:'utf8_text'} using first65536bytes.
  Try strict UTF8 on prefix, otherwise decode replacement and replacement_used=true.
  truncated iff whole body exceeds prefix cap. Empty observed body returns text''.
  It is a bounded text preview; exact bytes remain the separate attachment.

Absent legacy traces/unavailable bytes never synthesize a body/duration; list exact
None values and preserve original int/float elapsed. Incomplete/invalid/error/empty
captured bodies remain downloadable. Reused source mapping/timing remain original,
not a new latency/cost. Reader integrity does not certify world or parent ancestry.
No POST/PUT/DELETE route, CLI, static UI, forensic spool, export or new provider call.

## Tests / RED-GREEN / validation

- [x] RED missing catalog/factory/routes; implement only after meaningful RED.
- [x] Bounded real catalog: pagination/order/newinsert refresh/missing root, no writes,
  malformed/missing/oversized reservation header rows, duplicate IDs, unsafe paths/
  symlink/hardlink/traversal, custom node/header budgets. No full-reader calls, model
  path opens, preflight or leases. Reject stale malformed cursor types/bools.
- [x] API ASGI +actual owned uvicorn loopback: mode live/offline, real traced and
  legacy/failed-no-checkpoint archives, auth BEFORE mocked FS/body/spool spies, missing/
  wrong token401 and hostile Origin403. No-store on every error/response; no CORS.
- [x] Exact trace fields/body bytes/status/durations, stable prefix page chain during
  append, excluded later body/tampered seal rejection, selected corruption/missing
  body409, limits413, unsupportedWAL409 without source changes, unrelated corruptbody
  narrow integrity only. Existing normal operator routes/assets remain unchanged.
- [x] Unsafe text, invalidUTF8/JSON, empty/partial/HTTPerror bodies: exact attachment
  bytes+safe fixed filename/nosniff, preview cap/replacement/truncation including split
  UTF8 prefix, no rawexception/body/token in errors. Legacy/pending states stay unknown.
- [x] Offline factory cannot construct RuntimeService/RunController, reserve, load a
  world/model, call providers, acquire lease or mutate source. Missing root/DB creates
  nothing. Recursive source bytes/mtimes unchanged on success/failure.
- [x] Focused new suites plus tests/test_runtime_operator_api.py,
  tests/test_trace_analysis_reader.py and scoped Ruff/Black/whitespace. Own report
  commands/results/counts/warnings/scope/limits; freeze for independent review.

Root runs fullmake/separateexamples/exactcanonical26readonly/CLI7/sourceServe4/
wheel11+Serve4 and actual installed-wheel newAPI smoke afterreview, repeats aftermerge.
Root commits/pushes/preserves taskbranch; no main/milestone/tag. UI/offlineCLI and
forensic/portable export remain necessary later requirements, not claimed here.

## Root R1 correction contract — guarded JSON serialization

JSON-escaped lone surrogate code units may pass existing pure text validators but
cannot safely render as UTF-8 API text. A selected reservation with an unencodable
projected string must be metadata_state invalid (descriptive fields None), leaving
other page rows usable. Keep exact valid Unicode and all opaque stored body bytes.
Do not amend the shared reader or legacy domain validators. API projection and full
JSON response construction/encoding must occur INSIDE the shared adapter's guarded
error boundary, returning an explicit response so framework serialization cannot
fail afterward. Serialization failures for trace/other projected data return the
fixed409 trace_unavailable with Cache-Control:no-store on both live and offline
mounts; no traceback/privatevalue leaks. Use actual escaped headers and actual ASGI
serialization regressions, including another valid row, trace projection failure,
valid nonASCII text and unchanged exact body downloads/sourcebytes+mtimes. Same7paths.

Root R1 round2 clarification: EVERY projected reservation string must be UTF-8
encodable within per-row validation, including reserved_at. datetime.fromisoformat
accepts any single Unicode date/time separator, including a lone surrogate; parsing
as UTC does not establish encodability. Cover escaped-surrogate timestamps in actual
catalog and ASGI invalid-row/valid-row coexistence tests, and preserve valid encodable
Unicode separators. Correct prior report's timestamp assumption. Same7paths.
