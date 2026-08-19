# Task 19a subagent prompt — consumption and maintenance

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
