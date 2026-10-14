# v0.6 milestone completion plan

Date: 2026-10-07
Status: owner-approved execution on 2026-10-13; Phase0 and Tasks21–22 and15 completed.
Release version confirmed by owner: `0.6.0rc1`. Task15c is next.

**Goal:** Complete the autonomous founding-settlement vertical slice on
`milestone/v0.6`, with reproducible success, stall, and failure runs,
checkpoint/resume equivalence, explanatory read-only inspection, and a reviewed
release-readiness handoff to the owner.

**Architecture:** Preserve the existing manager/system/event architecture.
NPCs receive filtered interpretations and submit untrusted proposals through
the action gateway. Engine-owned objectives, needs, work, dispatches, and stages
determine outcomes; inspection remains privileged and read-only.

**Tech stack:** Python >=3.11, current Python development environment, strict
typing, dataclasses/protocols, SQLite snapshots, YAML, FastAPI, and packaged
HTML/CSS/JavaScript without a Node toolchain.

**Binding specifications:** `v0_6.md`, each task plan and matching `-prombt.md`,
`../development_rules.md`, `../npc_information_boundary.md`, and repository
`AGENTS.md`. This document coordinates delivery. It does not replace the
decision-complete implementation contracts or authorize a new correction task.

## Verified starting point

- Integration branch: `milestone/v0.6`, commit `32bc83e`.
- Last implementation merge: Task 20b, `5489b73`.
- Stable `main`: local and cached origin reference at `12f2f17`.
- Completed task sequence: 16, 16a, 15a, 15b, 17, 17a, 18, 18a, 15d, 19,
  19a, 20, 20a, and 20b.
- Task 21 branch contains committed contract refinement `69656ca`, based on
  `32bc83e`, including ADR-0024 and the expanded plan/prompt. There is no
  committed Task 21 implementation.
- Git registers `/tmp/living-world-task21`, but that checkout is absent. Its
  uncommitted contents, if any existed, cannot be inferred from Git history.
- The primary checkout has one user-owned unstaged change:
  `.codex/config.toml`, adjusting three agent configuration paths. Preserve it
  and exclude it from implementation commits.
- Live remote verification failed because SSH reported bad ownership or
  permissions on `/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf`. Cached
  upstream references are not proof of current remote synchronization.
- Last recorded validation: 927 tests passed, 10 deliberate skips, examples
  001–036 passed. These historical results are not fresh completion evidence.

## Constraints and review priorities

- Never commit, merge, tag, or push v0.6 to `main`; owner integration is separate.
- Work on one isolated task branch at a time, from the reviewed milestone head.
- Plans, prompts, and reports must name exact allowed files before execution.
- Managers own mutation, systems own behavior, and events are immutable.
- No raw state, internal IDs, hidden thresholds, or privileged inspector DTOs
  enter NPC context. Tape content has the same trust boundary as model output.
- Review crash/retry and checkpoint behavior so a proposal cannot be charged or
  executed twice or silently skipped after resume.
- Review scenario identity and label binding so changed configuration or tape
  content cannot resume an incompatible save.
- Review tick-boundary ordering so objectives, stage promotion, checkpointing,
  and terminal evaluation describe the same completed simulation state.
- Review partial initialization and failed saves so an invalid scenario cannot
  leave a half-configured world or replace a valid checkpoint.
- Review UI error states and detached payloads so operators can distinguish
  unavailable data, stalled progress, and authoritative terminal failure.

## Phase 0 — Restore a trustworthy execution starting point

- [x] Recheck branch tips, primary checkout changes, and registered worktrees.
- [x] Recover Task 21 from its existing branch into a durable isolated checkout;
  reconcile any recoverable artifacts before removing stale worktree metadata.
  Do not recreate the plan from the older milestone copy or reset the branch.
- [x] Check agent configuration path resolution in the actual execution
  environment. Treat the existing edit separately from milestone implementation.
- [x] Restore authorized remote access and read live remote tips before any
  push. Report any continuing limitation; do not claim a pushed delivery.
- [x] Run a non-mutating baseline with `make check`, `make examples`, and
  `git diff --check`. Record failures before implementation and classify them
  rather than silently absorbing unrelated repairs into Task 21.
