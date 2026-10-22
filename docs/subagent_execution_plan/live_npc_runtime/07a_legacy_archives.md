# LN07a — Automatically archive existing CLI runs without breaking compatibility

Status: owner-authorized bounded producer stage of original LN07, after reviewed
LN06 integration2da047f. LN07a archives existing CLI invocation forms; LN07b then
adds controller-owned live/service/resume/replay/browser-serving entrypoints. Task7
is not complete until both stages and aggregate acceptance. No actual provider call.

## Goal and architectural decision

Every existing CLI run (generic no-tape, generic tape, canonical path or founders
alias, raw SQLite continuation) saves independent complete checkpoints for later
analysis. Preserve ScenarioRunner, its engine/state reference, stop/finalization
precedence and existing mirror cadence; do not copy its loop or replace it with
per-tick detached reconstruction. An optional typed observer records archive
boundaries on the SAME owner thread. New live/controller service remains LN07b.

Python>=3.11, strict types/Protocols/dataclasses, existing managers/systems/immutable
events and NPC information boundaries. No world schema/SQLite schema/dependency/
provider/model/download/browser/main/tag/milestone changes. Schema12 writes/1–12
reads and all exact recorded world payloads stay unchanged. Retain all branches,
worktrees, owner-local master plan edit and current-plan SDD evidence.

## Exact allowed worker files

Create src/living_world/runtime/legacy.py, tests/test_runtime_legacy.py,
tests/conftest.py. Modify src/living_world/running/runner.py,
src/living_world/running/__init__.py, src/living_world/runtime/__init__.py,
src/living_world/cli.py, src/living_world/archives/model.py,
tests/test_runner_cli.py, tests/test_founders_cli.py, docs/canonical_founders.md,
and this task's -report.md. These12 worker paths only. Root owns plan/prompt/common
docs/VCS. No controller, archive store/catalog/assets, recorded/live driver, domain,
HTTP, inspection, packaging or other tests/source edits. Root amends before expansion.

## Runner observer producer seam

Define and export RunObserver Protocol from running:
- initialized(engine:SimulationEngine,scenario:LoadedScenario)->None
- tick_completed(engine:SimulationEngine)->None
- finished(engine:SimulationEngine,result:RunResult)->None

ScenarioRunner.run adds OPTIONAL keyword observer:RunObserver|None=None, preserving
all old calls/no-observer behavior. Validate callable methods before mutation.
Call initialized after scenario load, preparation and failed-tick/replay checks,
before evaluating stop/terminal/tick bound. Call tick_completed immediately after
one successful engine.step (tick complete), before terminal evaluation/checkpointing.
Never call after failed/poisoned/partial step. Call finished only after successful
preparation.finish and final RunResult.proposals_finalized calculation, immediately
before final _save. Existing checkpoint cadence, terminal/stop priority, finalization,
exceptions and stdout result remain unchanged. Callbacks never invoke another step,
replace engine/state, mutate world or become NPC context.

Observer exception is RunPersistenceError (chain safe original), not simulation
success; archive cannot be silently skipped. A failed _save never rolls archive back.
No observer API changes to domain SimulationEngine or repositories. Direct programmatic
ScenarioRunner without observer remains unarchived and unchanged; scope is normal CLI.

## LegacyArchiveSession ownership and archive cursor

In runtime/legacy.py define/export LegacyArchiveSession(catalog:RunCatalog,
config:AttemptConfig), context manager + RunObserver. Constructor reserves attempt
only, exposing ref:AttemptRef immediately; no engine/setup yet. Enter acquires its
AttemptLease and opens writable archive on current thread. Close/exit releases archive
then lease, including failed enter. No background thread/process. Methods:
- retain(scenario_path:Path,*,tape_path:Path|None)->RetainedInputs, using retain_inputs;
- observer initialized/tick_completed/finished as above;
- succeed(result:RunResult)->None after runner returns (mirror succeeded);
- fail(reason:str)->None, fixed code vocabulary legacy_run_failed/initialization_failed/
  interrupted; default exception exit records legacy_run_failed. No raw exception text.
- archive property:AttemptArchive only while entered; read-only last_revision:int|None.

Archive config mode recorded, launch_source cli, driver_format1. Add OPTIONAL
finalize_proposals:boolean to AttemptConfig.settings closed allowlist ONLY for recorded
mode. Missing legacy value meansTrue. Reject nonboolean or presence in other modes.
No SQL/archive format change. New CLI explicitly records not --checkpoint-only here;
max_ticks/save_every use existing limits fields, recorded_outcome when an alias exists.
software_revision uses existing living_world.__version__, never shell git calls.

Cursor exact closed semantic object (export legacy_cursor(engine)->Mapping[str,object]):
{format:1,mode:'legacy_recorded',scenario_fingerprint:<run_metadata.configuration_fingerprint>,
 next_tick:<state.tick>,tape_fingerprint:<replay_binding.tape_fingerprint or null>,
 next_index:<replay_state.next_index or null>}.
Validate run/scenario/seed binding and replay state, no operational IDs/time/counts.
feedback_cursor is {}. Existing replay events/cursors in world remain authoritative;
no invented HTTP request/response/action journal rows for legacy tape execution.

