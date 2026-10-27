# LN09c — Sealed privileged inference trace storage

Status: REVIEWED and TASK-VALIDATED; feature integration pending. October27,2026.
Spec: owner-approved live runtime plus explicit exact per-call request/backend/response/
timing retention requirement (October26), superseding old invalid-response nonretention.
Execution: existing approved bounded worker, independent review, root task/merged gates.

## Goal and task boundary

Add independently testable archive storage for exact opaque HTTP body bytes and closed
request/response trace metadata. Do not connect providers, broker or UI in this task.
LN09d will capture/import calls and copy sealed source trace evidence during reuse/replay;
LN09e will provide authenticated/offline operator analysis and portable export. Those
follow-on contracts must be finalized before their implementation, not inferred here.

Use content-addressed immutable BLOBs and optional trace metadata inside existing journal
entries. The existing journal boundary hashes metadata and BLOB references unchanged;
verify actual BLOB hashes on every archive validation. No new journal event kind, second
world store, new SQLite writer, world schema or semantic cursor change.

## Global constraints and exact allowed paths

Python>=3.11, strict hints, frozen dataclasses for immutable domain records. Preserve
manager mutation/system behavior, immutable events, filtered NPC contexts, untrusted LLM
proposals through gateways, and simulation authority. Raw trace bytes and metadata are
privileged engine/operator data, never NPC knowledge or ordinary inspector/world DTOs.
No new dependencies. Existing format-one behavior remains usable and byte-preserving on
read. Preserve all task branches/worktrees and owner-local master-plan edit.

Exactly seven worker paths:
- NEW src/living_world/archives/inference.py
- src/living_world/archives/model.py
- src/living_world/archives/store.py
- src/living_world/archives/__init__.py
- NEW tests/test_inference_trace_storage.py
- tests/test_run_archive_store.py (only update injected future-format fixture from 2 to 3)
- docs/subagent_execution_plan/live_npc_runtime/09c_inference_trace_storage-report.md

Root owns this task, matching saved prompt, CHANGELOG.md, docs/project_journal.md,
docs/backlog.md, continuation brief and ignored evidence. No other files without root
amending task AND saved prompt first. Worker: no Git/index/commits/subagents/full make/
examples/model server/downloads/other-checkout changes. Stop and report a missing seam.

## Architecture decisions and interfaces

### Format and storage ownership

New AttemptArchive.create databases use metadata format 2 and an additional table:
`inference_blobs(sha256 TEXT PRIMARY KEY, body BLOB NOT NULL)`.
The existing tables, reservation/setup/catalog formats, world schema, checkpoints,
configuration fingerprints and journal-boundary algorithm stay unchanged.
AttemptArchive._metadata accepts only integer formats 1 or 2. Add read-only property
`format_version: int`. Format-one ordinary create-history fixtures/open/record/commit/
commands remain supported; no automatic migration and no new table query on format one.
Trace-bearing writes or blob writes to format one fail ArchiveFormatError before any
publication. A legacy missing table is normal only in format one; format two requires
correct trace table even with zero traces. Do not expose a new public legacy creator;
tests can convert an isolated new empty fixture to genuine old metadata/table shape.

Existing RuntimeService owner-thread/readonly _connect guards remain authoritative.
No workers or background DB writers. Existing record/commit transactions and rollback
semantics retained. An insertion failure must leave neither journal refs nor blobs.

### Opaque bytes and references

In inference.py define frozen `InferenceBlob(body: bytes)` with computed read-only
`sha256: str` (lowercase SHA256 hexadecimal) and `byte_length: int`. Require actual bytes,
not bytearray/memoryview/text; retain zero-length bytes distinctly from unavailable data.
Public export InferenceBlob from archives package.

Define validators `validate_request_trace(value: object) -> Mapping[str, object]` and
`validate_response_trace(value: object) -> Mapping[str, object]` returning deeply frozen
closed metadata (or raising ArchiveFormatError). Use existing canonical/document/freezing
helpers; avoid import cycles with local imports or small safe dependency arrangement.
Request and response metadata below are explicit public engine-only wire documents;
follow-on tasks consume their exact keys. Reject unknown/missing keys, booleans where
integers/numbers expected, NaN/Infinity, malformed digests and invalid timestamps.

