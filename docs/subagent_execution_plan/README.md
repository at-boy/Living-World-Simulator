# Subagent Execution Plan: v0.2.3 to v0.5

## Baseline and objective

The repository starts at **v0.2.3**.  Its supported Python contract remains
`>=3.11`; Python 3.13.5 is the local validation runtime.  The objective is to
deliver the backlog milestones v0.3, v0.4, and v0.5 without bypassing the
engine's authority or the NPC information boundary.

This is a sequential plan.  A task begins only after the prior task has
landed, passed `make`, and had its documentation batch completed.  Each task
is deliberately bounded so one subagent owns the listed files and no others.

## Non-negotiable architecture

```text
authoritative WorldState
  -> engine-side perception translation
  -> immutable Observation
  -> NPC Memory / Belief / Experience / social knowledge
  -> filtered retrieval and NPC context
  -> LLM proposal
  -> simulation validation and manager-owned mutation
  -> immutable Event
```

LLMs never receive raw world attributes, internal identifiers, protected
evidence, or direct `WorldState` access.  They never create facts or apply
actions.  A belief, experience, conversation, and council conclusion remain
NPC interpretation until a simulation-owned handler validates an action.

## Task order

1. [01 Baseline and technical-debt reconciliation](01_baseline_and_technical_debt.md)
2. [01a Formatting corrective task](01a_formatting_corrective.md)
3. [02 Repository layer](02_repository_layer.md)
4. [03 YAML world-definition loading](03_yaml_world_definition_loader.md)
5. [03a HTTP world-inspection API foundation](03a_http_world_inspection_api.md)
6. [04 Regions, terrain, weather, and population](04_world_simulation_foundations.md)
7. [05 Organizations and settlement foundations](05_organizations_and_settlements.md)
8. [06 Construction, roads, housing, economy, production, and trade](06_settlement_economy.md)
9. [07 NPC identity, schedules, and occupations](07_npc_identity_schedules_occupations.md)
10. [08 Cognitive records and sleep consolidation](08_npc_cognition_records_and_consolidation.md)
11. [08a NPC knowledge](08a_npc_knowledge.md)
12. [09 Retrieval, context assembly, and boundary enforcement](09_npc_retrieval_context_boundary.md)
13. [09a Perception-boundary enforcement](09a_perception_boundary_enforcement.md)
14. [10 Local LLM cognition client](10_local_llm_cognition_client.md)
15. [11 NPC Cognition Protocol and action gateway](11_npc_cognition_protocol_action_gateway.md)
16. [12 NPC conversations](12_npc_conversations.md)
17. [13 Council meetings](13_council_meetings.md)
18. [13a HTTP inspection coverage for v0.4–v0.5](13a_http_inspection_coverage.md)
19. [14 v0.5 release closeout](14_v05_release_closeout.md)

## Delivery rule for every task

The assigned subagent writes or updates its specified tests and examples,
runs `make`, reviews its diff, and updates the task's specified documentation
before handoff.  It must not change a public interface owned by another task
without returning the task for architectural review.

## Approved orchestrator reports

Every task includes an approved report artifact in
`docs/subagent_execution_plan/`. The report is part of that task's allowed
scope, not a boundary exception. It must state: outcome; files changed;
interfaces added or changed; tests/commands run and results; documentation
updated; boundary compliance; and blockers or deferred work. A report does not
replace the required test, example, documentation, or `make` validation.

## Standard subagent briefing

Use the following briefing together with the complete contents of the selected
task file. Replace the placeholder with the task content below its title.

```text
You are an isolated Subagent developer specializing in Python 3.13, Ruff,
and Black.

Your scope is strictly limited to executing ONE specific task. Do not write
code outside this scope.

Here is the Codebase Standard you must follow:
- Use explicit type hints everywhere.
- Use dataclasses for domain state.
- Use Protocol for abstractions.
- Code must pass Ruff linting and Black formatting.

## INSERT TASK DETAILS ##

Write the necessary implementation, configuration, documentation, examples,
and corresponding pytest tests required by the task. Only edit the files
within Context Needed and Boundary, including the approved Orchestrator Report
artifact. Before handoff, create that report exactly at the task-specified
path.
```
