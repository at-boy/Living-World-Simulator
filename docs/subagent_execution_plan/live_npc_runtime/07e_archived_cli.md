# LN07e — Archived runtime CLI and read-only attempt inspection

Status: authorized bounded CLI stage after reviewed LN07d integration c604463.
Root contract decision review complete; implementation next.
Spec: docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md and original LN07.
Goal: expose reviewed service through explicit real-Ollama run/resume/fork/replay
commands and read-only archive inspection, preserving every existing CLI alias.
No service/domain/SQL/world/schema/dependency/browser/player changes. Python>=3.11,
strict types/frozen CLI records. NPCcontext/proposal/gateway boundaries unchanged.
Serve parser and functional operator factory bind in LN08; no placeholdercommand.
Original Task7 remains incomplete until final serve acceptance in LN08.

Exact worker boundary (seven paths):
- `src/living_world/cli.py`
- `src/living_world/runtime/entrypoints.py` (new)
- `tests/test_runtime_cli.py` (new)
- `tests/test_runner_cli.py`
- `tests/test_founders_cli.py`
- `docs/canonical_founders.md`
- `docs/subagent_execution_plan/live_npc_runtime/07e_archived_cli-report.md`
7workerpaths, rootplan/prombt/commondocs. CLI parser/dispatch in main module, newhelper
composition/monitor/errors/results inentrypoints, no service/privatecatalogreimplementation.

Flags: keepalloldaliases; run --preset founders --driver ollama --model MODEL;
--resume-attempt ID,--fork-attempt ID,--replay-attempt ID,--checkpoint REV; optional
archive-root/providerbaseURL/timeout/outputtokens/maxrequests; inspect --attempt ID
[checkpoint] archive-root, preserveoldscenario/db/foundersinspect. No inferlivefromDB.
Exactlyonetarget(positional/founders/preset/resume/fork/replay), validationbefore
attempt. Newpreset requiresollama+model, notape/checkpoint-only; oldroute unchanged.
Providerflags onoldrecordedroute reject, noignoredoptions. checkpoints onlyarchive
targets. No live max0 (AttemptConfigexistingmin1), oldrecordedmax0 stayscompatible.

Parserdefaults database/save_every ->None totrackexplicitoptions; oldroute resolves
world.sqlite3/1 BEFOREoriginal_execute. Newroute mirroronlyexplicitdatabase, cadence
sourceinherited/default1. Live defaults max20/maxrequests40; provideroptions minimal
requestedmodel+explicitoverrides, runtimepreflight fillsauthoritativedefaults.
NewrecordedlegacyCLI storeslimits.continuous bool (newmodelkey) fromactualoption,
oldstdout/engine_factory/state refs/StopControlbehavior untouched.

Resume usesEXACTsourceconfig. Explicitprovidedconfigoptions onlyacceptedifsemantically
equal toarchive (numericnormalization/URLslash/model :latestalias); changed=>2,use
explicitfork. Provider/driver/model/canonicalscenario cannot switchsavedbinding.
Limits compareeffectivechildbudget (recordednull->defaultunlesscontinuous) notraw
null. Replayrejectallconfigoverrideflags; checkpointmayboundcapturedsourcepoint.
Explicitfork permitsprovider/limits only per service; modelchange dropsolddigest
beforepreflight, oldconfigimmutable. Recordedforkcannotmodel/driverchange; typed
continuousTrue+null makesrecordedunbounded, maxTicksnumericmeanscontinuousFalse.

Newstart CLI reserves pendingOllamasetup, retainsfoundersscenario/defs withouttape
underlease, announces beforeproviderIO, thenservice.start SAMEref/inputs. Callback
on_reserved printsattempt/pathONCE forresume/fork/replay/new. Announceerror.ref if
notpreviouslyannounced. Any normal runtimefailurewithoutallocatedref getsmetadata-
onlyfaileduninitializedrecordedattempt viaexistingLegacyArchiveSession pattern;
parserandinspect neverreserve. Partial/newretentionfailure keepsknownref, best-effort
fail_setup, no overwrite/repair. No manual acceptancearchive deletion.

SIGINT: existingSignalStopControlsetsflag; newentrypointcontext ownsone stopwatcher
thread. It waits untilon_reserved firesEvent (ensuresclaimedattempt), thenpolls
control every<=0.02s; Stop ->stop_seenEvent, service.shutdown() (cancelsstartupGET).
No signalhandlerblockingjoins/newserviceprivateAPI. TrustedcustomStopControlnewroute
readsonwatcher; oldrouteunchanged. Watchererrorssanitize service_failed, mainmonitors
andshutdown; finallystop+joinwatcherandservice onALLpaths. PreexistingStopcancel
producesknownattempt, notshutdown-first-orphan. Ifcancelled beforecheckpoint and
Stop_seen, exit0+stderrstop_reason=operator_stop, no inventedticksummary/world.

