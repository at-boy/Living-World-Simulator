# Task 14 report — v0.5 release closeout

## Outcome

Version 0.5 release closeout is complete and ready for orchestrator review. No
tag was created, Task 14a was not started, and no post-v0.5 work was activated.

The first audit pass stopped correctly on inconsistent release versions. Task
14b was then planned, reviewed, and committed as `15ed625`; it synchronized
`VERSION`, project metadata, `living_world.__version__`, and `/health` at
`0.5.0` with a four-surface regression test. Task 14 resumed only after that
correction landed.

## Release version evidence

- `VERSION`: `0.5.0`.
- `pyproject.toml` project version: `0.5.0`.
- `living_world.__version__`: `0.5.0`.
- `GET /health`: `{"status": "ok", "version": "0.5.0"}`, sourced from the
  runtime export rather than an independent string.
- A clean editable installation built
  `living_world_simulator-0.5.0-0.editable-py3-none-any.whl` and installed it as
  `living-world-simulator-0.5.0`.

## v0.5 capability audit

Every former `v0.5 – AI Layer` backlog item was traced to production code,
tests, public imports, and examples before it was marked complete:

| Capability | Evidence | Result |
| --- | --- | --- |
| llama.cpp and local LLM clients | loopback-only Ollama/llama.cpp perception and cognition clients; provider and transport tests; opt-in manual examples | Complete |
| Cognition protocol | `NPCCognitionClient`, filtered `NPCContext`, structured `NPCDecision`/`ActionRequest`; parser and client tests | Complete |
| Decision and authority gateway | `DecisionEngine`, `NPCActionResolver`, explicit handler contract; rejection and application tests | Complete |
| Conversations and meetings | bounded `ConversationService` and `MeetingService`; tests and examples 020–021 | Complete |
| Councils | bounded `CouncilService`, attendance/diagnostic/fallback rules; council suites and example 022 | Complete |
| Context and information boundaries | deterministic holder retrieval, perception boundary, context assembler, information boundary; isolation and leakage tests | Complete |
| No direct LLM world authority | proposal-only cognition followed by independent simulation validation and manager-owned mutation | Complete |
| Manual council scenarios | settlement-wide, opposing-interests, and cognition-shaped scenarios shared by both providers | Complete |

No required v0.5 capability was deferred to v0.6. RAG/vector retrieval,
long-term ranking/decay, governance, inspector UI, and settlement evolution
remain explicitly future work.

## NPC information-boundary audit

The audit searched production cognition/perception assembly and manual examples
for `WorldState`, raw attributes, evidence, metadata, holder/entity IDs, action
keys, target IDs, and arbitrary runtime objects.

- Perception may inspect engine-side `PerceptionContext`, but validates only a
  qualitative description before it becomes cognition.
- Context assembly and retrieval use holder IDs only for engine-side selection
  and return filtered prose without provenance, metadata, or raw attributes.
- Local cognition serialization receives only validated `NPCContext` and the
  offered action vocabulary. Its result remains a proposal.
- Conversation observations contain visible speech with empty evidence and
  metadata. Council membership, invitations, and scheduling stay engine-side.
- Manual scenario setup may seed internal evidence and provenance through
  managers, while its safe trace records only the production-filtered request.
- Privileged HTTP inspection exposes authoritative operator data but is never a
  cognition input.

No information-boundary blocker was found.

## Documentation, backlog, and debt reconciliation

- `CHANGELOG.md` now has a dated `v0.5.0` release section and an empty
  `Unreleased` section for future changes.
- `README.md` summarizes the v0.5 local-model, cognition, dialogue, council,
  action-authority, and information-boundary contract and links its guides.
- `docs/backlog.md` replaces completed v0.4/v0.5 item lists with concise
  completion records while preserving every deferred idea.
- `docs/technical_debt.md` removes only the previously resolved lifecycle,
  immutable-history, repository, and baseline-audit entries whose criteria are
  verified by implementation and tests. No active high-priority debt remains.
- Architecture, core model, glossary, NPC-boundary, local-model, HTTP, journal,
  and release-checklist documentation were reviewed against public v0.5
  behavior. Existing detailed interface documentation remains accurate.

## Validation

- Clean environment on Python 3.13.5:
  `make install VENV=/tmp/living-world-task14-clean-20260812` — passed after
  approved dependency access. The first sandboxed attempt created the virtual
  environment but could not resolve package-index hosts; the required rerun
  with approved network access built and installed the editable `0.5.0`
  package successfully.
- Clean-environment checks and examples — passed.
- `make` — passed: Ruff, Black, **393 pytest tests**, examples **001–023**.
- `make examples` — passed independently for examples **001–023**.
- Documented public-import check — passed.
- Version consistency and HTTP health smoke check — passed.
- Targeted NPC-boundary search and review — passed.
- `git diff --check` — passed.

## Files changed by resumed Task 14

- `README.md`
- `CHANGELOG.md`
- `docs/architectural_direction.md`
- `docs/backlog.md`
- `docs/project_journal.md`
- `docs/technical_debt.md`
- `docs/subagent_execution_plan/14_v05_release_closeout-report.md`

Task 14's earlier committed audit also corrected `docs/release_checklist.md`.
Release metadata and production/test version changes belong to the separate
reviewed Task 14b commit. No source, test, example, dependency, or tag changed
during resumed Task 14.

## Blockers

None. Tagging remains an explicit orchestrator/release action and was not
performed by this task.
