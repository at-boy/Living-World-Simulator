# Task 18a subagent prompt — objective evaluation and events

Work only on `task/18a-objective-evaluation-events` after Task 18 merges.
Implement the typed deterministic evaluators, stable lifecycle transitions,
normalized evidence, and immutable events in the binding plan. Engine state is
authoritative; do not expose exact hidden criteria/evidence to NPCs or allow an
LLM to assert completion.

Stay within allowed files, add tests/example/docs and the truthful report, run
`make`, `make examples`, and `git diff --check`, and do not commit, merge, push,
or change branches.

The binding graph semantics, evaluator precedence, deferred-criterion policy,
scheduler position, and exact allowed-file boundary are in the Task 18a plan.
Implement concrete evaluators only for resource minimum, constructed
capability, capacity, and external connection. Register sustained need and
settlement stage as unavailable until Tasks 19 and 21 respectively; do not
invent those future domains or read arbitrary attributes as substitutes.
Use canonical direct `owns` relationships for owner-scoped capability/capacity
queries. Permit direct manager `BLOCKED -> COMPLETED`, emit one event per real
transition, and keep repeated unchanged evaluation idempotent. Amend both this
prompt and the plan before expanding their explicit boundary.
