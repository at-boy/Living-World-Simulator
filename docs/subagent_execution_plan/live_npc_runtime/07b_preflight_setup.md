# LN07b — Discoverable setup reservations and bounded model preflight

Status: bounded producer stage of owner-approved original LN07, following LN07a.
LN07c consumes this stage for live/service/resume/replay entrypoints. Original Task7
remains incomplete until all stages and aggregate acceptance. No CLI/browser change.

## Goal and decision

Reserve an attempt identity and retain inputs BEFORE provider setup. Resolve installed
Ollama model name/digest through bounded GET /api/tags, then publish effective immutable
configuration into the ordinary reservation and archive ONCE. Never rewrite config in
an initialized archive or pretend two-file updates are atomic. Interrupted/failed setup
remains discoverable without a fabricated world. Old reserve/fork/archive formats stay
readable and unchanged.

Python>=3.11 strict types/frozen safe records; standard library only. No world/SQLite
schema change, downloads, model generation, remote provider fallback, player/admin API,
main/milestone/tag changes or branch/worktree deletion. Config, model names/digests,
setup evidence, IPC paths and failures remain engine-only, never NPC context.

Official protocol checked October22: [Ollama List models](https://docs.ollama.com/api/tags)
uses GET /api/tags with models array, name/model and digest. Extra model detail fields
are permitted but never forwarded/persisted by preflight. No external research required
by worker; this exact contract governs parsing/alias/failure behavior.

## Exact allowed worker files

Create src/living_world/runtime/preflight.py, tests/test_runtime_preflight.py.
Modify src/living_world/archives/catalog.py, assets.py,
src/living_world/perception/local_llm_http.py, src/living_world/runtime/broker.py,
src/living_world/runtime/__init__.py, tests/test_run_archive_catalog.py,
tests/test_local_llm_http.py, tests/test_runtime_broker.py and own -report.md.
11workerpaths only. Root owns plan/prompt/common docs/VCS. No store/model/lease/
controller/driver/CLI/domain/packaging/other source or tests. Root amends before widening.

## New catalog setup interfaces

Public methods on existing RunCatalog:
- reserve_setup(requested:AttemptConfig)->AttemptRef (ollama mode only)
- setup_config(ref:AttemptRef)->AttemptConfig (immutable requested intent, read-only)
- complete_setup(ref:AttemptRef,effective:AttemptConfig)->None
- fail_setup(ref:AttemptRef,code:str)->None

Reserve creates ordinary nested UUID identity/owner.lock, but no attempt.json or
SQLite yet. Publish immutable setup.json under brief owned lease, fsync like current
reservation. Closed document:
{format:1,lineage_id,attempt_id,requested_config:<existing config_document>,reserved_at}.
Current reserve/fork behavior unchanged, no new fields in their metadata required.
Ref must validate fixed layout AND belong to this catalog root for all setup methods.

Caller acquires normal AttemptLease for retained inputs/provider setup/publication.
complete_setup/fail_setup require current-thread lease, valid setup intent, no prior
failure/final publication. Wrong thread, foreign ref, repeated/divergent completion,
missing/malformed/tampered setup or publication already begun fails closed; never
rewrite files or repair partial publication. Keep evidence for inspection.

complete_setup requires valid retained input manifest/hash/scenario/definitions/tape,
then creates ordinary attempt.json plus AttemptArchive.create with effective config
using existing reservation publication/error handling (factor narrow private helpers,
not a duplicate entire reserve). reserved_at is setup intent timestamp. Once either
final file is published, setup cannot be reconfigured. Crash between files yields a
discoverable incomplete failed publication, no usable world. No mutation of existing
SQLite archive_meta/config. No new SQL table/column/format. Keep requested intent.

Effective config mode/key/seed/software and non-provider settings exactly equal request.
All explicitly supplied non-identity provider options remain semantically equal
(numeric int/float normalization allowed, URL trailing slash normalization only).
Missing options may be filled by runtime preflight defaults. Model name may equal
request or append ':latest' ONLY when requested name has no tag (colon in last slash
component). Digest required canonical lowercaseSHA256; declared requested digest must
match after optional 'sha256:' prefix/case normalization. No arbitrary model/seed/limit
change. A shared validator enforces intent/final config constraints on completion AND
later catalog open; old archives without setup.json retain existing checks.

fail_setup writes immutable closed setup_failure.json:
{format:1,lineage_id,attempt_id,code,ended_at}. Code one of timeout/transport/http_error/
invalid_response/oversized_response/worker_failed/cancelled/model_missing/
model_digest_mismatch/invalid_preflight/setup_failed. Exact same-code repeat is
idempotent without timestamp/file changes; divergent code or final publication fails.
No raw error/body/CoT/auth data. No SQLite/world created on setup failure.

## Read-only discovery and pending retained inputs

Catalog.attempts reads valid pending intent: owned ->initializing; unowned with no
explicit failure ->interrupted; explicit failure ->failed with safe code/end time.
No checkpoint/revision/tick invented. If final attempt.json/SQLite present, ordinary
parity/config/input validation applies; partial final publication is initializing
while owned, failed/archive_incomplete once unowned. Malformed setup metadata is
invalid, not silently ignored. Legacy reservation/error/missing-file behavior stays.
open_attempt on unfinished setup rejects safely, no writes/repair. setup_config may
read intent after failure/completion for analysis, validating closed document safely.
No read creates directories, locks, sidecars, timestamps or files.

retain_inputs can run BEFORE SQLite creation only for a valid setup intent in the
same catalog. Validate captured identity against requested setup_config when DB is
absent; otherwise preserve current archive-config validation. Keep full immutable
CAS/hash/scenario/definition/tape checks and LN07a source normalization safety. Use
local import/shared helper to avoid assets/catalog import cycle. Failed pending inputs
remain readable for analysis; completed config preserves same scenario/seed. Do not
add a general unchecked input-capture path.

## Bounded GET transport and process ownership

UrllibJsonHttpTransport.get_json(*,url:str,timeout_seconds:float)->dict[str,object]
shares private request/read/decode helper with post_json. Existing JsonHttpTransport
Protocol stays post-only so fake/third-party old callers remain compatible. Preserve
encoding, digest reset, max+1 bounded reads, finite positive timeout, loopback origin,
proxy disable/redirect reject, UTF8/object/finiteJSON validation and safe error codes.
No duplicated HTTP guard or changed POST payload semantics.

In broker.py factor small owned-process reap helper used by existing DecisionBroker
and preflight. Exact existing terminate/join0.2, kill/join0.2, close policy remains;
only owned process, never server/other processes. No generic process framework or
broker API change. Existing broker tests must stay passing.

New runtime/preflight.py exports preflight_provider(requested:AttemptConfig,
*,cancel_event:threading.Event|None=None)->AttemptConfig
and ProviderPreflightError(code:str). No catalog mutation inside this function: caller
holds setup lease, retains inputs, invokes preflight, then complete_setup or fail_setup.
ProviderConfig/provider_config/client defaults remain authoritative; normalize timeout/
seed/output/response/temp/URL exactly as existing runtime. Do not duplicate defaults.

Use fresh spawn process + private temporary directory/atomic bounded JSON result file,
read only after exit, hard monotonic deadline including startup. Child receives only
resolved ProviderConfig and owned result path, never world/engine/inspector/ref/input
paths. GET endpoint only {base_url}/api/tags, max_response_bytes cap, timeout as socket
limit plus parent's absolute wall bound (trickled headers/body cannot evade it).
Parent polls in small bounded waits, rejects results first observed after deadline,
checks parent-only cancel_event on every poll (pre-set means no spawn), cancellation
raises fixed cancelled error and reaps promptly; reaps/cleans on success/error/timeout/
KeyboardInterrupt, no orphan worker or late result. Never pass the Event into child.
Result frame<=8192bytes, only chosen model/digest or fixed error. No raw tag body/extra
model details/CoT in IPC/archive/log. Parent validates frame/schema/name/digest again.
No model download/generate/show fallback or server control.

## Model identity and error semantics

models must be an array; each entry must provide nonempty name<=512characters with
no whitespace/control, valid SHA256 digest; optional model must equal name. Additional
details ignored. Any malformed/duplicate name entry fails invalid_preflight, never
silently selects a malformed duplicate. Match exactly one entry among requested name
and requested+':latest' only when untagged; both candidates ->invalid_preflight. Missing
->model_missing. Optional digest prefix 'sha256:' and hex case normalize to64lowerhex.
Declared model digest mismatch ->model_digest_mismatch, not silent update/reuse.

Success returns new AttemptConfig preserving other settings, provider explicit fully
resolved values incl actual name/digest/seed. It must feed existing provider_config and
effective_config_fingerprint unchanged. Same model tag with different digest changes
fingerprint. Ordinary resume with a pinned digest fails on installation change;
explicit fork may request changed provider later. No claim of deterministic generation
or hardware/model strategy success. All transport/worker/shape failures map to safe
ProviderPreflightError vocabulary above; no raw exception text/provider response.

## Tests and completion

TDD baseline catalog/assets/HTTP/broker; genuine RED then GREEN per coherent slice.
Required: pending identity+retainedinputs before GET; valid publication immutable
requested/effective docs+archive parity; wrong lease/root/types/identity/settings/digest;
repeat/divergent completion/failure; metadata/hash/role/tamper/link/escape guards;
legacy reserve/fork reads unchanged; byte-identical read-only pending/failed/completed
inspection; actual process death during setup and fault between final publications,
no inventedworld/no repair. Models exact/untagged/namespace/duplicates/malformed/missing/
pinned mismatch/fingerprint effects. Actual stubHTTP GET normal/proxy/redirect/UTF8/
JSON/overflow/HTTPerror; hung/trickled headers/body harddeadline; owned-process cleanup
on success/failure/timeout/interruption; explicit cancellation under a long configured
timeout returns promptly and cleans owned child. No real Ollama dependency in make.

Final focused: PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_preflight.py
 tests/test_run_archive_catalog.py tests/test_local_llm_http.py
 tests/test_runtime_broker.py tests/test_ollama_cognition_client.py -q.
Scoped Ruff/Black/whitespace; report true commands/counts/RED/GREEN/limits/selfreview.
Worker no VCS/subagents/fullmake/examples/installs. Root independent SPEC/QUALITY review,
corrections/rereview, task+merged make/separateexamples/whitespace and exact canonical
matrices before commits/integration. Preserve every branch/checkpoint/owner-local edit.

## Root review amendment — publication completion boundary

Review1 reproduced SQLite-file creation before schema/metadata initialization. Mere
existence of both final paths is not completion. Add immutable setup_complete.json
ONLY after ordinary attempt metadata and SQLite initialization both successfully
finish and close. Closed document {format:1,lineage_id,attempt_id,config_sha256};
config_sha256 is SHA256 of canonical(config_document(effective)).encode(). Validate
strict identity/fields/format/digest and parity on ordinary setup-backed open. No
marker or metadata rewriting, no read-side writes/repair, no SQL/schema change.

A valid setup intent without completion marker remains pending publication even if
both final paths exist: initializing while owned, failed/archive_incomplete when
unowned and any final path exists; unowned with neither remains interrupted. Such
setup cannot open or be reconfigured. Before classification still validate intent,
any present attempt.json closed identity/config/timestamp/parent/error parity and
retained inputs/hash/roles; malformed metadata remains archive_invalid. In this
unmarked publication window retained input identity uses validated setup intent
without opening partially initialized SQLite. Marker present requires both final
files and ordinary complete archive/input/config parity; corrupted/tampered marked
archives remain archive_invalid. Missing marker is an incomplete publication, including
a crash after valid SQLite creation but before marker; no legacy setup migration is
needed since this uncommitted format has no released consumers. Old archives without
setup.json remain unchanged. Failure marker conflicts with any final/completion file.

Test real fault boundary empty SQLite and schema/metadata-partial database; both
owned/unowned discovery; also fault after valid SQLite before completion marker.
Discovery/open leave bytes unchanged, no invented checkpoint/repair or second
completion. Marked completed archive corruption/config/marker tamper remains invalid.
Same11workerpaths. This root decision precedes correction implementation.
