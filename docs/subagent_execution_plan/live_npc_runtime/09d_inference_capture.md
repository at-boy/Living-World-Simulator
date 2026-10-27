# LN09d — Exact-byte HTTP and durable broker capture

Status: REVIEWED and TASK-VALIDATED; feature integration pending.
Spec: approved live runtime plus owner exact per-call request/backend/response/timing
requirement. Root October27 split: storage9c, transport/broker capture9d, runtime archive
wiring/reuse9e, admin/offline analysis/export9f, then original full BOTHprovider acceptance.
No worker may infer that later consumers are implemented by this producer task.

## Goal, constraints and allowed files

Capture exact prepared request bytes and bounded received response bytes/timings in an
owned durable spool, retaining evidence through timeout/cancel and until caller ack.
No archive writes, driver/replay changes or browser/export work in this producer task.
Update boundary document to explain optional bound exact-byte capture, privileged spool,
unknown/partial evidence, same filtered payload/no extra NPC data. Replace old categorical
invalid-response nonretention sentence with owner-authorized privileged bounded retention;
clearly state public archived runtime wiring/admin views remain follow-on work.

Python>=3.11, strict hints/protocols/frozen dataclasses. Preserve existing clients, provider
payload/envelope parsing, default transport behavior, fixed safe errors, loopback/no proxy/
no redirects, bounded reads, owned spawned process/reaping, and existing start signature.
Only filtered NPC context/options/configuration and owned paths enter child; no engine,
actor/entity IDs/handlers or arbitrary runtime objects. Trace metadata stays engine-only;
raw provider output is untrusted and never NPC knowledge. No dependencies or modelruns.

Exactly seven worker paths:
- NEW src/living_world/runtime/inference_trace.py
- NEW src/living_world/runtime/inference_spool.py
- src/living_world/runtime/broker.py
- src/living_world/perception/local_llm_http.py
- NEW tests/test_runtime_inference_capture.py
- docs/npc_information_boundary.md (bound capture flow and prior nonretention wording only)
- docs/subagent_execution_plan/live_npc_runtime/09d_inference_capture-report.md

Root owns task/prombt/common4/status/evidence and later consumer contracts. No other file
without task+savedprompt amendment first. Worker no Git/index/commits/subagents/fullmake/
examples/modelservers/downloads/othercheckout edits. Report a missing seam before coding it.

## Exact interfaces and decisions

### Prepared immutable request, runtime/inference_trace.py

Frozen `PreparedInference(body: bytes, request_trace: Mapping[str, object])` validates
actual bytes, exact SHA256/length and closed LN09c request metadata, freezes metadata.
Properties url:str, timeout_seconds:float, max_response_bytes:int read validated metadata.
`prepare_inference(config: ProviderConfig, context: NPCContext,
options: tuple[ActionOption, ...]) -> PreparedInference` builds current client payload,
canonical sorted compact ASCII JSON ONCE, <=16000 bytes, with existing /api/generate for
Ollama or /v1/chat/completions for llama_cpp. Metadata uses configured model/digest/kind,
Content-Type application/json declared header, UTC preparation timestamp, limits. No
model file read/network/SQLite. Avoid broker import cycles using TYPE_CHECKING/local imports.
Root later driver uses decoded prepared body for unchanged input fingerprint and stores
request_started+request_trace+BLOB atomically BEFORE dispatch. That caller is not this task.

Frozen `InferenceObservation(response_trace: Mapping[str, object], body: bytes | None)`
validates LN09c closed response metadata and exact byte availability/digest/length, deeply
freezes metadata. Unavailable requires None; observed empty requires b'' and nonnull hash.
A partial/oversized body's hash identifies observed prefix ONLY.
`settle_observation(observation: InferenceObservation | None, *, dispatch_started_at: str,
settled_at: str, broker_seconds: float) -> InferenceObservation` fills parent timing fields;
if None, produce explicit unavailable with all unobserved worker/HTTP fields null.
Do not derive durations from UTC or impose wall-clock ordering.

### HTTP observer, perception/local_llm_http.py

Add frozen `HttpObservation(body: bytes | None, complete: bool, status_code: int | None,
timestamps: Mapping[str, str | None], durations: Mapping[str, float | None])`.
Timestamp keys exactly http_started_at, headers_received_at, first_body_byte_at,
read_finished_at. Duration keys exactly http_seconds, headers_seconds, first_byte_seconds,
body_read_seconds. Freeze maps, exact types/finite nonnegative duration validation.
Unknown values null. No archive import in transport layer.

Add `post_bytes(*, url: str, body: bytes, timeout_seconds: float,
observer: Callable[[HttpObservation], None] | None = None) -> dict[str, object]` on
UrllibJsonHttpTransport. Actual bytes passed unchanged to urllib Request. Existing
post_json/get_json/JsonHttpTransport signatures and default behavior remain compatible.
Use existing no-proxy/no-redirect loopback policy and bounded finite JSON parsing.
Declared Content-Type remains application/json; not a packet/framing-header capture.

