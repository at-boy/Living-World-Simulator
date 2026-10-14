# Task 22 — recorded proposal tapes delivery report

Status: DONE for worker delivery on 2026-10-14; ready for independent review.
Independent review round 1 requested one P2 Unicode correction, now implemented
and ready for re-review. A root full-gate compatibility failure also required
the narrowly authorized work-phase retry-test correction recorded below.
This is not root acceptance, full validation,
integration, or release approval.

## Authority and pause history

Work is preserved uncommitted in `.worktrees/task22` on
`task/22-recorded-proposals`, HEAD `87970a1`, based on reviewed Task 21 checkpoint
`b055619`. The binding Task 22 plan, saved prompt and accepted ADR-0025 governed
implementation. Root amended the plan/prompt before the two schema-12 assertions
in `tests/test_settlement_stages.py`, before explicit direct-engine preparation
guards, before the narrow cursor/event-history clarification correction, and
before the named work-phase retry-test compatibility correction. No worker staging, commits, branches, merges, pushes, agents, config or
main changes occurred.

The user paused implementation at the five-hour usage boundary on 2026-10-14.
Root preserved a paused report before worker delivery was complete. At that
pause the last reported focused matrix was 398 passing tests, including 84 new
replay cases; those were historical worker results, not root verification.
The last global actor-order test had been saved before interruption. After the
user resumed with the allowance reset, the worker inspected the preserved
report/status, completed this report and reran the focused checks. Implementation
was not restarted. The initial resumed delivery matrix was 399 passing tests, including 85 replay
cases. Root then resolved the recorded cursor/history question by amending the
plan/prompt before a narrow manager/test correction. The clarified
delivery matrix was 412 passing tests, including 98 replay cases. After
independent review round 1, the narrow Unicode correction and its ten regression
cases bring the final worker matrix to 422 passing tests, including 108 replay
cases.

## Delivered behavior

- Strict safe-YAML version-1 tapes contain frozen ordered decisions and public
  actor labels. Duplicate/non-string YAML keys, unknown/missing fields, malformed
  shapes, bool-as-int, invalid ID-bearing prose and sequence gaps/reordering fail
  with fixed payload-free `ProposalTapeError` codes. Canonical UTF-8 JSON hashes
  normalized decisions with explicit nulls and preserved Unicode codepoints.
- The stateless per-entry cognition client receives only filtered `NPCContext`,
  ordinary offered vocabulary and expected entity-name identity. It never
  receives a world, ID binding, cursor, inspector, manager, handler or provider.
  Duplicate names do not change engine holder binding.
- Scenario runtime owns fresh label-to-entity bindings and validates resumed
  label/definition membership without requiring unchanged names. Historical
  mapped entities cannot be removed. Pending replay actors cannot be destroyed;
  destruction after their last entry remains subject to existing domain guards.
  Populated-world protection now includes all persisted collections.
- `ReplayManager` owns immutable binding/cursor records, exact reconfiguration,
  tick/index invariants and one resolution event per consumed entry. Accepted,
  rejected and speech-only decisions consume; invalid proposals/exceptions do
  not. Resolution events contain only sequence, actor label and outcome. Event
  failure restores the old cursor and removes only new transaction events.
- A replaceable proposal slot runs after ordinary systems and before work,
  consequences, needs, goals and stages. One global tape entry is attempted each
  tick. Read-only providers supply canonically ordered vocabulary with exactly
  one handler owner per offered key; ordinary `DecisionEngine` and
  `NPCActionResolver` retain proposal validation and domain action authority.
  Exhausted tapes idle. Speech is not automatically injected into cognition.
- Exceptions escaping any scheduler phase mark a process-local failed tick,
  retain the original cause and refuse subsequent step/run/save. Recovery loads
  the complete prior checkpoint; no generic world rollback is claimed.
  Preparation errors and repository save failures do not independently poison
  the engine; inspection and direct manager access remain available.
