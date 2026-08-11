# 13i — NPC dialogue opening guidance

## Task Description

Improve the shared local-cognition instruction so an NPC starts with a direct
position when its visible history contains only a topic/agenda, rather than
responding as though an earlier speaker said something. The instruction must
continue to limit replies to visible dialogue once labelled prior turns exist.

## Context Needed

- Create: `docs/subagent_execution_plan/13i_npc_dialogue_opening_guidance-report.md`
  and `tests/test_npc_dialogue_opening_guidance.py`.
- Edit: `src/living_world/cognition/local_llm_cognition_format.py`,
  `tests/test_local_llm_cognition_format.py`, `docs/local_llm_setup.md`,
  `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: Task 13g `SYSTEM_INSTRUCTIONS`, NPC-visible `conversation_history`,
  and Task 12/12a conversation turn semantics.

## Interface Contract

```python
SYSTEM_INSTRUCTIONS: str
```

- No public signatures, schemas, parser acceptance behavior, or action
  authority change.
- The instruction tells the model that a topic/agenda alone is not a prior
  speaker: begin with its own direct position and do not use acknowledgement
  language such as “I see” or “I agree” as a reply to non-existent dialogue.
- When labelled visible dialogue is present, the model may respond only to that
  visible history and still must not invent unseen speakers, facts, IDs, or
  raw attributes.
- This is guidance only; it neither edits generated text nor guarantees a
  particular model style.

## Test Criteria

- Tests assert the shared instruction contains direct-opening and
  visible-history-only guidance, without world data, action vocabulary, IDs,
  or numeric attributes.
- Existing response-shape and strict-parser tests pass unchanged.
- `make`, `make examples`, and `git diff --check` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/13i_npc_dialogue_opening_guidance-report.md`.
Report the instruction semantics, boundary evidence, strict-parser preservation,
tests/commands/results, files changed, and the guidance-only limitation.

## Boundary

- Touch only the listed instruction/test/docs/report files.
- Do not edit council scheduling, manual examples, clients, schemas, parser
  acceptance logic, NPC context assembly, persistence, HTTP APIs, or Makefile.
