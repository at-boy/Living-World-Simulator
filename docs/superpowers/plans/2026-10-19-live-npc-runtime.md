# Live NPC Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run real Ollama-driven founders with perception/memory feedback, preserved recorded modes, durable resumable archives and observable browser controls.

**Architecture:** A single controller stages each tick on an unpublished engine, obtains model decisions outside engine mutation, revalidates proposals in the existing proposal phase and publishes only after an atomic archive checkpoint. Versioned archive metadata and journals remain outside the deterministic world payload. Existing managers, systems, proposal gateways and read-only inspection remain authoritative.

**Tech Stack:** Python >=3.11; dataclasses and Protocols; standard-library SQLite, JSON, hashing, queues, subprocess/multiprocessing and HTTP; existing FastAPI/PyYAML; packaged JavaScript/CSS/HTML; existing Ollama cognition client; existing pytest/Chrome tooling.

**Spec:** [Approved live NPC runtime design](../specs/2026-10-19-live-npc-runtime-design.md), approved by the owner October 19, 2026. The owner's subsequent clarification explicitly requires pause, shutdown, later restart and continuation of the same world.

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

## Review Focus

1. Shutdown immediately after Pause reports success: persisted tick, NPC memories, pending proposals and cursor must resume together without duplicate actions — LN04/LN07 subprocess tests.
2. Duplicate/stale Step requests while inference is delayed: one accepted command advances at most one complete tick, old requests never execute after the controller becomes paused again — LN04/LN08 tests.
3. Disk-full/mirror failure after archive commit: report the authoritative archived checkpoint and failed output without overwriting prior evidence or claiming cross-file atomicity — LN02/LN03 tests.
4. Invalid/oversized/late model output and player-like prose: no hidden-state leak, unsafe HTML, late action application or silent recorded fallback — LN05/LN06/LN08 tests.
5. Archive opened with changed/missing assets, traversal paths or a live owner: inspection never writes, loads unrelated inputs or marks an active run interrupted — LN02/LN03/LN08 tests.

---

## Execution contract and file ownership

These are nine dependent tasks, not parallel implementation work. Each task must be
independently reviewable and leave the integration branch usable. An executor reads
this plan and the approved spec before its own exact task material. Within plan
file lists, every path is repository-relative; do not infer a different module
from a shorthand filename in explanatory prose.

Before dispatching LN01–LN09, materialize its section into
`docs/subagent_execution_plan/live_npc_runtime/NN_<slug>.md` and matching
`NN_<slug>-prombt.md`; copy the exact interfaces, allowed files, invariants, tests and
non-goals rather than inventing a second design. Start its `NN_<slug>-report.md`
truthfully pending; update evidence after implementation/review. Do not create an
implementation report falsely claiming delivery while only planning exists.

Common documentation allowance for each task: its own three artifacts;
`docs/subagent_execution_plan/live_npc_runtime/README.md`; `CHANGELOG.md`;
`docs/project_journal.md`; `docs/backlog.md`; and
`docs/orchestrator_handoff/continuation_brief.md`. Runtime/test allowances are exact
below. Amend task plus saved prompt before widening a boundary. Do not update
completed historical reports or generated egg metadata incidentally.

Use isolated task branches `codex/live-npc-lnNN-<slug>` from the reviewed integration
head, with durable `.worktrees/live-npc-lnNN` checkouts. One bounded worker, independent
read-only review, narrow corrections and re-review for nontrivial tasks. Root retains
architecture, disposition and integration. Do not delete any existing branch/worktree.
After focused RED/GREEN and review, root runs `make`, separate `make examples`, and
staged/unstaged `git diff --check` on the final task tree. Repeat current required
merged gates before pushing the integration head or starting a dependent task.

During execution the root may push this feature/task scope to the existing origin;
main/tag/publication remain separate owner actions. If remote authority is unclear,
resolve it before publication, not by changing destination or forcing refs.
Monitor five-hour usage and checkpoint/stop active workers BEFORE remaining <10%.
No implementation starts while plan review is pending.

Suggested commands below assume `TASK_ROOT` is the exact isolated checkout and
`TASK_PY` is its dependency environment's Python; set task-specific variables without
repurposing HOME/CODEX_HOME. Use `PYTHONPATH=src "$TASK_PY" -m pytest ...` from that
checkout. Never rely on an installed editable package importing another checkout.

## Planned source layout

| Path | Responsibility / owner task |
| --- | --- |
| `repositories/world_snapshot.py` | Public frozen snapshot value and existing codec extraction (LN01) |
| `archives/model.py`, `store.py` | Archive format1 records, schema and atomic checkpoint/journal repository (LN02) |
| `archives/catalog.py`, `assets.py`, `lease.py`, `mirror.py` | Attempt discovery, retained inputs, ownership, child attempts and compatibility output (LN03) |
| `runtime/contracts.py`, `controller.py`, `recorded.py`, `publication.py` | Single-owner lifecycle, candidate tick protocol, recorded adapter and immutable revisions (LN04) |
| `runtime/founders.py`, `feedback.py` | Tape-independent founders composition, local qualitative observations/memories and context selection (LN05) |
| `runtime/ollama_driver.py`, `broker.py`, `journal_replay.py` | Bounded real inference, live proposal system and offline replay (LN06) |
| `runtime/service.py`, existing `cli.py` | CLI/service ownership, shutdown/restart and explicit driver selection (LN07) |
| `api/operator.py`, `auth.py`, `inspection_routes.py`, `revision_source.py`, `static/runtime.*` | Separate controls/archive browser and reuse of GET-only inspection (LN08) |
| `examples/040_live_npc_runtime.py`, `examples/manual/ollama_founders_runtime.py` | Deterministic executable documentation and explicit real-provider acceptance (LN09) |

