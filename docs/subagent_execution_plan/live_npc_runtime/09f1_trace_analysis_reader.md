# LN09f1 — Read-only bounded trace analysis reader

> For agentic workers: use superpowers:subagent-driven-development, one bounded worker,
> independent spec/quality review, then root task and merged validation.

Status: AUTHORIZED prerequisite implementation, not started.
Goal: inspect saved per-call metadata and verified selected bytes without loading a
world/model or all inference BLOBs. This is the domain prerequisite for approved
admin/offline analysis; it exposes no network route by itself.
Spec: owner-approved live runtime design plus explicit exact per-call retention and
later analysis request; `docs/npc_information_boundary.md` remains binding.

## Architecture and review focus

Use a dedicated read-only SQLite snapshot, pure existing metadata/journal/trace
validators and the unchanged journal prefix hash. Existing AttemptArchive open and
all its full validation remain unchanged. Reusing its full accessors would load all
BLOBs; weakening that validator would break runtime integrity. Choose a separate,
explicitly narrower analysis reader. No new writer, migration, schema, cache or index.

Scope of verification is local trace metadata in a chosen journal prefix plus ONLY
explicitly selected body bytes. Do not certify checkpoint/world/command/lifecycle
consistency, parent lineage seals, reservation/retained-input identity, unreferenced or
unselected body integrity. A failed attempt with no complete world remains analyzable.
No parent/source archive reads, proposal recovery, spool reads, provider calls or leases.

Review focus: giant unselected BLOBs must not be materialized; prefix paging must not
upgrade after later append; invalid bytes/empty bodies must be exact; missing/corrupt
selected evidence must fail closed; narrower analysis must never claim full validity.

## Global constraints and exact worker files

Python >=3.11, strict hints, frozen dataclasses and immutable nested maps/tuples.
Managers mutate/systems behave/events immutable; simulation alone owns truth/goals/
stages. This is privileged engine analysis, never NPC knowledge. No dependencies.
Preserve every previous source fingerprint, archive format and recorded world hash.

Exactly four worker paths:
- NEW src/living_world/archives/trace_analysis.py
- NEW tests/test_trace_analysis_reader.py
- docs/npc_information_boundary.md (one appended engine-only analysis paragraph)
- docs/subagent_execution_plan/live_npc_runtime/09f1_trace_analysis_reader-report.md

Root owns this task, matching -prombt.md, common documents, continuation and evidence.
Worker no VCS/index/commits, subagents, full make/examples, modelservers/downloads,
other checkout edits or additional production paths. Report any missing seam first;
root must amend task and prompt before expansion. Do not use private store methods or
AttemptArchive even just for open/metadata; imports of pure public model validators
and lease.safe_path/validate_ref are allowed. No exports from archives/__init__.py yet.

## Public domain interfaces (in the new module only)

Frozen `TraceReadLimits` fields, with these defaults:
`max_journal_rows=100000`, `max_journal_bytes=67108864`, `max_row_bytes=2097152`,
`max_body_bytes=8388608`. Every field is an exact positive int, excluding bool.
Trusted callers may supply different finite positive limits, never an unlimited flag.
`TraceAnalysisLimitError(ArchiveFormatError)` has fixed message
`Trace analysis limit exceeded.` Exceeding a resource budget never silently truncates.
Invalid parameters/archives raise ArchiveFormatError with fixed safe diagnostics.

Frozen `TraceCall` fields:
`request_id:str`, `sequence:int` (request_started or response_reused sequence),
`base_revision:int`, `source_tick:int`, `actor_label:str`,
`response_kind:Literal['response_validated','response_failed','response_reused']|None`,
`error_code:str|None`, `outcome:str|None`,
`request_trace:Mapping[str,object]|None`, `response_trace:Mapping[str,object]|None`,
`content_digest:str|None`, `elapsed_seconds:float|int|None`, `source:Mapping[str,object]|None`.
No reconstructed request/response body, fabricated clocks or default capture state.
Trace maps are the exact validated original values; reused timing belongs original call.

