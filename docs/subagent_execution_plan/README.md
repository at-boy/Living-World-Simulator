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
8. [05a Immutable event-history attributes](05a_immutable_event_history.md)
9. [06 Construction, roads, housing, economy, production, and trade](06_settlement_economy.md)
10. [07 NPC identity, schedules, and occupations](07_npc_identity_schedules_occupations.md)
11. [08 Cognitive records and sleep consolidation](08_npc_cognition_records_and_consolidation.md)
12. [08a NPC knowledge](08a_npc_knowledge.md)
13. [09 Retrieval, context assembly, and boundary enforcement](09_npc_retrieval_context_boundary.md)
14. [09a Perception-boundary enforcement](09a_perception_boundary_enforcement.md)
15. [10 Local LLM cognition client](10_local_llm_cognition_client.md)
16. [11 NPC Cognition Protocol and action gateway](11_npc_cognition_protocol_action_gateway.md)
17. [12 NPC conversations](12_npc_conversations.md)
18. [12a NPC meeting coordination and directed dialogue](12a_npc_meeting_coordination.md)
19. [13 Council meetings](13_council_meetings.md)
20. [13b Manual council-example observability](13b_manual_council_example_observability.md)
21. [13c Council invitation-feedback trace](13c_council_invitation_feedback.md)
22. [13d Council invitation action-selection guidance](13d_council_invitation_action_selection.md)
23. [13e Council invitation diagnostics](13e_council_invitation_diagnostics.md)
24. [13f Explicit-decline caller fallback](13f_council_explicit_decline_fallback.md)
25. [13g Local cognition response-shape guidance](13g_local_cognition_response_shape_guidance.md)
26. [13h Deterministic council turn rotation](13h_deterministic_council_turn_rotation.md)
27. [13i NPC dialogue opening guidance](13i_npc_dialogue_opening_guidance.md)
28. [13j Manual council scenario and safe context tracing](13j_manual_council_scenario_and_context_tracing.md)
29. [13k Settlement-wide council scenario](13k_settlement_council_scenario.md)
30. [13l Opposing-groups council scenario](13l_opposing_groups_council_scenario.md)
31. [13m Cognition-shaped council scenario](13m_cognition_shaped_council_scenario.md)
32. [13a HTTP inspection coverage for v0.4–v0.5](13a_http_inspection_coverage.md)
33. [14 v0.5 release closeout](14_v05_release_closeout.md)

## Deferred post-v0.5 task candidates

These are documented design candidates, not active v0.5 work. They require a
separate milestone decision and must not delay Task 14.

1. [15 Read-only World Inspector UI architecture and vertical slice](15_world_inspector_ui.md)
2. [15a Spatial world-layout inspection contract and visualization](15a_spatial_world_inspection.md)

The broader proposed milestone sequence for progressing from a founding party
to an evolving town and regional simulation is documented in the
[post-v0.5 settlement-evolution roadmap](../post_v05_settlement_evolution_roadmap.md).
Its v0.6 work must be decomposed into isolated numbered plans and prompts only
after the milestone is explicitly authorized.

After the v0.6 vertical-slice acceptance target, the repository adopts the
milestone integration branch plus short-lived task branch workflow documented
in `docs/development_workflow.md`. Branch creation does not itself authorize a
roadmap task.

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
