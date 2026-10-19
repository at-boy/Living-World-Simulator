# Task 2 / LN02 — Atomic archive store

Status: authorized; contract prepared from reviewed integration b105d57.
Owner approved the nine-task plan and execution October19,2026. Root owns
architecture, independent review, full gates, VCS and integration.

Binding design: [approved spec](../../superpowers/specs/2026-10-19-live-npc-runtime-design.md).
Milestone plan: [approved plan](../../superpowers/plans/2026-10-19-live-npc-runtime.md).
LN01 frozen WorldSnapshot/encode_world/decode_world are integrated and retain schema12
bytes/schemas1–12 reads. Import those; do not duplicate/change the world codec.

## Global Constraints

- Branch `codex/live-npc-runtime` integrates these tasks; base `main` was `d8ea517`. Preserve `milestone/v0.6` at `6bf4c63` and `v0.6.0rc1` at `092715c`; no main integration/tag movement is authorized here.
- Python `>=3.11`; development Python3.13.5. Strict type hints, frozen domain records, manager-owned mutation, system-owned behavior and immutable events.
- No new runtime dependency or Node toolchain. No automatic model download, provider substitution, GPU driver installation, remote administration, player API, demographics or governance.
- Initial live defaults: 30-second request timeout; 512 generated tokens; 40 inference requests per attempt including retries; 20-tick headless bound; eight current perceptions; eight retrieved memories; 16,000-character serialized request ceiling; 1 MiB response limit. Reject booleans/nonpositive values for positive integer limits.
- One decision opportunity per eligible living founder per tick, sorted by scenario label. Existing recorded tapes retain one-entry-per-tick semantics.
- All CLI/browser/agent acceptance attempts archived; temporary unit fixtures explicitly choose temporary roots. No automatic deletion. Restart is a new linked attempt, browser pause/resume remains the current attempt.
- No model calls inside `SimulationEngine.step()`. No HTTP handler mutates an engine. Never persist or publish a poisoned/partial tick.
- Preserve world schema12 writes and schema1–12 reads, existing recorded payloads and public commands. Archive format1 is separate. Any necessary world-schema change requires root reconciliation and explicit contract amendment before code.
- Authenticated loopback-only operator controls; existing `create_app(engine)` and `/world/*` remain read-only. No tokens in URLs, logs, archives or browser persistent storage.
- User approval of this plan and execution method is required before implementation. Writing this plan does not execute its unchecked steps.


## Exact authorizing task text

## LN02: Atomic archive checkpoint and journal storage

**Files:**
- Create: `src/living_world/archives/__init__.py`, `src/living_world/archives/model.py`, `src/living_world/archives/store.py`, `tests/test_run_archive_store.py`.
- Uses LN01 without changing its interface. Slug: `archive_store`.

**Interfaces:** `AttemptArchive.open(ref: AttemptRef, *, read_only: bool = False)
-> AttemptArchive`; `load_world() -> WorldState`; `save_world(state: WorldState)
-> None` (GraphRepository compatibility, no live cursor guessing);
`append(entry: JournalEntry) -> int`; `commit(snapshot: WorldSnapshot, *,
expected_revision: int | None, driver_cursor: Mapping[str, object],
feedback_cursor: Mapping[str, object], entries: tuple[JournalEntry, ...]) -> Checkpoint`;
`checkpoint(revision: int | None = None) -> Checkpoint`; `entries() -> tuple[JournalEntry, ...]`;
`command(command_id: str) -> CommandReceipt | None`; readonly `database_path: Path`.
Live controller uses `commit`, never the compatibility `save_world`.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_run_archive_store.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** `test_checkpoint_cursor_and_outcomes_commit_together`,
  `test_failed_commit_keeps_previous_world_and_revision`, `test_duplicate_commit_is_idempotent`,
  `test_archive_metadata_does_not_change_recorded_payload`, `test_readonly_never_writes`.
  ```python
  first = archive.commit(snapshot0, expected_revision=None,
                         driver_cursor=cursor0, feedback_cursor={}, entries=())
  with pytest.raises(ArchiveRevisionConflict):
      archive.commit(snapshot1, expected_revision=999,
                     driver_cursor=cursor1, feedback_cursor={}, entries=())
  assert archive.checkpoint() == first
  assert read_world_row(archive.database_path) == (snapshot0.schema_version, snapshot0.payload)
  ```
  Each helper/fixture is defined in this test module, not production test switches.
