# 23 — Canonical founders scenarios and acceptance

## Status and dependencies

Authorized after reviewed Tasks 22, 15, and 15c. Execute on
`task/23-founders-acceptance`.

## Task description

Ship one canonical founding-settlement scenario with three recorded proposal
tapes and end-to-end acceptance coverage:

- **Success:** secures sustainable water, food, shelter, storage, and a homeland
  trade connection and reaches `settlement`.
- **Stall:** remains runnable but reaches its bound with blocked work/objective
  evidence and no false success/failure.
- **Failure:** reaches an engine-owned terminal failure from configured shortage,
  deadline, or viability criteria.

## Acceptance contract

- One documented `living-world run` command starts each bounded outcome; the
  inspector/API explains current needs, work, goals, stage, dispatches, and the
  event chain causing the stop reason.
- Same scenario/seed/tape yields byte-equivalent normalized final state and
  event history. An uninterrupted run and checkpoint/resume at multiple ticks
  converge to the same result and tape position.
- All initial data uses public scenario labels; no tape contains internal IDs or
  hidden criteria. Every proposal traverses filtered context, offered actions,
  decision validation, and the action gateway.
- Add canonical YAML/assets, end-to-end tests, numbered example/operator guide,
  changelog, journal, backlog, and report. Fix only integration defects within
  documented prerequisite interfaces; stop for any boundary expansion.
- Run `make`, `make examples`, `git diff --check`, and the three CLI scenarios.

## Report

Create `docs/subagent_execution_plan/v0_6/23_canonical_founders_acceptance-report.md`
with commands, normalized result evidence, resume comparison, inspector proof,
boundary audit, and limitations.
