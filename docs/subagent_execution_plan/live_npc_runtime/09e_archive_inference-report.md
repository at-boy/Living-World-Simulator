# LN09e worker report — automatic archive inference

Status: implementation frozen for independent review. Root review, authoritative full
validation, common documentation, VCS and integration remain outstanding.

## Implementation

Added owner-called `archive_inference.py` helpers with the contracted signatures.
Request trace and exact prepared bytes commit together before binding/dispatch.
Response trace, available bytes and validated/failed outcome commit together before
acknowledgement, clearing active state or staging. Missing injected-broker observations
use actual parent clocks and explicit unavailable evidence. Unsafe parsed prose remains
failed while its original privileged body is retained. Cleanup failures log only the
fixed warning `Inference trace cleanup pending.`

Live prepare rejects direct dispatch into format-one archives before feedback mutation;
checkpoint validation remains usable for legacy sources. Uncertain local trace-bearing
requests record unavailable metadata with unknown clocks. Close reaps first, imports
cached evidence as cancellation, acknowledges the actual broker result only after import,
and clears detached work/proposal references in `finally`. Failed imports retain active
identity/spools and cannot stage, resolve an action or publish a new world checkpoint.

Sealed live reuse verifies the exact prefix and copies trace fields plus referenced
BLOBs in one response-reused transaction. Offline replay eagerly captures authenticated
prefix BLOBs while the source is available, copies them atomically and rejects mismatching
already-local trace evidence. Trace metadata and timing remain those of the source call;
legacy omissions remain omissions. No source spool is consulted.

Updated NPC-boundary/local setup documentation for automatic privileged tracing,
legacy child resume, offline copy semantics and uncommitted forensic spool scope.
The only disturbances-fixture change is `ShelterBroker(DecisionBroker)` plus its import.
The existing pending-restart test in `test_runtime_ollama_driver.py` now creates a fresh
broker after simulated process loss and verifies retained prior spool evidence.

## RED/GREEN evidence

All commands used existing `.worktrees/task24/.venv` tools and `PYTHONPATH=src`.
No redundant full baseline was run.

- RED: `pytest -q tests/test_runtime_archive_inference.py`: **2 failed**. Both actual
  spawned endpoint tests showed the read-only HTTP handler could not find committed
  request trace/BLOB metadata before dispatch.
- First GREEN: same command: **2 passed** (3.36s). Both provider bodies, status and parent
  timing survived archive reopening; handler independently verified prior commit.
- Replay RED: same command after adding storage/reuse/replay cases: **1 failed,
  3 passed**. Offline imported response lacked `request_trace`.
- Initial requested regression command below: **1 failed, 294 passed** (112.42s).
  `test_pending_restart_is_uncertain_without_resend_then_retry_reuses_earlier_actor`
  reused the crashed broker object, including its newly durable unacknowledged binding.
  Corrected the allowed trace-aware fixture to create a fresh broker, preserve old
  evidence, and count calls across both objects. Targeted rerun: **1 passed** (0.75s).
- Intermediate new-test corrections: oversized-body expectations initially used cap
  instead of the producer's observed cap+1 prefix and `partial` instead of its defined
  `incomplete` state; corrected assertions. The new hard-crash subprocess initially
  opened its writer before acquiring its lease; corrected fixture ordering. These were
  test-authoring failures, not producer changes.
- Requested regression command:
  `pytest -q tests/test_runtime_archive_inference.py tests/test_runtime_ollama_driver.py tests/test_runtime_journal_replay.py tests/test_runtime_disturbances.py tests/test_runtime_inference_capture.py tests/test_inference_trace_storage.py tests/test_runtime_restart.py`:
  **310 passed** (125.46s). This run used 19 new cases.
- Final focused command after the final test-only legacy/source-removal coverage:
  `pytest -q tests/test_runtime_archive_inference.py`: **20 passed** (19.77s).
  Production code was unchanged after the combined 310-pass run.
- Scoped `ruff check` across three changed runtime modules and four allowed test
  modules: **passed**. Scoped `black --check` over the same seven files: **passed**.
- Eight changed implementation/test/document files scanned for trailing whitespace:
  **passed**. Root retains `git diff --check` responsibility under the no-VCS assignment.

New coverage includes both real spawned endpoints with commit-before-HTTP observation;
exact raw invalid JSON, invalid UTF-8/envelope, empty, HTTP error, oversized prefix and
unsafe prose retention; timeout/partial stop, complete captured stop, real captured
response import failure, request storage failure, fixed cleanup warning/no duplicate
response, direct legacy rejection/new-child tracing, legacy source omission preservation,
exact nested live response/body/timing copy, sealed prefix exclusion/tamper rejection,
exact offline world replay with the source directory temporarily absent, and an actual
hard-exit process leaving captured but unpublished bytes that child reuse does not consume.