Paths in this table are under `src/living_world/` unless prefixed `examples/`.
Create package `__init__.py` only in its owning task and explicitly export supported
interfaces. Do not expose internal IDs or archive metadata to NPC-facing modules.

## Shared data contracts

Define the records named here in their owning task; subsequent Interfaces blocks
refer to these exact names. Frozen dataclasses must validate constructor inputs and
freeze nested collections. JSON document fields accept only finite JSON values;
reject arbitrary runtime objects rather than serializing `repr()`.

- LN01 `WorldSnapshot(schema_version: int, payload: str)`, property `digest: str`:
  SHA256 of UTF8 `str(schema_version) + "\n" + payload`; payload is the existing
  canonical JSON string. Loading historical versions preserves their source row.
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
- LN04 `RuntimeStatus(attempt: AttemptRef, state: RuntimeState, state_version: int,
  revision: int | None, tick: int | None, activity: str | None, error_code: str | None)`.
- LN04 `DriverCommit(driver_cursor: Mapping[str, object], feedback_cursor:
  Mapping[str, object], journal_entries: tuple[JournalEntry, ...])`.
- LN05 `DecisionInput(actor_label: str, actor_id: str, context: NPCContext,
  options: tuple[ActionOption, ...], input_fingerprint: str)`. `actor_id` is
  engine-only and MUST NOT enter serialized provider input; the input fingerprint
  covers base snapshot, actor label, context/options, format and driver configuration,
  not timestamps/attempt UUIDs. SHA256 uses canonical JSON and existing serializers.
- LN06 `ProviderConfig(model: str, base_url: str = 'http://127.0.0.1:11434',
  timeout_seconds: float = 30.0, max_output_tokens: int = 512,
  max_response_bytes: int = 1048576, temperature: float = 0.0, seed: int | None = None)`;
  resolve omitted seed from scenario.seed before freezing effective attempt settings.

Archive SQL uses DELETE journal mode, not WAL, for straightforward immutable inspection
and physical-file checks. Foreign keys enabled; all writes owned by one runtime thread;
other threads receive frozen publications/queue handles, not writer connections.
RuntimeState is a str Enum with initializing, paused, running, awaiting_model,
pause_requested, provider_error_paused, stepping, completed, stopped, failed and
interrupted. Terminal states are completed/stopped/failed/interrupted. Human-readable
state labels in the transition table use hyphens for readability.

## LN01: Extract the existing world snapshot codec

**Files:**
- Create: `src/living_world/repositories/world_snapshot.py`, `tests/test_world_snapshot.py`.
- Modify: `src/living_world/repositories/sqlite_repository.py`, `tests/test_sqlite_repository.py`.
- Slug: `world_snapshot_codec`.

**Interfaces:** produces `encode_world(state: WorldState) -> WorldSnapshot`,
`decode_world(snapshot: WorldSnapshot) -> WorldState`; consumes existing private
serialize/deserialize/validation logic. `SQLiteRepository` public constructor and
GraphRepository load/save signatures remain unchanged.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_world_snapshot.py tests/test_sqlite_repository.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** `test_codec_preserves_exact_existing_row`,
  `test_codec_roundtrip_and_detachment`, `test_codec_rejects_corrupt_and_future_schema`.
  Pin the tuple and complete payload, not selected fields:
  ```python
  encoded = encode_world(populated_world)
  repository.save_world(populated_world)
  assert (encoded.schema_version, encoded.payload) == read_world_row(database)
  assert encode_world(decode_world(encoded)) == encoded
  assert decode_world(encoded) is not populated_world
  ```
  `read_world_row` is a test-only helper; use current schema12 and legacy fixture tests.
- [ ] **Step 2 — Observe RED** run `tests/test_world_snapshot.py`; expected import/name
  failure for absent codec. Existing serialization fixtures establish the reference.
- [ ] **Step 3 — Implement** exact functions above by extracting/reusing existing
  validators and canonical JSON; no second serializer or world field changes. Preserve compatibility aliases for
  existing private _serialize_world imports used by canonical tests; do not rewrite
  those assertions to accommodate codec drift. Keep
  current error types/diagnostics by translating codec errors at repository boundary.
- [ ] **Step 4 — Observe GREEN** focused codec/repository/replay tests plus canonical
  exact fresh/resume checks. Mutation of decoded state cannot mutate source snapshot.
- [ ] **Step 5 — Review, root gates and commit** `refactor: expose compatible world snapshot codec`.
  Root verifies no schema/version/dependency delta and records exact reviewed commit.

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

## LN03: Attempt catalog, retained inputs, ownership and compatibility mirrors

**Files:**
- Create: `src/living_world/archives/catalog.py`, `src/living_world/archives/assets.py`, `src/living_world/archives/lease.py`, `src/living_world/archives/mirror.py`, `tests/test_run_archive_catalog.py`, `tests/test_run_archive_mirror.py`.
- Modify: `src/living_world/archives/__init__.py`.
- Slug: `attempt_lifecycle`.

**Interfaces:** `RunCatalog(root: Path)`;
`reserve(config: AttemptConfig, *, parent: tuple[str, int] | None = None) -> AttemptRef`;
`attempts() -> tuple[AttemptSummary, ...]`; `open_attempt(attempt_id: str,
*, read_only: bool = True) -> AttemptArchive`;
`fork(attempt_id: str, revision: int, *, config: AttemptConfig | None = None) -> AttemptRef`;
`retain_inputs(ref: AttemptRef, scenario_path: Path, *, tape_path: Path | None) -> RetainedInputs`;
`AttemptLease(ref).acquire()/release() -> None`;
`write_checkpoint_mirror(checkpoint: Checkpoint, destination: Path) -> None`.
`AttemptSummary` has ref, mode, scenario, parent, started/ended time, lifecycle,
last_revision/tick optional and failure code. `RetainedInputs` has resolved scenario,
definitions, optional tape paths and content hashes; no live external file reference.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_run_archive_catalog.py tests/test_run_archive_mirror.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** unique attempt reservation; parent fork exact
  checkpoint; immutable assets with relative definition paths, spaces/?/#; missing or
  modified assets; path traversal/symlink escape; active-owner versus abandoned run;
  pre-world setup failure; mirror failure after archive commit.
  ```python
  child = catalog.fork(parent.attempt_id, revision=3)
  assert child.attempt_id != parent.attempt_id
  assert catalog.open_attempt(parent.attempt_id).checkpoint(3) == before
  assert catalog.open_attempt(child.attempt_id).checkpoint().snapshot == before.snapshot
  ```
