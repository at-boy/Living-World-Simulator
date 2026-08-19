# Continuation brief — August 19, 2026

## Current repository state

The v0.6 autonomous founding-settlement milestone is authorized and active.
Work uses a pushed milestone branch plus one pushed branch per isolated task.
Reviewed task branches are merged only into `milestone/v0.6`; `main` must not
be changed.

At this handoff checkpoint:

- current branch: `milestone/v0.6`;
- last implementation merge: `0fe099d` (`Merge Task 18 goals and objective graphs`);
- current milestone head and `origin/milestone/v0.6`: `0fe099d` before the
  documentation-only planning update that may follow this brief;
- `origin/main`: `12f2f17` and intentionally unchanged;
- worktree: clean;
- next authorized task: Task 18a on
  `task/18a-objective-evaluation-events`;
- no Task 18a branch or implementation has been started.

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

Task reports under `docs/subagent_execution_plan/v0_6/` contain exact files,
interfaces, review corrections, and validation evidence. ADR-0015 through
ADR-0019 capture the scenario, spatial, partial-world, dispatch, and goal
contracts.

## Current validation baseline

The final reviewed Task 18 delivery passed:

| Command | Result |
| --- | --- |
| Focused Task 18 goal/persistence/inspection suite | 65 tests passed |
| `make` | Ruff and Black passed; 547 pytest tests passed; examples 001–029 passed |
| `make examples` | Examples 001–029 passed |
| `git diff --check` | Passed |

These results are a checkpoint, not a substitute for rerunning validation on
future task branches.

## Next task: Task 18a

Task 18a is authorized because Task 18 is reviewed and merged. Its binding
artifacts are:

- `docs/subagent_execution_plan/v0_6/18a_objective_evaluation_events.md`
- `docs/subagent_execution_plan/v0_6/18a_objective_evaluation_events-prombt.md`

Create and push `task/18a-objective-evaluation-events` from the verified current
`milestone/v0.6` head. Implement only deterministic criterion evaluation,
stable graph lifecycle transitions/evidence, and engine composition. Needs and
settlement-stage criteria remain registered-but-unavailable until Tasks 19 and
21; work execution belongs to Tasks 20–20b.

Before implementation, reread Task 18's report, ADR-0019, the goal manager, and
the schema-v6 persistence surface. The Task 18a plan and prompt now contain the
binding evaluation semantics and exact allowed-file boundary. Amend both
explicitly before any expansion.

## Remaining approved sequence

Continue one reviewed task at a time in this order:

1. Task 18a — deterministic objective evaluation.
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
