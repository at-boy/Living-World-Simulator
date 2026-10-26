# LN08f — Public local operator serving

Status: authorized for implementation after reviewed LN08e integrationb26ddf3.
Base b26ddf3: task/merged2173tests,10existing skips,39examples and acceptancePASS.
Goal: launch recorded or real-provider worlds from the public CLI, paused by default,
and keep the authenticated browser controls/archives available during their lifetime.
Authority: owner-approved live runtime design and original LN07/LN08. No player API.
Tech: existing argparse, RuntimeService, AdminSession, operator factory and uvicorn.

## Boundary and ownership

Python>=3.11; strict hints/dataclasses/protocols. No dependencies/version/schema/domain,
provider, controller, service, archive or inspector/auth changes. No copied simulation
or owner loops. Exactly8 worker paths:
- src/living_world/cli.py
- src/living_world/runtime/entrypoints.py (serve option validation/sharedfailure helpers only)
- src/living_world/runtime/serving.py (new)
- tests/test_runtime_serve.py (new)
- tests/test_runtime_cli.py (existing-headless regression only)
- docs/canonical_founders.md
- docs/http_inspection_api.md
- docs/subagent_execution_plan/live_npc_runtime/08f_cli_serve-report.md
Root task/prombt/commonstatus separate. No worker VCS/index/subagents/fullmake/examples,
installs/downloads/realmodel calls/othercheckout writes. Unit temporary attempts allowed;
normal/manual simulations retain all archives, including failures. Missing producer
capability -> root exactcontract amendment before expanding scope/code.

## CLI and validation

Add public serve command, help describes local paused world/browser/archive control.
Exactly one target: --preset founders --driver ollama --model MODEL; --founders
success|stall|failure; --resume-attempt UUID; --fork-attempt UUID. No positional
scenario, --proposal-tape, --checkpoint-only, --replay-attempt or raw database target.
Checkpoint only on resume/fork. Flags archive-root/database(compatibilitymirror),
save-every, max-ticks|continuous, base-url, timeout-seconds, max-output-tokens,
max-requests, model/driver same existing types/meaning. Add --start-running false
bydefault, --admin-token-file PATH and --port default8000 permitting0..65535 forserve
only. Keep inspect port1..65535 and all old run/inspect parser/hooks/output unchanged.
Provide absent namespace fields scenario=None,proposal_tape=None,checkpoint_only=False,
replay_attempt=None so shared adapter receives its validated shape. Serve always
returns archived=True from validate_archived_options, including recorded founders.
Keep existing target/provider validation shared; reject ignored flags before effects.
Freshrecorded rejects all provider flags. Resume/fork uses _requested config equality
and pinned-model semantics, not duplicated validation. Preset requiresdriver/model,
rejectmax_ticks0; no host/workers/reload/CORS/remotehost options. Customenginefactory
unsupported forserve, reject before effects. No inference of live mode from mirror.

Public main imports run_served and ServeCLIError from runtime.serving, directly
returns run_served(arguments,control)->int forserve within existing guarded errorflow,
without printing old scenario result summary. Keep existing exceptions forrun/inspect.
For SignalStopControl, install SIGTERM in addition to SIGINT ONLY forserve; restore
both priorhandlers in finally on all outcomes. Injected StopControl keeps existing
no-handler policy. No signal handler performs blocking cleanup or HTTP/world work.

## Shared closed runtime failure policy

Add entrypoints.normalize_archived_failure(error:Exception,ref:AttemptRef|None)
->RuntimeCLIError: pure existing mapping (RuntimeCLIError passthrough, RuntimeStartupError
_exit(code), ArchiveError/OSError ->4archive_failed, otherwise5service_failed), no IO.
Add retain_failed_initialization(catalog:RunCatalog,*,on_reserved:Callable[[AttemptRef],None])
->AttemptRef: extract the existing fallback LegacyArchiveSession recorded/uninitialized,
seed0/currentversion/settings launch_sourcecli+driver_format1; callback beforeenter,
withsession fail(initialization_failed); preserve ref when allocation or partialfallback
fails, normalize4archive_failed. No newstorage or repair. Callback is trustedexisting
announcement; do not hide failure/allocate recursively. run_archived keeps firstknownref
announce, watcher_failed override, cancelled-and-stop_seen returnNone ordering, then
uses pure helper and fallbackhelper iff refNone. Preserve its original failure object
ref (which may remainNone even after fallback) and finally/watcher/result behavior.
Only remove extracted duplication; no broader headless refactor. Newserve uses same
helpers for source-preparation/launch errors, first announcing known allocatedref.
No normal attempt/fallback for parser/credential/import/bind/HTTPstartup failures.

