# Task 19a subagent prompt — consumption and maintenance

Planning gate: this prompt remains a high-level outline and must not be issued
to an implementation subagent until it and the binding plan have been amended
into a decision-complete contract on `milestone/v0.6`.

Work only on `task/19a-consumption-maintenance` after Task 19 merges. Implement
only deterministic configured consumption, storage/spoilage, upkeep,
deterioration/recovery, manager-owned mutations/events, persistence and
inspection from the binding plan. Do not let cognition select consequences or
implement work/stage behavior.

Stay inside allowed files, add tests/example/docs and the truthful report, run
`make`, `make examples`, and `git diff --check`, and do not commit, merge, push,
or change branches.

Use the exact boundary and scheduler order in the Task 19a plan: consequences
run before needs assessment, which runs before goal evaluation. Never call the
goal manager or directly complete criteria. Amend this prompt and the plan
before expanding the allowed files.
