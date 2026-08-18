# Continuation brief — August 18, 2026

## Current repository state

The v0.6 autonomous founding-settlement milestone is authorized and active.
Work uses a pushed milestone branch plus one pushed branch per isolated task.
Reviewed task branches are merged only into `milestone/v0.6`; `main` must not
be changed.

At this handoff checkpoint:

- current branch: `milestone/v0.6`;
- last implementation merge: `9c006fc` (`Merge Task 17a external dispatch lifecycle`);
- current milestone head and remote include the documentation-only handoff
  commit immediately following that merge; verify its hash from Git;
- `origin/main`: `12f2f17` and intentionally unchanged;
- worktree: clean;
- next authorized task: Task 18 on `task/18-goals-objectives`;
- no Task 18 branch or implementation has been started.

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

Task reports under `docs/subagent_execution_plan/v0_6/` contain exact files,
interfaces, review corrections, and validation evidence. ADR-0015 through
ADR-0018 capture the scenario, spatial, partial-world, and dispatch contracts.

## Current validation baseline

The final reviewed Task 17a delivery passed:

| Command | Result |
| --- | --- |
| Focused Task 17a/integration suite | 106 tests passed |
| `make` | Ruff and Black passed; 498 pytest tests passed; examples 001–028 passed |
| `make examples` | Examples 001–028 passed |
| `git diff --check` | Passed |

These results are a checkpoint, not a substitute for rerunning validation on
future task branches.

## Next task: Task 18

Task 18 is authorized because Task 17a is reviewed and merged. Its binding
artifacts are:

- `docs/subagent_execution_plan/v0_6/18_goals_objective_graphs.md`
- `docs/subagent_execution_plan/v0_6/18_goals_objective_graphs-prombt.md`

Create and push `task/18-goals-objectives` from the verified current
`milestone/v0.6` head. Implement only durable typed goal/objective definitions,
managed lifecycle state, persistence, deterministic privileged inspection, and
filtered NPC interpretations. Automatic evaluation belongs to Task 18a and
work execution belongs to Tasks 20–20b.

Before implementation, reread Task 17a's report and the current schema-v5
persistence surface. If Task 18 needs an interface or file outside its stated
boundary, amend the plan and saved prompt explicitly before code changes.

## Remaining approved sequence

Continue one reviewed task at a time in this order:

1. Tasks 18 and 18a — goals/objectives and deterministic evaluation.
2. Tasks 19 and 19a — needs, consumption, maintenance, and consequences.
3. Tasks 20, 20a, and 20b — work records, proposal gateway, and execution.
4. Task 21 — settlement development stages.
5. Task 22 — deterministic recorded proposal tapes.
6. Tasks 15 and 15c — FastAPI-hosted inspector and spatial view.
7. Task 23 — canonical success, stall, and failure founders scenarios.
8. Task 24 — milestone release-readiness closeout.

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

## Historical context

The v0.5 release and Tasks 01–14/14a/14b are complete and archived under
`docs/subagent_execution_plan/initial_v0_2_3_to_v0_5/`. The prior council and
local-model decisions remain documented in their reports and ADRs; do not
reconstruct them from chat history. The cross-milestone index is
`docs/subagent_execution_plan/README.md`, and the approved v0.6 objective and
sequence are in `docs/subagent_execution_plan/v0_6.md`.