With observer, emit before open (HTTP attempt, not proof bytes sent), after headers
(success OR HTTPError), first returned body byte, bounded prefix chunks and read end.
Read first available byte with read1(1), then read1 chunks <=65536 while total <=max+1;
HTTPResponse supports read1. A fallback bounded read is permitted for compatible streams
without read1, with honest first-client-observation timing. Handle IncompleteRead.partial
without retaining >max+1 bytes. Publish prefix before subsequent read may stall. In observed mode, also check a
worker-local monotonic total HTTP deadline before each read; slow-drip peers must not
keep an orphan worker alive indefinitely after parent hard kill. Existing socket timeout
plus these checks bounds orphan read termination (one in-flight read may consume its
configured socket timeout). Parent normal deadline/reaping remains authoritative.

HTTPError body/status must be observed before fixed http_error is raised. Invalid UTF8/
JSON/envelope responses retain raw bytes before parsing. Oversized response retains at
most max_response_bytes+1 bytes, marks incomplete (unless an actual EOF established full
body; conservative incomplete is valid), then existing oversized_response error. Empty
EOF is complete b'' distinct from no response. Read timeout/failure retains prefix;
body unavailable until a response stream observed, headers+zero read prefix is incomplete
b''. When worker killed before publication, unknown bytes remain unknown.

http_seconds is worker-local monotonic interval from HTTP attempt start to observed end;
headers_seconds=start->headers; first_byte_seconds=start->first returned clientbodybyte;
body_read_seconds=headers->read-end. These are observed client pipeline intervals,
including synchronous capture overhead, not isolated server generation latencies.
read_finished_at stays null if no body-read phase was entered (e.g. connect failure).
Final-stage durations stay null until stage ends,
not snapshot-progress durations. UTC wall clock may adjust. No claim of server token
start/generation time. Observer failure is fatal fixed LocalLLMHttpError worker_failed,
never silently drop capture and return accepted decision. Existing last_response_digest
semantics unchanged and distinct from incomplete prefix hashes.

### Durable spool, runtime/inference_spool.py

`create_trace_spool(root: Path, job_id: str) -> Path`: strict 32lowerhex job ID, private
root and exclusive owned leaf root/jobid (0700); no symlink traversal/non-directory leaf.
`publish_trace_snapshot(directory: Path, prepared: PreparedInference,
observation: InferenceObservation) -> None` writes a self-contained closed frame:
format=1, request_body_digest, response_trace, body_base64 (null or strict base64).
`read_trace_snapshot(directory: Path, prepared: PreparedInference)
-> InferenceObservation | None`: absent published snapshot returns None; ignore partial
files. Validate regular/nosymlink file, closed duplicate-free finite JSON, exact prepared
request digest, body hashes/lengths and <=max_response_bytes+1 observed bytes. Invalid
frame raises safe fixed error. Do not read or combine unrelated mutable body files.

Published filename observation.json. Exclusive observation.partial -> write/flush/fsync ->
os.replace -> directory fsync. Every frame <=8*(max_response_bytes+1)+65536 bytes; bounded
read limit+1, no unbounded file loads. Files0600, dirs0700, safe filenames/paths and owned
cleanup only. No SQLite or modelobjects. InferenceObservation supplies all response keys;
worker publications leave parent fields null. Record worker_started_at immediately and
worker_seconds only at final observation construction after HTTP/client parsing,
measured worker-start to that point; it excludes final publication/process termination.
Killed worker with no final observation leaves that phase duration null. No runtime crash recovery/source writer here.

### Broker binding and lifecycle, runtime/broker.py

Preserve start(job_id, config, decision_input) signature. Add
`bind_trace(job_id: str, prepared: PreparedInference, *, spool_root: Path) -> None`
and `acknowledge_trace(job_id: str, *, result: BrokerResult | None = None) -> None`. Binding initializes independent capture
state even when injected subclass skipped super().__init__. Reject rebinding, overlap,
unsafe job/path; reject prepared/config/context mismatch at start before network
(including kind/model/pin/URL/timeout/response cap and exact payload). Binding creates its own private spool after caller's
archive request transaction (later caller responsibility). Keep unbound direct broker
behavior compatible/temporary; only bound path is durable. Bound child receives prepared
bytes and canonical metadata JSON plus filtered request/config/path, no archive handle
or raw engine data. Do not pickle MappingProxyType/frozen metadata mappings across spawn;
reconstruct validated PreparedInference in child from primitive bytes/JSON.

Append optional BrokerResult fields `response_trace: Mapping[str, object] | None = None`
and `response_body: bytes | None = None`, preserving existing positional constructors.
When present validate/freeze as InferenceObservation; no body without trace. Bound real
broker always returns an explicit settled observation, including unavailable.

