# Task 13i — NPC dialogue opening guidance report

## Result

The shared local-cognition instruction now distinguishes a topic or agenda from
labelled prior dialogue. With only topic context, it asks the NPC to begin with
its own direct position and avoid acknowledgement phrasing that implies a
non-existent earlier speaker. Once labelled prior turns exist, it limits the
reply to that visible dialogue and forbids invented unseen speakers or claims.

This is guidance only. Provider text is not rewritten, repaired, or guaranteed
to follow a particular style.

## Boundary and authority evidence

- Only `SYSTEM_INSTRUCTIONS` changed in runtime code.
- Request serialization and NPC context assembly are unchanged.
- `RESPONSE_SCHEMA`, response parsing, and parser acceptance are unchanged.
- Action vocabulary validation and action-gateway authority are unchanged.
- The new guidance names no concrete world object, internal identifier,
  action key, target label, or numeric attribute.
- Tests isolate the guidance paragraph and check for representative concrete
  data and internal-ID-shaped text.

## Tests and validation

- Initial focused run exposed assertions that did not account for line breaks;
  the tests were corrected to compare normalized instruction whitespace.
- `PYTHONPATH=src .venv/bin/pytest
  tests/test_npc_dialogue_opening_guidance.py
  tests/test_local_llm_cognition_format.py`: 8 passed after correction.
- `make`: passed Ruff, Black, all 355 tests, and all 22 examples.
- `make examples`: all 22 examples passed.
- `git diff --check`: passed.

## Files changed

- `src/living_world/cognition/local_llm_cognition_format.py`
- `tests/test_local_llm_cognition_format.py`
- `tests/test_npc_dialogue_opening_guidance.py`
- `docs/local_llm_setup.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/13i_npc_dialogue_opening_guidance-report.md`