Frozen `TracePage` fields: `archive_format:int`, `boundary:JournalBoundary`,
`calls:tuple[TraceCall,...]`, `next_after_sequence:int|None`,
`integrity:Literal['trace_metadata_checked']='trace_metadata_checked'`.
Frozen `TraceBody` fields: `boundary:JournalBoundary`, `body:bytes`, `sha256:str`,
`byte_length:int`,
`integrity:Literal['selected_body_verified']='selected_body_verified'`.
Do not add a full-validity flag. Concrete DTO validation may use internal helpers.

`read_trace_page(ref:AttemptRef, *, boundary:JournalBoundary|None=None,
 after_sequence:int=0, limit:int=50, limits:TraceReadLimits=TraceReadLimits())->TracePage`
- limit exact int1..100; after_sequence exact int>=0 and <=selected boundary.sequence.
- None boundary captures current MAX(sequence), zero if empty, and its digest. Supplied
  boundary must be an existing row sequence or0, with exact recomputed digest. Gaps valid.
- Return calls ordered by their request sequence, strictly greater than after_sequence;
  next_after_sequence is last returned sequence only if more calls remain, otherwise None.
  To continue a stable page chain the caller supplies returned boundary, not None.
- State/outcome observations are restricted to that prefix. Later response/action rows
  must not make a pending request appear settled. A rowless prefix returns an empty page.

`read_trace_body(ref:AttemptRef, sha256:str, *, boundary:JournalBoundary,
 limits:TraceReadLimits=TraceReadLimits())->TraceBody`
- Revalidate the same prefix in a fresh snapshot, authorize digest ONLY through a trace
  reference in it, check body type/length and hash of ALL selected bytes before returning.
- Enforce max_body_bytes before loading body bytes. Return exact bytes including b'',
  invalid UTF8/JSON, incomplete prefix and error content; no text decoding/preview here.
- Unavailable/legacy/prefix-excluded digests reject, even if the table contains them.
- No unverified streamed bytes may escape. A bounded selected read into bytes is fine;
  chunked SQLite reads are also fine. Metadata paths never fetch raw body values.

## Read snapshot, metadata and prefix algorithm

Validate AttemptRef and fixed nested identity layout with validate_ref. Recheck safe_path
for directory/database (regular independent non-symlink archive.sqlite3) before each
open; never accept arbitrary relative filenames. Missing path must not create a file.
Use SQLite URI mode=ro, query_only=ON, no immutable=1, explicit BEGIN, bounded busy
wait (timeout1 second), rollback/close on every exit. Each call is one coherent snapshot;
no long-lived connection, lease or write. Fixed safe ArchiveFormatError on SQLite errors.
Use parameter binding for values. Check that metadata/journal and format2 inference_blobs
are ordinary tables (not views/virtual tables) and have the existing expected columns,
SQLite types and identity/primary-key constraints before reading potentially large values.

Read exactly one archive_meta(id=1) row within max_row_bytes BEFORE loading its payload.
Use existing loads/document/AttemptConfig/parent_boundary and UTC validation to validate
its closed structure, supported format1/2 and exact ref identity. This validates local
syntax only; do not claim reservation/ancestor integrity. Do not open worlds/checkpoints.

For selected journal prefix, enforce count<=max_journal_rows, sum UTF8 kind+payload
byte lengths<=max_journal_bytes, each row<=max_row_bytes BEFORE fetching unbounded TEXT.
Reject wrong SQLite value types, malformed JSON/duplicate keys, invalid row linkage types,
unknown journal shapes through JournalEntry/JournalRecord. Do not retain entire payloads:
keep only bounded call/response/outcome/trace-reference indexes needed for this result.
Metadata scan is O(prefix rows/bytes), memory bounded by explicit budgets; no claim of
constant-time pagination. Unselected BLOB data must never be loaded, even on format2.

