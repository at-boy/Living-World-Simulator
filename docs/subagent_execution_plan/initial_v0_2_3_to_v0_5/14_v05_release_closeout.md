# 14 — v0.5 release closeout

## Task Description

Verify the completed v0.5 capability set, synchronize release documentation
and metadata, and perform the final quality and information-boundary audit.

## Context Needed

- Create before delegation:
  `docs/subagent_execution_plan/14_v05_release_closeout-prombt.md`.
- Create: `docs/subagent_execution_plan/14_v05_release_closeout-report.md`.
- Edit: `VERSION`, `pyproject.toml`, `CHANGELOG.md`, `README.md`,
  `docs/backlog.md`, `docs/technical_debt.md`, `docs/core_model.md`,
  `docs/engine_glossary.md`, `docs/architectural_direction.md`,
  `docs/npc_information_boundary.md`, `docs/local_llm_setup.md`,
  `docs/project_journal.md`, `docs/release_checklist.md`.
- Inspect all source, all tests, all examples, all ADRs, and this plan.
- No production source files are edited in this task unless verification exposes
  a defect; a defect returns to its owning task.

## Interface Contract

- Release version becomes `0.5.0` consistently in `VERSION` and
  `pyproject.toml`.
- Documentation accurately states the public v0.5 interfaces, local-only LLM
  support, action gateway, conversations, councils, and NPC boundary.
- Remove only completed v0.3–v0.5 backlog items. Keep explicitly deferred RAG,
  vector search, long-term memory ranking, and unrelated future ideas.
- Remove technical-debt entries only if their original “Resolved when” criteria
  were satisfied by preceding tasks.

## Test Criteria

- Clean environment: install with supported Python, then run `make`.
- Verify every example executes and all public imports shown in README/docs
  exist.
- Perform a boundary audit: search generated prompt/context code and examples
  for `WorldState`, raw entity attributes, evidence, metadata, and internal-ID
  leakage.
- Review the complete diff and release checklist before tagging.

## Orchestrator Report

Create `docs/subagent_execution_plan/14_v05_release_closeout-report.md`.
Report release-version evidence, full validation results, boundary-audit
findings, documentation/backlog/debt reconciliation, and any release blocker.

## Boundary

- Documentation/configuration/release metadata only.
- The approved report artifact is also allowed.
- Do not “fix forward” implementation defects during release closeout.
- Adhere to every development rule, particularly changelog, journal, backlog,
  and final `make` requirements.
