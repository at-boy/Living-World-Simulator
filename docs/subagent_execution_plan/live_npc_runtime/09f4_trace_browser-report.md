# LN09f4 implementation report

Status: Frozen for independent review. Root retains completion and integration approval.

## Scope and behavior

Implemented the separate public static-only `create_trace_browser_router` and
mounted it beside the unchanged protected evidence router in live/offline apps.
Three fixed packaged resources, public no-store shell/assets, fixed runtime link,
second CLI browser announcement, package expectation and usage documentation are
within the exact fourteen-path task boundary. No runtime, archive, provider,
world, gateway, request-byte, dependency or evidence-router behavior was changed.
No Git/index/commit/integration action, full make/examples, model/native-provider
run or other-checkout edit was performed by this worker.

The page retains a memory-only administrator credential, clears the password
field on submission and private state on disconnect/401/403/pagehide. Evidence
reads use the existing same-origin GET endpoints, Bearer authorization,
`credentials: omit`, no-store and tracked ten-second AbortControllers. Session,
attempt/call-list and body-operation generations discard obsolete HTTP rejection,
JSON, preview and Blob completions. Object URLs are revoked after dispatch and
on replacement/disconnect/pagehide.

Attempts use paired cursors and preserve missing/invalid rows. Calls capture a
journal boundary once and reuse it on More/body reads; refresh clears selection
and captures a new boundary. Sequence zero is handled explicitly. Tables and
preformatted metadata use DOM text only and stay within local horizontal
containers at 360px. The page shows actual saved backend/model, opaque model
identity, source/tick/revision/request identifiers, outcome/error, integrity,
request metadata and all stored response timestamps/durations. Null displays as
unavailable; zero remains zero. Pending, legacy, complete, incomplete-prefix and
reused-source evidence are explicit. Preview is bounded UTF-8 text; downloads
preserve exact opaque bytes, including empty/invalid UTF-8/NUL bodies.

Root ruling: `model_digest` is an opaque saved nonempty identity string, matching
the API (including `sha256:` and path-like textual values). Only actual body,
content and journal SHA256 fields must match lowercase 64-hex. The root amended
the task and saved prompt before this narrow correction. No other scope ruling
or architectural deviation was needed.

## Verification evidence

All pytest commands used `PYTHONPATH=src` and
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
Actual browser tests used existing Playwright and `/usr/bin/google-chrome`,
headless, owned loopback uvicorn sockets/threads, temporary archive fixtures and
browser download capture. No cases were silently simulated or claimed passed
when skipped. Held routes are released in finally; browser/server/thread/socket
owners are reaped/closed in finally.

- RED `python -m pytest -q tests/test_trace_browser.py`: 2 failures because both
  apps returned 404 for the required public shell.
- GREEN same command after shell integration: 2 passed.
- RED `python -m pytest -q tests/test_trace_browser.py -k chrome --maxfail=1`:
  1 failure (2 deselected), real Chrome login remained inert before browser JS.
- GREEN browser evidence/race/malformed suite at that stage: 46 passed in 101.46s.
- RED opaque model identity regression: 1 failure (46 deselected), saved calls
  were rejected by the overly strict model-digest validator; root ruling above.
- GREEN `python -m pytest -q tests/test_trace_browser.py -k opaque --maxfail=1`:
  2 passed (46 deselected), both mounts.
- RED body-metadata coherence regression: 1 failure (59 deselected), malformed
  complete-body/null-length DTO was accepted; correction also requires known
  timestamp/duration keys with valid nullable types.
- GREEN targeted body-pair/timestamps, old-login/listing races and offline shell
  inertness: 13 passed (50 deselected) in 26.73s.
- Harness correction: an initial delayed-login test removed its route handler
  before reconnect and allowed the old pending login to complete unexpectedly.
  Retaining the first held route while forwarding the next login resolved the
  test-harness ordering defect; no product change was made for that failure.
- `python -m ruff check src/living_world/api/trace_browser.py src/living_world/api/trace_analysis.py src/living_world/api/operator.py src/living_world/api/analysis_serving.py tests/test_runtime_browser.py tests/test_trace_browser.py tests/test_trace_analysis_cli.py`: passed.
- `python -m black --check src/living_world/api/trace_browser.py src/living_world/api/trace_analysis.py src/living_world/api/operator.py src/living_world/api/analysis_serving.py tests/test_runtime_browser.py tests/test_trace_browser.py tests/test_trace_analysis_cli.py`: passed, seven files unchanged.
- `python -m pytest -q tests/test_trace_browser.py tests/test_trace_analysis_api.py tests/test_trace_analysis_cli.py tests/test_runtime_browser.py`:
  153 passed, 1 failed in 231.92s. The sole failure was the offline malformed
  catalog-cursor test asserting the transient `Connected.` notice after an
  immediate expected invalid-cursor error had already replaced it. The test now
  asserts connected session visibility before its expected error; product code
  was unchanged.
- Final-tree `python -m pytest -q tests/test_trace_browser.py -k bad_identity`:
  4 passed, 67 deselected in 8.28s (both identity/cursor variants, both mounts).
- Final-tree `python -m pytest -q tests/test_trace_browser.py -k 'old_login or paired_cursor'`:
  6 passed, 65 deselected in 13.63s. Root explicitly directed this narrow
  harness-only correction validation instead of repeating all four files; the
  root post-review full gate will cover the entire final tree.
- Final-tree Ruff and Black checks were repeated after the test-only correction:
  passed, seven Python files, no warnings or skipped cases reported.
- Whitespace/Git validation and all full repository, installed-wheel and merged
  acceptance gates remain root-owned; this worker was explicitly forbidden Git
  operations and full make/examples.