- [x] Inspect the complete refined Task 21 plan, prompt, ADR, and directly
  relevant interfaces. Confirm its task branch still descends from the reviewed
  milestone head.

Exit: recoverable Task 21 planning work preserved, baseline known, user edit
preserved, branch provenance clear, and any remote blocker recorded.

## Phase 1 — Task 21: settlement development stages

Use the expanded contract on `task/21-settlement-development-stages`, not the
shorter plan currently present on the milestone branch.

- [x] Reconcile criterion evaluators, goal ownership, maintenance records,
  lifecycle guards, scheduler order, persistence, and information filtering
  against the current implementation before assigning code.
- [x] Implement the specified immutable stage records and manager-owned
  `founding_camp -> settlement -> town` transitions.
- [x] Implement objective-backed requirements, population and maintained
  capability criteria, one adjacent promotion per tick, idempotence, and
  stage-phase rollback after goal evaluation.
- [x] Deliver schema-11 persistence/migration, detached GET-only inspection,
  explicitly selected qualitative NPC prose, and example 037.
- [x] Prove both promotions, independently blocking requirements, invalid and
  population-only configuration, lifecycle guards, rollback, legacy loading,
  failed-save preservation, scheduler order, and save/resume equivalence using
  the exact test matrix in the refined task contract.
- [x] Independently review, correct, validate, report, and integrate.

Exit: stage progression is durable and engine-owned; Task 22 starts only from
the reviewed Task 21 milestone merge.

## Phase 2 — Task 22: recorded proposals and replay integration

Completed under the refined Task22 plan/prompt and ADR-0025.

- [x] Specify exact tape schema, scenario/tape identity binding, actor-label
  mapping, offered-action matching, sequence ordering, exhaustion, unused
  entries, safe diagnostics, and public interfaces.
- [x] Specify who schedules actor decisions and when, relative to ordinary
  systems, work execution, need/goal/stage evaluation, and checkpointing.
- [x] Specify a durable replay cursor and its atomic relationship to accepted,
  rejected, and failed proposals. Assign persistence ownership and migration
  explicitly; do not use a process-local cursor as resume evidence.
- [x] Separate engine-side actor binding from the cognition adapter. The
  adapter receives only `NPCContext` and offered `ActionOption` values and
  returns ordinary untrusted decisions; it never resolves internal IDs.
- [x] Assign concrete runtime/CLI composition hooks and allowed files so Task
  23 can select a tape without constructing a special engine in a test.
- [x] Implement loader, adapter, and agreed hooks through TDD and a numbered
  example; preserve the ordinary action-gateway validation path.
- [x] Test malformed tapes, identity mismatch, actor/action mismatch, gateway
  rejection, exhaustion/unused entries, cursor recovery, and uninterrupted vs
  resumed replay. Show diagnostics contain no hidden payloads or secrets.
- [x] Independently review, correct, validate, report, and integrate.

Exit: a bounded replay can run through public runtime interfaces and resume
without duplicated or skipped proposal execution. No live model is required.

## Integration ownership checkpoint before inspector implementation

Resolve these assignments in plans/prompts while preparing Tasks 22 and 23;
do not wait for acceptance testing to discover them:

1. **Initial domain setup:** `ScenarioRuntimeManager.bind()` currently creates
   definitions, entities, and relationships. Specify how canonical assets
   configure goals, needs, consequences, work, external dispatch setup, spatial
   placements, and stage programs through existing managers, atomically and
   idempotently on resume. Task 23 owns canonical setup; Task 21 deliberately
   excludes scenario-YAML stage configuration.
2. **Terminal outcomes:** `ScenarioRunner` currently accepts only tick-limit
   and operator-stop terminal names. Task 23 must receive explicit scope for
   engine-owned goal/stage success and configured failure interpretation, with
   deterministic precedence and inspectable evidence. Stall remains a bound
   reached without terminal success/failure. Exceptions are execution errors,
   not an invented simulated failure outcome.
3. **Replay normalization:** Specify exactly which operational metadata may
   differ across new/resumed runs. Never normalize away domain state, event
   order, work charges, transitions, or proposal cursor differences.