- [ ] **Step 2 — Observe RED** run the two new archive test modules. Use two actual
  processes for exclusive ownership and unexpected exit, temporary filesystem roots.
- [ ] **Step 3 — Implement** reserve UUID attempt directory before loading scenario;
  default catalog root `$XDG_STATE_HOME/living-world/runs` or
  `~/.local/state/living-world/runs`, explicit root overrides; no code mutates HOME.
  Capture asset bytes by SHA256 into local content-addressed storage and preserve
  loader-relative names in a private per-attempt input tree. Atomic temp-file rename
  publishes manifests, but SQLite remains authoritative for progress. Lock using
  stdlib advisory file locking (fcntl on POSIX, msvcrt on Windows); never infer death
  from PID alone. Read discovery derives interrupted status if no owner exists;
  GET/discovery does not persist that status or mutate historical DB bytes.
- [ ] **Step 4 — Implement compatibility export** backup/construct a standalone
  closed temp SQLite snapshot in destination directory, fsync then atomic replace.
  Validate source/destination alias and reject overwrite of archive-owned storage.
  Parent input is read-only; child copies its exact world/cursors and reconstruction
  inputs with parent reference. New-model config requires explicit child settings;
  no archived model/token credentials inferred. Mirror failure is `ArchiveMirrorError`
  with archived attempt/revision and failed destination, never a fake rollback claim.
- [ ] **Step 5 — Observe GREEN** test all catalog/mirror cases, including destination
  disk/permission failure after archive commit and corrupt/future-format input. Views
  preserve DB bytes; failed-before-initialization attempts show `tick=None`.
- [ ] **Step 6 — Review, root gates and commit** `feat: retain discoverable isolated run attempts`.

## LN04: Single-owner controller, recorded adapter and complete-revision publication

**Files:**
- Create: `src/living_world/runtime/__init__.py`, `src/living_world/runtime/contracts.py`, `src/living_world/runtime/controller.py`, `src/living_world/runtime/recorded.py`, `src/living_world/runtime/publication.py`, `tests/test_runtime_controller.py`, `tests/test_runtime_recorded.py`.
- Modify: `src/living_world/running/runner.py` only to extract shared pure limit/terminal evaluation if needed, preserving public Runner/ScenarioRunner behavior.
- Slug: `safe_controller`.

**Interfaces:** `RunController(archive: AttemptArchive, composition: ScenarioComposition,
 driver: TickDriver, *, max_ticks: int | None, start_paused: bool)`;
`submit(command: CommandEnvelope) -> CommandReceipt`; `poll() -> RuntimeStatus`;
`status() -> RuntimeStatus`; `published(revision: int | None = None) -> Checkpoint`;
`close() -> None`. `poll` advances owner work without waiting on provider IO.
`ScenarioComposition.initialize() -> SimulationEngine`, `restore(snapshot:
WorldSnapshot) -> SimulationEngine`, `terminal_condition(engine: SimulationEngine) -> str | None`,
`finalize(engine: SimulationEngine, *, stopped: bool) -> None`.
`TickDriver.prepare(candidate: SimulationEngine, base: Checkpoint,
 archive: AttemptArchive) -> TickPreparation`.
`TickPreparation.poll() -> Literal['waiting','ready','provider_error']`,
`request_pause() -> None`, `install() -> None`, `finish_tick() -> DriverCommit`,
`close() -> None`. Define `SnapshotRepository(snapshot: WorldSnapshot)` in runtime/recorded.py with
`load_world() -> WorldState` returning decode_world(snapshot), and
`save_world(state: WorldState) -> None` raising RepositorySaveError. Candidates cannot bypass archive commit.
Composition restores existing definitions/scenario/preparation;
`install` only configures the candidate's proposal slot, never advances it.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_controller.py tests/test_runtime_recorded.py tests/test_runner_cli.py tests/test_recorded_proposal_tapes.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** pause before first tick; one step then paused;
  duplicate command IDs; ID reuse with different body; stale state_version queued
  behind another step; pause during waiting; terminal zero-step; late tick failure;
  save failure; old publication unchanged while preparing; stop/pause durability.
  ```python
  receipt = controller.submit(CommandEnvelope('step-a', 'step', status.state_version))
  drive_owner_until_idle(controller)
  assert controller.status().tick == start_tick + 1
  assert controller.status().state is RuntimeState.PAUSED
  controller.submit(CommandEnvelope('step-a', 'step', status.state_version))
  drive_owner_until_idle(controller)
  assert controller.status().tick == start_tick + 1
  ```
  Define deterministic fake TickPreparation and owner-driving helper in tests only.
- [ ] **Step 2 — Observe RED** new controller tests. Add recorded fixtures before
  adapter changes, pin old complete success/stall/failure hashes from LN09 below.
- [ ] **Step 3 — Implement state machine** use an owner-thread queue with immutable
  status publications, separate monotonically increasing `state_version` and durable
  checkpoint `revision`. All transitions, command admission/results and audit writes
  are owner-thread operations. HTTP uses queue Future/receipt, never owns SQLite.