- Runner preparation atomically configures binding/cursor and replaces the
  proposal slot. Replay-bound engines require matching controlled preparation
  before direct advance/save and runner finish, including zero-tick/exhausted
  runs. Finalization precedes stopping saves. Final limits/terminal stops reject
  unused entries; operator stops and explicit checkpoint-only bounds keep
  resumable leftovers. Ordinary runner/CLI output stays compatible.
- SQLite schema 12 persists labels and replay records in the same atomic
  snapshot as domain effects. Schemas 1–11 load empty labels/absent replay and
  never infer bindings. Strict replay fields, fingerprints, references,
  cursor/tick relations, live pending actors and exact cursor/resolution-event
  correspondence are validated after records load.
  A failed save preserves the previous snapshot.
- Detached operator inspection exposes replay binding/cursor/label mappings at
  GET-only `/world/replay` and `replay_configured` in the summary. State-aware NPC
  filtering rejects fingerprints, internal binding values, replay numeric data
  and privileged field names, while public label keys are not hidden by default.
- Example 038 uses an engine-authored greeting handler through `EntityManager`,
  filtered context and a read-only provider, then resumes a speech-only entry.
  Literal assertions verify accepted/no_action outcomes, durable effects and
  absence of automatic memory injection.

## Inspected changed files

New implementation:

- `src/living_world/replay/__init__.py`
- `src/living_world/replay/model.py`
- `src/living_world/replay/loader.py`
- `src/living_world/replay/client.py`
- `src/living_world/replay/manager.py`
- `src/living_world/replay/system.py`
- `src/living_world/replay/runtime.py`
- `tests/test_recorded_proposal_tapes.py`
- `examples/038_recorded_proposal_tapes.py`

Integration:

- `src/living_world/state/world_state.py`
- `src/living_world/scenarios/runtime.py`
- `src/living_world/managers/entity_manager.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/running/runner.py`
- `src/living_world/running/__init__.py`
- `src/living_world/cli.py`
- `src/living_world/api/inspection.py`
- `src/living_world/api/server.py`
- `src/living_world/cognition/information_boundary.py`

Existing test expectations:

- `tests/test_inspection_api.py` adds the summary's replay-configured flag.
- `tests/test_scenario_run_contract.py`, `tests/test_spatial_domain.py` and
  `tests/test_sqlite_repository.py` expect schema 12 on forward writes; SQLite's
  unsupported-version fixture advances to 13.
- `tests/test_settlement_stages.py` changes only the two current-schema
  assertions from 11 to 12, under the prior root amendment.
- `tests/test_work_execution.py` changes only
  `test_failed_construction_phase_preserves_next_entity_relationship_and_event_ids`
  under the root full-gate amendment. The injected failure and retry now call
  `WorkExecutionSystem.step(engine.state)` directly. All rollback, next-ID and
  successful-completion assertions remain unchanged; the modified helper and
  fixture arguments are explicitly typed.

Documentation and task artifacts:

- `CHANGELOG.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/npc_information_boundary.md`
- `docs/project_journal.md`
- `docs/backlog.md`
- `docs/subagent_execution_plan/v0_6/22_recorded_proposal_tapes.md`
- `docs/subagent_execution_plan/v0_6/22_recorded_proposal_tapes-prombt.md`
- this report

ADR-0025 was accepted before implementation and remains the authoritative
architectural record; it required no implementation-time amendment.

## Red/green and correction evidence

Tests were introduced before the corresponding loader/model, manager/engine and
runtime integration. Initial red collection checks explicitly reported the
missing replay package/modules; they were feature-absence collection errors,
not assertion failures. First loader/model green: 6 tests; manager/failure-guard
green: 8 tests. Runtime/persistence then produced two substantive red assertions:
resume lost the scenario label map and saved replay cursor. Schema-12 persistence
made the initial 12 replay cases green.

