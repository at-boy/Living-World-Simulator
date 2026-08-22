# Continuation brief — August 22, 2026

## Current repository state

The v0.6 autonomous founding-settlement milestone is authorized and active.
Work uses a pushed milestone branch plus one pushed branch per isolated task.
Reviewed task branches are merged only into `milestone/v0.6`; `main` must not
be changed.

At this handoff checkpoint:

- current branch: `milestone/v0.6`;
- last implementation merge: `0b6760f` (`Merge Task 20a work action gateway`);
- implementation baseline on `milestone/v0.6` and its origin: `0b6760f`; this
  checkpoint-only documentation update follows that merge;
- `origin/main`: `12f2f17` and intentionally unchanged;
- worktree: clean after the reviewed Task 20 merge;
- next authorized task: Task 20b, subject to a fresh orchestrator checkpoint
  and a decision-complete review of its plan and saved prompt;
- Task 20 is independently reviewed, validated, committed, merged, and pushed;
- Task 20a is independently reviewed, validated, committed, merged, and pushed;
- Task 20b has not started.

Always verify these statements with `git status --short`, `git branch -vv`, and
recent history before acting. The repository is authoritative if external
state has changed.

## Completed v0.6 sequence

The following tasks were implemented on pushed task branches, independently
reviewed, corrected where necessary, validated, committed, merged with
`--no-ff`, and pushed to `milestone/v0.6`:

| Task | Result | Milestone merge |
| --- | --- | --- |
| 16 | Versioned YAML scenario/run identity and deterministic initial graph | `808bdde` |
| 16a | Bounded/continuous runner, checkpoints, resume, and CLI | `ca5b75c` |
| 15a | Canonical two-dimensional spatial ADR | `a6d77a9` |
| 15b | Spatial domain, schema-v3 persistence, and inspection | `2e43ada` |
| 17 | Partial external-world references and schema-v4 persistence | `c909d8a` |
| 17a | Deterministic dispatch lifecycle, gateway, and schema-v5 persistence | `9c006fc` |
| 18 | Engine-owned goals/objectives, schema-v6 persistence, inspection, and filtered interpretations | `0fe099d` |
| 18a | Deterministic criterion evaluation, lifecycle transitions, and evidence | `033ed60` |
| 15d | NPC-safe qualitative spatial and direct-road perception | `43405ee` |
| 19 | Settlement needs, sustained pressure evaluation, schema-v7 persistence, inspection, and filtered interpretations | `a3f4bc5` |
| 19a | Consumption, storage/spoilage, maintenance consequences, and schema-v8 persistence | `bba7549` |
| 20 | Authoritative work orders, aggregate reservations, schema-v9 persistence, inspection, and filtered interpretations | `bb9fa53` |
| 20a | Actor-bound proposal-to-work gateway, authoritative preflights, and self-volunteering | `0b6760f` |

Task reports under `docs/subagent_execution_plan/v0_6/` contain exact files,
interfaces, review corrections, and validation evidence. ADR-0015 through
ADR-0022 capture the scenario, spatial, partial-world, dispatch, goal, need,
work-order, and proposal-gateway contracts.

SQLite snapshot support now spans schema versions 1 through 9. The v0.6
progression is run identity in schema 2, spatial placements in schema 3,
external references in schema 4, external dispatches in schema 5, goals and
objectives in schema 6, settlement needs in schema 7, and consequences in
schema 8, followed by work definitions, states, and reservations in schema 9.
Legacy versions load newer collections as empty and write forward.

## Current validation baseline

The final reviewed Task 20a delivery passed:

| Command | Result |
| --- | --- |
| Focused Task 20a named-file matrix | 295 passed; 10 deliberate Task 20 matrix skips |
| `make` | Ruff and Black passed; 893 pytest tests passed, 10 deliberate skips; examples 001–035 passed |
| `make examples` | Examples 001–035 passed |
| `git diff --check` | Passed |

