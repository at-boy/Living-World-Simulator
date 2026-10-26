# LN08e — Shared prepared archived launch

Status: independently reviewed and root task-validated delivery; feature integration
and repeated merged gates pending.
Base: codex/live-npc-runtime e990961, reviewed/merged validated2140/10/39examples.
Goal: expose the existing RuntimeService before its blocking launch, sharing exact
launch preparation between headless run and the later local browser server.
Authority: approved live-runtime design, original LN07/LN08 execution. This task
adds no CLI command. Default paused serving is a later consumer decision.

## Ownership and scope

Python>=3.11. Preserve RuntimeService as sole world/archive owner, existing launch
composition, manager mutation, immutable events, NPC filtering and untrusted gateway
proposals. No schema, domain, provider, HTTP, parser, exports or dependency changes.
Worker may change exactly:
- src/living_world/runtime/entrypoints.py
- tests/test_runtime_launch_request.py (new)
- tests/test_runtime_cli.py (only regression coverage for this extraction)
- docs/subagent_execution_plan/live_npc_runtime/08e_prepared_launch-report.md
Root owns this task, matching saved -prombt and four common status documents.
No worker VCS/index operations, subagents, other-checkout writes, full make/examples,
installs/downloads, real model calls or unrelated cleanup. Unit temporary attempts
are allowed; normal/manual simulation attempts must remain in persistent archives.

## Exact adapter contract

In runtime.entrypoints add frozen dataclass ArchivedLaunch with service:RuntimeService
and private callable field _start:Callable[[bool],RunController], repr=False. Method
launch(*,paused:bool)->RunController delegates to that callable. No public export.
Factory prepare_archived_launch(arguments:argparse.Namespace,*,catalog:RunCatalog,
on_reserved:Callable[[AttemptRef],None])->ArchivedLaunch accepts a validated target
namespace. Copy namespace attributes defensively (parser values are immutable
primitives/Paths). Configuration/source reads and mirror cadence use existing
_requested and inherited replay cadence; do not reimplement equality/model pin rules.
Prepare returns a constructed service without launching threads, reserving attempts,
retaining inputs or contacting providers. Read-only source/config validation may fail
before returning. Caller can access the service before launch blocks in owner setup.

Returned closure uses a Lock and private used flag. Require type(paused) is bool;
invalid paused raises RuntimeCLIError(2,invalid_configuration) BEFORE consuming the
one-shot. First valid launch atomically consumes it BEFORE allocation, retention or
provider effects, even if launch fails. Subsequent or concurrent calls immediately
raise the same closed error with no second allocation/provider/source effect.
Release guard before blocking launch. No reset/retry of this adapter; provider Retry
remains the existing controller operation. Dataclass has no mutable public launch state.

Move existing live-preset materialization, config construction, reserve_setup,
AttemptLease retain_inputs, cleanup/fail_setup and RuntimeCLIError(ref) propagation
into the closure unchanged, substituting paused for hardcoded False. Keep retained
asset lifetime valid through retain, then call service.start with retained inputs.
Existing resume/fork/replay delegate unchanged with requested config/checkpoint and
paused. Save cadence remains inherited from source/config exactly as run_archived.
Do not copy owner loops or construct engines here.

## New recorded founders preparation for the later serve consumer

The same factory also accepts founders success/stall/failure (no preset/source target)
and prepares a recorded service launch through existing canonical assets. There is
no legacy headless routing change: run --founders still uses its established runner.
Use FoundersOutcome and assets.tape_for; load scenario identity with existing loader.
Settings match cli._execute: launch_source=cli, driver_format=1,
finalize_proposals=not checkpoint_only, recorded_outcome=founders, limits containing
max_ticks, continuous bool and effective save_every. Effective cadence a.save_every
or1; stall max_ticks defaults5 only when absent and not continuous, otherwise retain
caller limits. Other outcomes preserve absent max_ticks and scenario default.
No provider settings/calls for recorded paths.

Use public LegacyArchiveSession(catalog,config), manually enter, retain scenario/tape,
and direct close in finally before service.start. On successful retention no entries,
lifecycle or checkpoint are written; direct close releases preparation ownership for
RuntimeService.start. NEVER call successful __exit__, which would settle interrupted.
On entering/retaining failure, best-effort fail(initialization_failed) while handle
is usable, always close, then raise RuntimeCLIError(4,initialization_failed,ref).
Preserve ArchiveReservationError and its allocated ref when constructor fails.
Do not use private session fields, raw SQLite or add storage APIs.
Normal announcement is service on_reserved exactly once; do not call callback early
on successful retention. Preparation errors carry their ref so existing caller catch
can announce identity. A caller controls failure-reporting policy; adapter must not
invent a second fallback attempt or print. An exception in callback is still existing
service behavior. Config/materialization errors before reservation propagate for the
existing outer failure normalizer; no token/provider body in errors.