An inspection/CLI red pair demonstrated the missing replay inspection method
and unrecognized tape/checkpoint flags. A direct-engine resume red demonstrated
that missing preparation entered ordinary systems; the configuration guard now
rejects before ticking. A substantive operator-terminal red showed finalization
incorrectly rejected operator leftovers; finalization now recognizes
`operator_stop` terminal selection as an operator stop. The full focused matrix
also exposed stale schema-11 expectations and the new summary flag; the permitted
expectations were updated without changing domain behavior.

Additional literal regression cases cover shape/vocabulary/ownership failure,
context isolation, transaction rollback, exact phase order, atomic slot install
failure, idempotent/changed preparations, schemas 1–11 defaults, nine schema-12
corruption cases, failed-save preservation, complete late-tick recovery,
zero-tick/operator/finalization ordering and fresh/resumed snapshot convergence
at checkpoint positions 0, 1, 2 and 3. The final actor-order case confirms the
explicit global sequence with duplicate names and consumed/pending actor
lifecycle behavior.

Transient development issues were corrected: eager model/state imports caused
an import cycle (replay type imports in WorldState are now type-checking-only),
test helper names caused collection warnings (renamed), and a trial FastAPI
TestClient import required unavailable `httpx2` (removed in favor of existing
route metadata checks; no dependency change). Formatting/import and one
single-element-slice lint finding were corrected. Root's pre-review clarification additionally required cursor/history bijection.
Thirteen new regressions first failed with missing rejection, then passed after
complete-state validation was added to `ReplayManager`. They cover missing,
duplicate, gapped or extra resolution evidence, wrong/future ticks, actor/subject
mismatch, unexpected/missing attributes, invalid outcome, bool sequence and
contradictory reserved history during configuration. Next-state prevalidation
before event creation is exempt. Existing checkpoint/resume and no-binding
legacy behavior remain green.

Independent review round 1 found one P2 strict-input defect: escaped lone
surrogates could pass loader/direct tape validation and later raise a raw
`UnicodeEncodeError` when fingerprinted. Root accepted the finding. Eight YAML
field regressions and one direct-construction regression first failed because no
`ProposalTapeError` was raised; a supplementary-Unicode preservation case passed
as an existing-behavior control. `ProposalTape.__post_init__` now validates the
same canonical UTF-8 byte representation used for hashing before accepting a
tape. Invalid encoding raises fixed `invalid_tape` diagnostics with suppressed
cause; accepted codepoints remain unchanged and are never Unicode-normalized.
The ten-case correction selection passed after the fix. Scope is limited to the
model, replay tests and this report; re-review remains pending.

## Focused validation after review-round-1 correction

All project imports use `PYTHONPATH=src`; the worktree venv contains dependencies
without an editable project install.

- `PYTHONPATH=src .venv/bin/pytest -q tests/test_recorded_proposal_tapes.py tests/test_runner_cli.py tests/test_scenario_run_contract.py tests/test_simulation_engine.py tests/test_simulation_scheduler.py tests/test_sqlite_repository.py tests/test_spatial_domain.py tests/test_inspection_api.py tests/test_npc_information_boundary.py tests/test_settlement_stages.py`
  — PASS, 422 tests, zero skips and no reported warnings (108 replay cases).
- `.venv/bin/ruff check src tests examples/038_recorded_proposal_tapes.py`
  — PASS, no findings.
- `.venv/bin/black --check src tests examples/038_recorded_proposal_tapes.py`
  — PASS, 199 files unchanged.
- `PYTHONPATH=src .venv/bin/python examples/038_recorded_proposal_tapes.py`
  — PASS, all example assertions; no reported warnings.
- `git diff --check` — PASS, no whitespace findings.

The worker did not run the full repository `make` or separate `make examples`;
the binding contract assigns those authoritative gates to root after independent
review and corrections, then again after milestone integration.

## Root full-gate compatibility correction — round 2