ServeCLIError is a separate closed exception with exit_code/reason and sanitizedstr;
allowedpairs:2/invalid_configuration,2/server_unavailable,4/credential_file_failed,
5/server_failed,5/service_failed. main catches and prints fixed reason via _error.
No tokenfilesystem or servererror mislabeledarchivecorruption; no rawexceptions/secret
path content in logs/errors. Runtime failures keep existing2/3/4/5/6 mapping.

## Credentials and bind preflight — before normal attempt allocation

Compute catalog root with existing RunCatalog (constructor is read-only) and candidate
mirror path. Validate pure target/token destination rules, lazy import optionaluvicorn,
reserve socket bound127.0.0.1:requestedport (0allowed), obtain actual nonzeroport.
Issue AdminSession with exact http://127.0.0.1:actualport origin; no tokenCLIargument.
If both sys.stdout.isatty() AND sys.stderr.isatty(), and no tokenfile, print token
once only to localstderr as Admin token: TOKEN. If either redirected, explicit
--admin-token-file required; missing=>2invalid_configuration beforeallocation.
If tokenfileprovided eveninteractive, never print token. URL/stdout/log/archive/config/
manifest/journal contain neither token nor nonce. Nonce stays existingheader/memory.

Tokenfile contains token+newline only. Existing parentdirectories required; never
mkdir/overwrite. Reject any symlink component/final target and existing finalfile.
Reject canonical destination equal/inside/ancestor of catalog.root and equal/inside/
ancestor of compatibilitymirror path ifprovided. Do pure overlapvalidation before
allocation. Path canonicalization is forcomparison only; safe fileoperations use
retained parentdirfd obtained by opening each absolute component with O_DIRECTORY|
O_NOFOLLOW and dir_fd, then final O_CREAT|O_EXCL|O_RDWR|O_NOFOLLOW with0600/fchmod.
Use currentUID regularfile,nlink1; no fallback insecure flags. Close allfds onfailure.
Existing/invaliddestination=>2invalid_configuration; creation/write/fsync/closeIO=>4
credential_file_failed. Never reflect filesystemexception text. Capture dev/inode/uid
and retain parentfd through session; afterowned lifecycle cleanup remove only when
same inode/type/uid/nlink/mode0600 AND exact content. Preserve replaced/modified files.
Read/stat/unlink relative to anchored parentfd with nofollow, close descriptors always.
SameUID check-then-unlink replacement race is best-effort, do not claim atomicinodeunlink.
Before successful credential publication, track bytes actually written; on write,
fchmod/fsync/close failure remove the still-owned partial file only if its same
inode/uid/type/link identity and exact tracked written contents remain. No leaked
partial credential file or unlink of an external replacement. Creation failure before
ownership never unlinks. Cover injected shortwrite/failure and partialcleanup tests.
TokencleanupIO=>4credential_file_failed only when the prior outcome was0; retain an
already nonzero failure reason.
no raw filecontent output. Tests use ownedtempfiles only, no actualusercredentialfile.

## Serving, launch readiness and lifetime

After successful bind/credentialdelivery, prepare_archived_launch with catalog and
fast deduplicated attempt/archive announcement (stderr, flush, no token). Source/config
read failures use sharednormalizer/fallback then exitmappedcode; no worldready claim.
Construct create_operator_app(prepared.service,None,auth=session). Reuse service.controller
publication getter; no new API/lifespan path. Uvicorn.Config access_log=False,
log_level=error, no reload/workers; non-main non-daemon serverthread with prebound socket.
Main owns signals; uvicorn nonmain skips signalcapture. Catch serverthread exceptions
as fixed server_failed, no raw tracebacks. Blocking launch never runs on ASGI loop.
Wait at most5s for server.started, checking control, thread failure/liveness each0.01s
with monotonic deadline. Do not startworld until HTTPstarted. Startupstop=>0 afterclean
shutdown/noattempt; startupserverfailure=>5server_failed/noattempt. Print exactly
runtime_url=http://127.0.0.1:PORT/runtime to stdout/flush AFTER real HTTPready, tokenfree.
This indicates HTTPreadiness only; attempt announcement is allocatedidentity only.
Worldreadiness comes only from durable service status/controller publication.

