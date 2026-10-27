# LN09e — Automatic archived inference and sealed trace reuse

Status: IMPLEMENTED and independently reviewed after one test-only correction; root task validation passed, feature integration pending. Producer9d integrated176ce62, fully validated.
Spec: owner-approved live runtime plus explicit exact per-call backend/model/request/
response/timing retention; invalid raw retention authorized. Existing execution method:
bounded worker, independent review, root task/merged gates, preserved branches/pushes.

## Goal and architecture

Connect reviewed9c storage and9d capture to EVERY new archived live-runtime cognition
call for BOTH providers. Record exact prepared body before dispatch; record observation
and outcome before any decision is staged/applied. Copy authenticated source trace fields
and BLOBs on live reuse/offline replay without new calls/timings. No new lifecycle owner,
writer/thread, controller, world schema, provider configuration, deterministic cursor or
fingerprint change. Existing RuntimeService owner invokes archive transactions.

Standalone/manual cognition/perception clients outside an archived attempt remain outside
this composition; no claim they are archived. Preflight discovery GETs are not inference.
Admin/offline analysis/export and uncommitted-spool forensic views are LN09f, not this task.
No product server/GPU launcher, modeldownloads, player API or domain behavior changes.

## Global constraints and exact allowed files

Python>=3.11 strict hints/protocols/frozen dataclasses. Managers mutate/systems behave,
events immutable. NPC contexts remain holder-filtered, no rawWorldState/entity IDs/
others' hidden cognition/arbitrary objects. LLM output untrusted, gateway/engine alone
owns truth/goals/stages. Raw traces privileged, never NPC/ordinary API text or unsafeHTML.
No dependencies. Preserve legacy read/write storage, recorded scenarios and exact hashes.

Exactly ten worker paths:
- NEW src/living_world/runtime/archive_inference.py
- src/living_world/runtime/ollama_driver.py
- src/living_world/runtime/journal_replay.py
- NEW tests/test_runtime_archive_inference.py
- tests/test_runtime_ollama_driver.py (trace-aware expectations/fixture coverage only)
- tests/test_runtime_journal_replay.py (trace-aware expectations/coverage only)
- tests/test_runtime_disturbances.py (ONLY ShelterBroker inherit DecisionBroker so the
  existing fake satisfies the declared broker interface, plus necessary import)
- docs/npc_information_boundary.md (new flow and superseded nonretention wording only)
- docs/local_llm_setup.md (automatic archive traces, legacy resume and scope only)
- docs/subagent_execution_plan/live_npc_runtime/09e_archive_inference-report.md

Root owns task/prombt/common4/continuation/evidence. Worker no VCS/index/commits/subagents/
fullmake/examples/realmodels/downloads/othercheckout edits. Fake HTTP test servers allowed.
Report missing producers/architectural ambiguity before expanding; amend BOTH task/prompt.

## Producer interfaces to use

archives.InferenceBlob(body:bytes); AttemptArchive.format_version, record/append with
inference_blobs=tuple, inference_blobs(digests,through_sequence=...), JournalBoundary.
Existing storage validates all body hashes/references atomically, prefix-restricted reads.
PreparedInference(body,request_trace), prepare_inference(config,context,options),
InferenceObservation(response_trace,body), settle_observation(...parent timing...), utc_now.
BrokerResult.response_trace/response_body optional fields; real bound broker supplies
settled metadata even failure. DecisionBroker.bind_trace(job,prepared,spool_root=Path),
start(job,config,item), poll(job), close(), acknowledge_trace(job,result=result).
Real close reaps/harvests/caches cancelled result; injected fake close may clear its own
poll state. Inherited binding/ack handles no-super overrides; suppliedresult neverbypasses
real cached/reaped guard. Broker never opensSQLite. Real success cannot lack complete2xx
matching response evidence; do not weaken that producer invariant.

## Helper responsibilities and signatures

New archive_inference.py contains owner-called transaction helpers and pure projections,
not background writers or lifecycle management:
- `record_request(archive: AttemptArchive, request: Mapping[str, object],
  prepared: PreparedInference) -> None`: request includes request_id, atomically record
  request_started plus request_trace and InferenceBlob(prepared.body).
- `observation_for_result(result: BrokerResult, *, dispatch_started_at: str,
  broker_seconds: float) -> InferenceObservation`: use existing result trace/body unchanged
  if present. Otherwise explicit unavailable with parent UTC now and actual measured
  parent interval, never synthetic fake elapsed or invented worker/HTTP times.
