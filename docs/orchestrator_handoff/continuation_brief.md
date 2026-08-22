# Continuation brief — August 22, 2026

## Current repository state

The v0.6 autonomous founding-settlement milestone is authorized and active.
Work uses a pushed milestone branch plus one pushed branch per isolated task.
Reviewed task branches are merged only into `milestone/v0.6`; `main` must not
be changed.

At this handoff checkpoint:

- current branch: `milestone/v0.6`;
- last implementation merge: `a3f4bc5` (`Merge Task 19 settlement needs`);
- current milestone head and `origin/milestone/v0.6`: `ecf175a` before the
  Task 19a planning-only amendment that follows this brief;
- `origin/main`: `12f2f17` and intentionally unchanged;
- worktree: clean before the Task 19a planning-only amendment;
- next authorized task: Task 19a on `task/19a-consumption-maintenance`;
- Task 19a's plan and prompt have been reconciled against the merged Task 19
  implementation and now bind the exact implementation contract;
- Task 20 must not start before Task 19a is independently reviewed, committed,
  merged, and pushed.

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

Task reports under `docs/subagent_execution_plan/v0_6/` contain exact files,
interfaces, review corrections, and validation evidence. ADR-0015 through
ADR-0020 capture the scenario, spatial, partial-world, dispatch, goal, and need
contracts.

SQLite snapshot support now spans schema versions 1 through 7. The v0.6
progression is run identity in schema 2, spatial placements in schema 3,
external references in schema 4, external dispatches in schema 5, goals and
objectives in schema 6, and settlement needs in schema 7. Legacy versions load
newer collections as empty; Task 19a must define the next migration explicitly
if it adds persisted policy or consequence state.

## Current validation baseline

The final reviewed Task 19 delivery passed:

| Command | Result |
| --- | --- |
| Focused Task 19 needs/goal/persistence/inspection/context suite | 126 tests passed |
| `make` | Ruff and Black passed; 655 pytest tests passed; examples 001–032 passed |
| `make examples` | Examples 001–032 passed |
| `git diff --check` | Passed |

These results are a checkpoint, not a substitute for rerunning validation on
future task branches.

## Next task: Task 19a

Task 19a is authorized because Task 19 is reviewed, merged, and pushed. Its
current artifacts are:

- `docs/subagent_execution_plan/v0_6/19a_consumption_maintenance_consequences.md`
- `docs/subagent_execution_plan/v0_6/19a_consumption_maintenance_consequences-prombt.md`

The plan and prompt now bind exact policy/state records, IDs and validation,
per-tick integer arithmetic, a single atomic consequence phase, manager-owned
mutations, event kinds and attributes, shortage/recovery and terminal
deterioration semantics, capacity-bounded storage/spoilage, schema-v8
persistence/migration/validation, detached inspection, fixed qualitative
NPC-visible translation, whole-phase rollback, tests, and the exact allowed
file boundary. Commit and push this planning-only change on `milestone/v0.6`,
then create and push `task/19a-consumption-maintenance` from that amended head
and delegate only the binding contract.

Before planning or implementation, reread the Task 19 report, ADR-0020, need
model/manager/system, resource and entity mutation APIs, scheduler, schema-v7
persistence, inspection surface, goal evaluator, and NPC boundary. Confirm how
Task 19a consequences become authoritative inputs to Task 19 assessment without
calling the goal manager or directly deciding run failure. Amend plan and prompt
together before any boundary expansion.

## Remaining approved sequence

Continue one reviewed task at a time in this order:

1. Task 19a — consumption, maintenance, and consequences.
2. Tasks 20, 20a, and 20b — work records, proposal gateway, and execution.
3. Task 21 — settlement development stages.
4. Task 22 — deterministic recorded proposal tapes.
5. Tasks 15 and 15c — FastAPI-hosted inspector and spatial view.
6. Task 23 — canonical success, stall, and failure founders scenarios.
7. Task 24 — milestone release-readiness closeout.

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

## Historical context

The v0.5 release and Tasks 01–14/14a/14b are complete and archived under
`docs/subagent_execution_plan/initial_v0_2_3_to_v0_5/`. The prior council and
local-model decisions remain documented in their reports and ADRs; do not
reconstruct them from chat history. The cross-milestone index is
`docs/subagent_execution_plan/README.md`, and the approved v0.6 objective and
sequence are in `docs/subagent_execution_plan/v0_6.md`.
