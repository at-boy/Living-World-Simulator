# Task 19 subagent prompt — settlement needs and pressure

Work only on `task/19-settlement-needs` after Task 18a merges. Implement only
typed food/water/shelter/storage assessment, managed state/events, persistence,
inspection, and qualitative filtered perceptions. Needs describe authoritative
pressure but never choose NPC actions. Do not consume resources or implement
maintenance/work/stages.

Stay inside allowed files, add tests/example/docs and the truthful report, run
`make`, `make examples`, and `git diff --check`, and do not commit, merge, push,
or change branches.

Use the exact allowed-file boundary and Task 18a integration contract in the
binding Task 19 plan. Implement and register the concrete
`SustainedNeedCriterion` evaluator through Task 18a's protocol, schedule needs
assessment before goal evaluation, and keep exact need state/evidence out of
NPC context. Amend this prompt and the plan before expanding the boundary.