- [ ] **Step 2 — Observe RED** run `tests/test_run_archive_store.py`; confirm missing
  archive interface. Include actual transaction rollback tests with injected SQLite
  constraint failure and read-only permissions, not only a mocked success method.
- [ ] **Step 3 — Implement** archive format1 tables: `archive_meta` (version/config),
  `world_snapshots` (compatible current row), `checkpoints` (revision PK, snapshot,
  digest/cursors), `journal` (monotonic sequence PK, kind, canonical payload), `commands`
  (command_id PK, envelope hash, result), `lifecycle` (append-only state transitions).
  Commit world row/checkpoint/resolution entries/cursor in one BEGIN IMMEDIATE
  transaction, optimistic expected_revision check before mutation. WorldSnapshot
  requires exact int schema type, never bool. Repeated identical commit returns
  prior revision; divergent reuse fails. No domain events for archive
  timestamps/IDs. A control_requested entry admits a canonical command envelope;
  a control_resolved entry settles its command row in the same transaction as its
  stepping checkpoint. Crash recovery must never run an applied command again.
  Expose engine-only `ArchiveError`, `ArchiveRevisionConflict` and
  `ArchiveFormatError`; reject unknown/newer formats on read without migration writes.
- [ ] **Step 4 — Observe GREEN** focused archive and codec tests; subprocess kill at
  transaction boundaries proves old-or-new complete state, never world/cursor mismatch.
  Validate malformed row types (including bool-as-int), hashes and journal schemas.
- [ ] **Step 5 — Review, root gates and commit** `feat: persist atomic run archive checkpoints`.


## Exact shared archive records

- LN02 `AttemptConfig(mode: Literal['recorded','ollama','journal_replay'], scenario_key:
  str, seed: int, software_revision: str, settings: Mapping[str, object])`;
  settings is an explicitly allowlisted nonsecret configuration document.
- LN02 `AttemptRef(lineage_id: str, attempt_id: str, directory: Path)`; IDs are
  lowercase UUID4 hex (32 characters), never paths supplied by a browser.
- LN02 `Checkpoint(revision: int, snapshot: WorldSnapshot, driver_cursor:
  Mapping[str, object], feedback_cursor: Mapping[str, object])`.
- LN02 `JournalEntry(kind: str, payload: Mapping[str, object])`: kind is a closed
  enum vocabulary `request_started/response_validated/response_failed/action_resolved/
  candidate_aborted/control_requested/control_resolved/attempt_finished`; validate
  each payload schema when appended and again when loaded. Formats are versioned.
- LN02 `CommandEnvelope(command_id: str, action: Literal['pause','resume','step',
  'stop','retry'], expected_state_version: int)` and
  `CommandReceipt(command_id: str, status: Literal['queued','applied','rejected'],
  state_version: int, revision: int, reason: str | None)`.

## Root architecture resolutions for LN02

These decisions close storage seams required by later authorized tasks; do not
implement catalog, controller, provider or browser behavior in this task.

### Initialization, identity and ownership

Add classmethod `AttemptArchive.create(ref: AttemptRef, config: AttemptConfig, *,
parent: tuple[str, int] | None = None) -> AttemptArchive`. It creates only a new
`ref.directory / "archive.sqlite3"`, rejecting an existing database. Directory
reservation belongs to LN03. `open` requires an existing valid database; never
initializes or repairs it, including writable opens. Store immutable format1,
ref/config/parent and a UTC creation timestamp in archive_meta. Expose read-only
`ref`, `config`, `parent`, `created_at: str`, `latest_revision: int | None`;
`lifecycle() -> tuple[Mapping[str, object], ...]` returns immutable append-only
records with exact sequence/state/reason/timestamp fields; `close()` releases resources
and context-manager support is allowed. Record owning thread; reject writer calls
from other threads. Read-only opens use SQLite mode=ro and perform no DDL, recovery,
journal-mode changes or metadata changes. Reject identity/path symlink escapes.
Use DELETE journal mode, foreign_keys=ON and explicit BEGIN IMMEDIATE for writes.
No durable writer connection is shared with readers.

