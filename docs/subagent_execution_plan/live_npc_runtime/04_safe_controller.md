# Task 4 / LN04 — Single-owner safe controller

Status: owner-authorized; decision-complete contract from reviewed integration5544fdb.
[Design](../../superpowers/specs/2026-10-19-live-npc-runtime-design.md) and
[master plan](../../superpowers/plans/2026-10-19-live-npc-runtime.md) bind this task.

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


## Root-resolved controller and producer contract

LN01–LN03 are reviewed/integrated. This task creates the model-free controller and
recorded adapter; no Ollama, CLI, HTTP or browser behavior. No world/schema/dependency
changes. Existing recorded canonical rows remain exact. Runner remains unchanged;
its optional extraction is unnecessary for this fixed recorded composition.

### Explicit producer corrections and protocol amendments

1. Add optional exact-nonnegative-int admitted_state_version to the closed
   control_requested payload beside envelope. Legacy entries lacking it retain
   prior expected_state_version interpretation. New controller ALWAYS supplies
   its actual current state_version. Queued CommandReceipt.state_version and
   load-side replay use this admission version, never an untrusted future client
   expected version. Existing monotonic settlement checks remain relative to the
   actual queued version. A fresh future/stale envelope is durably requested then
   rejected with current version; it cannot increase controller version or block
   settlement. No SQL schema change; update model/store and focused regressions.
2. Recorded AttemptConfig.settings.limits.max_ticks permits exact int0 (and None),
   matching preserved RunConfiguration zero-tick requests. Other modes/positive
   limits remain positive; bool is always rejected. Preserve existing assertions;
   tell root before changing any old assertion that explicitly contradicts this.
3. Extend TickDriver with synchronous model-free initialize(candidate:SimulationEngine,
   archive:AttemptArchive)->DriverCommit. Called ONLY to establish an absent initial
   checkpoint, before first model request; obtains explicit driver/feedback identity.
   Existing checkpoint restoration consumes its saved cursors, never resets them.
4. TickPreparation.poll additionally permits 'paused'. request_pause latches no-new-IO
   intent; after its bounded current request is accounted for, poll returns paused
   even when later actor slots remain unrequested. ready alone cannot represent this
   partial preparation boundary. Add read-only activity:str|None and error_code:str|None
   properties for classified operational publication. All future LN05/LN06 drivers
   implement this amended protocol; fake implementations remain tests only.

The above supersede incomplete original seams. All other exact interfaces stand.

### Public records, ownership and construction

contracts.py owns RuntimeState str Enum with exact values initializing, paused,
running, awaiting_model, pause_requested, provider_error_paused, stepping, completed,
stopped, failed, interrupted; terminal completed/stopped/failed/interrupted. Frozen
RuntimeStatus(attempt,state,state_version,revision,tick,activity,error_code), frozen
DriverCommit(driver_cursor,feedback_cursor,journal_entries), ScenarioComposition,
TickDriver and TickPreparation Protocols. RuntimeStatus fields: attempt:AttemptRef,
state:RuntimeState, state_version:int, revision:int|None, tick:int|None,
activity:str|None, error_code:str|None. DriverCommit fields: driver_cursor:Mapping[str,object],
feedback_cursor:Mapping[str,object], journal_entries:tuple[JournalEntry,...].
Deep-freeze cursor documents through the
existing finite-JSON helpers; journal_entries exact tuple of JournalEntry. Validate
all constructors: exact nonnegative ints, nullable checkpoint/tick together,
short nonempty activity/code strings or None, expected Enum/reference types.

RunController requires a valid writable archive created/opened by the current owner
thread; for catalog attempts caller already holds AttemptLease for its lifetime.
Controller does not acquire/release caller's lease. submit/poll/close require the
creating thread; status/published return immutable cached values safely to readers.
Never expose candidate/engine/writer connections through those read methods.
max_ticks is None or exact nonnegative int (0 immediate bound), start_paused exactbool.
No constructor simulation/IO beyond argument validation. Initial status initializing,
state_version0, revision/tick None. First poll performs composition.initialize if no
checkpoint, otherwise restore(saved snapshot); initialize driver only for no checkpoint.
Commit complete initial world/cursors before publishing or acknowledging init Pause.
Restoration must not introduce extra domain mutations: compare canonical encodes of
restored world and decoded saved world (legacy source bytes remain published as saved).