- `record_response(archive: AttemptArchive, request_id: str, result: BrokerResult,
  observation: InferenceObservation, *, decision: NPCDecision | None,
  error_code: str | None) -> None`: atomically record response_validated or failed plus
  response_trace and optional body BLOB. Exclusive decision/error, same old optional
  content_digest/elapsed_seconds semantics; unsafe decision may become unsafe_response
  while retaining original raw body. No empty BLOB for unavailable; b'' is real bytes.
- `trace_fields(started: JournalEntry, response: JournalEntry | None)
  -> dict[str, object]`: copy only present request_trace from started and response_trace
  from response plus existing optional content_digest/elapsed_seconds from response;
  matching request IDs required. No reconstructed/mutated metadata or timestamps.
- `capture_trace_blobs(source: AttemptArchive, boundary: JournalBoundary,
  entries: tuple[JournalEntry, ...]) -> tuple[InferenceBlob, ...]`: verify boundary before
  and after prefix-restricted body reads, verify supplied entries belong to exact prefix,
  gather unique sorted referenced digests, return matching immutable bytes. Current DB
  possession outside prefix is insufficient. Later append allowed, prefix edits reject.
- `acknowledge_recorded(broker: DecisionBroker, request_id: str,
  result: BrokerResult) -> None`: after successful response transaction ONLY, call ack
  with actual result. Cleanup failure retains evidence and logs ONLY fixed warning
  `Inference trace cleanup pending.` with no exception details/body/path; it need not
  discard a response already durably saved. This is cleanup, not capture/import success.

Use exact signatures for neighboring consumers. Internal helper decomposition is free
within files. Preserve strict types; do not introduce duck-typed untraced fallback for
actual production brokers. Existing injected fakes perform no HTTP and may truthfully
have unavailable body evidence.

## Live dispatch, settlement and cleanup ordering

1. Keep validate_checkpoint usable for legacy sources. In live prepare, reject archive
   format!=2 BEFORE feedback mutation/journal/network with ArchiveFormatError fixed message
   `Exact inference traces require archive format two; resume into a new attempt.`
   Normal catalog resume/fork creates format2 child and remains supported. No read migration.
2. Build ONE PreparedInference per candidate item when request is needed. Existing input
   fingerprint uses decoded prepared body payload, exactly same canonical fields as before;
   trace/timestamps/BLOB hashes do not enter fingerprints or semantic driver/feedback cursors.
   Reuse comparison still uses original request/context/config fields. Preparing a body for
   comparison does not mean a new HTTP call or a historical trace was captured.
3. Fresh dispatch: generatejob -> record_request transaction COMMIT -> set active record
   (item/job/request/prepared + own dispatchUTC/monotonic) -> bind_trace with spool_root
   archive.database_path.parent/'inference-spool' -> start. Storagefailure means no bind/
   process/HTTP. Binding/startfailure settles worker_failed using cached brokerresult if
   available, otherwise unavailable parenttiming; no staging/world effects.
4. Poll result -> state-aware existing _validated gateway/prose check -> observation ->
   record_response COMMIT -> acknowledge_recorded -> clearactive -> stage ONLY ifsuccess.
   Import failure must not clearactive prematurely, stage, advanceworld or ack. Let existing
   controller fail/discard safely; retain spool. Do not convert archive failure into a
   successful provider result. Existing error codes/lifecycle remain unchanged.
5. close: reap/harvest with broker.close FIRST. If active, retrieve cached result via poll;
   injected close may invalidate polling, so fallback explicit cancelled/unavailable parent
   evidence only when no retrievable result. Parent always records cancelled, never stages
   a completed decision after close. Keep actual returned result for ack equality even if
   enclosing journal outcome is cancellation. Record before ack. Clear detached proposal/
   work hooks and staged references in finally even on archiveerror, without masking the
   failure. Existing candidate_aborted/committed-checkpoint ownership retained. No duplicate
   response identity: a successfully recorded response must not be re-settled on laterclose.

Uncertain local unresponded requests still require explicitRetry. If their existing
request has a request_trace, uncertain response may receive unavailable metadata with
UNKNOWN/null clocks (no historical timing reconstruction). Legacy local requests without
trace remain untraced. Do not import source spool or synthesize history from new prepared
payload. Every actual new call is traced; old unavailable evidence stays unavailable.

## Sealed reuse and offline replay