| Current state | Allowed command | Required result |
| --- | --- | --- |
| initializing | pause/stop | latch intent; acknowledge only after valid initial checkpoint or classified setup failure |
| paused | resume | running; reuse valid matching staged responses, no immediate duplicate inference |
| paused | step | stepping; exactly one committed tick then paused/terminal |
| running/awaiting-model/stepping | pause | pause-requested; stop new calls/ticks, await bounded current call or current complete tick |
| paused/provider-error-paused/running/awaiting-model | stop | finalize stopped at last durable boundary; no unfinished world export |
| provider-error-paused | retry | new request-attempt for failed/uncertain slot, retained matching earlier actor responses |
| provider-error-paused | resume/step | reject with provider_retry_required |
| completed/stopped/failed/interrupted | any mutation | reject terminal_attempt; explicit fork required |

  All unlisted state/action pairs reject. Persist the interrupted run/step intent
  through provider-error-paused; retry returns to that same intent and a successful
  retried step still advances only its one requested tick.
  Valid duplicate command_id returns its prior receipt/result before stale-version
  validation; same ID with different canonical envelope rejects. New ID with old
  expected_state_version rejects. No automatic model retries or queued step credits.
- [ ] **Step 4 — Implement candidate/publication protocol** restore last checkpoint,
  prepare outside mutation, install driver, call one existing engine.step, evaluate
  existing terminal rules once at each boundary, finalize when appropriate, encode,
  atomically commit then publish. On any exception retain previous publication and
  quarantine/discard candidate. Pause success means checkpoint+cursors durable.
  Stop does not mutate a terminal success into failure. RunController.submit is owner-thread-only; RuntimeService supplies queued Futures
  to other threads. Persist the final Step receipt with its checkpoint transaction
  before publishing; settle non-stepping controls with journal/lifecycle in one
  transaction. Recorded adapter uses exact
  ReplayPreparation/FoundersPreparation, no additional observations or changed tape.
- [ ] **Step 5 — Observe GREEN** controller/recorded/runner/replay suites and exact
  recorded matrices. Use subprocess paused checkpoint -> exit -> reopen/fork to
  assert tick, complete world, cursor and history survive. This gate already works
  without Ollama; later tasks add live-provider-specific restart coverage.
- [ ] **Step 6 — Review, root gates and commit** `feat: control runs at durable tick boundaries`.

## LN05: Tape-independent founders composition and qualitative NPC feedback

**Files:**
- Create: `src/living_world/runtime/founders.py`, `src/living_world/runtime/feedback.py`, `tests/test_runtime_founders_feedback.py`.
- Modify: `src/living_world/founders/runtime.py`, `src/living_world/founders/__init__.py`, `src/living_world/cognition/npc_context.py` (optional retriever injection/limit extension only), `src/living_world/cognition/retrieval.py` (explicit policy selection only), `docs/npc_information_boundary.md`.
- Existing founders/replay tests retain their assertions; new cases belong in the new test module. Slug: `npc_feedback`.

**Interfaces:** `FoundersLiveComposition(inputs: RetainedInputs)` implements LN04
ScenarioComposition; shared `prepare_founders_world(engine: SimulationEngine,
scenario: LoadedScenario) -> FoundersPolicy` extracted from FoundersPreparation
without changing recorded composition order. `FoundersFeedback(request_size: Callable[[NPCContext, tuple[ActionOption, ...]], int])`;
`FoundersFeedback.prepare(candidate: SimulationEngine, base: Checkpoint) -> tuple[DecisionInput, ...]`;
`FoundersFeedback.after_tick(candidate: SimulationEngine, outcomes: tuple[JournalEntry, ...]) -> Mapping[str, object]`.
Cursor stores holder/source-change fingerprints and pending observable results, never
raw prompt data inside WorldState. `DecisionInput` is LN05's public runtime value.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_founders_feedback.py tests/test_npc_context.py tests/test_npc_cognition_client.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** `test_only_local_alive_founders_receive_camp_changes`,
  `test_private_cognition_and_hidden_goal_values_never_enter_requests`,
  `test_unchanged_perception_does_not_duplicate_memory_on_restart`,
  `test_actor_result_is_observed_on_next_decision`, `test_context_budget_is_deterministic`.
  ```python
  inputs = feedback.prepare(candidate, base)
  assert tuple(item.actor_label for item in inputs) == ('ada', 'bryn')
  assert hidden_marker not in serialize_decision_request(inputs[0].context, inputs[0].options)
  memories = candidate.memories.memories_for(inputs[0].actor_id)
  assert len(memories) == 2  # fixture contains mandate plus one visible condition
  assert all(m.source_observation_ids for m in memories)
  assert all(m.holder_id == inputs[0].actor_id for m in memories)
  ```
  Pin the exact qualitative templates in test fixtures: communicated mandate,
  local need/work projections and acted/witnessed results; no invented numeric prose.
- [ ] **Step 2 — Observe RED** new feedback tests using managers to create actual
  placements/goals/observations/memories, including another holder's secret records.
- [ ] **Step 3 — Implement** explicitly communicate mandate once; living same-camp
  eligibility via existing spatial manager, owned result feedback and observed camp
  changes only. Use existing typed goal/need/work/external projections and validate
  every final prose through NPCInformationBoundary. Record observations/memories
  through managers. Mandate uses CognitiveSalience(0.8, is_core=True); changed local
  conditions/results use CognitiveSalience(0.6, is_core=False). Never fabricate a
  perception from an unseen dispatch or another NPC's uncommunicated model speech.
- [ ] **Step 4 — Implement bounded retrieval** expose core mandate plus at most eight
  current perceptions and eight distinct holder-owned retrieved memories total
  (deduplicate core/retrieved overlap). Stable salience/newest/tie-ID ordering; prune
  oldest optional entries until injected request_size <=16000 characters; retain required
  identity/mandate/options. If required content alone is too large, fail preparation.
  Fingerprint exact serialized input and base world/driver identity; exclude actor_id,
  operational UUID/time from provider JSON. Capture staged provenance in archive cursor
  for deterministic reconstruction, not extra untyped world attributes.