4. **Inspector access:** Specify how the operator inspects a bounded run's saved
   world and how a running engine is hosted. State process/snapshot freshness
   explicitly; do not imply a separate API process automatically observes a
   live runner's in-memory state.

Prefer amending existing Task 22/23 contracts if these are composition work
within milestone scope. If evidence establishes a separate prerequisite
capability, propose one isolated documented task with its own plan/prompt/report
and obtain authorization before adding it to the sequence.

## Phase 3 — Tasks 15 and 15c: operator inspection

Execute and merge separately, in that order.

- [x] Expand Task 15's contract with exact route, packaged asset paths, API-to-
  view mappings, ordering, refresh/freshness behavior, and browser test method.
- [x] Implement same-origin read-only views for world/tick, entities,
  relationships, resources, history, needs, goals, work, dispatches, and stages.
- [x] Test actual navigation/drill-down, loading/empty/error/unavailable states,
  accessible controls, read-only requests, DTO detachment, and installed-package
  asset availability. Static request-string inspection alone is insufficient.
- [x] Review, validate, report, and merge Task 15 before starting Task 15c.
- [ ] Specify and implement deterministic map scaling, labels, overlaps,
  unplaced entities, resizing, and entity click-through from detached spatial
  DTOs. Test empty and degenerate bounds and malformed/error responses.
- [ ] Review, validate, report, and merge Task 15c.

Exit: operators can explain domain state and inspect placement through a
packaged browser client without mutation requests or NPC integration.

## Phase 4 — Task 23: canonical founders acceptance

- [ ] Finalize the exact public scenario/setup format, three tape selections,
  CLI commands, seed, tick bounds, success/failure criteria, and stop precedence.
  The task contract must explicitly include the integration ownership above.
- [ ] Ship one canonical founding scenario with success, stall, and failure
  tapes using public labels and the reviewed managers/runtime interfaces.
- [ ] Success must sustain water, food, shelter, storage, and a homeland
  connection and reach `settlement`. Task 21 tests separately prove town
  promotion; canonical success need not grow to town.
- [ ] Stall must remain valid and runnable at its bound with explanatory
  blocked work/objective evidence and no false terminal result.
- [ ] Failure must follow configured engine-owned shortage, deadline, or
  viability criteria with events explaining its authoritative outcome.
- [ ] Run each documented command without a live model or manual per-tick
  intervention. Compare two fresh runs and checkpoint/resume at multiple ticks
  using byte-equivalent normalized final state, event history, and tape cursor.
- [ ] Exercise inspection for each outcome, including the causative event
  chain, not merely endpoint availability.
- [ ] Audit every proposal's filtered-context/offered-action/gateway route;
  exclude hidden criteria and internal IDs from tape-visible content.
- [ ] Isolate prerequisite defects in documented correction work rather than
  hiding them in scenario assets or widening the task silently.
- [ ] Independently review, run required validation plus all three scenarios,
  report commands/results/comparisons, and integrate.

Exit: the milestone's one-command acceptance target is demonstrated end to end.

## Phase 5 — Task 24: release-readiness closeout

- [ ] Perform one independent whole-milestone review against the acceptance
  target, including all task reports, merges, authority/information boundaries,
  schemas/migrations, APIs, UI, public exports, and installed assets.
- [ ] Resolve implementation defects in bounded correction tasks with fresh
  review and validation before resuming closeout.
- [ ] Use the owner-confirmed `0.6.0rc1` consistently across every release
  version surface. No tag is authorized.
- [ ] Update README/operator/API docs, release notes, changelog, journal,
  backlog, roadmap, milestone index, and continuation brief consistently.
- [ ] Re-run repository gates, all canonical outcomes, replay/resume comparisons,
  and wheel/install/import/CLI/static-asset smoke checks.
- [ ] Produce a requirement-to-evidence closeout report and list any remaining
  limitations. Unavailable tooling or failed remote access blocks the affected
  completion claim.
- [ ] Leave milestone implementation committed, reviewed, and pushed; verify
  live remote tips and confirm `main` was unchanged. Keep the user configuration
  edit separate; distinguish a clean release checkout from that known local edit.