Request trace exact keys:
- format: integer 1
- provider_kind: ollama or llama_cpp
- model: nonempty string
- model_digest: nonempty string or null (actual configured pin, not fabricated)
- method: POST
- url: credential-free loopback HTTP endpoint; /api/generate for ollama,
  /v1/chat/completions for llama_cpp; no query/fragment/params
- headers: exactly {Content-Type: application/json}; these are application-declared
  headers, not a claim to capture TCP/framing or automatically generated HTTP headers
- body_digest: lowercase SHA256
- body_length: integer 1..16000 (complete canonical ASCII JSON provider body bytes)
- prepared_at: timezone-aware ISO8601 UTC string
- timeout_seconds: finite positive int/float, not bool
- max_response_bytes: positive integer, not bool

Response trace exact keys:
- format: integer 1
- body_state: complete, incomplete, or unavailable
- body_digest: SHA256 or null
- body_length: nonnegative integer or null
- http_status: integer 100..599 or null
- timestamps: closed map of dispatch_started_at, worker_started_at, http_started_at,
  headers_received_at, first_body_byte_at, read_finished_at, settled_at; every value is
  timezone-aware ISO8601 UTC string or null
- durations: closed map of broker_seconds, worker_seconds, http_seconds,
  headers_seconds, first_byte_seconds, body_read_seconds; every value finite nonnegative
  int/float or null, never bool

Complete/incomplete requires nonnull body digest/length, including observed empty bytes;
unavailable requires both null. A body hash on incomplete evidence hashes only that
observed prefix and must never be described as the complete response hash. Unknown
stages/durations stay null. Wall clock may adjust, so do not impose wall-clock ordering
or compute durations from UTC; duration clocks are scoped to parent or worker. The
metadata type validates representation, not a fabricated claim of actual HTTP activity.
Outcome/validation remains the enclosing existing response journal kind/code/decision.

### Existing journal metadata extension

JournalEntry request_started gains optional request_trace using request validator.
response_validated and response_failed gain optional response_trace using response
validator. response_reused gains optional request_trace AND response_trace; response_trace
requires request_trace on reused records. Omitted fields preserve every old schema/hash.
Do not change content_digest (existing complete accepted transport-body hash) or existing
elapsed_seconds semantics, response identity, proposal validation or action ownership.

Store-level audit must check a response_trace's request has a request_trace, response
observed length <= original request max_response_bytes+1, and referenced BLOB actual
length agrees with metadata. Request body bytes <=16000. Reused response references are
checked against their copied request metadata, not a newly executed call. Legacy
response_reused can legitimately have no trace at all or request trace only if the sealed
source prefix lacked observation evidence. Do not invent missing traces.

### Transactional APIs and validation

Extend existing signatures compatibly:
`append(entry: JournalEntry, *, inference_blobs: tuple[InferenceBlob, ...] = ()) -> int`
`record(entries: tuple[JournalEntry, ...], *, lifecycle: str | None = None,
reason: str | None = None, inference_blobs: tuple[InferenceBlob, ...] = ()) -> tuple[int, ...]`

Store supplied blobs and entry metadata in the SAME existing writer transaction. Identical
body/hash insertion is idempotent; same hash/different body or malformed existing rows is
an archive format error. Existing divergent journal identity remains a revision conflict,
never an opportunity to patch/upgrade a published trace. Do not extend commit in this
producer task: runtime records request/response before checkpoint publication via record.

Full _validate recomputes actual byte hashes and checks SQLite value types (TEXT is not
BLOB), metadata lengths, all references and no unreferenced blobs. Thus corruption,
missing BLOBs, dangling references or unbound rows fail closed. All trace metadata and
body refs are immutable after journal publication. Existing duplicate journal write plus
identical blobs is idempotent. Reject supplied blobs that would remain unreferenced.

