# LN07e archived CLI implementation report

Status: implementation prepared for root independent SPEC/QUALITY review. Root retains
completion, integration, VCS, and full validation authority. No commit or push performed.

## Behavior and architecture

`cli.py` preserves the established scenario/founders runner, injected engine factory,
StopControl, error behavior, aliases, and stdout summary. Parser defaults now retain
explicit-option information; the old route resolves database/save cadence/continuous
before entering its original implementation. Newly recorded legacy attempts persist
the actual boolean continuous intent.

Explicit preset, resume, fork, and offline replay routes use `runtime/entrypoints.py`
and the reviewed `RuntimeService`. Frozen `ArchivedRunResult` and closed-code
`RuntimeCLIError` keep composition outcomes separate from legacy `RunResult`.
Configuration/target conflicts are rejected before allocation/provider IO. Live preset
settings contain requested model plus explicit provider options; preflight remains the
authoritative normalization/default/digest producer. Existing loopback validation is
reused. No download or retry behavior was introduced.

New live setup reserves one pending attempt, retains scenario/definitions without a
tape under its caller lease, releases that lease, and starts that same reservation in
the service. The service callback announces once before provider IO. Known allocated
failure references are preserved. Otherwise valid preallocation runtime failures use
the established metadata-only failed/uninitialized recorded-session pattern; failed
fallback persistence reports a safe archive failure. An unusable catalog root cannot
create a fallback, and returns safe `archive_failed` without claiming persistence.

Resume compares only supplied options using normalized numeric/URL/model alias
semantics and effective recorded tick budgets, then submits the original raw config.
Changed options require explicit fork. Fork changes only provider/limits while
preserving source fields; a changed effective model drops the old digest. Replay
rejects config overrides and performs no provider IO. Mirror cadence inherits from
the source for resume/fork/replay, or defaults to one; archived routes write a mirror
only when an explicit database was supplied. The archive remains authoritative.

The stop watcher waits for the reservation callback before querying the trusted
StopControl. It requests bounded service shutdown outside the signal handler and
sanitizes collaborator errors. Cleanup joins both service and watcher on all paths,
including shutdown failure. SIGINT during startup GET and generation is covered with
real subprocess tests. Cancelled pre-checkpoint startup emits its known reference and
operator stop without fabricating a world summary. Request-budget transient states
wait for the service's normal budget Stop; provider pauses become explicit failures
without Retry. Final summaries read archive checkpoint zero, latest checkpoint, and
the latest attempt_finished journal outcome after shutdown.

Standalone `load_archived_inspection` opens read-only, loads retained inputs and the
selected snapshot, creates an ephemeral SnapshotRepository engine, binds retained
scenario/definitions, and verifies exact encoded-world equality. Only requested
inspection uses the existing serve hook/GET-only app. It never constructs a runtime
controller, acquires a writer lease, steps, repairs storage, or contacts a provider.
The existing scenario/database inspector stays intact.

NPC prompts, perception, filtered context, cognition proposals, gateway validation,
engine authority, manager/system ownership, immutable events, persistence format and
catalog/service implementations were not changed. Operator inspection still uses the
existing engine-facing GET endpoints. No new NPC-visible pathway was introduced.

## Exact edit boundary

Seven worker-owned paths were edited, all in `.worktrees/live-npc-ln07e`:

- `src/living_world/cli.py`
- `src/living_world/runtime/entrypoints.py` (new)
- `tests/test_runtime_cli.py` (new)
- `tests/test_runner_cli.py`
- `tests/test_founders_cli.py`
- `docs/canonical_founders.md`
- this report

No VCS/index/worktree operations, subagents, installs, real model calls, full make,
examples, or other-checkout writes were performed. CLI executions were pytest unit
fixtures in temporary directories; no ad-hoc normal acceptance archive was created or
deleted. Root owns persisted normal acceptance and its evidence location.

## TDD and validation evidence