Root's authoritative `make` attempt reported 1 failed, 1193 passed and 10
existing skips. The sole reported failure was
`test_work_execution::test_failed_construction_phase_preserves_next_entity_relationship_and_event_ids`:
the old test retried `engine.step()` after its injected failed tick, conflicting
with Task 22's explicit failed-engine refusal/reload contract. This was a root
full-gate result, not a worker full validation claim.

Root amended the plan and saved prompt before expanding scope to only this
named test. The worker reproduced its red result: the retry raised
`FailedTickError` with the retained injected completion failure. The test now
composes a typed `WorkExecutionSystem` and calls its phase-local `step` directly
for both injection and retry. All original rollback, next-entity/relationship ID
and successful completion assertions are preserved. No production work code or
other work tests changed. Existing replay regressions continue to verify whole
engine step/run/save refusal and checkpoint reload independently.

Final focused checks for this narrow correction:

- `PYTHONPATH=src .venv/bin/pytest -q tests/test_work_execution.py tests/test_recorded_proposal_tapes.py`
  — PASS, 138 tests (30 work-execution cases and 108 replay cases), no skips or
  reported warnings.
- `.venv/bin/ruff check tests/test_work_execution.py` — PASS, no findings.
- `.venv/bin/black --check tests/test_work_execution.py` — PASS, file unchanged.
- `git diff --check` — PASS, no whitespace findings.

The earlier 422-case focused matrix remains recorded above. The worker did not
repeat full `make` or `make examples`; independent re-review and the root full
rerun are pending. A focused pass is not a correction of the recorded root full
gate until root reruns that gate.

## Limitations and integration status

- The previously flagged historical cursor/event interpretation is resolved by
  root's 2026-10-14 plan/prompt clarification and the narrow correction. Complete
  state requires exactly resolution sequences 1 through cursor, configured-tick
  arithmetic, mapped actor/subject, exact attributes and closed outcomes. Legacy
  history with no binding never invents progress; contradictory reserved history
  prevents replay configuration.
- Label history has no public deletion/clear API. Legacy populated saves lacking
  labels cannot enable replay by guessing IDs from names or entity order.
- Failed ticks require reload; this is not an in-memory whole-world transaction
  framework. Trusted Python offer factories are a typed composition boundary,
  not a sandbox for arbitrary application code.
- Default CLI offers support speech-only tapes. Canonical founders content,
  goal/stage terminal composition, UI, live providers and release work remain
  outside Task 22 scope.
- Independent re-review and task-tree root validation are complete. Milestone
  integration and merged validation follow in the orchestrator checkpoint.
  This task does not establish whole-milestone acceptance.


## Root acceptance — 2026-10-14

Independent spec and quality review passed with NO SUBSTANTIVE FINDINGS after
the Unicode correction and the exact allowed work-phase compatibility test
correction. Root inspected both correction diffs and dispositioned the initial
findings; no finding was waived. Root accepts Task22 for milestone integration.

Task-tree authoritative validation after all corrections:

| Command | Result |
| --- | --- |
| `make` | PASS; Ruff/Black passed,1194 tests passed,10 existing deliberate skips; examples001–038 passed |
| Separate `make examples` | PASS; examples001–038 |
| `git diff --check` and `git diff --cached --check` | PASS |

The initial full-gate1193-pass/1-fail result remains recorded above; the fresh
1194-pass result supersedes it for acceptance. No new unexplained warnings or
skips were reported. Root retained the intentional failed-engine reload boundary
and all original work-phase rollback/ID assertions. Main remains outside scope.

## Milestone integration

Task22 delivery `02b35fe` merged into milestone/v0.6 as `7806f29`. Root repeated
make using VENV=.worktrees/task22/.venv:1194 passed,10 existing skips and
examples001–038; separate examples passed. Whitespace checks passed. No main
integration or tagging occurred. Live remote verification is recorded in the
orchestrator continuation checkpoint.