Then one non-daemon launchthread calls prepared.launch(paused=notstart_running), using
Future/Event for immutable result/error publication. Main pollcontrol every0.01s and
checks serverthread liveness/exception. No blockingservice call from eventloop. Do
not wait on launchfuture before serving. Setup mayblockprovider while authenticated
GETstatus returns liveNone and archivecatalog remainsusable. Defaultpaused initial
checkpoint no advancement or provider decisionturn; preflight tagsstillpermitted.
Serverremainsalive after worldcompleted/stopped/failed and setupfailed, until signal/
StopControl/serverfailure. Onlaunchfailure, announce knownref or fallback iffnone,
normalize/print fixed error once, retain mappedexit for eventualstop, keepHTTPavailable
forcatalog. Provider_error_paused staysavailable for explicit existingRetry; do NOT
apply headlessauto-stop policy. Browserdisconnect/refresh/GET never issues Stop.
No HTTPstart/resume/fork world lifecycle API. Historicalviews remainfixed/read-only.

## Stop, exit and failure precedence

Intentionalstop duringstartup: cancelled or service_closed is normal0 onlyafter
successful cleanup; producer archives retain truthful setupfailure/interruption.
Other startupfailures preserve mappedexit whenuserquits. Main catches controlcallback
failure/unexpectedserverdeath =>5service_failed/server_failed, then cleanup. Main first
calls service.shutdown whileHTTPstillavailable (existing owner stops and joins5s),
then sets server.should_exit, joinsserver atmost12s and launchthread atmost6s; these
joins remain separate from existing owner authority. Existingapplifespan shutdown
canrepeatjoin idempotently. No forcedkill, daemonization, fake successfulsettlement
or dropped pendingrequests. Any cleanup/joinfailure=>5service_failed overrides other
outcomes, retain evidence; if uncooperative non-daemon remains, process maystayalive,
never promise forcible boundedprocess exit. All sockets/ownedcredentialfds cleanup
in finally evenpreflightfailure. No SIGKILL/termination of unrelated processes.
After finaljoins read controller.status again: finalmirror/archive failure overrides
apparentlycompletedstatus using existing _exit mapping. Startupfailed remainsmapped;
otherwise worldFAILED mappedcode, successfuloperatorstop/completed/budgetstop=>0.
No simulated terminalsuccess claim. Tokencleanup failure4 only if the otherwise final outcome was0.
Print errors once fixedclosedcode, suppress only intentionalstartupcancel afterstop.

## Meaningful tests and acceptance

TDD beforeimplementation. Actualsubprocess CLIserve with tempcatalog/tokenfile/port0:
HTTPreadiness, login/auth/status, defaultpaused idleGET noadvance, Step/Pause ACK,
SIGINT/SIGTERM cleanup+exactrestartchild world/driver/feedbackcursors/sourcebytes;
start-running/finitebudget stillinspectable, completed/stopped archives/history;
actualChromepublicCLIpage login/control/fixedhistoricalsource and logoutnoStop.
FakeOllama blockedsetup HTTPusable/liveNone/cooperativeinterrupt; blockedStep/allowPause;
providererrorpause and explicitRetry, setupfailure retainedcatalog+mappedexitatquit,
ref-lesspreownerclose onefailedidentity notfallback. No actualmodel untilLN09.

Tokenredirect/nooverwrite/600/symlinks/overlap/replacedmodifiedpreserved/redaction,
missinguvicorn/bind/startupfailure noattempt, signalrestore and injectedcontrolerrors,
serverdeath/cleanupjoinfailure nofalse0, finalmirrorfailureafterownerjoin. Existing
headless source/outputs/errors unchanged; sharedhelpers don'tduplicateannouncement or
fallback, no raw secret/providererror. Offlinewheels11assetresources and installedconsole
entrypoint supportserve. Use bounded event/process/HTTP waits, no hangingtests or sleeps
as soleproof. Root actualnormalserveacceptance archives retained outsideunittemps.

Focused test_runtime_serve.py +test_runtime_launch_request.py +test_runtime_cli.py +
test_runner_cli.py +test_founders_cli.py, scopedRuff/Black, rootwhitespace. Workerreport
RED/GREEN, commands/results/counts/warnings, changedpaths, exactlifecycle/security,
limitations/rootgatespending; no successfuloutputdumps. Do notcommit. Independent
highreview before root task/merged make, separateexamples, canonical26/newCLI7/wheel11
and publicserveacceptance. Preserveallbranches/worktrees/ownerlocalplanedit. Original
LN07/LN08 mayclose onlyafter publicserveacceptance; installedOllama remainsLN09.
