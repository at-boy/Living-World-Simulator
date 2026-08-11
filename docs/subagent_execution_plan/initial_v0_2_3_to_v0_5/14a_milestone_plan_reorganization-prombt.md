# Task 14a subagent prompt — milestone plan reorganization

You are an isolated documentation-maintenance subagent. Execute only Task 14a
from `docs/subagent_execution_plan/14a_milestone_plan_reorganization.md`, and
only after Task 14 is committed and the worktree is clean.

Read the task plan, `docs/subagent_execution_plan/README.md`,
`docs/post_v05_settlement_evolution_roadmap.md`,
`docs/development_workflow.md`, and the orchestrator continuation brief in
full. Inspect the complete execution-plan directory and search the repository
for references to every path that will move before changing files.

Use Git-aware moves. Preserve every historical plan, saved `-prombt.md`,
correction artifact, and report for Tasks 01 through 14, Task 14b, and Task 14a
in the `initial_v0_2_3_to_v0_5/` archive. Move Task 15 and 15a artifacts to
`v0_6/`.
Create the two milestone overview files and keep the root README as the complete
cross-milestone index. Preserve global task numbering and the established
`-prombt.md` spelling.

Repair every affected repository link or path reference. Do not rewrite
historical content beyond necessary path/link correctness, and do not leave
duplicates, redirects, or symlinks. Do not create or switch branches and do not
start any v0.6 implementation.

Create the required Task 14a report, move the complete Task 14a artifact set
into the initial archive, audit local Markdown links and stale old paths, run
`make`, `make examples`, and `git diff --check`, then hand the uncommitted
delivery to the orchestrator for independent review.
