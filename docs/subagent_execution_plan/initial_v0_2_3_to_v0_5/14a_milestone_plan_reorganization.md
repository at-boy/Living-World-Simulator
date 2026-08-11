# 14a — Milestone plan reorganization

## Task Description

After Task 14 has closed v0.5, reorganize the accumulated execution-plan
artifacts into milestone-owned directories. Preserve the complete planning,
prompt, correction, and report history while establishing the structure used
by v0.6 and later milestone branches.

This is a documentation organization task. It does not start Task 15, Task
15a, or any v0.6 implementation.

## Preconditions

- Task 14 is implemented, independently reviewed, validated, reported, and
  committed.
- The worktree is clean.
- The final Task 14 plan, prompt, and report exist before any move begins.

## Target Structure

```text
docs/subagent_execution_plan/
├── README.md
├── initial_v0_2_3_to_v0_5.md
├── initial_v0_2_3_to_v0_5/
│   ├── 01_...
│   ├── ...
│   ├── 14_v05_release_closeout...
│   ├── 14b_release_version_consistency...
│   └── 14a_milestone_plan_reorganization...
├── v0_6.md
└── v0_6/
    ├── 15_world_inspector_ui.md
    └── 15a_spatial_world_inspection.md
```

Future milestones follow the same shape: one milestone overview Markdown file
beside one directory containing that milestone's task plans, saved prompts,
correction prompts, and reports.

## Context Needed

- Create, initially at the current root:
  `docs/subagent_execution_plan/14a_milestone_plan_reorganization-prombt.md`.
- Create during execution:
  `docs/subagent_execution_plan/initial_v0_2_3_to_v0_5.md`,
  `docs/subagent_execution_plan/v0_6.md`, and
  `docs/subagent_execution_plan/14a_milestone_plan_reorganization-report.md`.
- Move every execution-plan artifact whose filename belongs to Tasks 01 through
  14, corrective Task 14b, or Task 14a into
  `docs/subagent_execution_plan/initial_v0_2_3_to_v0_5/`. This includes task
  plans, saved `-prombt.md` files, correction prompts, reports, and other
  task-prefixed historical artifacts.
- Move Task 15 and Task 15a plans and any existing associated artifacts into
  `docs/subagent_execution_plan/v0_6/`.
- Keep `docs/subagent_execution_plan/README.md` at the root and update it as the
  cross-milestone index.
- Update every affected reference elsewhere in `docs/` and repository Markdown
  files, including handoff documents, roadmap documents, and relative links.
- Do not edit production code, tests, examples, package metadata, or release
  version files.

## Milestone Overview Contracts

`initial_v0_2_3_to_v0_5.md` records:

- the initial baseline and completed v0.3, v0.4, and v0.5 objectives;
- the historical task order and the final release-closeout task;
- that its directory is an immutable planning archive except for future link or
  factual corrections;
- links to the plans, prompts, and reports through the root index.

`v0_6.md` records:

- the autonomous founding-settlement vertical-slice objective and acceptance
  target from `docs/post_v05_settlement_evolution_roadmap.md`;
- `milestone/v0.6` as the future integration branch name;
- Task 15 and 15a as supporting observability candidates, not automatically
  authorized implementation;
- that later v0.6 tasks require isolated plans, prompts, reports, review, and
  explicit authorization.

## Migration Rules

- Use Git-aware moves so history remains traceable.
- Preserve filenames and the established `-prombt.md` spelling.
- Preserve globally unique task numbering across milestones.
- Do not rewrite historical task content merely to make it read as current.
  Update paths and links only where required for navigation or correctness.
- Do not leave duplicate copies at the old paths.
- Do not add redirects or symlinks unless a concrete external compatibility
  requirement is discovered and documented before implementation.
- A milestone directory does not authorize its tasks, and the reorganization
  does not create or switch Git branches.

## Verification Criteria

- The root directory contains only the cross-milestone README, milestone
  overview files, and milestone directories; no Task 01–15 artifact remains
  loose at the root.
- Every Task 01–14b and Task 14a artifact is present in the initial-program
  directory.
- Every existing Task 15/15a artifact is present in the v0.6 directory.
- The root README presents the historical order and links successfully to every
  plan, prompt, correction artifact, and report.
- Repository searches find no stale references to the old loose task paths.
- All relative Markdown links under `docs/` resolve to existing local targets.
- No historical artifact content is lost or silently renamed.
- `make`, `make examples`, and `git diff --check` pass.

## Orchestrator Report

Create
`docs/subagent_execution_plan/14a_milestone_plan_reorganization-report.md`
before moving the Task 14a artifact set into the initial-program directory.
Report the exact moves, overview/index changes, reference audit, validation,
boundary compliance, and any unresolved external-link compatibility concern.

## Boundary

- Documentation paths and Markdown content only.
- Do not start or implement Task 15, Task 15a, or another v0.6 capability.
- Do not create, delete, merge, or switch Git branches in this task.
- Do not alter implementation behavior or release metadata.