These results are a checkpoint, not a substitute for rerunning validation on
future task branches.

## Next task: Task 20b

Task 20b is next because Task 20a is reviewed, merged, and pushed. Its current
artifacts are:

- `docs/subagent_execution_plan/v0_6/20b_work_execution.md`
- `docs/subagent_execution_plan/v0_6/20b_work_execution-prombt.md`

Before Task 20b implementation, reconcile its high-level plan and prompt against
the merged Task 20 work lifecycle/reservation contract, Task 20a proposal
boundary, existing scheduler phase order, and each authoritative domain-effect
manager. The contract must bind automatic selection, labor availability,
undercollateralization, charge-once semantics, progress arithmetic, blockage and
recovery, exact domain effects for all six categories, events, rollback,
save/resume, scheduler placement, tests, and allowed files.

## Remaining approved sequence

Continue one reviewed task at a time in this order:

1. Tasks 20, 20a, and 20b — work records, proposal gateway, and execution.
2. Task 21 — settlement development stages.
3. Task 22 — deterministic recorded proposal tapes.
4. Tasks 15 and 15c — FastAPI-hosted inspector and spatial view.
5. Task 23 — canonical success, stall, and failure founders scenarios.
6. Task 24 — milestone release-readiness closeout.

Task 24 leaves `milestone/v0.6` ready for owner integration. It does not merge
or push anything to `main`.

## Branch, review, and delivery rules

- Start each task from the current reviewed milestone head and push the task
  branch immediately.
- Execute or delegate only one documented task at a time.
- Every implementation task requires its existing plan and `-prombt.md`, plus a
  truthful `-report.md` before approval.
- Independently inspect every delivery. Require corrections for behavior,
  strict typing, tests, report accuracy, file-boundary compliance, persistence,
  or NPC-boundary defects.
- Run focused tests while correcting, then `make`, separate `make examples`,
  and `git diff --check` before approval.
- Commit and push only reviewed work, merge with a descriptive `--no-ff` commit
  into `milestone/v0.6`, and push that branch.
- Never commit, merge, or push to `main` during this milestone workflow.

## Non-negotiable architecture

Preserve this authority and information flow:

`WorldState -> perception -> immutable cognitive records -> filtered NPC
context -> cognition proposal -> action gateway -> world event/state change`

NPC-facing input must never contain raw `WorldState`, internal record/entity
IDs, privileged inspection DTOs, unrestricted attributes, another NPC's hidden
cognition, exact hidden criteria/policy, or arbitrary runtime objects. Model
output remains an untrusted proposal until the gateway and domain manager
validate and apply it.

Recent concrete boundaries to preserve:

- exact spatial coordinates and containment are privileged engine truth;
- external references are deliberately partial, not simulated remote places;
- dispatch IDs, costs, delays, reliability, seed calculation, reservations,
  and outcomes are engine-only;
- NPC dispatch proposals choose only engine-authored qualitative labels;
- filtered goal interpretations in Task 18 must hide internal IDs, exact
  criteria, evidence, and authoritative status unless legitimately perceived.
- need definitions, owners, thresholds, quantities, pressure, windows, and
  history are privileged; NPCs receive only selected qualitative need prose;
- Task 19 assessment runs after ordinary systems and before goal evaluation;
  Task 19a consequences must run before assessment and must use manager-owned
  authoritative mutation and immutable events.
- Task 20 reservations are engine-owned aggregate locks, not resource
  deductions or item identities; Task 20 adds no scheduler or execution path.

## Historical context

The v0.5 release and Tasks 01–14/14a/14b are complete and archived under
`docs/subagent_execution_plan/initial_v0_2_3_to_v0_5/`. The prior council and
local-model decisions remain documented in their reports and ADRs; do not
reconstruct them from chat history. The cross-milestone index is
`docs/subagent_execution_plan/README.md`, and the approved v0.6 objective and
sequence are in `docs/subagent_execution_plan/v0_6.md`.
