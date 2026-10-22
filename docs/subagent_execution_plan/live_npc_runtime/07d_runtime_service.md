# LN07d — Owner-thread runtime service and exact restart

Status: authorized bounded service stage after reviewed LN07c integration d782e20;
implementation independently reviewed and task-validated; integration gates next.
Original Task7 incomplete until service/CLI/serve acceptance.
Spec: docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md, original LN07.
Existing LN01–07c contracts remain binding. Python>=3.11, strict types, no dependency/
world/SQL/schema change. Managers mutate, systems behave, immutable events; NPC
feedback/context/gateway rules unchanged. No CLI/browser/player/serve implementation.

## Goal and file boundary

Provide one owner thread for archive/composition/driver/controller lifecycle, exact
new/resume/fork/replay construction, thread-safe commands and bounded cleanup. Keep
recorded CLI aliases/runner/hooks unchanged; CLI consumers follow in LN07e.

Exact17workerpaths:
- src/living_world/runtime/service.py (new ownerthread/queue/public service/loop)
- src/living_world/runtime/launch.py (new internal construction/resource owner below)
- tests/test_runtime_service.py (new)
- tests/test_runtime_restart.py (new)
- src/living_world/runtime/recorded.py
- src/living_world/runtime/ollama_driver.py
- src/living_world/runtime/feedback.py
- src/living_world/runtime/controller.py
- src/living_world/runtime/__init__.py
- src/living_world/archives/model.py (only recordedlimits.continuous)
- src/living_world/runtime/journal_replay.py
- tests/test_runtime_recorded.py
- tests/test_runtime_ollama_driver.py
- tests/test_runtime_controller.py
- tests/test_runtime_founders_feedback.py
- tests/test_runtime_journal_replay.py
- docs/subagent_execution_plan/live_npc_runtime/07d_runtime_service-report.md

No catalog/assets/store/lease/CLI/domain/protocol/packaging changes. Root amends
exactplan and prompt BEFORE any scope expansion. Root owns common docs/VCS.

Keep service queue/thread coordination separate from mode construction. Internal
launch.py owns RuntimeStartupError and _LaunchFactory(catalog,cancel_event,on_reserved),
with start/resume/fork/replay methods corresponding to public service launch arguments.
They run only on owner and return private dataclass _Launch(ref,archive,composition,
driver,max_ticks,stack:ExitStack), with close() releasing owned stack on owner.
Factory owns reserve/retain/preflight/open/restore/validation/composition construction
and startup failure settlement; service creates controller from bundle, owns loop/
mirror/commands/finalclose. No engine/lease/resource crosses owner boundary. Public
RuntimeStartupError re-exported by service/runtime, other launch types stay private.
Use existing ScenarioComposition/TickDriver protocols for bundle fields; concrete
driver types expose pure startup validation inside factory. No generic plugin factory
or runtime architecture replacement; just separate these two coherent responsibilities.

## API and owner rules

RuntimeService(catalog:RunCatalog,*,on_reserved:Callable[[AttemptRef],None]|None=None,
mirror_path:Path|None=None,save_every:int=1). One launch per instance.
start(config:AttemptConfig,inputs:RetainedInputs,*,paused:bool)->RunController
resume(attempt_id:str,revision:int|None=None,*,paused:bool)->RunController
fork(attempt_id:str,revision:int|None=None,*,config:AttemptConfig,paused:bool)->RunController
replay(attempt_id:str,revision:int|None=None,*,paused:bool)->RunController
submit(command:CommandEnvelope)->concurrent.futures.Future[CommandReceipt]
shutdown(*,failure_code:str|None=None)->None
run_owner_loop(controller:RunController,*,stop_event:threading.Event)->None
RuntimeStartupError(ref:AttemptRef|None,code:str) exposes safe fixed code and identity.
Closed codes: SETUP_CODES, broker.ERROR_CODES, invalid_configuration, incompatible_save,
archive_failed, initialization_failed, service_closed, service_not_ready, service_failed,
mirror_failed. Preflight preserves safeProviderPreflightErrorcode; archive IO ->
archive_failed; scenario/tape/source semantic incompatibility ->incompatible_save;
bad public argument/config ->invalid_configuration; firstcontrollerpoll failed ->
its initialization_failed; callback/unexpectedlocalfailure ->setup_failed or
service_failed. No rawexceptionmessage/providerprose. ArgumentsyntaxTypeError/ValueError
may fail before thread/attempt; afterallocation alwaysref on startup error.
Inownerfinally catch BaseException to settle startup/pending Futures and release
resources, withsafe service_failed/cancelled mapping; no uncaught threadtraceback.
Public catalog property provides original catalog for read-only operator composition.
No mutable engine/composition/broker is exposed. Returned controller supports
only its existing thread-safe status/published from caller; owner-only APIs still fail.

