# 22 — Deterministic recorded proposal tapes

## Status and dependencies

Authorized after reviewed Task 21. Execute on `task/22-recorded-proposals`.

## Task description

Add a strict versioned YAML proposal-tape contract and an
`NPCCognitionClient` adapter that returns recorded entries as ordinary
untrusted `NPCDecision` and `ActionRequest` values. Tapes make automated runs
replayable but never bypass offered-vocabulary or action-gateway validation.

## Contract and boundary

- Tape version 1 binds scenario key/fingerprint and orders entries by sequence,
  public actor label, expected offered action key/target label, optional speech,
  rationale, and string arguments.
- Reject unknown fields, duplicate/out-of-order sequence, scenario mismatch,
  unknown actor label, internal IDs in prose, malformed decisions, unexpected
  offered actions, and exhausted/unused tapes with stable safe diagnostics.
- The adapter receives only filtered `NPCContext` and offered `ActionOption`
  values. It cannot read `WorldState`, resolve internal IDs, mutate state, or
  declare outcomes.
- Add loader/client/runtime composition hooks, tests/example/docs, changelog,
  journal, backlog, and report. Do not require a live local model or implement
  canonical scenario content. Run `make`, `make examples`, and
  `git diff --check`.

## Tests

Cover strict loading, deterministic replay, context isolation, vocabulary
mismatch, exhaustion/unused entries, gateway rejection, save/resume cursor
policy, and no provider payload/secrets in errors.

## Report

Create `docs/subagent_execution_plan/v0_6/22_recorded_proposal_tapes-report.md`.