initialized commits initial complete prepared world (even tick>0 raw DB resume),
tick_completed commits EVERY complete tick regardless save_every, finished commits
post-finalization world/cursor if changed. Deduplicate identical snapshot/cursors;
finalization-only same-tick revision is allowed, no tick/action fabrication. Use exact
encode_world and atomic AttemptArchive.commit. Validate initialized config identity
before publication. Never archive state from a failed step or failed finalization.
If terminal predicate fails after a successful tick, that complete tick remains
archived; legacy mirror semantics are unchanged.

succeed records attempt_finished and lifecycle completed, or stopped for operator_stop
(including matching terminal operator_stop); last_revision exact. Failure records
failed lifecycle/attempt_finished at last complete revision (None before initialworld),
and candidate_aborted with last revision only for an initialized UNFINISHED runner
candidate. Track successful observer.finished; a subsequent mirror failure has a
complete final archived world and must NOT add candidate_aborted. Earlier failed
step/terminal/finalization candidates may be discarded from their last complete base.
Do not falsely claim failed attempted tick committed. Normal context exit without
succeed/fail records interrupted. Settlement idempotent in this session. Cleanup or
audit failure must not hide original exception; if no prior failure, propagate as
archive/persistence failure. No hidden fallback/no automatic deletion.

## CLI integration and error behavior

Add --archive-root PATH to run only in this stage. None resolves RunCatalog.default_root
at execution. Preserve all old selectors/flags/defaults, build_parser/main public
hooks and exact stdout. Inspect remains read-only, no new attempt and no archive writes.
Parser-invalid selectors/arguments are not started simulation attempts; preserve early
SystemExit2 with no database/archive side effects.

After syntactic validation, preliminarily load/validate scenario only enough to obtain
existing LoadedScenario identity (full existing loader, no duplicate parser). Reserve
LegacyArchiveSession BEFORE engine_factory/scenario execution/preparation. Emit one
stderr line attempt=<id> archive=<absolute attempt directory> immediately after reserve,
including later failures. Retain immutable scenario/definitions/tape; execute with the
returned retained paths, reload their scenario for classification/preparation, preserve
exact bindings/payloads. Engine_factory still receives the actual SQLiteRepository
for --database and is called exactly once, on the invoking thread. stop_control still
sees original mutable engine state. No live mode inferred from database.

If scenario loading/asset/tape validation fails before actual identity is known,
reserve one metadata-only failed recorded attempt with scenario_key='uninitialized',
seed0, software_revision current version, launch_source cli and no inputs/checkpoint.
Display it and preserve ORIGINAL configuration/compatibility exit classification.
No raw malformed bytes/exception text in journal/settings. If reservation/archive fails,
return4, identifying attempt if one was reserved. Never reserve a second attempt for
an error after a real attempt already exists. No attempt for inspect or parser error.

Use observer for runner, then session.succeed only after final runner mirror save.
Catch ArchiveError/OSError from archive work as persistence4; retain current domain/
configuration mappings2/3/4/5, including custom engine failing step5. stderr may add
archive-authoritative revision on mirror failure, never claim mirror caught up. Older
raw DB continuation remains independent new attempt (no guessed parent); archive-based
linked resume belongs LN07b. --database/defaultworld.sqlite3 retains old mirror behavior,
--save-every cadence unchanged. --checkpoint-only/finalized metadata exact.

## Tests, docs and boundaries

Add autouse fixture in NEW tests/conftest.py setting XDG_STATE_HOME to tmp_path-owned
location via monkeypatch for each unit test. Existing explicit archive roots/custom
XDG tests may override it normally. Inherited subprocesses use this temporary unit
root; do not globally mock production defaults or disable archiving. Normal manual/
CLI/agent acceptance remains persistent. Root canonical helper will explicitly retain
archives alongside its persistent evidence directory.

TDD baseline existing runner/founders CLI and recorded regressions. Genuine RED for
missing observer/session/configflag/CLIarchives, then GREEN vertical slices. Required
regressions: all3 canonical outcomes archived complete ticks+exact payloads; generic
no-tape and generic tape; rawDB resume tick>0; default/mirror cadence/checkpoint-only;
custom factory one call and retained-state StopControl; preinitial setup failure and
missing/invalid scenario discoverable; failed partial step/terminal predicate/finalizer
boundary; archive-first mirror failure; lease released on every failure/normal exit;
metadata strict bool/mode/legacy missing flag; parser/inspect no writes; old stdout/
exitcodes2/3/4/5; no uvicorn import in run; no live provider in make. Do not weaken old
assertions or add test-only production escape hatches.

Focused final: PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_legacy.py
 tests/test_runner_cli.py tests/test_founders_cli.py tests/test_recorded_proposal_tapes.py
 tests/test_canonical_founders.py -q. Smallest relevant tests during corrections.
Scoped Ruff/Black/whitespace. Report true commands/counts/RED/GREEN/warnings, boundary,
selfreview/limitations. Worker no VCS/subagents/fullmake/examples/dependency operations.
Root independent review, task+merged make/separateexamples/whitespace and exact recorded
matrices precede commits/integration. LN07a alone does not claim new live/service/
archive-resume/replay/serve/browser capabilities or original Task7 completion.
