# LN09h worker implementation report

Date: 2026-11-12. Status: implementation ready for root independent review;
native acceptance and final task completion remain root-owned.

## Deliverables and boundary

Only these five worker-owned files were created:

- `examples/manual/local_founders_runtime.py`
- `examples/040_live_npc_runtime.py`
- `tests/test_runtime_acceptance.py`
- `docs/live_npc_runtime.md`
- this report

No production package, dependency, canonical policy, parser, gateway, HTTP server,
schema, or persistence changes. No worker commits, native model calls, downloads,
installations, or other checkout edits. Common documents and task/prombt are
root-owned. All synthetic fixture traffic uses owned ephemeral loopback servers.

The manual helper validates before allocation, composes the public archived
factory/runtime service, counts committed advancing ticks, retains attempt
identity, and emits scalar-only JSON. A watcher covers blocking startup and
inference, requests service shutdown for cancellation/deadline, and is joined.
First failure wins through cleanup; provider/budget states remain truthful.
A post-initial-checkpoint launch failure reads the already retained checkpoint
for available summary fields without inventing an initialized world.

The numbered example uses the real broker against an explicitly synthetic
no-action HTTP fixture. It checks retained inference bodies, closes the fixture,
then compares every initial/advancing world, driver cursor and feedback cursor
through offline replay, plus unchanged source file bytes/mtimes. Temporary
catalog/server cleanup and import safety are exercised.

## TDD and focused evidence