- [ ] **Step 5 — Observe GREEN** context/information-boundary/perception/feedback suites;
  relocate or destroy an actor between boundaries, mutate a work target legitimately,
  and assert changed safe inputs/offers. Recorded fixtures/hashes stay unchanged.
- [ ] **Step 6 — Review, root gates and commit** `feat: feed observed world changes into NPC decisions`.

## LN06: Bounded Ollama decisions, live proposal journal and exact offline replay

**Files:**
- Create: `src/living_world/runtime/ollama_driver.py`, `src/living_world/runtime/broker.py`, `src/living_world/runtime/journal_replay.py`, `tests/test_runtime_ollama_driver.py`, `tests/test_runtime_journal_replay.py`, `tests/test_runtime_broker.py`.
- Modify: `src/living_world/cognition/ollama_cognition_client.py`, `src/living_world/perception/local_llm_http.py`, `tests/test_ollama_cognition_client.py`, `tests/test_local_llm_http.py`, `src/living_world/runtime/__init__.py`.
- Slug: `live_driver`.

**Interfaces:** `OllamaTickDriver(config: ProviderConfig, feedback: FoundersFeedback,
 broker: DecisionBroker)` implements TickDriver; `JournalReplayDriver(source:
AttemptArchive, feedback: FoundersFeedback)` same protocol, zero model calls.
`DecisionBroker.start(job_id: str, config: ProviderConfig, decision_input: DecisionInput)
-> None`, `poll(job_id: str) -> BrokerResult | None`, `close() -> None`.
`BrokerResult` contains job_id, safe NPCDecision optional, error_code optional,
response_digest optional and elapsed_seconds; job/actor IDs remain engine-only.
Extend `OllamaCognitionClient` with optional `max_output_tokens: int = 512`,
`temperature: float = 0.0`, `seed: int | None = None`, and
`UrllibJsonHttpTransport(max_response_bytes: int = 1048576)` preserving old callers.
Add `OllamaCognitionClient.build_payload(context: NPCContext, actions:
tuple[ActionOption, ...]) -> dict[str, object]` and have decide use it. The live
feedback request_size counts canonical JSON of this complete HTTP body, including
system/schema/model/options and escaped prompt; it does not budget just the inner
NPC JSON. Live driver and worker independently enforce the same16000-character
limit before sending. Journal replay reconstructs the same source payload encoder.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_ollama_driver.py tests/test_runtime_journal_replay.py tests/test_runtime_broker.py tests/test_ollama_cognition_client.py tests/test_local_llm_http.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** timeout/unavailable/unsafe/oversized/late output;
  real gateway effect; two-actor ordering; no provider call inside step; valid speech
  without action; action becomes invalid before proposal phase; budget exhausted;
  uncertain request after kill; exact journal replay and input/model mismatch; required versus optional context
  pruning at the full16000-character HTTP-body boundary including escaping.
  ```python
  run_with_fake_http_provider(controller, replies=valid_replies)
  expected = controller.published().snapshot
  replay = replay_archived_attempt(catalog, source_attempt, forbid_network=True)
  assert replay.published().snapshot == expected
  assert replay.domain_events == original_domain_events
  assert replay.work_charges == original_work_charges
  ```
  Helpers are defined in tests against production driver/controller APIs.
- [ ] **Step 2 — Observe RED** new modules; existing provider tests pin old JSON/schema
  behavior before adding optional generation cap and bounded response reading.
- [ ] **Step 3 — Implement IO broker** one owned, spawned worker process per inference
  request, with an explicit wall-clock deadline. It receives only provider config,
  NPCContext and options (never engine/actor_id/inspector). Return bounded JSON bytes
  through IPC, not arbitrary provider objects. DecisionBroker.start strips actor_id and all
  other engine-only DecisionInput fields before sending IPC. Reconstruct NPCDecision through existing
  parser then revalidate in parent. On deadline/close terminate and reap only this
  owned process; late results cannot apply to a different job or base revision.
  This keeps controller/UI responsive and shutdown bounded, unlike a blocking HTTP
  call inside a tick. Fake brokers are test-only; production uses real process/HTTP.
  Reject credential-bearing provider URLs and HTTP redirects;
  loopback validation must survive malformed ports and IPv6 addresses. Treat invalid
  UTF8 and response-body overflow as classified provider errors. Add these actual
  HTTP cases to tests/test_local_llm_http.py, preserving llama.cpp compatibility.
- [ ] **Step 4 — Implement live driver** persist request_started before send; persist
  safe response_validated/response_failed after completion; no raw invalid response
  body or model chain-of-thought. Reuse only actor/slot/fingerprint-matching validated
  responses after restart. Count all requests/retries against40 default budget;
  first failure pauses, explicit retry increments count. No fallback to canned action. Provider payload retains stream=false, think=false
  and the current response JSON schema; options.num_predict is max_output_tokens.
  Pin temperature=0 and seed=scenario.seed in effective generation settings where
  supported, without claiming bitwise live inference determinism.
  Live proposal system runs in the one existing proposal slot, uses current offered
  handler bundle and ordinary gateway revalidation. Record accepted/rejected/no-action
  outcomes; atomic checkpoint commit marks only successfully committed slot effects.
- [ ] **Step 5 — Implement offline replay** start from source initial checkpoint and
  retained configuration/inputs, regenerate feedback and offers, compare fingerprints,
  apply recorded safe proposals in the live schedule. Abort on divergence or missing
  applied records. Preserve alternate failed inference attempts as analysis, not
  extra simulated turns. Input fingerprint validation uses the source attempt's recorded
  driver configuration, not the new replay attempt's operational mode/UUID/time.
  Compare every committed world snapshot/event/charge, not
  normalized subsets. A detached world mirror cannot satisfy live driver binding.