All pytest commands used `PYTHONPATH=src` and
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`
(the same interpreter is denoted `$TASK_PY` below).

- Baseline: `-m pytest tests/test_runner_cli.py tests/test_founders_cli.py -q`:
  **52 passed**.
- Initial RED: `-m pytest tests/test_runtime_cli.py -q`: **1 failed, 5 passed**;
  archive resume failed because `--resume-attempt` did not exist.
- Initial implementation regression run: runtime/runner/founders CLI slice:
  **16 failed, 42 passed** because omitted continuous intent reached the legacy
  runner as None. Normalizing the legacy collaborator input restored compatibility.
- GREEN: `-m pytest tests/test_runtime_cli.py tests/test_runner_cli.py
  tests/test_founders_cli.py -q`: **58 passed**.
- Fake live provider/request-budget/offline replay/provider failure and real
  subprocess SIGINT GET/generation slice: runtime CLI **12 passed**.
- Expanded runtime/selected new legacy/founders tests: **22 passed, 1 failed**;
  FastAPI TestClient required absent httpx/httpx2. Replaced that test harness with
  real uvicorn plus stdlib HTTP, without installing dependencies. Its focused rerun:
  **1 passed**. Expanded runtime-only run later: **28 passed**.
- Self-review RED: `-m pytest tests/test_runtime_cli.py::test_replay_inherits_source_mirror_cadence
  -q`: **1 failed**, source cadence four was replaced by one. Source cadence
  inheritance fix: **1 passed**.
- Self-review RED: `-m pytest tests/test_runtime_cli.py::test_invalid_catalog_root_errors_are_closed_codes
  -q`: **2 failed**, catalog-construction errors escaped as human exception text.
  Archived-only safe error mapping fix: **2 passed**.
- Prior five-file focused gate: **129 passed**, then **139 passed** after additional
  edge cases and replay cadence coverage. The final current-tree gate is recorded
  below after the last safe-error correction.

Final current-tree command:

```text
PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_cli.py tests/test_runner_cli.py tests/test_founders_cli.py tests/test_runtime_service.py tests/test_runtime_restart.py -q
```

Final result: **141 passed in 57.95 seconds**, no warnings reported.

Scoped checks use `$TASK_PY -m ruff check` and `$TASK_PY -m black --check` on the
five changed Python files: **both passed**, Black found all five unchanged.
A Python scoped whitespace/conflict-marker check over all seven worker paths:
**passed, seven files, zero findings** (final newline/trailing whitespace/conflict
markers). VCS-based `git diff --check` remains a root gate. Successful command
output is intentionally not copied.

## Self-review and remaining root gates

Self-review checked explicit/default option handling, exact raw resume config,
restricted fork fields, alias/digest handling, retained-input ownership, announcement
identity, startup cancellation readiness, watcher exception/cleanup handling, budget
pause races, closed failure mapping, final archive snapshot/journal selection,
read-only reconstruction, existing hooks, and documentation limitations. Replay
cadence and early catalog error sanitization were corrected with regression tests.

Coverage includes all three canonical recorded outcomes and checkpoint-zero child
resume, generic no-tape child resume/fork, changed config refusal and source byte
preservation, actual continuous intent, missing server/model, changed digest pin,
provider failure without retry, request-budget stop, offline replay, real SIGINT
during GET/generation, preexisting Stop, broken trusted control, fallback failures,
read-only archive bytes/mtime, absent inspection worlds, actual HTTP GET/POST behavior,
and initial archive checkpoint selection after publication-cache eviction.

Root still must independently review SPEC and QUALITY, resolve findings/re-review,
run authoritative full task and merged-tree `make`, separate `make examples`,
`git diff --check`, exact recorded matrices, and persisted normal CLI acceptance.
Browser controls and final serve acceptance remain LN08 work; installed-Ollama
acceptance belongs to LN09. No
claim is made that LN07 as a whole is complete or that a real installed model was
accepted in this worker stage.

## Independent review correction 1 — final shutdown truth

Root independent SPEC/QUALITY review found a P1 error in the result consumer:
`run_archived` retained terminal status observed before owner shutdown. A final
mirror failure during join could therefore be summarized as successful completion
or operator Stop even though the archive recorded failed/mirror_failed. The earlier
self-review and 141-test gate did not catch this race.

Read the appended root contract and saved-prompt correction before editing. Scope
remained the same seven paths; this round changes `entrypoints.py`,
`test_runtime_cli.py`, this report, and the canonical guide acceptance-stage wording. No index or VCS operations were performed.

Correction: after successful `service.shutdown()` join, obtain fresh immutable
`controller.status()` and apply the existing failure check before reading outcomes
or constructing any success result. Mirror failure consequently returns exit 4 with
safe `mirror_failed` and its original attempt reference; archive checkpoints remain
authoritative. No service/catalog change was needed.

Added deterministic completed and operator-stopped regressions. The final mirror
blocks on a main-thread shutdown Event and then raises OSError. The stopped case
also gates the owner loop on cooperative shutdown, ensuring a real STOPPED status
precedes final failed settlement. Both cases verify failed archive lifecycle, final
attempt_finished failed/mirror_failed, last complete checkpoint/revision, unchanged
source bytes, exit 4, safe error, exactly one known attempt announcement, and empty
success stdout. Synchronization uses Events, not timing-only sleeps.

- RED: `$TASK_PY -m pytest tests/test_runtime_cli.py::test_final_mirror_failure_after_terminal_observation_is_not_success -q`
  with `PYTHONPATH=src`: **2 failed**; both returned zero despite verified archived
  mirror failure.
- GREEN: same command after the post-join status refresh: **2 passed**.
- Final current-tree five-file focused suite (same command listed above):
  **143 passed in 58.25 seconds**, no warnings reported.
- Scoped Ruff and Black checks over the five changed Python files: **passed**;
  Black found all five unchanged. Scoped seven-file whitespace/conflict-marker
  check: **passed, zero findings**.
- Corrected acceptance-stage wording in this report and the canonical guide:
  browser/serve acceptance is LN08; installed-Ollama acceptance is LN09.

Correction self-review checked that failure handling precedes result construction,
post-join status is immutable and observer-only, known references and complete
archive snapshots are retained, and no writer/service ownership boundary changed.
Root re-review and full task/merged gates remain required.


## Root task acceptance — October 22, 2026

Independent review initially found one P1: stale terminal status after owner shutdown
could report success despite failed final mirror. Root amended the exact task/prompt
before correction. Scoped re-review: P1 ADDRESSED, SPEC PASS / QUALITY PASS, zero
open findings, NO SUBSTANTIVE FINDINGS. Final focused143passed; source/test correction
is unchanged after review. Nine changed delivery paths before common docs: seven
worker paths plus two root-owned task/prompt amendments; no boundary expansion.

- `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`: PASS, 2055 tests passed / 10 existing deliberate skips, 39 examples.
- Separate `make examples` with the same VENV: PASS, 39 examples.
- `git diff --check`, staged whitespace and `git diff --exit-code -- src tests`: PASS.
- Exact canonical recorded matrix: PASS, full schema-12 success/stall/failure payloads
  match LN07d, two fresh runs/resume1/3/4/terminal zero-step cases. All26 normal
  CLI invocations retain readable complete archive checkpoints.
- New normal CLI acceptance: PASS, seven retained attempts (including two truthful
  failed/uninitialized cases); linked child initial world/driver/feedback exact,
  resumed tick2 and forked tick3 equal uninterrupted reference worlds, parent bytes
  unchanged, selected-checkpoint inspector exact/read-only. Evidence in ignored
  `ln07e-task-cli-recheck` with source-before hashes/results/invocations.
- Initial root helper used an invalid UUID for missing-source and stopped at parser
  validation. Corrected valid UUID and clean rerun passed; all original seven
  attempts and invocation/failure evidence remain in `ln07e-task-cli`. No deletion.

Evidence in ignored current-plan SDD workspace: `ln07e-review-1.diff`,
`ln07e-fix-1.diff`, review findings/final reports, `ln07e-task-make.log`,
`ln07e-task-examples.log`, `ln07e-task-matrix` and both CLI acceptance folders.
Task delivery is ready; feature merge and repeated merged gates remain required.
No browser/serve or actual installed-model acceptance is claimed (LN08/LN09).
