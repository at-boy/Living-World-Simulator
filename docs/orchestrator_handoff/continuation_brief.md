# Continuation brief — August 22, 2026

## Current repository state

The v0.6 autonomous founding-settlement milestone is authorized and active.
Work uses a pushed milestone branch plus one pushed branch per isolated task.
Reviewed task branches are merged only into `milestone/v0.6`; `main` must not
be changed.

At this handoff checkpoint:

- current branch: `milestone/v0.6`;
- last implementation merge: `bba7549` (`Merge Task 19a consumption and maintenance`);
- current milestone head and `origin/milestone/v0.6`: `bba7549` before the
  Task 20 planning-only amendment that follows this brief;
- `origin/main`: `12f2f17` and intentionally unchanged;
- worktree: clean before the Task 20 planning-only amendment;
- next authorized task: Task 20 on `task/20-work-orders`;
- Task 20's plan and prompt have been reconciled against the merged Task 19a
  implementation and now bind the exact implementation contract;
- Tasks 20a and 20b must not start before Task 20 is independently reviewed,
  committed, merged, and pushed.

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

Task reports under `docs/subagent_execution_plan/v0_6/` contain exact files,
interfaces, review corrections, and validation evidence. ADR-0015 through
ADR-0020 capture the scenario, spatial, partial-world, dispatch, goal, and need
contracts.

SQLite snapshot support now spans schema versions 1 through 8. The v0.6
progression is run identity in schema 2, spatial placements in schema 3,
external references in schema 4, external dispatches in schema 5, goals and
objectives in schema 6, settlement needs in schema 7, and consequences in
schema 8. Legacy versions load newer collections as empty; Task 20 must define
the next migration explicitly
if it adds persisted policy or consequence state.

## Current validation baseline

The final reviewed Task 19 delivery passed:

| Command | Result |
| --- | --- |
| Focused Task 19 needs/goal/persistence/inspection/context suite | 126 tests passed |
| `make` | Ruff and Black passed; 729 pytest tests passed; examples 001–033 passed |
| `make examples` | Examples 001–033 passed |
| `git diff --check` | Passed |

These results are a checkpoint, not a substitute for rerunning validation on
future task branches.

## Next task: Task 20

Task 20 is authorized because Task 19a is reviewed, merged, and pushed. Its
current artifacts are:

- `docs/subagent_execution_plan/v0_6/20_work_orders_reservations.md`
- `docs/subagent_execution_plan/v0_6/20_work_orders_reservations-prombt.md`

The reconciled plan and prompt bind exact work/requirement/reservation records,
settlement/objective/location/prerequisite references, aggregate locks without
resource deduction, manager lifecycle and release rules, immutable events,
schema-v9 persistence/migration/validation, detached inspection, fixed
qualitative NPC-visible translation, rollback, tests, and the exact allowed
file boundary. Commit and push this planning-only change on `milestone/v0.6`,
then create and push `task/20-work-orders` from that amended head and delegate
only the binding contract.

Before implementation, reread the Task 19a report, Tasks 20a/20b plans,
ADR-0016, ADR-0019, ADR-0020, goal/objective ownership, spatial containment,
resource mutation APIs, schema-v8 persistence, inspection, and NPC boundaries.
Task 20 adds no action handler, work system, scheduler phase, resource charge,
domain effect, or direct goal mutation.

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