publication.py owns a lock-protected immutable status/current-checkpoint publication
and at most8 complete cached checkpoints. publication updates status+checkpoint as one
operation. Separate operational state transitions retain the same durable revision.
published(None) returns last checkpoint, unknown/evicted revision raises LookupError;
no read-side archive IO. LN08 will resolve evicted history through a separate read-only
catalog. Never hold publication lock across model prep, engine step or archive IO.

### Admission, versions, results and idempotence

Archive command rows/journal are authoritative; in-memory queue owns dispatch only.
Validate known ID with exact canonical envelope before stale/lifecycle checks: identical
repeat returns existing queued/applied/rejected receipt, never queues twice or changes
state. Divergent reuse raises exported CommandConflictError(ValueError); original
immutable envelope/result remain unchanged. Malformed/conflicting protocol envelopes
are not admitted commands. Every fresh well-formed envelope, including rejected stale/
future/lifecycle commands, gets control_requested with admitted_state_version and
control_resolved if rejected. Nonstepping settlement + lifecycle uses one record txn.

state_version changes on accepted lifecycle/intent transitions and complete publication,
not on duplicate/no-op status reads or rejected inputs. Reject a fresh envelope unless
expected_state_version equals the current version at admission. Revalidate that equality
and lifecycle at queue dispatch too: two queued Step envelopes with the same version
cannot both execute after the first returns to paused. No queued step credits.
Fresh valid commands are admitted queued; poll dispatches in FIFO order before starting
new work. One Step can remain pending across provider error/retry; store applied Step
receipt ONLY with its one completed checkpoint, receipt.revision=new revision.
Use short reasons: stale_state_version, lifecycle_conflict, terminal_attempt,
provider_retry_required, operator_paused, operator_stopped, initialization_failed.

Use original transition table. initializing pause/stop latch intent and settle only
after durable initial checkpoint or classified setup failure; other initializing
commands reject. paused resume enters running; paused step enters stepping. A Pause
while preparing latches pause_requested, calls preparation.request_pause, schedules
no new IO/ticks, then waits through nonblocking polls for paused/ready/provider_error.
Before engine.step begins, cancel any unapplied Step receipt as rejected operator_paused;
no domain tick advanced. Pause success acknowledges complete existing checkpoint and
settled controls, then healthy paused or provider_error_paused if the call failed.
Once synchronous engine.step began, finish/commit its complete boundary before any
later command dispatch. A Step then settles applied exactly once; later Pause rejects stale_state_version
if its version is stale, otherwise lifecycle_conflict in already-paused state. Never interrupt a mutating tick.

Provider error retains prior durable publication, discards candidate, closes owned
preparation and enters provider_error_paused with error_code. Preserve interrupted
intent (running, step command ID, or paused after explicit Pause). retry starts a new
preparation request attempt from same durable boundary, preserving journal responses;
its receipt settles when scheduling retry. A retained Step still commits only one tick.
A paused retry only prepares/cache-validates a response and returns paused without a
tick. No provider retry is automatic. Resume/Step in provider_error_paused reject.
Stop only allowed by original table, finalizes at prior durable boundary, rejects any
unapplied Step as operator_stopped, closes preparation and persists stopped result.
All unlisted pairs reject; terminal states reject mutation. close is idempotent owned
shutdown: discard unpublished candidate, settle pending controls where persistence
works, finalize safe stop if nonterminal, close archive/preparation; caller releases lease.

### Tick transaction and failures

poll does at most bounded owner work and never waits on provider IO. Stage by restoring
last durable snapshot with composition, then driver.prepare. Waiting only publishes
operational activity. When ready (and no pending pause/stop), install proposal system,
execute exactly one existing engine.step, evaluate terminal once at the boundary,
finalize when terminal or max_ticks reached, encode, commit world/cursors/outcomes and
Step receipt in one archive txn. State tick must increase by exactly1; max_ticks counts
this attempt's completed ticks from its initial saved tick. Parent/offline time never
counts. No extra observations, goals, work or events in recorded mode.