Bound child uses adapter JsonHttpTransport.post_json: validate URL/timeout and rebuilt
payload equal decoded prepared body, then call post_bytes using ORIGINAL stored bytes.
Client rebuilding is only validation; no wire reencoding. Existing clients and parsing
unchanged. HTTP callback publishes each bounded observation with worker fields; publish
final worker duration even when client parsing fails. Publication failure prevents a
successful decision. Existing fixed result.json remains bounded; same atomic/fsync
publication for bound results. Do not include raw exceptions in IPC or safe errors.

poll deadline and close cancellation reap owned process BEFORE final snapshot harvest;
never delete spool before harvest. Preserve timeout/cancelled outcomes even if body had
completed; no accepting decisions after cancellation/deadline. Bound successful real
result requires complete observed body matching its complete response_digest and 2xx
status; malformed/mismatched/missing observation cannot become accepted untraced result.
Capture corruption produces fixed worker_failed/unavailable evidence and retains corrupt
spool. Missing publication after crash gives unavailable/worker_failed as appropriate.

Parent merges dispatch_started_at/settled_at UTC and broker_seconds monotonic interval
through reaping. Owned process starts only after binding, worker/runtime ownership exact.
close caches cancelled result accessible by poll(job); cached settlement remains idempotent.
ack is only valid after settlement and removes ONLY fully validated imported own job
spool; caller promises archive import already succeeded. For real-bound jobs whose inherited start ran, ack requires actual cached settlement
and reaped process; supplied result must equal cached settlement and cannot authorize
early deletion. For injected no-super brokers whose overridden start never created a
real worker, an explicit matching job result supplies caller settlement evidence. No
cached or supplied result means reject; later archive consumer always passes result.
Ack before settlement rejects.
Corrupt/unimported spools remain retained. No autoack in poll/close. Keep existing error
codes and process ownership semantics; never kill unrelated PID after restart.

Injected test brokers overriding start/poll/close keep compatibility; inherited binding
and ack must not require unrelated initialized fields. They perform no HTTP and may have
no observation; later driver will mark unavailable rather than invent a network call.
This does NOT permit actual real-broker accepted decisions to bypass trace verification.

## Review focus and implementation/test sequence

- [ ] RED tests for exact prepared/store-ready bytes and metadata for BOTH providers;
  fake loopback HTTP server receives identical bytes via bound real spawned broker.
- [ ] RED tests for raw invalidUTF8/JSON/envelope, HTTPError bodies/status, emptybody,
  max+1 oversize, partial body then timeout/connection close, slow-drip total deadline,
  and first-client-byte timing.
- [ ] Implement immutable prepared/observation models and post_bytes observer path while
  preserving existing unbound clients/default transport/parser behavior.
- [ ] Implement closed bounded durable spool and binding/reap/harvest/ack lifecycle.
- [ ] Test fsync/atomic replacement, read/publish failure, malformed/duplicate/oversized
  frames, digest mismatch, invalid binary vs null, symlink/nonregular paths, modes,
  partial-file-only crash, headers-only/bodyprefix/final worker crash publication points.
- [ ] Test close/deadline with complete or partial captured body, reaping before harvest,
  idempotent poll, start failure, caller neveracks (spool retained), ack-before-settlement
  rejected, corruptedspool retained, injected ImmediateBroker-style no-super compatibility.
- [ ] Test observer failure neverreturns decision, mismatched prepared/config/URL/body
  rejected beforenetwork, actualproduction result withoutcompleteevidence rejects.
- [ ] Test timestampnulls, nonfinite rejection, backward UTC clocks without negative
  derived durations, no invented header/first-byte timings or complete hash forprefix.
- [ ] GREEN newfocused plus existing broker/HTTP/Ollama/llama/runtime compatibility,
  scoped Ruff/Black and whitespace. Record actual RED/GREEN commands/counts/warnings.
- [ ] Write own report/freeze; root independentreview, fulltask/mergedgates and VCS.

Focused: PYTHONPATH=src VENV/bin/python -m pytest -q tests/test_runtime_inference_capture.py
 tests/test_runtime_broker.py tests/test_local_llm_http.py tests/test_ollama_cognition_client.py
 tests/test_llama_cpp_cognition_client.py
 tests/test_runtime_llama_cpp.py tests/test_runtime_ollama_driver.py
Existing VENV task24/.venv, no install.
Root fullgates: make then separateexamples, exactcanonical26/readonly archives/CLI7/
sourceServe4/wheel11+actualServe4, whitespace and reviewedsource equality. Rootalone
commits/pushes task, noff integratesfeature, repeatsgates, preservesbranches/owneredit.
No main/milestone/tag. Pause before five-hour remaining drops below10%.
