# Task 13g — Local cognition response-shape guidance report

## Result

The shared local cognition system instruction now requires exactly one bare JSON
object with no surrounding prose, Markdown, or code fence. It explicitly
requires the `spoken_text` and `action_request` top-level fields. A null action
request remains permitted when no action is genuinely proposed. An object-valued
action request must contain `action_key`, `target_label`, `rationale`, and
`arguments`; the guidance specifies `null` for an unoffered target and `{}` for
no arguments.

The instruction includes generic, schema-shaped templates for both an
action-request response and a null-action response. Their values are
placeholders only: they contain no world data, action-key literal, entity or
internal-record identifier, or numeric attribute.

## Strict parser preservation

`parse_decision_response` was not changed. Tests confirm it continues to accept
compliant null-action and offered-action responses, and to reject missing
`arguments`, missing `target_label`, Markdown-wrapped JSON, and unoffered
actions. No repair, normalization, inferred fields, or unoffered action is
accepted.

## Provider request evidence

The Ollama request test verifies its `system` and `format` values equal the
shared `SYSTEM_INSTRUCTIONS` and `RESPONSE_SCHEMA`. The llama.cpp request test
verifies its system message and response-format schema equal those same shared
objects.

## Validation

- `PYTHONPATH=src .venv/bin/pytest tests/test_local_llm_cognition_format.py tests/test_npc_cognition_client.py tests/test_ollama_cognition_client.py tests/test_llama_cpp_cognition_client.py` — 32 passed.
- Focused Black and Ruff checks — passed.
- `make` — passed: Ruff, Black, 339 tests passed, and all numbered examples passed.
- `make examples` — passed: all numbered examples passed.
- `git diff --check` — passed.

## Changed files and boundary

- `src/living_world/cognition/local_llm_cognition_format.py`
- `tests/test_local_llm_cognition_format.py`
- `tests/test_npc_cognition_client.py`
- `tests/test_ollama_cognition_client.py`
- `tests/test_llama_cpp_cognition_client.py`
- `docs/local_llm_setup.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- This report

No council policy, manual example, HTTP transport, parsing acceptance logic,
action resolution, information-boundary validation, persistence, HTTP API, or
Makefile code was changed. Instruction tuning improves local-model compliance
but cannot guarantee it; invalid responses remain non-authoritative and are
rejected.
