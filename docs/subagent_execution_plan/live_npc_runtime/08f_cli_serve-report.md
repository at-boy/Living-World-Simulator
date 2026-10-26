# LN08f implementation worker report

Status: independently reviewed after one corrected P2 and root task-validated.
Delivery commit follows; feature integration/repeated merged gates remain pending. No worker VCS/index operation, installation,
model request, producer change, or source archive rewrite was performed.

## Scope and behavior

Eight worker paths:

- `src/living_world/cli.py`
- `src/living_world/runtime/entrypoints.py`
- `src/living_world/runtime/serving.py`
- `tests/test_runtime_serve.py`
- `tests/test_runtime_cli.py`
- `docs/canonical_founders.md`
- `docs/http_inspection_api.md`
- `docs/subagent_execution_plan/live_npc_runtime/08f_cli_serve-report.md`

The public `serve` route uses the shared prepared launch and existing authenticated
operator application. Recorded founders, live preset, resume and fork targets
share existing validation/configuration semantics. Serve starts paused unless
`--start-running` is explicit. Serve-only port zero supports dynamic loopback
binding; inspect retains its prior port restriction. Custom engine factories and
ignored options reject before effects. Existing run/inspect routing and summaries
remain unchanged. Shared failure normalization/fallback are extracted without a
new storage policy; headless regression proves the original failure ref stays
None even when the fallback is retained and announced once.

HTTP readiness is established before the launch thread starts. HTTP and launch
threads are non-daemon; signals remain on the main thread. RuntimeService retains
all world mutation, leases, commands, provider ownership and final settlement.
HTTP remains available through slow provider setup, paused/error-paused states,
completion, Stop and failed setup. Reads, browser refresh and Disconnect issue
no Stop. Explicit Retry remains the only serving response to provider error pause.

Main shutdown joins the owner while HTTP remains available, then requests HTTP
exit and separately joins HTTP (12 seconds) and launch (6 seconds). Thread
start/join errors are closed and do not bypass socket/credential cleanup. Final
controller status is checked after owner settlement; mirror failure overrides an
apparently successful stop. Cleanup failure overrides other outcomes with
service_failed. Credential cleanup failure only replaces an otherwise successful
exit. Non-daemon threads are never forcibly killed; an uncooperative survivor can
keep the process alive after the bounded join attempts.

## Credential custody

Redirecting either output stream requires a token file. Interactive terminals
without a file receive the token once on stderr; an explicit file suppresses that
output. URL/stdout/archives/configuration/logs do not contain token or nonce.
Uvicorn diagnostics use a null handler so server exceptions cannot print private
exception text; no access log is enabled.

Destination comparison rejects overlap with the catalog or compatibility mirror,
including ancestors. File operations retain a parent directory descriptor opened
component-by-component with O_DIRECTORY/O_NOFOLLOW; lexical symlink components
before `..` are also rejected. Creation is exclusive, regular-file/current-UID/
single-link checked, fchmod 0600, complete short-write handling, fsync and close.
Cleanup checks identity, owner, type, link count, permission mode and exact content
relative to the retained descriptor. Replaced, modified, chmoded, hardlinked or
symlinked files survive. Failed publication removes only our unchanged partial
bytes. Same-UID replacement between the final identity check and unlink remains
best effort, not atomic inode unlink. No real user credential file is exercised.

## TDD and validation evidence