Headlesswaitimmutablecontrollerstatus (smallEventwait). requestbudgettransienterror
isNOTproviderfailure; waitserviceautomaticStopped. OtherPROVIDER_ERROR_PAUSED ->
shutdown(failure_code=actualsafeerror), exit6, noimplicitRetry. FAILED mirror/audit/
archivecodes=>4; tick_failed=>5. Normalbudget=>0explicitreason; gameCOMPLETED=>0.
RuntimeStartupError mappingsinvalid_configuration2/incompatible_save3/archive_failed
andmirror_failed4/initialization_failed4/service_failed5/providerSETUP_CODES6
(exceptsetup_failed4, cancelledwithStop0). Unknownerrorssafe5, knownrefannounced.
Shutdownfailuremustnotclaimcleanexit, fixedsafeerror/ref preserved.

ArchivedRunResult frozenfields scenario_key,start_tick,end_tick,resumed,stop_reason
string,terminal_condition optional,proposals_finalized optional. KeepoldRunResult
printeridentical; mainformats enumornewstring. Initialtick fromARCHIVEcp0, not8entry
publicationcache which mayevictfast unpausedrun. Finalfromactualcompletecheckpoint,
reasonmostrecentattempt_finished (notextra lifecycle row). BudgetStoppedoutcome
request_budget_exhausted printsplainstop_reason=request_budget_exhausted; completed
None=>tick_limit; custom=>terminal_condition:name; ordinaryStop=>operator_stop.
Fork/resume statusresumed; replay statusnew. Recordedproposals_finalized inferred
fromsameoldrules flag+notoperatorstop whenreplaybinding exists; live/replay omit.

inspecthelper: catalog.open_attempt readonly+load_retained_inputs+selectedsnapshot;
SimulationEngine(SnapshotRepository(snapshot)), load_scenario exactretaineddefs;
assert encode_world equalsselectedsnapshot, serveexistingGET-onlycreate_app via
existinguvicornhookonlywheninspectrequested. Noownerlease/controller/step/providerIO,
readonly bytes/mtime invariant. Missingworld fails4. No serverdeps requiredrun.

Enginefactoryhook remainsoldroute; newarchivedroutes rejectnondefaultcustomfactory2
clearlyratherthanpretendingapplied, since compositions owndetachedengineconstruction.

Tests trueRED flags/routes; fake loopback Ollama missingserver/model/changedpin/
providerfailure/noRetry/budgetstop/realSIGINTduringGETandgeneration cleanup; exact
stdoutoldaliases, all3canonicalmatrix andnewarchivecursorresume/genericnotape/tape/
continuous/forkchangedcfg/sourcebytes; offlinefullreplay; readonlyarchiveinspect
actualHTTP/consolehook/noGETduringrun/uvicornimportisolation; fallbackmetadatafailed
attempts/knownallocatedref. PersistnormalagentacceptanceCLIarchives; unitfixturetemp
allowed. Rootreview/task+mergedmake/separateexamples/exactmatrices beforecommit.

## Exact helper interfaces and final gates

New runtime/entrypoints.py is CLI composition, not a second runtime framework.
run_archived(arguments:argparse.Namespace,control:StopControl)->ArchivedRunResult|None
load_archived_inspection(catalog:RunCatalog,attempt_id:str,revision:int|None)->SimulationEngine
ArchivedRunResult frozen dataclass: scenario_key:str,start_tick:int,end_tick:int,
resumed:bool,stop_reason:str,terminal_condition:str|None,proposals_finalized:bool|None.
stop_reason is operator_stop/tick_limit/request_budget_exhausted/terminal_condition;
terminal_condition nonNone only with terminal_condition reason.
RuntimeCLIError(exit_code:int,reason:str,ref:AttemptRef|None=None) uses closed existing
safe runtime/provider/archive codes; exit_code2/3/4/5/6 only, no rawproviderbody.
Main catches RuntimeCLIError separately, prints via same existing error helper.
Common result printer accepts existing enum or new string; existing exact stdout
line/order remains unchanged for old RunResult. No new public runtime exports needed.

Stop watcher starts before launch but checks StopControl only after on_reserved
sets a readinessEvent (ref announced, serviceclaimed), preventing shutdown-first
orphan race. Cleanup stops watcher and service and joins every normal/error path;
watcher failures sanitized, no uncaught threadtraceback. Existing legacyCLI keeps
StopControl on originalrunner; newroutes may query trusted control from watcher.

Newinspect builds an ephemeral detached engine from exact readonly checkpoint and
retainedscenario/definitions, never a controller/provider. It must check reconstructed
world exactness, then use existing _serve_inspection only. Tests verify source bytes/
mtime and no owner.lock writes/sidecars, including absent/malformedarchives.

Focused TDD baseline old runner/founders CLI, trueRED missingnewarguments/behavior,
GREEN per slice. Final: PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_cli.py
 tests/test_runner_cli.py tests/test_founders_cli.py tests/test_runtime_service.py
 tests/test_runtime_restart.py -q. TASK_PY=/home/at-boy/Projects/codex/Living-World-
Simulator/.worktrees/task24/.venv/bin/python (one continuous absolute path).
Scoped Ruff/Black/whitespace/selfreview/report actualcommands/counts/limits.
Worker no VCS/index/subagents/fullmake/examples/install/othercheckoutwrites.
Root owns exactplan/prombt/common docs/architecture, independentreview/fixloops,
task+mergedmake/separateexamples/whitespace/exact recordedmatrices, persisted
normalCLIattemptverification before commit/integration. Ask root before expanding.