## Headless integration compatibility

run_archived constructs its catalog as before, calls factory with announce, assigns
service=prepared.service, starts existing stop watcher then prepared.launch(paused=False).
Retain its watcher readiness, control polling, wait, provider-error stop policy,
status/result fields, error mappings/ref announcement/fallback and final joins.
Preserve ordering of watcher_failed override, cancelled stop returnNone and fallback
failure identity. No shared failure-normalization refactor in this task. Existing
run/inspect CLI hooks, return values, stderr/stdout and injected engine behavior remain.
No change to finalized recorded tape behavior or terminal zero-step restarts.

## Tests and evidence

TDD: show meaningful failing tests before implementation. Test service exposed while
provider setup blocked and cooperative cancellation available (fake provider only);
paused true yields initial durable revision/tick without auto advancement, pausedFalse
runs; namespace mutation cannot alter prepared target/config; invalidpaused and
sequential/concurrent one-shot guard, including failed first launch, no duplicate
attempts/provider effects. Use events/bounded joins rather than timing-only assertions.
Recorded all3 outcomes match canonical final world/cursors, truthful lifecycle/outcome;
stall default5/explicitlimit/continuous/cadence; preparation handoff has no premature
settlement; injected retention failure leaves one inspectable failed attempt with
identity and no retained lease. Resume/fork/replay inherit config/cadence, exact child
initial world/driver/feedback cursor and source bytes unchanged. Exercise existing
headless live success/error/stop/final-mirror cases and original recorded CLI suite.
Existing helpers/fixtures may be imported but do not edit files outside scope.

Focused pytest includes new test plus test_runtime_cli.py, test_runtime_service.py,
test_runner_cli.py, test_founders_cli.py and test_runtime_preflight.py. Scoped Ruff,
Black, git diff --check. Report command/result/counts/meaningful warnings; no successful
output dumps. Worker report gives RED/GREEN evidence, changed paths, architecture,
limitations and root gates pending. Do not commit. Root performs independent read-only
review then make, separate make examples, whitespace, retained canonical26/newCLI7
and wheel11 checks on task and merged trees. Preserve task branch/worktree and owner
master-plan edit. CLIserve and actual installed-Ollama acceptance remain incomplete.

## Pre-owner cancellation amendment — root decision before correction

The new exposed service can be closed before launch or during input retention. If
service.start raises RuntimeStartupError with code service_closed AND ref is None,
no owner accepted the already prepared attempt. Settle that exact local ref under
preparation ownership, then re-raise RuntimeStartupError(local_ref,service_closed)
so the caller announces it without allocating a fallback attempt. For live preset,
use AttemptLease(local_ref) plus catalog.fail_setup(local_ref,setup_failed). For
recorded founders, reuse the same now-closed LegacyArchiveSession object: enter it,
fail(initialization_failed), always directclose. Do not construct a second session
or attempt. If settlement/close fails, raise RuntimeCLIError(4,archive_failed,local_ref)
instead, preserving physical evidence without repairs. No callback/print here.
NEVER touch/settle any service.start exception carrying an owner ref; existing owner
failure/cancellation handling remains authoritative. No changes to service internals.
Tests both modes closed before launch and a deterministic shutdown-during-retention
race: exactly one failed/inspectable attempt, closed exception carries that ref,
no controller/provider call/checkpoint, no leaked lease, one-shot remains consumed.
Existing callback/error policies and headless cancellation remain unchanged. This
amendment addresses a lifecycle gap created by exposing the service before launch.

Recorded preparation close clarification: the FIRST direct session.close after
retention (including finally after enter/retain failure) must also preserve identity.
If it raises, normalize RuntimeCLIError(4,archive_failed,session.ref), overriding the
less severe initialization failure if needed, and never call service.start. Preserve
physical evidence; no repair/re-reservation. Established close releases what it can;
do not claim successful lease cleanup when close itself failed. Add injected close
failure tests after successful retention and masking a retention failure, with exact
ref and one attempt/no controller/provider. No broader failure-normalization refactor.