Record last lifecycle and publish only after the durable world commit. A pre-commit
validation/step/encode/commit exception quarantines/discards candidate, preserves prior
world/publication, and terminates failed with a short classified code; attempt_finished
records failure against last durable revision if storage still works. No automatic
persistence retry. Provider errors follow recoverable path above instead of failed.

Post-commit operational/audit failure is distinct: committed world/Step receipt cannot
be rolled back. Publish that newly durable checkpoint with failed status and safe
audit_failed code, exposing its real revision; do not pretend the archive stayed at
its prior revision. This explicit rule supersedes the blanket plan 'any exception
retains previous publication' only after a successful complete SQL commit. Test this
boundary so restart never repeats a committed step or hides an archive-ahead state.

Terminal detection occurs at initial saved boundary and after each completed tick,
using composition. A saved terminal world advances zero ticks. Finalization must not
change a successful domain world into failure. State transitions/outcomes/clock and
archive IDs remain outside WorldState. No runner/manager mutation from other threads.

### Recorded production composition and driver

recorded.py exposes SnapshotRepository(snapshot) with detached decode load and save
always RepositorySaveError, plus RecordedFoundersComposition(inputs:RetainedInputs,
*,finalize_proposals:bool=True) and RecordedTickDriver(). Composition.initialize starts
an empty engine via SnapshotRepository and existing load_scenario/FoundersPreparation;
restore uses saved snapshot then same existing idempotent setup/preparation. Restore
resource vocabulary and domain/proposal systems in existing order. Keep one ephemeral
preparation per engine; do not share candidate engines. Tape required and loaded via
existing YAMLProposalTapeLoader, retained input hashes validated at construction.

terminal_condition uses founders_terminal_conditions in configured scenario order,
strict bool results; no model claims. finalize wraps FoundersPreparation.finish with
real RunResult/StopReason semantics: stopped uses OPERATOR_STOP, matched terminal uses
TERMINAL_CONDITION, otherwise TICK_LIMIT; preserve finalize_proposals=False for future
legacy checkpoint-only CLI. Track the attempt initial tick once, never reset on each
restore. Generic scenario authoring is not implemented here.

Recorded driver initialize produces explicit cursor {format:1, mode:'recorded',
tape_fingerprint:<binding>, next_index:<replay state>, next_tick:<world tick>},
feedback_cursor={}. prepare validates saved cursor against world binding/current
replay progress and returns immediately ready; install preserves existing proposal
system (no new observations/clients), finish_tick returns next exact cursor and no
additional journal outcomes (existing immutable replay resolution events are in world).
Pause immediately yields paused, activity/error None; close no-op. No tape finalization
on mere pause; terminal/limit/stop finalization uses composition only.

### Focused tests and file boundary

Tests must exercise real archived/controller/recorded integration, deterministic fake
waiting preparations and injection-only failures via test classes, no product switches.
Cover deferred init/latches, explicit initial cursor, exact child restoration, max0,
future/stale IDs with truthful receipt version, duplicate/changed-body requests, queued
stale Step, successful Step receipt/checkpoint atomicity, pause before tick vs completed
tick, provider error/retry preserving Step/paused intent, bounded fake waiting responsiveness,
owner/read thread safety, failed/partial tick quarantine, precommit rollback, postcommit
audit failure, terminal zero-step, finalization modes and cached eviction.
Compare old complete schema12 hashes, actual events/charges, fresh versus child-resumed
world/cursor/history. Include real subprocess paused checkpoint->exit->fork/reopen proof.

Worker creates runtime/__init__.py, contracts.py, controller.py, recorded.py,
publication.py under src/living_world, tests/test_runtime_controller.py,
tests/test_runtime_recorded.py; modifies archives/model.py, archives/store.py and
 tests/test_run_archive_store.py ONLY for the two explicit producer corrections above;
updates only04_safe_controller-report.md. Existing runner/replay/founders code and
assertions preserved. Root task/prompt amended before any further scope expansion.
Root common docs are this task's three artifacts, index, changelog/journal/backlog/
continuation. No worker VCS/subagents/full gates. Root independent review and current
make/separate examples/whitespace/canonical CLI on final task and merged trees required.
