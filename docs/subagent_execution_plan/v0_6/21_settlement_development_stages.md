# 21 — Settlement development stages

## Status and dependency

Authorized after reviewed Task 20b. Execute on
`task/21-settlement-development-stages`.

## Task description

Add configurable engine-owned `founding_camp`, `settlement`, and `town` stages.
Typed criteria reuse authoritative goal evidence for sustained water, food,
shelter, storage, maintenance, external connection, and population/capability
requirements; population alone can never promote a settlement.

## Contract and boundary

- Managed stage state advances monotonically unless an explicit future policy
  adds decline. Evaluate after work, needs, and objective systems in stable
  order; emit one auditable event per transition with normalized evidence.
- Validate ordered unique stages, supported criteria, owner references,
  duration windows, configuration contradictions, idempotence, and legacy save
  defaults.
- Extend state/manager/system, persistence, detached inspection, safe
  qualitative NPC perception, tests/example, ADR/docs, changelog, journal,
  backlog, and report.
- Tests prove founding-camp to settlement and settlement to town, missing each
  capability, unsustained criteria, save/resume, event uniqueness, and that an
  LLM or population alone cannot promote. Run `make`, `make examples`, and
  `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/21_settlement_development_stages-report.md`.