## Root pre-dispatch decision review

This section clarifies the earlier compact draft; it supersedes conflicting draft
wording. Original LN07 initialization/archive failures use exit 4. Simulation and
unexpected service execution failures use 5; provider setup/runtime errors use 6.
No worker may make undocumented interface or ownership choices.

Exact new option names: `--preset founders`, `--driver ollama`, `--model MODEL`,
`--resume-attempt ID`, `--fork-attempt ID`, `--replay-attempt ID`, `--checkpoint REV`,
`--base-url URL`, `--timeout-seconds SECONDS`, `--max-output-tokens N`,
`--max-requests N`. Preserve existing flags. No new serve parser in this task.
Timeout must be finite and positive; numeric counts use positive integers, checkpoint
is nonnegative, attempt IDs use existing identifier validation. Validate credential-
free loopback URL using existing provider validation before reserving a new attempt.
Parser/option errors exit 2 and create no attempt. Unknown archive/source or absent
checkpoint is an archive/read failure (4); incompatible retained world/cursor is 3.
No provider IO on rejected flags or inspection.

New live `--continuous` means max_ticks=None without a recorded-only continuous key;
request budget still bounds provider usage. Default new live limit is 20 ticks and
40 requests. Recorded config persists continuous boolean; True implies max_ticks=None.
Live fork and resume compare this effective tick intent, not a fabricated boolean.
All explicit override defaults are None (including driver/model/provider/counts and
continuous detection); track whether options were supplied so omission inherits.
Resume must compare an explicit --driver against the saved mode; a replay-mode
resume cannot accept --driver ollama. Replay rejects every config override, including
save cadence/finalization; an explicit operational --database mirror is allowed.
`--checkpoint-only` and `--proposal-tape` are old-route options and rejected on all
new archived run targets. Preset requires explicit --driver ollama and --model.
Fork cannot change scenario, seed, recorded outcome, finalization, disturbance,
launch source or software revision; merge only authorized provider/limits fields.
Retain all other source config fields, use existing provider normalization, remove
old digest only when the effective model changes, and let service validate identity.
Resume explicit equal flags preserve the original raw AttemptConfig, never rewrite
it. Requested untagged model means the same :latest alias as preflight, not arbitrary
tag equivalence. Do not add response-size, temperature or seed CLI flags here.

Inspect has exactly one target: existing scenario/founders plus explicit --database,
or --attempt with optional --checkpoint and --archive-root. Archive target rejects
scenario/founders/database; legacy target rejects checkpoint/archive-root. --port
remains serving-only. Old scenario/founders inspect route and hooks remain intact.
Archive inspect rejects nondefault injected engine_factory before IO (exit 2).
No inspection attempt allocation, owner lease, repair, write, SQLite sidecar or model
request is permitted. Archive initialization uses retained scenario and definitions
and must prove exact reconstructed snapshot equality before existing GET-only serve.

Runtime failure fallback is metadata only: when an otherwise valid run reaches a
runtime error without an allocated child, create one separate failed/uninitialized
recorded attempt using the established legacy-failure pattern. Do not fabricate
source lineage, world, replay binding, provider validation or a successful live
attempt. If source identity is unknown use the existing unknown-scenario fallback.
When any typed error supplies a ref, preserve/announce that ref; do not allocate a
replacement. Failure to reserve fallback is reported safely (exit 4) and cannot
claim persistence succeeded. No fallback for parser errors or inspect.

No raw exception/provider text is emitted by new routes. RuntimeCLIError reason is
from closed safe codes, with fixed guidance if helpful. Existing old-route human
errors remain compatible. Source mismatch before service launch must still use the
appropriate safe error and fallback rules above. Stopped pre-checkpoint startup
prints the known attempt and operator_stop on stderr, returns 0 with no world summary.

The StopControl collaborator is trusted, as in existing main. Watcher errors must
be caught and sanitized; cleanup stops/joins the watcher and service on every path.
If bounded joining cannot finish, report service_failed rather than claiming clean
exit. A callback announces and signals reservation before provider GET. New-start
retention occurs under the caller lease, which must be released before service.start;
service then becomes the sole writer. No cross-thread archive/engine mutation.
Observer status/checkpoints and read-only catalog access are the only monitor data.
Handle request-budget transient state without racing it into provider failure: wait
for the service's automatic normal budget Stop before summary/shutdown.

Final results come from archive cp0 and latest complete checkpoint after shutdown;
no trusting a short publication cache or inventing initial tick. Read the most recent
attempt_finished to distinguish budget/Stop/game terminal outcomes. Old RunResult
stdout byte format stays identical. New live/replay output omits proposals_finalized;
recorded output matches established binding/finalization/operator Stop semantics.
No terminal failure is described as settlement success. Documentation must include
exact new commands, loopback-only providers, no downloads, failure archives, restart
lineage, explicit forks, offline replay, read-only selected-checkpoint inspection,
mirror/archive precedence and the remaining browser/installed-model acceptance work.