Interpreter for every Python command:
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`;
working directory is the assigned LN08f checkout, with `PYTHONPATH=src`.

- Initial `pytest tests/test_runtime_serve.py -q`: RED, 5 failed/4 passed;
  missing serve command/module, not a runtime dependency failure.
- Initial required focused five-file gate after implementation: GREEN, 131 passed.
- Expanded security/lifecycle gate: GREEN, 35 passed. Symlink-before-dotdot test
  first failed because abspath erased the lexical component; retaining lexical
  components before nofollow traversal corrected it.
- Additional TDD RED: optional checkpoint-only serving flag absent and directory
  descriptor close error misclassified. Both corrected within the amended scope.
- Additional TDD RED: injected HTTP thread start/join failures escaped cleanup.
  Both corrected; focused regression GREEN, 2 passed.
- Actual Chrome public-CLI browser test: GREEN, 1 passed using installed
  `/usr/bin/google-chrome` and repository Playwright support, no downloads. The
  CUA Chrome surface was unavailable; the established browser-test path worked.
- Final combined command: `pytest tests/test_runtime_serve.py
  tests/test_runtime_launch_request.py tests/test_runtime_cli.py
  tests/test_runner_cli.py tests/test_founders_cli.py -q`: GREEN, 176 passed,
  no skips or warnings, 64.89 seconds.
- Scoped `ruff check` over the five changed Python/test paths: PASS.
- Scoped `black --check` over the same paths: PASS, 5 files unchanged.

The previous combined run had 173 passes and one nondeterministic preowner-close
test failure. Its old fixture closed the service before any intentional stop,
then raced the error publication against user stop. Replaced that fixture with
explicit enter/release Events: stop closes the service before owner entry, so
both recorded and live preset paths deterministically retain one truthful failed
identity and return normal intentional-stop status. Focused corrected test passed
both cases. No production exception was suppressed to fix the test.

Tests cover real CLI subprocess port-zero HTTP/auth/default-paused idle reads,
Step and Pause ACK, both SIGINT and SIGTERM, exact cold resume world/driver/
feedback cursors and unchanged source bytes, full recorded completion, partial
recorded checkpoint-only completion/restart, finite request budget, failed setup
catalog retention and eventual mapped exit, fake provider blocked setup and
blocked decision with responsive Pause, explicit Retry, missing server/bind/startup
failure without allocation, signal restoration/injected control errors, server
death, cleanup/thread failures, preowner-close identity and final mirror failure.
Security tests cover redirected output, no overwrite, permissions, symlinks,
overlap, modified/replaced files, short writes, write/fchmod/fsync/close failures,
partial cleanup, redaction and cleanup-error precedence.

Actual Chrome test launches the public CLI subprocess rather than constructing an
app fixture: login, Step, fixed historical revision while another Step advances
the live world, Return to live and Disconnect. It asserts no browser storage,
cleared token/frame, still-paused live world, and one page POST.

## Root-dispositioned recorded partial-tape issue

The first bounded-success acceptance exposed existing unused-tape validation:
without checkpoint-only, a recorded success tape cut at tick 1 finalizes unused
entries and reports closed tick_failed through the runtime owner. Root compared
retained legacy runs: max-ticks 1 without the flag exits 2/unused_entries; with
checkpoint-only exits 0. Root amended task and saved prompt before parser changes
to permit this existing opt-out only for fresh recorded serve. Preset/resume/fork
reject it before effects; children inherit source finalization configuration.
No producer/controller/composition behavior changed. The new test confirms
completed tick 1, finalize_proposals=false, HTTP still alive and exact cold resume.
Generic budget completion records outcome=None in the existing archive contract;
no terminal condition called tick_limit is fabricated. A request budget of one
can stop at tick 0 because the two founders require more than one request for a
complete tick; its truthful outcome remains request_budget_exhausted.

## Limits and root gates

No installed Ollama/model validation is claimed; all provider tests use local
fakes. Browser tests use owned temporary catalogs. Root normal public-serving
acceptance must retain its attempts outside unit temporaries. Full make, separate
examples, independent high review, canonical 26/new CLI 7/wheel asset 11 checks,
installed console entrypoint and retained normal serving acceptance remain root
responsibilities. No milestone closure or commit/integration is claimed here.

## Independent review correction round 1/5

Finding: final FAILED controller status unconditionally replaced an established
serving/control exit 5 with mirror_failed exit 4. Verified against the actual
selection branch. Root amended both task and saved prompt before this correction
with the explicit priority: cleanup/join 5, existing serving/control 5 preserving
its specific reason, final FAILED runtime mapping, then prior startup failure;
credential cleanup 4 only when the otherwise final result is 0.

Only `runtime/serving.py`, `tests/test_runtime_serve.py`, and this report changed
for the correction. The final status is still read after joins, but its mapping
now replaces the result only when no ServeCLIError exit 5 is already established.
Cleanup failure retains its later overriding service_failed selection.

TDD evidence:

- `pytest tests/test_runtime_serve.py::test_final_mirror_failure_after_join_overrides_stop -q`:
  RED, 2 failed/1 passed. Both control+final-mirror and server-death+final-mirror
  returned 4/mirror_failed before the guard; success+final-mirror remained 4.
- Smallest targeted precedence, cleanup, thread and token-cleanup regression set:
  GREEN, 8 passed in 1.82 seconds after the correction.
- Added combined server-death+final-mirror+cleanup-error coverage, which must
  preserve cleanup service_failed exit 5 over the server_failed reason.
- Full `pytest tests/test_runtime_serve.py -q`: GREEN, 56 passed in 24.02 seconds;
  no skips or warnings.
- Scoped `ruff check src/living_world/runtime/serving.py tests/test_runtime_serve.py`: PASS.
- Scoped `black --check` on the same two files: PASS, 2 files unchanged.

Combined tests use the real runtime owner and failing final mirror; only the HTTP
server is replaced in the server-death branch so thread exit and owner shutdown
can be synchronized by Events without a hanging lifespan. They verify truthful
archive mirror_failed status persists while the public process preserves the
higher-priority serving reason, emits one fixed error, and leaks no private text.
The successful-stop branch still returns mirror_failed exit 4. No unchanged
headless suite rerun, full make, VCS/index operation or commit was performed for
this correction. Scoped independent re-review and all root gates remain pending.

## Root review and task gates — October26,2026

Initial review oneP2 finalFAILED overwrites serving5; correction round1 independently
ADDRESSED, SPEC/QUALITYPASS, NO SUBSTANTIVE FINDINGS/open0. Independent combined4
PASS/1.42s; correctedserve56PASS/24.02s, no source changes after finalreview.
- make VENV=shared absolutevenv: PASS2230,10existing deliberate skips,343.98s;
  actualChrome including publicCLI browser and39examples, no new warnings.
- Separate make examples after make closed: PASS39.
- Whitespace unstaged/cached: PASS; source/tests/pyproject exactreviewedstagedsource.
- recorded_matrix.py: PASS exacthistoricalhashes/taskcomparison,26retainednormalCLI
  attempts and all latestcomplete checkpoints openedreadonly.
- archived_cli_acceptance.py: PASS7retainedcases including2expectedfaileduninitialized,
  exactchildworld/driver/feedbackcursor, resume/forkparity/sourcebytesunchanged.
- served_cli_acceptance.py: PASS4retainednormalpublicserveattempts incl1failedsetup,
  defaultpaused/idle, Step1, INT/TERMcleanup, exactcoldresume/fork initialstate,
  sourcebytes unchanged, historicalHTTP, failedsetupHTTPusable and mapped6,
  no credentialleaks/leftoverfile.
- wheel_serving_check.py: PASS offline isolatedbuild/extractedimport/11resources/
  existingroutes/CLIhelp plus4actualpublicserveattempts importedfromextractedwheel
  incl1failedsetup, same lifecycle/restart/inspection/credentialchecks.
Evidence rootignoredworkspace ln08f-task-{make,examples,matrix,cli,serve,wheel}.
Normalarchives total41 across compatibility+CLI+source/wheelserve, all retained.
Root2extra legacypartialtape diagnosticattempts retained separately; no producer
behavior changed. Root realOllama preliminarysmoke is separate LN09 evidence,
not complete acceptance. Taskbranch/worktree preserved, integrationgates next.