The browser suite covers real live/offline mounting, API login, current catalog
paging/refresh, stable calls prefix after actual journal append, paired catalog
cursor and zero sequence, explicit previews, actual binary/empty downloads with
SHA256-derived names and byte comparisons, hostile text inertness, mobile and
desktop overflow, backend/model/zero/null/reused-source/legacy semantics,
malformed numeric/container/digest/cursor/body/timing DTOs, invalid identity
selection refusal, fixed 404/409/413, private-state clear, timeout, pagehide,
old-login and old-listing 401/403 after reconnect, late call-list selection and
refresh races, and late preview/download after call/attempt/refresh/reconnect or
explicit body-operation replacement. Offline constructor spies and file
bytes/mtime snapshots verify shell inertness; real browsing likewise preserves
source files except the explicit test-owned append.

## Limits

This remains privileged saved evidence browsing over the existing bounded API.
Integrity labels do not certify a complete world, lifecycle, ancestry, provider
or model. No export, historical-world selection, generation-rate estimate,
source repair, archive migration, full LN09/native grammar acceptance or new
world/model execution is claimed. Root decides completion only after independent
review and required current-tree/full/installed-wheel validation.

## Review correction round 1

Status: Frozen again for original-reviewer scoped re-review. The root-owned
round-1 review found P2 request-body DTO validation allowed null request digest
and length even though saved request evidence requires a digest and positive
length. Only `static/analysis.js`, `tests/test_trace_browser.py` and this report
changed in this round.

`requestOK` now requires a valid non-null digest and a positive safe integer
request body length. Whole request traces can still be null for legacy metadata;
response-body length zero remains valid. No API, archive or ownership change.
Actual Chrome malformed-call cases independently cover null request digest,
null request length, both null and zero request length, in both live/offline
mounts. They require the fixed invalid-evidence message, no rendered calls,
hidden detail panel and all four disabled body controls. The existing valid-body
browser case now also captures an actual request download and checks its exact
`b"{}"` bytes and digest-based filename, alongside existing binary/empty response
download coverage.

Commands use the same task24 Python/PYTHONPATH described above:

- RED `python -m pytest -q tests/test_trace_browser.py -k 'request_digest_null or request_length_null'`:
  4 failed, 75 deselected in 28.72s. Both independently-null request fields were
  incorrectly accepted in each actual browser mount; expected fixed invalid
  evidence error was absent.
- GREEN `python -m pytest -q tests/test_trace_browser.py -k 'request_digest_null or request_length_null or request_both_null or request_length_zero or body_pair or saved_bytes'`:
  12 passed, 67 deselected in 27.34s; no warnings or skipped cases reported.
  Exact covering tests: `test_chrome_rejects_malformed_call_dtos`, parameterized
  over `offline`/`live` and `request_digest_null`, `request_length_null`,
  `request_both_null`, `request_length_zero`, `body_pair` (10 cases), plus
  `test_chrome_saved_bytes_paging_refresh_and_mobile[offline]` and `[live]`
  (2 cases). The good-body cases verify ordinary request bytes, invalid UTF-8/NUL
  response bytes, an empty response and unchanged source snapshots.
- `python -m ruff check tests/test_trace_browser.py`: passed.
- `python -m black --check tests/test_trace_browser.py`: passed, one file unchanged.

No four-file/full make/examples rerun, VCS operation, subagent, dependency change,
model call, source repair or scope expansion was performed. Root retains scoped
re-review disposition and full final-tree validation.


## Root task validation

Independent spec/quality review PASS after one P2 corrected in original-worker
round1;1addressed/0open. `make VENV=<task24venv>` PASS2815tests/10existing deliberate
skips669.49s, actualChrome and39examples. Separate `make examples`39PASS;
`git diff --check`PASS. Exactcanonical26/priorhash/read-only, CLI7/sourceServe4,
installedwheel14resources+Serve4/41normalattempts and savednative9archives30localcalls
allPASS. Actualinstalledwheel offlineAPI8 plusChrome login/preview/exactnativebody
download/sourcebytes+mtimes unchanged/no newattempt PASS; screenshot visually checked.
Installedwheel analyzeCLI16requests/twoprocesses/realSIGINT+SIGTERM0/custodycleanup/
sourceunchanged PASS. No newmodelcalls. Alljobs0 prefixln09f4-task/session1205.
Reviewedsourceaddf3358ab37769b5a002d69ede8fa513f88c7688db7fbe567e020d9b57616d8/300files unchanged.
Taskdelivery ready; featureintegration and repeatedfullgates remainpending. Root
retains completion. No worldselection/export or fullLN09/nativegrammar claim.


## Root feature integration validation — November1

Delivery7d3f793 integrated withoutconflicts after contractc91fd2d. Independent
spec+qualityPASS, one P2 addressed/zeroopen. Repeated `make`PASS2815tests/10existing
deliberate skips673.35s, actualChrome/39examples; separateexamples39 and whitespace
PASS. Exactcanonical26/priorhash/read-only/CLI7/sourceServe4/wheel14+Serve4/41normal
attempts/native-reader9archives30localcalls allPASS. Actualinstalledwheel offlineAPI8
plusChrome login/preview/exactnativebodydownload and analyzeCLI16/twoactualsignals
SIGINT/SIGTERM0/custodycleanup/sourcebytes+mtimes unchanged/no newattempt allPASS.
No newmodelcalls. Prefixln09f4-merged/session46718 alljobs0; reviewedsource
addf3358ab37769b5a002d69ede8fa513f88c7688db7fbe567e020d9b57616d8/300files unchanged.
Task COMPLETE, readyforfeaturemergecommit/push. Ownerpatch294b203... and allbranches/
worktrees/archives preserved. No main/milestone/tag or fullLN09/nativegrammar claim.