### Transactions, revision and idempotence

First checkpoint revision0 uses expected_revision=None; next revision n+1 requires
expected_revision=n. Decode/validate the supplied snapshot before commit; save exact
schema/payload bytes and digest, including supported legacy rows. Validate/freeze
finite JSON cursors; storage does not guess or normalize driver semantics.
A canonical commit fingerprint covers expected revision, complete snapshot, both
cursors and ordered entries. Repeating the identical operation returns the original
checkpoint without appending rows or changing current-world bytes; divergent reuse
raises ArchiveRevisionConflict. Repeating an older exact commit never rolls back the
latest current row. Any validation/SQL/constraint failure rolls back everything.
`save_world` is supported only for config.mode=recorded; it encodes state, preserves
existing cursors (empty before initial), and commits with the latest expected revision.
Live/journal_replay save_world rejects instead of inventing progress. load_world and
checkpoint reject absence of a complete initial checkpoint, never fabricate a world.

`append` delegates to additional `record(entries: tuple[JournalEntry, ...], *,
lifecycle: str | None = None, reason: str | None = None) -> tuple[int, ...]`.
This atomic operation supports non-stepping command settlement/lifecycle, required
by LN04. commit inserts checkpoint, world row, journal and command/lifecycle effects
in one transaction. Lifecycle values are the global RuntimeState vocabulary;
LN02 validates/stores values, LN04 owns legal transitions. Exact stored state strings:
initializing, paused, running, awaiting_model, pause_requested, provider_error_paused,
stepping, completed, stopped, failed, interrupted. Terminal subset:
completed/stopped/failed/interrupted. The RuntimeState enum itself belongs to LN04;
LN02 accepts these strings without importing a future runtime module. Record UTC timestamps
outside world payload. attempt_finished also appends its terminal lifecycle state. Persist an internal
nullable lifecycle.journal_sequence foreign key for that mandatory effect; exactly
one corresponding row per terminal journal entry, matching terminal state and
reason/outcome. Ordinary lifecycle transitions may have null journal_sequence.
Validate correspondence on every load; public lifecycle records retain only the
four sequence/state/reason/timestamp fields.
No archive metadata generates domain events. Public errors wrap SQLite/validation
failures as ArchiveError/ArchiveFormatError; revision conflicts remain distinct.

### Closed, immutable data and configuration

Use the exact frozen dataclasses in Shared data contracts. Deep-freeze mapping
values to read-only maps and arrays to tuples; convert back only for canonical JSON.
Reject arbitrary objects, non-string keys, duplicate JSON object keys in archive documents on load (the existing world codec
retains its own compatibility behavior),
NaN/infinity and bool-as-int. IDs in AttemptRef and parent are lowercase UUID4 hex;
command/request IDs are nonempty opaque strings, not filesystem paths. Revisions,
versions, source ticks and slots are exact nonnegative ints; digests lowercase
64hex. Config seed exact int (negative permitted); strings nonempty; directory Path.

AttemptConfig.settings closed top-level keys: provider, limits, recorded_outcome,
launch_source, disturbance, driver_format, source_config_fingerprint. Empty allowed.
provider closed fields: model, base_url, timeout_seconds, max_output_tokens,
max_response_bytes, temperature, seed, model_digest. limits closed fields: max_ticks,
max_requests, max_perceptions, max_memories, max_request_characters, save_every.
Positive limits reject bool; max_ticks may be null for explicitly unbounded service.
Provider numeric values finite; timeout positive; temperature nonnegative; model
nonempty; base_url loopback HTTP(S), no credentials/query/fragment. model_digest
nonempty opaque digest (Ollama may prefix sha256:). recorded_outcome success/stall/failure;
launch_source cli/browser/agent; disturbance none/resource_loss/work_blockage;
driver_format positive int; source_config_fingerprint SHA256. No token, password,
raw response, arbitrary settings or external runtime objects accepted. Unknown keys
fail. Provider preflight and runtime defaults remain later tasks.

### Journal format1 exact payload keys

All keys below required except explicitly optional. Unknown keys fail both constructor,
append and load. Nested documents use exact closed schemas, not arbitrary JSON bags.

