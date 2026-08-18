# 20a — Proposal-to-work action gateway

## Status and dependency

Authorized after reviewed Task 20. Execute on `task/20a-work-action-gateway`.

## Task description

Add domain action handlers that translate only offered NPC proposals into
validated work creation/priority/assignment requests. Initial categories are
gather water, produce food, build shelter, build storage, maintain capability,
and establish external trade connection.

## Contract and tests

- Build `ActionOption` values from current engine-authorized categories and
  public target labels. Resolve labels internally; never put work/entity/goal/
  external-reference IDs into prompts or request prose.
- Validate actor eligibility, target existence, location, prerequisites,
  affordability, duplicate active work, and authorization before mutation.
  Rejection records no work and consumes nothing; accepted application uses the
  Task 20 manager and existing action resolver protocol.
- Add focused handler/composition tests/example/docs, changelog, journal,
  backlog, and report. Cover malformed/unoffered/unauthorized requests, label
  ambiguity, validation-before-apply, rollback, and cross-NPC isolation.
- Do not execute work, let cognition assign outcomes, or expose raw state. Run
  `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/20a_proposal_work_gateway-report.md`.
