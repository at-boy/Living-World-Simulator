# LN09f3 — Offline protected analysis CLI

Status: COMPLETE; independent spec+qualityPASS/no findings; task and repeatedmerged gates2736/10existing skips/allcompatibility/native/API+CLI wheel checks PASS. Delivery78d7a56 preserved/pushed. Use one bounded worker,
independent spec/quality review and root task/merged gates. Goal: launch the inert
saved-trace app through a supported loopback command while preserving existing run,
serve and inspect behavior. Browser page and exports are subsequent tasks.
Spec: docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md (owner approved),
plus later explicit exacttrace retention/analysis requirements and approvedexecution.

## Architecture / seven worker paths

Reuse create_analysis_app(RunCatalog,auth=AdminSession) unchanged. Extract the existing
audited token-file custody without behavioral changes; no parallel implementation.
No runtime/service/controller/world/preflight/provider/lease/attempt construction.
No source migration/repair/cache/new files or source bytes/mtime changes. Python>=3.11,
strict hints, no dependencies, no NPC/gateway/prompt/config/fingerprint changes.

- NEW src/living_world/api/local_admin.py: existing ServeCLIError + token-file custody
- src/living_world/runtime/serving.py: narrow extraction imports/aliases only
- NEW src/living_world/api/analysis_serving.py: inert loopback server adapter
- src/living_world/cli.py: analyze parser/dispatch and signal selection only
- NEW tests/test_trace_analysis_cli.py
- docs/trace_analysis.md: CLI use and exact serving boundary
- docs/subagent_execution_plan/live_npc_runtime/09f3_offline_analysis_cli-report.md

Root owns task/prombt/common docs/evidence/full gates/VCS. Worker no otherpaths,
subagents/index/commits/fullmake/examples/dependencies/models/downloads. Unitfixtures
only; actual owned test subprocess/loopback permitted, cleanup in finally. Report
missing seam before scope expansion. No new UI/assets/export/archive-reader changes.

## Shared local-admin custody

Move existing ServeCLIError and _Credential logic from runtime/serving.py into
api/local_admin.py, public class name AdminTokenFile. Preserve closed allowedpairs:
(2,invalid_configuration),(2,server_unavailable),(4,credential_file_failed),
(5,server_failed),(5,service_failed). Same .exit_code/.reason/string behavior.
AdminTokenFile dataclass fields/methods and file semantics are unchanged except name:
open(path:Path,protected:list[Path])->AdminTokenFile; publish(token:str)->None;
close()->None. Keep anchored parent descriptors, O_NOFOLLOW/O_DIRECTORY walks,
resolved protected-path overlap, refusal of any existing final node, exclusive0600,
regular/uid/nlink checks, fsync/short-write cleanup, exactbyte+identity based removal,
modified/replaced/hardlinked custody preservation, fixed closederrors. No new token
location/default/token persistence policy. Existing same-UID unlink race limitation
stays truthful. Do not silently harden/refactor unrelated custody during extraction.

runtime.serving re-exports import aliases ServeCLIError and AdminTokenFile as
_Credential so old exception types/private test imports remain identical. Preserve
legacy run_served lifecycle/startup/failure cleanup and accepted options verbatim.
Shared module has no imports of runtime/provider/catalog/world or app ownership.

## CLI and adapter interfaces

New `living-world analyze [--archive-root PATH] [--port PORT]
[--admin-token-file PATH]`. Help: serve saved call evidence read-only without running
a world. No scenario positional argument, provider/model/run/resume/fork flags.
Default archive root existing RunCatalog.default_root; default port8000.
CLI startup rejects a symlink/unsafe/non-directory existing catalog root with fixed
2 invalid_configuration; an absent root remains allowed. Validate without creation. Reuse exact
_serve_port validation0..65535 (0 chooses actual ephemeralport). Loopback127.0.0.1 only,
no host/remote/CORS option. Missing root is allowed and MUST remain absent.

NEW api.analysis_serving.run_analysis(arguments:argparse.Namespace,
control:StopControl)->int. Success returns0 after explicit stop; failures raise existing
ServeCLIError with fixedcodes. Reuse existing Control protocol, no owner callback.
cli.build_parser adds analyze; main bypasses validate_archived_options for analyze
rather than fabricating unused scenario fields. Route analyze before simulation
execution and keep exception handling/finally signal restoration. Install SIGINT and
SIGTERM handlers for serve/analyze; existing run/inspect signal behavior unchanged.
Custom engine_factory is never invoked for analysis. Legacy options never ignored.

