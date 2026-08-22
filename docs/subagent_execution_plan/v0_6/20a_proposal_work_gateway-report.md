# Task 20a report — proposal-to-work action gateway

## Delivered

- Added frozen, slotted creation, fixed-priority, and self-assignment offer
  records plus an actor-bound `WorkActionHandler` with deterministic closed
  action options and fixed safe resolutions.
- Added exact live-NPC/settlement placement and active settlement-goal/objective
  authorization checks at construction, validation, and application.
- Added side-effect-free `WorkManager` preflights for creation, priority, and
  assignment. Creation admission checks aggregate cross-kind availability and
  nonterminal duplicate identity without reserving or deducting stock.
- Preserved manager-only mutations, existing exact events, atomic rollback,
  allocator restoration, apply-time stale-state propagation, and one-person
  self-assignment. Offers remain ephemeral and schema 9, inspection, HTTP,
  scheduler, context assembly, prompts, and LLM clients are unchanged.
- Expanded static NPC-visible canonical-ID rejection through every current
  record prefix, while retaining final state-aware boundary validation for
  every offered label and description.
- Added executable example 035, ADR-0022, and focused architecture, boundary,
  glossary, backlog, changelog, and journal documentation.

## Test coverage

`tests/test_work_action_gateway.py` covers strict frozen/canonical offers, all
six category/target families, invalid target policy, closed ordering and label
normalization, hidden-field omission, actor isolation and placement, exact
ACTIVE authorization, safe mutation-free rejection, duplicate identity across
every nonterminal status and terminal-history allowance, affordability,
capability vocabulary, priority and self-assignment events, multi-person
rejection, stale apply propagation, mutation-free preflights, event-failure
rollback and work/reservation allocator reuse, and schema-9 resume with
reconstructed offers and next work ID. `tests/test_npc_cognition_client.py`
adds the complete newer canonical record-prefix matrix.

Independent-review corrections add the literal integration matrix: council
majorities resolve through the caller-bound work handler and another member
cannot replay it; serialized all-eight-key model input contains only keys,
fixed descriptions, and public labels; every terminal/no-op priority case,
double-booked labor, direct and cross-kind input shortages, and rejection-family
allocator preservation are explicit. Stale creation coverage now includes
destroyed/moved/missing locations, missing or stale cross-settlement
prerequisite history, missing maintenance/external targets, removed capability
vocabulary, and expired deadlines. A valid incomplete prerequisite remains
intentionally admissible at creation and blocks only `mark_ready()`, preserving
Task 20 semantics.
Schema/context/scheduler regressions prove schema 9 contains no offers,
privileged inspection has no offer surface, no work action system is
registered, and neither offers nor work interpretations are auto-injected into
`NPCContext`.

Focused validation covered every plan-listed existing suite alongside the new
gateway suite. During full validation, the broadened canonical-ID matcher first
collided with existing qualitative council and external-dispatch action keys.
The correction now recognizes generated numeric record IDs and named canonical
goal/need/policy IDs only at token boundaries; dedicated external-dispatch,
manual-council, cognition, and gateway regressions passed after the correction.

## Validation

- Focused plan-listed matrix: **295 passed, 10 deliberate Task 20 valid-family
  skips**.
- `make`: Ruff and Black passed; **893 passed, 10 deliberate skips**; examples
  001–035 passed.
- Separate `make examples`: examples 001–035 passed.
- `git diff --check`: passed.

## Limitations and deferred work

Task 20a does not persist offers, register a global resolver or scheduler
system, select multi-person crews, charge or deduct resources, progress or
execute work, apply domain effects, mutate goals, or inject work into NPC
context. Those execution responsibilities remain Task 20b.
