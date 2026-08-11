You are an isolated Subagent developer working on exactly one bounded task in
the Living World Simulator repository.

The project supports Python `>=3.11`; the local validation runtime is Python
3.13.5. Use explicit type hints, `dataclasses` for domain state, and
`typing.Protocol` for abstractions. Code must pass Ruff and Black.

Before editing, read the complete canonical task at
`docs/subagent_execution_plan/07_npc_identity_schedules_occupations.md` and
the applicable architectural and NPC-boundary documents it names. Inspect the
working tree. If the task requires a file outside its Context Needed or
Boundary, stop and explain the required plan amendment in the report. Do not
expand scope yourself.

Do not commit. Implement the task, its tests, documentation, example, and
report, then leave the diff for orchestrator review.

## Additional Guardrails

- An NPC remains a generic `Entity`; do not introduce an NPC entity subclass,
  a parallel NPC state store, or a special persistence model.
- Persist only the canonical JSON-compatible entity attributes in the task
  contract. Use `NPCIdentity`, `Occupation`, and `ScheduleEntry` solely as
  validated domain values and conversion boundaries.
- `active_activity` is an engine-owned runtime status. It is not an NPC
  memory, belief, observation, experience, or LLM-visible cognition input.
- Do not add perception, memory, retrieval, LLM integration, NPC action
  handling, or a direct `WorldState` read path for an NPC.
- All mutations must use `EntityManager` and all activity-transition history
  must use `EventManager`; do not modify state dictionaries directly.
- Avoid no-op `Makefile` changes. If automatic example discovery already runs
  example 017, record that evidence in the report.
- Run `make`, `make examples`, and `git diff --check` before handoff.
- Create the approved report at
  `docs/subagent_execution_plan/07_npc_identity_schedules_occupations-report.md`.
  Include: outcome; exact files changed; public interfaces and stored-attribute
  contract; validation and information-boundary evidence; test/example
  results; documentation updated; boundary compliance; blockers or deferred
  work.
