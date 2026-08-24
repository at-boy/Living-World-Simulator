# Task 21 worker prompt — settlement development stages

Read `AGENTS.md` and
`docs/subagent_execution_plan/v0_6/21_settlement_development_stages.md` in full.
Work only on the already-pushed `task/21-settlement-development-stages` branch
and implement that decision-complete contract exactly.

Add the engine-owned per-settlement `founding_camp -> settlement -> town`
lifecycle under `src/living_world/stages/`. Promotion consumes only completed,
settlement-owned typed goal objectives and their normalized evidence. Extend
the closed goal criterion vocabulary with the specified population and
maintained-capability criteria, and make `SettlementStageCriterion`
authoritatively evaluate managed stage state.

Preserve manager-exclusive mutation, one adjacent promotion per tick, full
stage-phase rollback, immutable events, exact scheduler placement after goals,
schema-11 persistence with empty schema-1-through-10 defaults, detached
GET-only privileged inspection, and explicitly selected qualitative NPC prose
with no automatic context injection. Population or LLM output alone must never
promote or mutate stage state.

Use test-driven development and stay inside the plan's allowed-file boundary.
Add focused tests, example 037, required project documentation, and a truthful
report; keep the accepted ADR-0024 contract accurate. Run focused tests during
implementation. Before returning,
run the complete focused Task 21 matrix, `make`, separate `make examples`, and
`git diff --check`; report commands, results, counts, and meaningful warnings.

Do not expand scope, change branches, commit, merge, push, or modify `main`.