Token delivery matches serve: without tokenfile require BOTH stdout/stderr TTY before
any catalog construction, bind or source IO. Otherwise raise2 invalid_configuration,
no token emitted.
Explicit tokenfile must be outside catalog root/ancestors using shared custody; never
write inside source. Missing parent/existingfile/symlink/hardlink/overlap rejected as
sharedcontract. Terminal prints Admin token to stderr only in TTYmode. File mode must
never print token, credential content/path, source paths, raw responses or tracebacks.
Credentials stay out of URLs/env/archives/logs. Issue AdminSession for actualboundorigin.

Import optional uvicorn with fixed2 server_unavailable if absent. Bind/listen one
owned IPv4 loopback socket; bindfailure5 server_failed. Publish token only after
socket exists. Construct only create_analysis_app(catalog,auth=auth), uvicorn.Config/
Server; same quiet/access-log-disabled configuration as existing serve. Server.run
uses owned socket in named non-daemon thread. Future captures thread exceptions as
fixed5 server_failed without rawdiagnostics. Startup deadline5seconds, poll0.01;
control stop may terminate startup cleanly before URL announcement. Announce exactly
`analysis_url={actual_origin}/analysis/status` to stdout only after server.started;
this is the current authenticated JSONstatus endpoint, not a new browserUI promise.
After startup poll control/serverliveness0.01 until stop or fixedfailure. Never call
RunCatalog.attempts/open_archive/reserve, RuntimeService/RunController or provider.
Existing API handles authenticated bounded filesystem work perrequest.

Finally set server.should_exit, join HTTPthread with timeout12, record unexpected
thread exit/exception or joinfailure/alive as5 service_failed/server_failed; close
owned socket and sharedcredential on every exit. Cleanup failures must not leak
exceptions or delete another file. Preserve the first primary failure. If there was no primary failure, HTTP/thread/
socket cleanup failure takes5 service_failed; credentialclose alone takes4
credential_file_failed. Both cleanup types together take5. A live
uncooperative Python thread cannot be forcibly terminated; do not claim that guarantee.
Normal actual tests must prove no owned server/thread/socket/credential remains.
Never finalize an attempt or allocate a failed simulation for analysis-start failure.

## Test cycle / acceptance

- [x] RED parser/analyzer/sharedpublic interfaces absent; meaningful failurefirst.
- [x] Parser actualconsole help/invalidports/unknownsimulationflags rejected; nonTTY
  missingtoken2 beforebind/no rootcreation; no enginefactory call; restoredhandlers.
- [x] Shared extraction keeps existing test_runtime_serve custody/lifecycle coverage
  passing. New tests directly cover publicclass aliasidentity and protectedcatalogroot,
  missingparent/existing/symlink/hardlink/overlap rejection and modified/replacedtoken
  preservation. Injection failures use owned fixtures, no realuser paths.
- [x] Actual childprocess/loopback over temp traced/legacy/no-checkpoint+failed headers:
  auth401, Origin403, offline status, discovery/pages/exactbody/no-store/POST405;
  oneSIGINT and oneSIGTERM terminate0, sourcebytes+mtimes/catalogIDs unchanged,
  no newattempt/lock/provider/model/world and no token/traceback in capturedlogs.
- [x] Missingcatalogroot startup/read/shutdown leaves it absent. Adapter spies forbid
  RuntimeService/RunController/preflight/reservation/lease/fullreader construction.
- [x] Fixed bind/serverimport/startup/HTTPthread/start/join/control/credentialwrite/
  credentialcleanup failures; alwayscleanup/sanitizedcodes. Only actualpassed cleanup
  is claimed. Selected malformed source remains APIrowinvalid/fixederror, no programcrash.
- [x] Focused test_trace_analysis_cli +test_runtime_serve +test_trace_analysis_api,
  scoped Ruff/Black/whitespace; own report commands/counts/warnings/boundaries thenfreeze.

Focused commands use task24venv with PYTHONPATH=src: `python -m pytest -q
tests/test_trace_analysis_cli.py tests/test_runtime_serve.py tests/test_trace_analysis_api.py`;
`python -m ruff check` and `python -m black --check` the changed Pythonpaths.

Root fullmake/separateexamples/exactcanonical26/CLI7/sourceServe4/wheel11+Serve4/
savednative reader9archives30calls plus installed-wheel actual analyze subprocess
requests/signals/read-only smoke afterreview and repeated afterfeaturemerge. Preserve
branches/owneredit, no main/milestone/tag. No finished browser/offlineexport acceptance.
