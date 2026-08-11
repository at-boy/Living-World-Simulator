# 13l — Opposing-groups council scenario

## Task Description

Extend the manual scenario catalog with a council in which eligible NPCs have
different, overlapping affiliations and materially opposed interests. The
scenario should make disagreement and coalition-like voting observable without
adding factions, reputation consequences, institutional seats, or governance
rules that the engine does not yet implement.

## Context Needed

- Create:
  `docs/subagent_execution_plan/13l_opposing_groups_council_scenario-report.md`.
- Edit: `examples/manual/council_scenarios.py`,
  `tests/test_manual_council_scenarios.py`, `docs/local_llm_setup.md`,
  `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: Task 13k's scenario catalog, organization membership eligibility,
  multiple affiliations, opaque IDs, Task 13j safe tracing, and the current
  majority proposal behavior.

## Interface Contract

- Add one named scenario to the existing manual catalog; do not add another
  provider-specific implementation or change the default scenario.
- Use five NPCs who are all valid members of the convening organization. Give
  them safe NPC-visible interests representing at least two opposing groups,
  with at least one independent or cross-affiliated perspective.
- Offer at least three plausible actions so no vote is predetermined by a
  single available action. The agenda and self-knowledge may describe interests
  and affiliations in natural language, but must not expose relationship IDs,
  entity IDs, numeric relationship scores, or hidden attributes.
- Group affiliation influences only the filtered context from which an NPC may
  reason. It does not force attendance, dialogue, proposals, votes, or the
  local model's result.
- Keep resolutions in the manual accepted no-mutation gateway. Do not create
  durable factions, institutional voting weights, group delegates, secession,
  reputation effects, or authoritative political alignment.

## Test Criteria

- Offline tests prove deterministic scenario discovery and construction for
  both manual entry points without provider calls.
- Tests prove every attendee is independently eligible in the convening
  organization and the safe context represents opposed and cross-cutting
  interests without internal identifiers.
- Tests prove at least three meaningful actions are available and no setup code
  predetermines an NPC proposal or final majority.
- Context trace and result rendering retain the Task 13j safety guarantees.
- `make`, `make examples`, and `git diff --check` pass. Live model behavior is
  reported as variable, not asserted by offline tests.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13l_opposing_groups_council_scenario-report.md`.
Report the affiliations and alternatives, eligibility evidence, scenario
selection, tests/commands/results, exact files changed, boundary compliance,
and the deferred faction/governance/reputation work.

## Boundary

- Touch only the listed shared manual scenario, test, documentation, and report
  files.
- Do not change production relationship, council, cognition, action gateway,
  persistence, HTTP, provider-client, or world-state interfaces.
- Do not force model behavior, assign voting weights, infer engine truth from
  dialogue, or implement any future political consequence.