- request_started: request_id, base_revision, source_tick, actor_label,
  input_fingerprint, config_fingerprint, request (decoded JSON object from existing
  serialize_decision_request). Request exact fields identity, self_knowledge,
  current_perceptions, core_cognition, retrieved_information, conversation_history,
  actions; cognition exact kind/text/importance/is_core and actions key/description/
  target_labels. Validate existing ActionOption/RetrievedCognition/prose invariants;
  no holder/internal metadata fields. Contextual hidden-world filtering remains
  LN05/LN06 and never becomes an archive authorization shortcut.
- response_validated: request_id, decision (exact NPCDecision JSON spoken_text and
  action_request; action_request null or exact action_key/target_label/rationale/
  arguments string-map). Reuse existing decision/action constructors; verify offered
  vocabulary against its request when storing/loading. No raw body or reasoning.
- response_failed: request_id, code, optional content_digest. Code closed:
  timeout, transport, http_error, invalid_response, oversized_response, unsafe_response,
  cancelled, worker_failed, uncertain. No freeform exception/body field.
- action_resolved: base_revision, source_tick, actor_label, request_id,
  outcome (accepted/rejected/no_action), event_references (string array).
  References engine-only; require matching request slot identity when appended/loaded.
- candidate_aborted: base_revision, reason (nonempty classified string).
- control_requested: envelope (exact CommandEnvelope fields).
- control_resolved: receipt (exact CommandReceipt fields).
- attempt_finished: lifecycle (terminal state), outcome (nonempty string or null),
  last_revision (nonnegative int or null).

Request IDs unique; duplicate identical identity-bearing request/response/action or
command entries return their existing sequence and no extra row/effect; divergent
request/command ID reuse fails. Other repeated audit entries remain distinct. Response/action entries must
refer to known requests; response_validated versus response_failed may not contradict
one another for one request. Each new inference retry has a new request_id. Applied
slot resolution uniqueness prevents accidental duplicate committed actions. Controls
persist canonical envelope hash and queued receipt when requested; resolved requires
known command, exact receipt command_id, monotonic state_version/revision and no
rewrite of settled applied/rejected results. Return prior result for exact repeats.
Step applied receipt must be committed alongside its corresponding checkpoint,
with receipt.revision equal the newly committed revision; append/record cannot settle
an applied step alone. Other controls settle via record. Controller, not storage,
owns stale-state and lifecycle admission. A queued receipt uses the latest complete revision at admission (revision0
before an initial checkpoint); this does not claim that world data exists.
Persist an engine-only nullable journal revision_context column: current revision
for append/record, new revision for entries within commit, null before initial.
Read validation reconstructs queued receipts from this context and verifies exact
context types/checkpoint references; do not add context keys to closed payloads.

### Verification emphasis

Real SQLite constraint failures after world-row mutation must prove full rollback.
Use test-only triggers/subclasses and real subprocess termination before and after
COMMIT; no production hooks or timing sleeps as correctness assertions. Reopen writer
for any necessary SQLite crash recovery, then validate old-or-new complete snapshot,
cursors, entries, receipt and revision. Read-only byte/mtime tests use clean closed
archives and exercise missing/future/corrupt formats, digest/type/cross-reference
corruption, no-file/no-schema creation and rejected writes. Include actual filesystem
read-only access where available, documenting platform limits. Focused TDD only;
root owns full gates after independent review.

## Ownership and exact allowed-file boundary

Worker creates only src/living_world/archives/__init__.py, model.py, store.py and
tests/test_run_archive_store.py; worker updates only this task's
02_archive_store-report.md. No other writes, staging, commits, subagents, full
make, dependencies, codec/source edits or main/tag changes. Root common-document
allowance is this task's three artifacts, live_npc_runtime/README.md, CHANGELOG.md,
docs/project_journal.md, docs/backlog.md and continuation_brief.md.

Worker tests use PYTHONPATH=src and dependency-only Python from task24/.venv in
this isolated checkout. Focused RED/GREEN archive+codec/repository regressions,
lint/format/whitespace only. Canonical report records command/result/counts,
meaningful warnings, self-review and unresolved concerns, without raw passing logs.
Root performs independent review, full make, separate examples, whitespace and
recorded compatibility on final task/merged trees before commit/push.