Hash the unchanged canonical JSON array of records, incrementally: start b'[', then
comma-separated canonical record documents, end b']'. Each document has exactly
sequence, kind, payload, checkpoint_revision, revision_context. It must equal the existing
AttemptArchive.journal_boundary digest byte-for-byte, including empty b'[]'. No reconstructed
or normalized semantic fields beyond existing loads/canonical behavior.

Build local call index: request_started and response_reused introduce unique request IDs;
reused supplies response in the same row. response_validated/failed must match an earlier
request and have at most one settlement. action_resolved must match a locally validated/
reused call, actor/base_revision/source_tick and have at most one outcome. Unknown,
duplicate/contradictory identities reject. No implicit failed outcome for pending calls.
Require no_action iff the retained decision has no action_request.
Validate offered decision against original request via model.validate_offered, not world.
For traced responses require traced request; response length<=request.max_response_bytes+1.
Format1 must have no trace fields. Referenced digest lengths must agree across the prefix;
format2 BLOB schema must match existing store expectations. Check every prefix reference
has a BLOB-valued row with declared length, using length/typeof and digest-specific SQL.
Do not scan/hash unrelated BLOBs or reject later-body orphans outside selected prefix.
Listing may succeed with corrupt unselected body CONTENT of unchanged length; its narrow
integrity tag makes this explicit. Selected corrupted bytes must reject. Full existing
AttemptArchive validation must still reject that same corruption.

## Required TDD and coverage

- [ ] RED named reader imports/behavior absent; implement only after meaningful RED.
- [ ] Real format2 archive fixtures: metadata page exact model/backend/timing/actor/tick/
  error/action/reuse source, multiple calls, stable paging limit1 and immutable DTOs.
- [ ] Exact prefix hashes vs existing full reader: empty, gapped sequences, full journal,
  pending then appended response/action, and tampered old prefix. Later append must not
  upgrade captured page or authorize later body; altered prefix rejects on next call.
- [ ] Request/response BLOBs, b'', invalid UTF8/JSON, HTTP errors and incomplete/unavailable
  retain exact distinction; legacy format1 remains untraced, no schema write/migration.
- [ ] Selected same-length corruption, missing/wrong-type/length/conflicting bodies,
  traced response without request, request cap+1 breach, duplicate/unknown settlements
  and malformed metadata/journal schemas/types reject. Legacy unsupported traces reject.
- [ ] No-checkpoint failed/partial attempt can list valid local traces. Corrupt world/
  command/lifecycle or unselected BLOB does not imply certified world validity; include
  a fixture demonstrating analysis passes narrowly while existing full reader rejects.
- [ ] Bounded memory: unrelated16MiB zeroblob plus tiny valid calls, metadata/selected
  small read Python peak stays below8MiB after imports/fixture setup (tracemalloc scoped
  to reader calls). Full-reader methods monkeypatched to raise prove they are unused.
  Query tracing/fixtures prove no metadata operation fetches raw unselected body bytes.
- [ ] Custom small row/count/total/body limits fail explicitly before large payload/body
  materialization; boundary/limit bool, invalid digest, unknown sequence and unsafe paths
  (database/directory symlink, hardlink, traversal) reject. Missing DB creates nothing.
- [ ] All success/failure reads preserve recursive source bytes AND file mtimes, including
  lock/reservation/retained inputs; no lease acquisition/provider/model/world loading.
  Real concurrent writer test proves one coherent snapshot / later append support.
- [ ] Focused new suite + tests/test_inference_trace_storage.py,
  tests/test_run_archive_store.py and tests/test_run_archive_catalog.py, scoped Ruff/Black,
  whitespace. Write truthful RED/GREEN/counts/scope/limits report, freeze for rootreview.

Root later runs make, separateexamples, whitespace, exactcanonical26readonly/CLI7/
sourceServe4/wheel11+Serve4 after independent review and repeats after featureintegration.
Only root commits/pushes/integrates focused preserved taskbranch; no main/milestone/tag.
No admin API, CLI, UI, export, forensic spool, provider or proposal-contract change here.