Exit: `milestone/v0.6` is ready for separately authorized owner integration.
No merge to `main`, release tag, or v0.7 implementation is part of completion.

## Recommended working-method changes

Retain sequential task integration and independent per-task review. Parallel
implementation offers little benefit because these tasks share persistence,
runtime composition, documentation, and acceptance contracts.

1. **Durable isolation:** replace disposable `/tmp` task checkouts with managed
   or persistent worktrees. Preserve existing branch names and recover the Task
   21 branch; archive worktrees only after reviewed integration and verification.
2. **Contract first:** expand each short plan and saved prompt just before its
   implementation. Name exact interfaces, allowed files, failure semantics,
   schema changes, and tests. Resolve the integration checkpoint early.
3. **Use agents selectively:** one bounded worker plus one independent read-only
   reviewer for medium/large tasks. Use narrowly scoped explorers only for
   concrete unresolved questions; root retains architecture and integration.
   Small corrections can be root-owned but still receive relevant review.
4. **TDD and efficient gates:** focused tests while developing; full `make`,
   separate `make examples`, and `git diff --check` after review corrections and
   before approval. Re-run the required gate on the merged milestone before
   pushing/starting a dependent task. Amend contradictory older workflow/prompt
   language explicitly before reducing its prescribed repeated full runs.
5. **One validation owner:** the root owns authoritative final validation.
   Workers provide focused evidence and required delivery checks; reviewers
   inspect contracts/diffs and run focused checks when needed. Avoid redundant
   full runs on an unchanged tree unless mandated or evidence warrants them.
6. **Evidence and context:** report command, result, counts, warnings, reviewed
   commit, merge commit, and verified remote tip; keep successful logs out of
   reports. Update the continuation brief at every integrated task boundary.
   Start fresh root sessions for 21, 22, 15/15c, 23, and 24 as needed.
7. **Truthful acceptance:** describe recorded tapes as deterministic proposal
   drivers. They prove unattended engine execution and reproducibility; they
   do not establish that a live LLM autonomously chooses a successful strategy.

## Plan handoff

Recommended approach: task-by-task worker implementation with independent
review and root-owned integration, following the repository's task contracts.
Implementing everything in one long root session would reduce review isolation
and increase context and integration risk. Additional concurrent workers are
not recommended.

The owner approved execution and the proposed workflow on 2026-10-13.
Continue the documented dependency order without repeated authorization
questions. Detailed task amendments are reconciled and independently reviewed
before their implementation; scope expansion beyond the milestone remains a
separate authorization boundary.

## Execution checkpoint — 2026-10-13

Owner approved execution with "well sounds like a plan, take it from the top".
Phase 0 recovered Task 21 into `.worktrees/task21`, rebuilt its test environment,
verified live remote tips through a scoped SSH invocation and preserved the
user configuration edit. Native worktree creation succeeded but filesystem
permissions prevented edits there, so the writable project-local checkout is
the active implementation worktree.

Task 21 delivery `c821efe` was independently reviewed, corrected for strict
test annotations, validated, and merged as `1ab288b`. Both task and merged gates
passed 1086 tests / 10 existing skips and examples 001–037; live remote tips
confirmed the merge and unchanged `main` at `12f2f17`. Task 22 is next; its
contract amendments precede implementation.

## Execution checkpoint — 2026-10-14

Task22 delivery `02b35fe`, reviewed spec/quality PASS after safe Unicode validation
and exact work-phase compatibility-test correction, merged as `7806f29`. Root
task and merged gates1194 passed/10 existing skips, examples001–038; schema12
replay/event bijection enforced. Task15 contract independently CONTRACT READY;
transfer into isolated branch before code. Remaining sequence15,15c,23,24.
Owner resumed with hard usage boundary: stop before10% five-hour allowance
remains, save checkpoint and interrupt active workers with buffer.

Task15 deliverydea51cb, merge91e33bf: independent review PASS after four bounded
corrections; task/merged1229passed/10existing skips,31Chrome cases,examples001–038,
installed assets/routes and wide/narrow visual gates passed. Task15c draft final
contract/seam review CONTRACT READY; implementation follows isolated transfer.