Each launch claims service once, starts one owned non-daemon thread; lease/writable
archive/composition/broker/controller created, operated and closed only there. Launch
blocks until first initialized published status (paused/running/terminal), or raises
safe startup error. No lock held while waiting startup Future/join/callback/provider;
shutdown may run on caller while launch blocks. Detect duplicate launch/shutdown-first
without allocating another attempt. Validate public argument types before spawning.

Submit before startup resolves returns a completed Future with fixed service_not_ready
exception; shutdown can always cancel setup. Once controller is ready, owner queue
and Futures resolve once by controller.submit on owner, never caller. Queue is FIFO; cancelled
Future is skipped safely; controller conflict exceptions stay on that Future without
killing service. A queued receipt is NOT an applied pause acknowledgment. Source of
durable applied/rejected receipt remains archive.command. Drain pending Futures to
fixed service-closed exception on teardown; no hanging Future, droppedacceptedcommand
or out-of-thread controller mutation. Keep owner alive idle after terminal until
shutdown so terminal rejections/idempotent command receipts work.

Use shared small bounded Event waits (<=0.02s while active, <=0.05s idle), no busy
loop. Every iteration processes queue then at most one controller.poll. Standalone
run_owner_loop polls identically without service queue until stop_event, closes in
finally; service may share a private loop helper with a queue pump, no duplicated
engine/runner loop. shutdown is idempotent and sets parent-only preflight cancellation
Event plus owner-stop/wakeup; join owned thread with timeout bounded by preflight
worker cleanup plus small polling/SQLite allowance (5seconds). Owner shutdown call
never self-joins. If owner fails to exit within the deadline, raise fixed service_failed
and retain owned thread/ref/stop intent for later join; never report successful
shutdown or abandon ownership while it is alive. Normal/failure/cancel paths must
leave no owned provider/thread/lease after successful shutdown. Trusted callbacks
are application code, not sandboxed; tests release an intentionally blocked callback
after timeout and confirm a subsequent join succeeds. No server control.

## New start and linked construction

start consumes SAME alreadyreserved attempt owning RetainedInputs, not a new attempt.
Derive private input tree/ref using existing RetainedInputs path/hash-role rules;
validate fixed ref layout belongs to catalog root and exact load_retained_inputs
paths/hashes. Reject foreign/unbound inputs/config mismatch. Ollama requires matching
pending setup intent; recorded requires matching ordinary reserved config and empty
archive. Caller reserves+retains before start. on_reserved executes owner once after
identity validation and before providerIO; callback error -> setup_failed.
Do not mark or mutate a foreign, alreadyinitialized/terminal/failed attempt or a
configuration-mismatched supplied input reservation while rejecting start. Failure
settlement begins only after matching pending/empty intent+inputs+lease are accepted.
Preserve mismatched existing attempt bytes and expose safe ref/error truthfully.

New Ollama: owner lease, validated inputs; preflight_provider(requested,cancel_event=
service_event); complete_setup then writable open; FoundersLiveComposition +
FoundersFeedback(exact fullbuild_payload length) +OllamaTickDriver(config,broker).
Use provider_config/client_for/encoded_body defaults/cap exactly, never duplicate.
No world mutation before preflight/initial persistence. New recorded: optional tape
selects composition below; no HTTP/client construction. Live max_ticks uses declared
limits.max_ticks (missing default20), None unbounded, max0 forbidden by existing model.
Recorded resolves RunConfiguration semantics: continuousTrue unbounded, otherwise
max_ticks numeric or scenario.default_max_ticks if missing/None. Do not rewriteconfig.
Add strict optional limits.continuous recorded-only boolean to AttemptConfig, default
False when missing; True requires max_ticks absent/None, false preserves oldvalidation.
Other modes reject continuouskey, all other limits retain existing strict behavior.
No SQL/world/configformat bump; old rawNone now has deterministic default behavior.

resume: source mode recorded/ollama/journal_replay; changed options unavailable.
Live reserve_fork_setup(source,revision,requested=None), invoke callback before GET.
Resolve actual captured source pair from catalog pending summary, not fresh latest.
Under owner lease validate restored source snapshot/cursors BEFORE terminal check
and before complete_setup. Healthy nonterminal uses pinned preflight; terminal plain
resume uses exact alreadyresolved source config without GET/generation. Then complete
child clone, open writable and validate child before controller construction. Inexact
legacy live provider metadata without resolved digest may not skip preflight.