Live _reuse already verifies parent continuity/seals and picks request/response from
source records. When external response copied, trace_fields + capture_trace_blobs and
response_reused publish in ONE destination archive.record transaction. No body publication
without reference or separate blob transaction. Local reuse keeps original evidence;
no fresh call/trace/timing. Nestedreuse copies immediate source's authenticated localrefs,
retaining existing source={attempt_id,request_id,boundary}; never reach newer ancestors.

_CapturedSource obtains immutable needed data while source available: after validating
sourcepoint and prefixrecords, eagerly capture all unique referenced prefix BLOBs using
capture_trace_blobs and retain hash->InferenceBlob mapping. No source HTTP/GGUF/filesystem
model reads. Captured metadata/blobs never grow from later source append. Replaydriver
copies tracefields+BLOBs for each imported response_reused in same batch record; dedupe
blobs byhash. Existing local import detection stays idempotent and must match preserved
trace fields, not silently accept mismatching evidence. Reused timing belongs sourcecall,
not fresh latency/cost. Legacy omitted traces stayomitted; no fake body reconstruction.

Do not weaken source checkpoint/cursor/world comparison, retention/input hashes, no-action
or disturbance replay semantics. Copied traces can be read locally after source removed;
full world restart may still require original lineage (not a promise to remove that need).
Trace-bearing writes to format1 replay destinations reject before publication; ordinary
untraced legacy operations remain valid.

## Hard crash and analysis boundary

Ordinary resume owns CHILD only; source readonly and sealed. Unimported source private
spools are retained UNCOMMITTED FORENSIC evidence, never silently imported into source
or sealed child, never used as recoveredproposals. Unknown/unpublished bytes stayunknown.
No latewriter, sourcelease redesign or crossrestart PIDkill. Normal stop/cancel imports
under existingowner. Later9f must include attempt+lineage+forensic files in analysis/export
and distinguish already journaled evidence. No admin API/frontend/export in this task.

## Required RED/GREEN and meaningful tests

- [x] RED actual spawned fakeHTTP tests for BOTH endpoints prove server-received body
  equals request_trace BLOB; read-only server handler observes request archive transaction
  already committed before receivingHTTP. Responses/status/timings persist after reopen.
- [x] RED request-storagefailure prevents network/process/bind; response-storagefailure
  after captured result prevents staging/worldrevision/actionoutcome and retains spool.
- [x] Implement helper and live ordering, error/close paths with parent timestamps; tests
  success, invalidJSON/UTF8/envelope/unsafeprose, HTTPerror, empty, oversizeprefix, timeout,
  cancellation and stop after partial/complete capture, cached/injectedfake compatibility.
- [x] Test ackfailure after successfulimport preserves complete canonicalevidence, fixed
  warning contains no rawsecret; repeatedclose doesnot duplicate responses. Importfailure
  cleanup still clears detached hooks without fabricating committed effects.
- [x] Test genuine legacydirect rejection beforefeedback/net and normal legacy->newchild
  trace capture, untraced legacy source reuse/replay without historical body fabrication.
- [x] Implement prefix-authenticated tracecopy and capturedreplay blobs; test exactbody/
  metadata/timing equality, nestedreuse, pending-request prefix excludes laterresponse,
  prefix-boundary tamper/missingblob rejects atomically, child localread after sourcegone,
  offline replay without server/GGUF and unchanged complete worlds/events/cursors.
- [x] Test hardcrash published unimportedspool is retained and NOT silently consumed by
  childreuse/replay; explicit unknown response state, no sourcebyte changes.
- [x] Run newfocused plus existing driver/replay/disturbance/broker/storage/restart suites,
  scoped Ruff/Black and whitespace. Update only ShelterBroker inheritance/import in its
  existing fixture file. No weakening assertions to accept missing actualcall evidence.
- [x] Write report RED/GREEN commands/results/counts/warnings/scope/limits, freeze.

Use existing .worktrees/task24/.venv, PYTHONPATH=src. Focused new file then
 tests/test_runtime_ollama_driver.py tests/test_runtime_journal_replay.py
 tests/test_runtime_disturbances.py tests/test_runtime_inference_capture.py
 tests/test_inference_trace_storage.py tests/test_runtime_restart.py.
Root independentlyreviews, resolvesfindings, then make/separateexamples/whitespace/
canonical26readonly/CLI7/Serve4/wheel11+Serve4 and sourceequality. Rootalonecommits/pushes
preservedtask, noff featureintegration/repeatedgates. No main/milestone/tag. Stopbefore
five-hourremaining<10%, noreset/automaticresume. Do notclaim admin/realprovideracceptance.