- [ ] **Step 6 — Observe GREEN** driver/broker/replay/provider tests plus real local
  stub-HTTP subprocess tests for hard deadline, huge body and process cleanup. Kill
  before response, after journal response, and after commit-before-publication; recovery
  must not duplicate committed actions or consume another HTTP response unnecessarily.
- [ ] **Step 7 — Review, root gates and commit** `feat: run and replay bounded live Ollama decisions`.

## LN07: Archived CLI/service entrypoints and pause–shutdown–restart continuity

**Files:**
- Create: `src/living_world/runtime/service.py`, `tests/test_runtime_cli.py`, `tests/test_runtime_restart.py`.
- Modify: `src/living_world/cli.py`, `src/living_world/runtime/__init__.py`, `tests/test_runner_cli.py`, `tests/test_founders_cli.py`, `docs/canonical_founders.md`.
- Slug: `runtime_entrypoints`.

**Interfaces:** `RuntimeService(catalog: RunCatalog)`;
`start(config: AttemptConfig, inputs: RetainedInputs, *, paused: bool) -> RunController`;
`resume(attempt_id: str, revision: int | None, *, paused: bool) -> RunController`;
`run_owner_loop(controller: RunController, *, stop_event: threading.Event) -> None`;
`RuntimeService.submit(command: CommandEnvelope) -> concurrent.futures.Future[CommandReceipt]`
queues to the owner and resolves controller.submit there, never in an HTTP thread;
`shutdown() -> None`. Public old CLI `main(..., stop_control, engine_factory)` hooks
remain compatible. Operator web factory is integrated in LN08, not a placeholder.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_cli.py tests/test_runtime_restart.py tests/test_runner_cli.py tests/test_founders_cli.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing CLI/restart tests** preserve old aliases/exit codes and
  stdout run summary (add attempt location on stderr); archive all three outcomes and
  provider/setup failure; default CLI must not require uvicorn; no live model in make.
  Pause live at tick k, acknowledge durability, shut down process, start another:
  ```python
  before = pause_and_shutdown(first_process)
  child = restart_from_archive(before.attempt_id, before.revision)
  assert child.initial_snapshot == before.snapshot
  assert child.parent == (before.attempt_id, before.revision)
  step_once(child)
  assert child.tick == before.tick + 1
  assert previous_work_not_charged_again(child)
  ```
  Assert complete persisted observations/memories, pending journal and driver cursor,
  not just tick. Check original attempt bytes remain unchanged after child creation.
- [ ] **Step 2 — Observe RED** run CLI/restart modules with real child processes and
  fake loopback HTTP server. Pin old tests before parser changes.
- [ ] **Step 3 — Implement explicit CLI** retain `run --founders success|stall|failure`
  and all current flags. Add `run --preset founders --driver ollama --model MODEL`,
  `run --resume-attempt ID [--checkpoint REV]`, `run --replay-attempt ID`, and
  `serve --preset founders --driver ollama --model MODEL [--start-running]`.
  Also support `serve --founders success|stall|failure` and
  `serve --resume-attempt ID [--checkpoint REV]` (paused by default), plus
  `inspect --attempt ID [--checkpoint REV] --archive-root PATH` as a read-only
  archive inspector entrypoint. Existing inspect scenario/database forms remain valid.
  New `serve` defaults paused; CLI live default20ticks, recorded bounds unchanged.
  Common options: `--archive-root PATH`, `--base-url`, `--timeout-seconds`,
  `--max-output-tokens`, `--max-requests`, and `--admin-token-file PATH` for serve;
  `--port` for serving only. Mutually exclusive new-run/resume/replay targets;
  resume rejects changed driver/model/scenario. Add `--fork-attempt ID` to run/serve
  for an explicit child with changed model/limits; it cannot switch a recorded
  binding to live or change scenario identity. Invalidated prepared parent responses
  stay archived but are not reused with the changed configuration.
  Never infer live mode from an existing raw database. Preserve `--database` recorded
  compatibility mirror and `--save-every` mirror cadence; archive each completed tick.
- [ ] **Step 4 — Implement lifecycle ownership** pre-reserve attempt before setup;
  retain/validate inputs; preflight installed Ollama/model via bounded GET /api/tags (record name and digest) without automatic download;
  load/create initial durable checkpoint and obtain lease. SIGINT requests safe stop;
  bound broker/process cleanup. A confirmed pause is safe for later process exit:
  store checkpoint/cursors/control receipt before acknowledging. Hard-kill remains
  recoverable from last committed checkpoint even without a final manifest update.
  At restart create child and restore exact world/definitions/cursors; simulation
  time does not advance while off. Terminal saves do not take another model turn.
- [ ] **Step 5 — Observe GREEN** CLI/runner/founders/recorded/restart suites; real
  subprocess quit after pause and reopen; Ctrl-C during inference; missing server;
  failure before any world checkpoint; mirror failure after archive is ahead. Existing
  documented recorded commands still work and old stdout summary is preserved.
  Keep existing configuration/compatibility/persistence/simulation exit codes2/3/4/5;
  live provider failure uses6. A requested finite tick/request-budget stop uses0
  with explicit stop reason, not fabricated terminal success; initialization/archive
  failure uses4 and still identifies the reserved attempt when one exists.
- [ ] **Step 6 — Review, root gates and commit** `feat: launch and resume automatically archived runs`.

## LN08: Local-admin controls, coherent live inspection and historical archive browser

