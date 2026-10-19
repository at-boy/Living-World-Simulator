# Task 19 subagent prompt — settlement needs and pressure

Work only on `task/19-settlement-needs` after Tasks 18a and 15d merge. Implement
only typed food/water/shelter/storage assessment, managed state/events,
persistence, inspection, and qualitative filtered perceptions. Reuse Task
15d's NPC-safe translation/boundary contract where location prose is needed.
Needs describe authoritative pressure but never choose NPC actions. Do not
consume resources or implement maintenance/work/stages.

Stay inside allowed files, add tests/example/docs and the truthful report, run
`make`, `make examples`, and `git diff --check`, and do not commit, merge, push,
or change branches.

Use the exact allowed-file boundary and Task 18a integration contract in the
binding Task 19 plan. Implement and register the concrete
`SustainedNeedCriterion` evaluator through Task 18a's protocol, schedule needs
assessment before goal evaluation, and keep exact need state/evidence out of
NPC context. The plan's model fields, pressure arithmetic, source scoping,
level precedence, history retention, event taxonomy, schema-v7 migration,
sustained-duration semantics, inspection shape, and fixed qualitative NPC
projection are binding; do not invent alternatives. Strengthen the final NPC
boundary for need IDs/numbers, but do not automatically inject need
interpretations into NPC context. Amend this prompt and the plan before
expanding the boundary.