Explicit Ollama fork same producer path with providedconfig; always preflight even
terminal when model identity changed, never generation at terminal. Config change
invalidates reuse by existing effective fingerprint; initial child world/cursors stay
exact source. Recorded fork uses ordinary catalog.fork; same mode/scenario/seed,
software and non-limitsettings unchanged, onlylimitsmaychange. Resume preserves
archived finalization flag, missing meansTrue. Never recorded->live. All source trees
remain byte-identical. On recorded revisionNone choose one source.fork_point and pass
selected revision to ordinaryfork; service owns capturedsource reference until setup.
Recorded cp0 is an immutable source copy before semantic validation; validate child
before controller state publication. If semantic validation fails, mark linked child
failed at copiedcp0, retain evidence and never step/publish a readycontroller.

Semantic startup validation rejects world/cursor mismatch even terminal/max0. Add
public pure validate_checkpoint(candidate,base,archive)->None on recorded and Ollama
drivers. Ollama factors current prepare's provider/binding/world/cursor/parent checks;
feedback.validate_checkpoint(candidate,base) validates closed cursor+provenance only,
NO _observe/initialize/prepare or candidate mutation. Existing prepare calls these
then stages feedback as before. Changedconfig sealedchild exception remains exact.
Service checks restored source with sourceconfig, then child with effectiveconfig;
startup must not use tickprepare or generate requests to validate. It may validate
semantic cursors against recordedsource independently of upcomingproviderchanges;
changedconfigurationexception only applies to the exactsealednewchild. No mandatory
TickDriver protocol change or existing fake driver changes.

## Generic recorded composition

Add RecordedScenarioComposition(inputs,*,finalize_proposals=True,max_ticks:int|None=None) supports no tape,
generic ReplayPreparation and canonical FoundersPreparation. Exact canonical rule:
scenario.key==canonical_founders_v1 OR entityattributescontainsfounders_policy;
FoundersPolicy validation and tape required for canonical. Keep existing strict
RecordedFoundersComposition wrapper public behavior and weakproxy/cache collection.

Hash-check all present inputroles, construct SnapshotRepository, load_scenario and
correct preparation; failedtick/replay guards same as runner. No tape with stored
replaybinding fails missing_replay_preparation. Validate ALL scenario terminal names
upfront; genericonlytick_limit/operator_stop, canonicalalsoexistingcustompredicates.
No new custompredicateextension or arbitrary runtime objects in config. Restore
world exact; preparation.finish(existingRunResult,archivedfinalizeflag), notape no-op.
No copying runner loop or changing old runner/CLI injected state references.

RecordedTickDriver(*,cursor_kind:Literal[recorded,legacy_recorded]=recorded) uses
existing _cursor or legacy_cursor, never translates savedcursor. Nonlegacy recorded
requires tape; legacy supports no tape. validate_checkpoint compares cursorcanonical
exact and feedback{}; fresh initialize returns same selectedkind. Resume chooseskind
from source closed cursor; reject unknownkind/shape. New start uses legacy_recorded
for no tape and recorded for tapedservice runs. Existing recorded tests unchanged.

Old legacy limits.max_ticks=None did not record continuous intent. Missingcontinuous
resolves False/default, preserving historical default commands; newexplicitrecorded
fork can use continuousTrue. Document inability to recover the unrecorded historical
continuous preference, preserving exact world/cursors; no invented originalintent.

## Controller stop/terminal/budget and failures

Add optional initial_stop_precedes_terminal:bool=False constructor keyword. Service
setsTrue for recorded; existing direct caller default unchanged. On initialqueuedstop
withpolicyTrue, skipcustomterminal/max0 precedence, finalize(stopped=True), publish
STOPPED withoutstep; canonicalstrictfinalization semantics otherwise unchanged.
Posttick custompredicate ordering unchanged. New RecordedScenarioComposition stores
initialtick on firstcompose, evaluates custompredicates first, then may return
tick_limit when delta>0, resolvedmax reached and tick_limit is selected in scenario.
Controller already handles max withoutselectedbuiltin; initialmax0 remains ordinary
TICK_LIMIT result, not namedterminal (same legacy preloop semantics). Store selected
terminal per candidate for preparation.finish. Stop commands run before a nexttick,
so use OPERATOR_STOP/terminalNone; old CLIposttick StopControl ordering remains on
its unchanged runner. Strict RecordedFoundersComposition wrapper keeps max_ticks=None
default, preserving current direct adapter behavior and all exact payloads.
Shutdown before firstpoll submits internal stop envelope on owner thenclose, so
recorded initialstop policy applies without provider/tick work.