**Files:**
- Create: `src/living_world/api/operator.py`, `src/living_world/api/auth.py`, `src/living_world/api/inspection_routes.py`, `src/living_world/api/revision_source.py`, `src/living_world/api/static/runtime.html`, `src/living_world/api/static/runtime.css`, `src/living_world/api/static/runtime.js`, `tests/test_runtime_operator_api.py`, `tests/test_runtime_browser.py`.
- Modify: `src/living_world/api/server.py`, `src/living_world/api/static/inspector.js`, `src/living_world/api/static/inspector.html`, `src/living_world/runtime/service.py`, `src/living_world/cli.py`, `pyproject.toml` (three runtime asset package-data entries only), `docs/http_inspection_api.md`, `docs/world_inspector_ui.md`.
- Slug: `operator_browser`.

**Interfaces:** `create_operator_app(service: RuntimeService, controller: RunController
| None, *, auth: AdminSession) -> FastAPI`; `AdminSession.issue() -> AdminSession`
contains cryptographic token and CSRF nonce never archived;
`create_inspection_router(resolve_inspector: Callable[[Request], WorldInspector])
-> APIRouter`; existing `create_app(engine: SimulationEngine) -> FastAPI` unchanged.
`RevisionSource(catalog: RunCatalog, *, controller: RunController | None = None)`;
`RevisionSource.open(attempt_id: str, revision: int) -> WorldInspector` is detached,
read-only, with validated archived inputs. Keep at most eight loaded inspectors;
archive remains source of truth when evicted. No open runner attached to history.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_operator_api.py tests/test_runtime_browser.py tests/test_inspection_api.py tests/test_world_inspector_browser.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing API/browser tests** unauthorized/missing token; cross-origin
  POST; wrong CSRF; duplicate/stale step; delayed model request with responsive status;
  coherent multi-panel revision; expired cache reload; malformed/traversal archive ID;
  literal malicious prose rendering; historical no-controls/read-only byte preservation.
  ```python
  before = read_all_archive_bytes(historical_attempt)
  inspect_historical_in_real_browser(attempt_id, checkpoint_revision)
  assert read_all_archive_bytes(historical_attempt) == before
  assert await_status_during_delayed_inference().tick == committed_tick
  assert unauthorized_step().status_code == 401
  ```
  Browser assertions must exercise actual routes/DOM, not source-code request strings.
- [ ] **Step 2 — Observe RED** new API/Chrome tests using existing ASGIClient/browser
  patterns. Add routes-refactor regression coverage for all current GET-only APIs.
- [ ] **Step 3 — Implement separate control routes** GET `/runtime/status`,
  POST `/runtime/commands`, GET `/runtime/commands/{command_id}`; POST body is exact
  CommandEnvelope, 202 queued, 200 known result, 409 stale/lifecycle conflict,
  401 auth failure, 403 origin/CSRF failure. No other HTTP method invokes mutation.
  Route handlers call RuntimeService.submit, not controller.submit directly.
  Audit only nonsecret command data; persistent results owned by controller.
  Require Bearer token and `X-CSRF-Token`, validate exact configured Origin; no CORS.
  CLI provides the token only through the local interactive terminal (never a
  logger or archive); stdout-redirected automation uses a protected owner-only
  token file chosen explicitly outside the archive, not an insecure default.
  No token-bearing URLs. Token entered
  in browser stays memory-only; disconnect/logout clears it.
- [ ] **Step 4 — Implement archive/revision routes** GET `/archives`,
  `/archives/{attempt_id}`, `/archives/{attempt_id}/checkpoints`; bind existing GET
  inspection router under `/archives/{attempt_id}/checkpoints/{revision}` and the
  live inspector under `/live/checkpoints/{revision}`. UI first reads status to pin
  revision, then refreshes all panels at that revision. Unknown archive/checkpoint404;
  unsupported/corrupt input409 with safe diagnostic, no automatic migration writes.
  Refactor route definitions once for reuse, keeping `create_app(engine)` behavior
  and packaged inspector default API base unchanged. New inspector API base is a
  server-generated validated prefix, never arbitrary query-provided URL.
- [ ] **Step 5 — Implement runtime UI** `/runtime` page shows live controls, last
  committed tick/revision, model/actor activity, outcomes/errors and archive list.
  Controls disable during incompatible states, show pause-requested until durable
  acknowledgment, and reuse one command ID until resolved. Historical inspector is
  fixed/read-only with clear source/time/parent/mode/checkpoint labels. Use textContent
  for model/player prose; accessible names, keyboard operation and narrow viewport.
- [ ] **Step 6 — Observe GREEN** operator+existing inspection tests; real Chrome
  scripted pause/resume/step, archive selection and malicious-text tests. Installed
  wheel must contain the three new runtime assets plus all existing eight assets.
  Exercise an actual uvicorn loopback instance, not only ASGI route mocking.
- [ ] **Step 7 — Review, root gates and commit** `feat: observe and control archived worlds in the browser`.

## LN09: Real-model acceptance, replay proof and operator handoff

**Files:**
- Create: `examples/040_live_npc_runtime.py`, `examples/manual/ollama_founders_runtime.py`, `tests/test_runtime_acceptance.py`, `docs/live_npc_runtime.md`.
- Modify: `README.md`, `docs/local_llm_setup.md`, `docs/release_checklist.md`, and common task documents.
- Slug: `live_acceptance`. No new production behavior: isolate any prerequisite defect in its owning task contract and re-review before acceptance.

