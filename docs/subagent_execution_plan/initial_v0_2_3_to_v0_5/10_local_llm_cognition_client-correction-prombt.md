# Task 10 — Correction Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Correct only the Task 10 gap below; do not commit.

## Required Correction

The task requires action keys and target labels to be proposal vocabulary, not
engine IDs. The cognition client has no `WorldState`, so add a format-level
guard that rejects conventional internal record IDs anywhere in client-visible
values:

- `entity_<digits>`, `relationship_<digits>`, `event_<digits>`,
  `observation_<digits>`, `belief_<digits>`, `experience_<digits>`,
  `memory_<digits>`, `knowledge_<digits>`, and `npc_relationship_<digits>`;
- reject them in all `ActionOption` visible fields, `ActionRequest` visible
  fields/arguments, and `NPCDecision.spoken_text`;
- parsed provider output must therefore produce
  `NPCCognitionInvalidResponseError`, never an accepted decision.

Do not add a broad word blacklist and do not access `WorldState`. Add direct
value-object and parsed-provider-response tests. Update the report with this
boundary evidence and post-correction validation results.

## Allowed Files

- `src/living_world/cognition/npc_cognition_client.py`
- `src/living_world/cognition/local_llm_cognition_format.py`
- `tests/test_npc_cognition_client.py`
- `docs/subagent_execution_plan/10_local_llm_cognition_client-report.md`

Run `make`, `make examples`, and `git diff --check`. Do not edit other files
and do not commit.