Add owneronly controller.stop_for_budget(): only when PROVIDER_ERROR_PAUSED with
request_budget_exhausted; discard unfinishedcandidate then stop/finalize committed
world with fixed reason=request_budget_exhausted in attempt_finished AND last
lifecycle row. No fabricated game terminal/success, no retry/generation. Service
automatically applies this after polling thatbudget state; other providererrors
remain provider-error-paused until explicit Retry/Stop/shutdown.

Add owneronly controller.fail_service(code:str) restricted to fixed broker/provider
codes plus mirror_failed/service_failed, invokesexisting_fail withlatestcheckpoint.
shutdown(failure_code=...) validatesclosedcode beforequeue andfails nonterminal
controller beforeclose; normalshutdownusesexistingcloseStop. HeadlessCLI lateruses
this forproviderfailure exit6; browsernormalStopremainsStop. Fresh setup failure
beforeSQLite usesfail_setup withsafeexistingcode; afterarchivecreation beforecontroller
recordfailedattempt_finished atlatestrevision orNone andclose; partialpublication
neverrepair/reconfigure. RuntimeStartupError alwaysincludesallocatedref ifknown.

Mirroring: optional explicit path; write_checkpoint_mirror AFTER archivecommit,
initial/final plus every save_every completedticks relative to childinitialtick,
no duplicate write for operational same-tick revisions exceptfinalboundary. Mirror
error fails service atlatestcommittedcp withmirror_failed, archiveaheadtruthful.
No fabricatedrollback, overwritingarchivefiles or defaultworld.sqlite3 in service.

## Replay construction

replay accepts Ollama source only, captures oneForkPoint. Build replayconfig mode
journal_replay,sameidentity/seed/software, source_config_fingerprint fromsource,
launch_source inherited, max_ticks=None. Ordinaryreserve(parent selectedpair,
parent_journal_boundary=point.boundary), retaininputs then JournalReplayComposition
(source,FoundersLiveComposition(inputs),source_point=point), driver gets
composition.source_point (same object/horizon), sameencodedrequestsize sourceprovider.
No catalog.fork here: new replay initializes firstcapturedcp, notlast. Zero HTTP.

Replay resume/fork unchangedconfig only: ordinaryfork selectedreplaycheckpoint,
resolveoriginalOllamasource bycycle-guardedparentchain throughreplayancestors until
firstmodeollama; use firstreplayancestor storedparentrevision+parent_journalboundary
to construct ForkPoint, not newlycapturedhorizon. Matchsourcefingerprint+inputhashes;
missing/seal/config/cycle/modefailclosed. Buildcomposition/driver sharedpoint and
validate selectedworld+bothcursors corresponds capturedsourcecheckpoint. Add
JournalReplayDriver.validate_checkpoint(candidate,base,archive) pure: _target, exact
world and any capturedsource checkpoint sameworld+bothcursors ignoringrevision;
reuse at prepare start before advancing selection. No replay
provider/model/limit changes and no replay->live.

## Tests/gates

Genuine RED then GREEN slices: launchonce, owner/thread/lease/factory creation, queued
Futureadmission notdurableACK, FIFO/idempotence/conflicts/cancelledFuture/shutdown
drain, setup cancellation while startblocks, callbackbeforeGET/failedcallback,
missingprovider/model/pinchange/failurebeforeworld, sameinputattempt/noorphan.
Exactfresh/paused/step/stop/resume for genericnotape/generictape/canonicaltape, both
cursorkinds, legacy flags/limits, terminal/max0tampervalidation, initialstopprecedence,
unknownterminalnames andretainedbytefailure. requestbudget normalstop vsprovidererror
Retry; callback/mirrorfail afterarchiveahead. ZeroHTTPterminalplainresume/replay.
Real subprocess pause at committedtick, exit, laterprocess child exactinitialworld/
cognition/work/cursors and onecompletedstep; no off-time/doublecharge, sourcebytes
unchanged. Hardkill aftercp and childstartuprecoverable; cleanupnoownedworker/lease
left aftermissingserver/trickle/cancel/shutdown. Replay exactfullworld/cursors/outcomes
and sharedhorizon despiteconcurrentsourceadvance; replayresumefromearliercheckpoint.
Worker scopedchecks/report; rootindependentreview andfulltask+mergedmake, separate
examples,whitespace/exactrecordedmatrices withallCLIattemptsretained beforecommits.
No VCS/index/subagents/fullgates/examples/install byworker.

Focused final command: PYTHONPATH=src "$TASK_PY" -m pytest
 tests/test_runtime_service.py tests/test_runtime_restart.py
 tests/test_runtime_recorded.py tests/test_runtime_ollama_driver.py
 tests/test_runtime_controller.py tests/test_runtime_founders_feedback.py
 tests/test_runtime_journal_replay.py -q.
TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python.

## Root construction clarification — semantic versus attempt termination

For zero-extra-turn startup, terminal means ONLY an authoritative custom/game
condition returned by composition.terminal_condition(restored_world). A source
manifest's COMPLETED from tick/request budget, STOPPED from operator exit, or
FAILED/INTERRUPTED is an operational attempt outcome, not permanent world death.
Never copy source lifecycle/attempt_finished/control/request rows into the child.
New child starts from exact saved world/cursors with renewed child-relative limits;
valid stopped/budget-limited worlds must continue. Pending/failed provider requests
still require existing explicit Retry. True custom terminal plain live resume may
skip GET using resolved pinned config and must not generate/step; changedprovider
terminal fork still resolves newmodel viaGET, then detects customterminal with0turns.

Regression cases: stop at tickk thenshutdown/resume child+1; budget-limited completed
nonterminal source resumes andadvances undernew childbudget; truegame terminal
zeroextraGET/generation forplainresume. No source lifecycle propagation even for
unchanged explicitfork. Same17paths; this clarifies existing world/attempt ownership.

## Root shutdown/mirror construction clarification

Final mirror must run after Stop publication but before archive close, so a mirror
failure can durably record failed attempt at the last complete checkpoint. Add
owner-only RunController.settle_shutdown()->None, factoring existing close settlement
(initial queue/initialization/stop/pending rejection/discard and safe shutdownfailure)
without closing archive or setting _closed. It is idempotent for settled/terminal
controllers. close calls this helper then archive.close and _closed=True as before;
no copied settlement loop and existing direct close behavior remains compatible.

Service owner shutdown queues internal initialStop when required by contract, calls
settle_shutdown, exports final complete checkpoint if needed while archive open,
records mirror_failed via fail_service on failure, then finally controller.close
and launch bundle close. No service call to private controller._stop, no temporary
reopening of a closed controller/archive, no source changes. Same17paths.
Test finalmirrorfailure on stopped/nonterminal shutdown and completed final boundary,
exact archived snapshotahead and failed lifecycle, safe repeatedshutdown/cleanup.

## Root independent review correction round 1

Review found two P2 startup failure gaps. Scope is now19workerpaths: prior17 plus
src/living_world/archives/catalog.py and tests/test_run_archive_catalog.py, narrowly
for ordinary fork post-allocation error identity. All other excluded boundaries hold.

1. Ordinary catalog.fork owns child allocation but currently loses its reference
when retention/child copy fails before return. After _reserve returns a ref, wrap
subsequent ordinary Exception failures in existing ArchiveReservationError(ref),
preserving original cause, child files and parent bytes. Never enumerate/diff catalog
contents to guess identity, duplicate the fork loop in service, repair/delete child
or change successful mode/clone/seal behavior. Pre-allocation validation unchanged.
No BaseException/control-flow remapping required; service cancellation remains
cooperative. Update existing failure test to expect typed allocated-ref wrapper.

LaunchFactory linked recorded/replay path catches that typed failure, validates
returned ref belongs to catalog/new child relationship, acquires its normal owner
lease and accepts only this newly allocated child for failure settlement. _guard
then records failed/archive_failed at actual latestrevision (None before commit,0
if commit succeeded then raised) when SQLite is valid. No invented checkpoint or
repair if publication itself is incomplete. Startup error always includes allocated
ref. Same principle for recorded/replay resume and explicit fork.

2. Cancellation after controller construction but before first poll must use SAME
settle_shutdown -> finalmirror/audit -> close sequence as normal shutdown. Mirror
state/helper must be available for this path; derive initial/final tick from the
settled complete publication if initialpoll has not set it yet. Do not merely
close controller in finally and skip mirror. No duplicate settlement/mirror loops.
Successful cancellation with a complete stopped world writes exact final mirror.
Mirror failure durably records mirror_failed at last complete checkpoint while
archive open; mirror_failed takes precedence over cancelled startup error when
startup Future has not resolved. Finally always closes owner resources.

Required genuine RED/GREEN: recorded and replay clone failure before cp0 / commit-
then-raise, all known child ref+parent+failedoutcome / correct revision / sourcebytes
unchanged / leasecleanup; retention failure identity. Early controlled-constructor
shutdown with valid mirror and failing mirror, exact completed checkpointahead,
truthful failed lifecycle/error and repeatedshutdowncleanup. Focused correction
checks first, then original focused suite PLUS tests/test_run_archive_catalog.py.
19allowedpaths current; initial17path report is historical and correction supersedes.