**Interfaces:** executable deterministic example040 with temporary catalog and fake
provider; manual acceptance CLI uses the production RuntimeService, not a special
world engine. Arguments: `--model`, `--archive-root`, `--max-ticks`, `--resume-attempt`,
`--replay-attempt`, `--disturbance` with closed choices `none|resource_loss|work_blockage`.
Disturbance harness uses existing resource/work managers at completed boundaries;
no arbitrary Python expressions or player endpoint. Record disturbance schedule in
attempt inputs so journal replay applies identical authorized changes.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_acceptance.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing acceptance tests** complete recorded matrix/hash
  compatibility; live safe feedback/action execution; deterministic controlled
  disturbances; off-line replay; paused world cold restart; archive completeness.
  Hash fixtures are the reviewed schema12 payloads, not archive timestamps:
  success `ec4a908de25253fa56872c5b5db9cd3c7a65d640c5be5c9b0b398b3a9f78fad0`;
  stall `6fcb0e0003c59faa1eb661329ea55fbbb4ed21e297ff6cef180733e302e6ec3d`;
  failure `fd80996bb1e122cd38e9f16fcb96ad1ecccf0dd5dcb530529a59aa3806024f2f`.
- [ ] **Step 2 — Observe RED then implement example/harness** drive only public
  production interfaces. Example040 is deterministic/model-free and joins make;
  real model acceptance is opt-in and archives every attempt, including unsuccessful
  runs. Harness never injects successful decisions in place of Ollama responses.
- [ ] **Step 3 — Run real Ollama gate** inspect installed models/server; if necessary
  start a temporary owned native Ollama process within existing permissions, retain
  its exact PID/lifecycle and stop only that owned process. Podman is authorized for
  scoped testing, but do not install drivers or claim GPU use without evidence.
  Model must be installed; missing tooling/model is an explicit blocked acceptance
  gate, never a fake-transport substitute or automatic download.
- [ ] **Step 4 — Execute baseline and disturbances** report actual calls, context
  snapshots, observed feedback, ordinary gateway results, final state/outcome and
  archive IDs. Inspect resource loss/work blockage inputs and rejected stale action
  behavior. Do not require the real model to choose a fixed response or always win;
  the gate requires valid world-affecting decisions and demonstrated changed safe
  observations/offers. If no actual valid action occurs, report that gate unmet.
- [ ] **Step 5 — Prove restart and offline replay** pause actual live run, wait for
  durable acknowledgment, exit program, restart child at same checkpoint; compare
  complete initial world/cursors/memories and advance from there without duplicate
  effects. Replay completed live archive with Ollama unavailable and compare every
  committed snapshot/event/charge. Open baseline, disturbances and failed/interrupted
  attempts in actual browser inspection; prove historical DB/world preservation.
- [ ] **Step 6 — Root final gates** independent whole-branch review with scoped fixes;
  current make, separate examples, whitespace; installed wheel/entrypoint/import/
  old+new assets/API/actualserve checks on Python3.13 and installed compatibility
  on3.11. Run all recorded two-fresh/resume1/3/4 and terminal-zero-step comparisons.
  Record current counts (do not assume the previous1416), meaningful warnings and
  unresolved tooling. Verify live origin feature/task refs and unchanged main/tag/
  milestone. Preserve all requested branches, archives and owner edits.
- [ ] **Step 7 — Write requirement-to-evidence report and commit**
  `docs: validate live NPC runtime and archived restart workflow`.
  Include honest capability/limits, archive locations/IDs, controls and restart
  commands, model/performance evidence and any unmet acceptance criterion. Root alone
  decides branch readiness. Main merge/tag/publication require later owner action.

## Provider reference checked during planning

Ollama's [generate API](https://docs.ollama.com/api/generate) documents structured
format, stream and think fields; its [parameter reference](https://docs.ollama.com/modelfile)
documents num_predict, temperature and seed. The [local model list](https://docs.ollama.com/api/tags)
returns model names/digests for preflight. Implementation must test the actual
installed server; these references are not a claim of successful local inference.

## Plan self-review and handoff

Coverage: codec/compatibility LN01; atomic history/journals LN02; isolation/inputs/
ownership/mirrors LN03; safe lifecycle/publication LN04; filtered feedback LN05;
live provider/budgets/journal replay LN06; normal CLI and durable shutdown/restart
LN07; controls/history UI LN08; real acceptance/package/operator evidence LN09.
The five Review Focus conditions have explicit tests in their owning tasks.

All shared types/interfaces are defined above or named existing repository symbols.
Later tasks consume exact earlier interfaces; no task may silently alter them.
The plan specifies decisions and observable tests, not complete implementation
bodies. The journal payload schema is fixed as follows: request_started records request_id,
base_revision, source_tick, actor_label, input/config fingerprints and safe
serialize_decision_request JSON; response_validated records request_id and parsed
NPCDecision JSON; response_failed records request_id, classified code and optional
content digest; action_resolved records matching slot, accepted/rejected/no_action
and engine-only event references; candidate_aborted records base_revision/reason;
control_requested/control_resolved record CommandEnvelope/CommandReceipt;
attempt_finished records lifecycle/outcome and last revision. Unknown keys/types
fail load/append. No raw provider body or token fields are accepted.
Live cursor format1 contains schedule labels, binding fingerprint, next_tick and
next_slot (zero at a completed boundary); feedback cursor format1 contains per-holder
source-kind/source-ID last qualitative hashes and pending observable result keys.
New observations compare last qualitative hashes so unchanged facts do not create
memories every tick; source revision/provenance identifies each actual change.

Root self-review covers scope, missing spec sections, contradictions, type
names, validation ownership and task boundaries. Runtime/test changes have not begun;
no new test or real-model pass is claimed by this planning artifact.

Recommended execution: sequential bounded workers with independent task reviewers,
root-owned integration and final whole-branch review. This follows repository
practice and puts review gates around persistence, control authority and cognition
before their dependent UI and real-model acceptance. Owner plan review and execution
confirmation are next; do not execute unchecked steps from planning approval alone.

Planning verification: six documentation files and22localfilelinks checked; nine
tasks,55checkbox steps and28Modify paths checked against existing or earlier planned
files. No placeholders/conflict markers; whitespace check passed. Heading anchors
were not checked. No implementation/full-suite/live-model validation was performed
for this documentation-only planning checkpoint.