## Scope and limits

Changed nine allowed paths (including this report): three runtime modules, the new
archive-inference test file, the allowed driver restart fixture, the disturbances fixture,
and two boundary/setup documents. No edit to `test_runtime_restart.py` or existing replay
suite. No dependency, producer, world schema, deterministic fingerprint, source spool
recovery, admin/export, real model, product server, launcher or download work.

No Git/index/commit/merge/push, full make/examples, other checkout edits or subagents.
All HTTP servers were test fixtures. Existing producer/storage tests supply additional
missing-BLOB/atomic validation and broker trust-boundary coverage; these producers were
not weakened. No real-provider acceptance is claimed. Full root validation and independent
review remain required before approval or commit.

## Independent review R1 correction — round 1/5

Read root's exact `ln09e-review-1.md`. R1 correctly identified that the prior offline
trace case used unavailable fake response evidence and only asserted the request BLOB.
Added `test_offline_replay_preserves_captured_response_evidence_and_local_identity`
to the existing approved new test file; no production change was needed.

The new source runs real spawned HTTP inference for both founders with two distinct
nonempty raw bodies and distinct actual response timings (server delays 0.03/0.15s).
The test commits the complete source tick, eagerly constructs replay, shuts down the
HTTP server and makes the source directory unavailable. While it remains unavailable,
the destination must preserve exact request bytes/request_trace, response bytes and
response_trace (including every timestamp/duration), content_digest and elapsed_seconds.
It compares the complete world snapshot, events, driver cursor and feedback cursor.
A second import of the same local tick must leave journal records and BLOBs unchanged.
Finally, a valid local response trace is altered in SQLite: storage accepts the altered
nonnegative duration, but replay must raise its specific local inference trace mismatch
error without publishing further records or changing the completed checkpoint.

Targeted proof and validation (existing task24 environment, `PYTHONPATH=src`):

- New test selector alone: **1 passed** (2.05s).
- In-memory mutation runs used `PYTHONPATH=src:tests .../.venv/bin/python`,
  `pytest.main([-q, --tb=short, <new-test-selector>], plugins=[Mutant()])` in fresh
  subprocesses. Each plugin changed only the loaded replay projection/comparison in
  that process; no production file was edited. Six independent intended REDs:
  omit response_trace; alter original broker duration; omit digest/elapsed;
  ignore local response-trace identity; omit elapsed alone; alter original timestamp.
  Each run produced **1 failed** with exit 1. Metadata omissions/changes failed exact
  equality/key assertions; ignoring identity failed the expected-error assertion.
- Final `pytest -q tests/test_runtime_archive_inference.py`: **21 passed** (21.60s).
- Scoped Ruff and Black checks on the changed test file: **passed**.
- Changed test/report trailing-whitespace scan: **passed**.

Correction scope: only `tests/test_runtime_archive_inference.py` and this report.
No production/producer/VCS/full-gate/subagent/model changes. The unchanged combined
310-test suite was not rerun, as instructed. Frozen again for independent re-review;
root retains full gates, disposition and completion responsibility.

## Root independent review and task validation

Independent astra spec/quality review1 requested one P2 regression-coverage correction.
Original worker's bounded test-only fixround1 and original reviewer scoped re-review
resolved it: R1 ADDRESSED, no substantive findings. Packages/reports retained in ignored
root plan workspace. Root verified allowed paths and the evidence gap before correction.

Root compatibility gates passed: exact canonical26/two-fresh/resume1/3/4 and read-only
complete points (prior payload hashes exact, database bytes unchanged); CLI7, sourceServe4,
offline wheel11resources+actualServe4. All41 normal attempts retained. Full task make passed2547tests/10existing skips479.81s, actualChrome and39examples.
Separate make examples39 and git diff --check passed; reviewed source remained exact.
Featureintegration and repeated merged gates remain pending.
Reviewed source/tests/pyproject SHA18fc232fb2bfec70272a8faa2c46144ed9479527fd46b94b5c2e3c300548bd35.

## Root feature integration validation

Task delivery62ea35c pushed on preserved codex/live-npc-ln09e-archive-inference.
Clean noff integration repeated make: PASS2547tests/10existing deliberate skips478.25s,
actualChrome/39examples. Separate examples39, whitespace, exactcanonical26/read-only
unchanged/priorhashes/CLI7/sourceServe4/wheel11+actualServe4 PASS. All41normalattempts
retained per gate tree. Reviewed source/tests/pyproject SHA18fc232fb2bfec70272a8faa2c46144ed9479527fd46b94b5c2e3c300548bd35
and owner-local masterplan diff unchanged. Live remote main/milestone/tag refs unchanged.
Implementation is reviewed and validated; admin/offlineanalysis/export and real BOTH
provider acceptance remain separate requirements. No realmodel used in these gates.