All Python commands below use
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/`
and `PYTHONPATH=src`, from this task worktree. No redundant inherited full-suite
baseline was run; root supplied reviewed inherited validation.

- RED: `pytest -q tests/test_runtime_acceptance.py`: 1 expected failure,
  `test_real_archived_steps_and_offline_replay`, because the manual helper file
  did not exist. No implementation existed before this test.
- Initial workflow correction: that test exposed selecting source checkpoint 0
  limits replay to tick 0. Removing that selector uses the full source history;
  focused rerun passed (1 test). The first demo execution also failed its journal
  assertion because the asserted response entry name was wrong; corrected to the
  actual `response_validated` contract.
- Expanded intermediate run: 23 passed, 5 failed. Failures were
  `test_stop_during_startup_or_inference_closes_owned_threads[True-POST]`,
  `test_failed_provider_retains_error_and_attempt`,
  `test_missing_source_retains_uninitialized_failure`, and
  `test_manual_subprocess_signals_are_cooperative_and_sanitized[POST-2]` /
  `[POST-15]`. Four used the wrong fixture model name and reached `model_missing`
  before inference; one used a malformed UUID. Fixture inputs were corrected;
  the next full acceptance run passed 28 tests.
- `pytest -q tests/test_runtime_acceptance.py -k 'cleanup or preflight or missing_source'`:
  3 passed, 27 deselected. This includes real service cleanup fault injection;
  provider failure keeps priority, while cleanup failure after success yields 5.
- Additional RED: `pytest -q tests/test_runtime_acceptance.py -k failed_initial_mirror`:
  1 expected failure, 30 deselected. A real invalid mirror destination left a
  durable tick-0 checkpoint but the helper returned null checkpoint fields.
  After the bounded helper correction, identical command: 1 passed, 30 deselected.
- `pytest -q tests/test_runtime_acceptance.py tests/test_runtime_disturbances.py tests/test_runtime_preflight.py tests/test_runtime_cli.py`:
  175 passed. This run began before the final mirror-summary regression was added;
  final helper changes are covered by the subsequent final acceptance run below.
- `pytest -q tests/test_runtime_launch_request.py tests/test_runtime_service.py`:
  60 passed.
- Final `pytest -q tests/test_runtime_acceptance.py`: 31 passed, 50.85 seconds.
  This exercises the final helper/demo and includes the durable mirror-failure
  summary regression and explicit broker-child/thread cleanup assertions.
- Scoped `ruff check` on the helper, 040 example and acceptance tests: passed.
- Scoped `black --check` on the same three files: passed (3 files unchanged).
- `git diff --check`: passed. No meaningful warnings in final passing runs.

The standalone `python examples/040_live_npc_runtime.py` execution passed after
correcting the response-entry assertion. The final acceptance suite also runs it
as an isolated subprocess, requiring exit 0, its concise synthetic PASS line,
and no leftover temporary catalog.

Coverage includes strict helper limits/route rejection without allocation,
real step/durable-state accounting, retained startup/provider/mirror failures,
request-budget early stop with zero committed steps, callback exception
sanitization, startup and actual in-flight inference deadlines/cancellation,
owned SIGINT/SIGTERM subprocesses, helper/owner/thread and broker-child cleanup,
cold resume/fork with exact inherited world/cursors/configuration/policy,
unchanged source bytes/mtimes, and no repeated completed tick-2 disturbance.
`work_blockage` with no synthetic work remains `no_eligible_work` explicitly.

## Self-review and limits

Checked public-owner-only mutation, main guards for spawned imports, finite
requests/deadlines, cleanup/failure precedence, scalar summaries, source
preservation and closed error codes. The guide documents both native backends,
explicit founders request contract, separator, disturbances, cold children,
offline replay, archive locations, exit semantics, cancellation and browser
control references.

Synthetic passing tests are not evidence of native acceptance. No real model,
GPU, server installation, browser or native disturbance acceptance was attempted.
Deadlines remain cooperative with existing service cleanup; no strict wall-time
guarantee is made. Root retains independent review, full make/examples gates,
Python 3.11/package checks, common documents, Git integration and final verdict.

## Independent review correction round 1

Root relayed two confirmed P3 contract gaps: oversized integer timeouts raised
`OverflowError` during `math.isfinite`, and mixed-option help swallowed
`SystemExit(0)` and emitted an invalid-configuration result. Only the helper,
acceptance tests and this report changed in this round; the numbered example
and guide remain frozen.

Corrections:

- Compare timeout bounds before `math.isfinite`, rejecting both positive and
  negative `10**1000` without conversion or catalog allocation.
- Parse the helper-option prefix even when the separator is absent, so ordinary
  argparse help succeeds. Preserve successful `SystemExit(0)` from either
  helper or production parser without a JSON summary. Only tokens before the
  literal separator are parsed by the helper; `--help` / `-h` after it retain
  production `run` help semantics. Malformed arguments remain exit 2.

Using the same environment and worktree as above:

- RED: `pytest -q tests/test_runtime_acceptance.py -k 'oversized_integer_timeout or mixed_helper_help or help_after_separator or malformed_helper_arguments'`:
  8 expected failures, 1 passed, 31 deselected. The two signed oversized-timeout
  cases raised `OverflowError`; four mixed helper-help cases (with/without
  separator, long/short flags) and two production-help cases returned 2 instead
  of 0. The malformed-helper-with-help case already correctly returned 2.
- GREEN: `pytest -q tests/test_runtime_acceptance.py -k 'oversized_integer_timeout or mixed_helper_help or help_after_separator or malformed_helper_arguments or invalid_helper_inputs or main_separator'`:
  18 passed, 22 deselected. This covers the new cases plus existing helper limit,
  missing separator, missing options and malformed production-option checks.
  Help assertions require no summary, no stderr errors and no catalog creation.
- Scoped `ruff check examples/manual/local_founders_runtime.py tests/test_runtime_acceptance.py`:
  passed.
- Scoped `black --check examples/manual/local_founders_runtime.py tests/test_runtime_acceptance.py`:
  passed (2 files unchanged after formatting).

No new warnings, production/native activity, Git operations, full-suite gates,
or remaining correction concerns. Frozen again for root scoped re-review and
root-owned final validation.

## Root independent review and task validation — November12

Independent initial spec review found two P3 explicit-contract gaps; correction
round1 fixed oversized-timeout validation and help routing. Fresh scoped sol/high
re-review: both ADDRESSED, spec/quality PASS, NO SUBSTANTIVE FINDINGS. Root-owned
native report and README links also independently factchecked with no gaps.

Frozen358 source SHA256
`48215a24be4adaff9ee3fb0ef3a6457ddfcff970be456df4e3e1484c31e93b45`
remains unchanged. Root `make VENV=<task24venv>`: 3029passed/10existing
deliberate skips in759.95s, including actualChrome and40examples; separate
`make examples VENV=<task24venv>`40PASS and `git diff --check`PASS.

Initial fullgate session19158/prefixln09h-task truthfully failed1/3028passed/10
skips in800.83s: existing half-second normal-model-missing preflight returned
timeout under concurrent native workload. Isolated three preflight cases PASS
2.91s without code changes. Quiet fullmake recovery session75217/prefixln09h-task-r2
then PASS. Recovery explicitly reuses only five already-passing unchanged-source
foundation jobs; all previously unrun checks executed. All13jobs0: canonical26
fresh/resume1,3,4/terminal-zero-step/priorhashes; CLI7; Serve4+failedsetup; wheel14
assets+Serve4; native-reader9archives30calls; installedwheel API8+Chromeexactbody
download; CLI16+actualSIGINT/SIGTERM/custody; historicalworld HTTP9+Chrome; exact
traceZIP CLI4; separateexamples/verification/whitespace. Originalfailed evidence
remains intact; no test deadline or product change was made.

Fresh actual installed current wheel onPython3.11.2 session14564: import and
console entrypoint, canonical26 restart matrix, publicServe4+failedsetup, new
040 synthetic actualHTTP/offline replay and exacttraceexports4 PASS. Existing
local uv used offline/no-deps to reinstall current builtwheel; hardlink-to-copy
fallback warning only. Default validationPython3.13.5; no systeminstall/download.

Native main sixcases48realcalls: both baselines and resource-loss PASS, both
work-blockage explicitly UNMET/no_eligible_work. Both models chose larger shelter
labor3 vs2founders; no injectedwork/labor/decisions or productdefect inferred.
Allsixcases still pass exacttrace/body/backend/model/timing, ordinaryaccepted
actions, coldinitialworld/cursors, offline fullworld/events/cursors/retainedtrace
replay and sourcebytes+mtimes checks. Two actualChrome nativecontrol/coldchild
proofs add8realcalls; providerstopped offline replay PASS includingsealedresponse
reuse and duplicate shutdowncheckpoint semantics. Nine actualinstalledwheel
saved-native browsercases PASS/sourceinventoryunchanged, includingfailedattempt.
Allownedmodels/CLIservers stopped; PID/UID/startidentity/argv/logs/catalogs retained.
See [root native evidence](../../orchestrator_handoff/live_npc_native_acceptance_2026_11_12.md).

This completes the bounded helper/example/guide task, not originalLN09 or whole
branch readiness. Appliednativework acceptance, portableworld/parentclosure,
uncommittedforensic export and finalwholebranchreview remain. Featureintegration
and repeated fullgates pending; preserve taskbranch/worktree and owneredits.
