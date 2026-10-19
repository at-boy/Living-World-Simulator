# Task 20a subagent prompt — proposal-to-work gateway

Work only on `task/20a-work-action-gateway` created from the milestone commit
containing the decision-complete Task 20a plan. Read `AGENTS.md`, the binding
Task 20a plan, Task 20 plan/report, Task 20b plan, ADR-0010, ADR-0021, the
existing action resolver/decision interfaces, external-dispatch action analogue,
and directly relevant tests before editing.

Implement exactly the binding plan: frozen ephemeral engine-authored creation,
priority, and self-assignment offers; eight closed actor-bound action keys;
safe deterministic `ActionOption` construction; exact goal/objective and actor
authorization; mutation-free WorkManager preflights; admission-only aggregate
affordability; nonterminal duplicate detection; stale-offer revalidation; one
manager mutation per accepted action; existing manager events/rollback;
canonical static ID filtering plus final state-aware NPC validation; focused
tests; example 035; ADR/docs; and a truthful report.

All hidden offer fields, action ordering, label normalization, authorization,
duplicate identity, self-assignment rule, request-argument rejection, fixed safe
resolutions, failure propagation, no-event rejection, schema-9 non-change,
resume behavior, tests, and allowed files are binding.

Do not persist offers, change WorldState/schema/inspection/HTTP/scheduler,
register a global resolver, modify conversation/council behavior, infer policy
from LLM prose, assign another NPC or a multi-person crew, execute/progress work,
deduct resources, apply domain effects, mutate goals, alter prompts/LLM clients,
or implement Task 20b.

Stay inside the exact allowed-file boundary. Create
`docs/subagent_execution_plan/v0_6/20a_proposal_work_gateway-report.md` with
actual files, behavior, invariants, tests, review corrections, and limitations.
Run focused tests, then `make`, separate `make examples`, and
`git diff --check`. Report exact results. Do not commit, merge, push, or change
branches. Stop and report any contract conflict or required out-of-scope file.