Add `inference_blobs(digests: tuple[str, ...], *, through_sequence: int | None = None)
-> tuple[InferenceBlob, ...]`. Require tuple of unique valid digests and return same
requested order. Validate within one read transaction. Each requested digest MUST be
referenced by request_trace/response_trace of a journal record visible in that exact
prefix; being present elsewhere in the BLOB table is insufficient. Use existing _prefix
sequence semantics (zero means empty, missing nonzero sequence rejected, gaps legal).
Read-only access never mutates archive bytes. This primitive supports later sealed
source-copy and export; no catalog or runtime lineage changes in this task.

A journal seal binds trace metadata and hash refs using UNCHANGED _boundary. Source
bytes absent at a captured prefix cannot become visible via later response publication.
Mutating BLOB data is rejected by archive validation even if journal metadata untouched.
No new trace means exact historical seal/config/world/cursor hashes remain unchanged.

## Review focus and task tests

Most likely failure classes: invalid binary bodies and empty-vs-missing responses;
atomic failure between BLOB insertion and journal publication; source observation after
captured fork horizon; legacy format-one read/write without migration; privileged bytes
leaking into world/checkpoint/cursor or changing historical seals.

- [ ] Write failing tests in test_inference_trace_storage.py for frozen bytes/hash records,
  closed metadata, enum/types/nonfinite/UTC/loopback/endpoint validation; arbitrary invalid
  UTF8 and embedded NUL bytes round-trip, observed empty complete response vs unavailable.
- [ ] Verify targeted new tests fail for missing behavior; record RED evidence.
- [ ] Implement immutable metadata/BLOB model and compatible journal optional fields.
- [ ] Add format-two schema/version property and atomic record/append blob insertion,
  same-snapshot validation and prefix-restricted read interface.
- [ ] Test request+blob atomic publication and observation+response atomic publication,
  crash/injected SQL failure rollback, duplicate idempotence, divergent identity,
  read-only/cross-thread guards, corrupt digest/length/type/row/reference and orphan BLOB.
- [ ] Test response max+1 length allowed but >max+1 rejected, response requiring request
  metadata, reused request-only trace, invalid response-only reuse.
- [ ] Test saved prefix before response cannot retrieve that later response's body, exact
  prefix seal unchanged after later append, missing/gapped sequence behavior, and copying
  only authorized prefix blobs into a new archive produces locally readable evidence.
- [ ] Test genuine format-one read and ordinary writer behavior unchanged, opening it
  leaves database bytes unchanged and no trace table appears; trace write rejected
  atomically. New format-two missing table rejected. Ordinary untraced journal seals,
  snapshots/cursors and old request documents remain byte-identical.
- [ ] Run focused tests and directly related archive/catalog/fork/runtime compatibility
  tests; scoped Ruff/Black and git diff --check. No unrelated fixes. Write own report.

Focused command: VENV/bin/python -m pytest -q tests/test_inference_trace_storage.py
  tests/test_run_archive_store.py tests/test_run_archive_catalog.py
  tests/test_run_archive_fork_setup.py tests/test_runtime_broker.py
Use existing VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv
with PYTHONPATH=src when needed. Report commands/results/counts/warnings only, no pasted
successful output. Report actual RED/GREEN, remaining limits and allowed-path inventory.

## Root completion gates

Root independently reviews contract/diff/report and resolves all substantive findings.
Only then root runs make VENV=ABS_VENV, separate make examples after make exits,
git diff --check, exact canonical26/read-only hashes, archived CLI7/sourceServe4,
offline wheel11resources+actualServe4; verify reviewed sources unchanged after formatters.
Root alone updates common4/status, commits/pushes focused task and integrates no-ff into
codex/live-npc-runtime, repeats merged gates and pushes feature. Preserve branches and
owner edit. No main/milestone/tag action. Do not call capture/admin/real-provider acceptance
complete from storage tests. Stop with headroom BEFORE five-hour remaining below10%.
