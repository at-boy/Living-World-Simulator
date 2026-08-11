# Task 13e — Council invitation diagnostics report

## Delivered behavior

Unavailable invitation feedback now carries one fixed `CouncilInvitationDiagnostic`:

- `provider_unavailable` for `NPCCognitionClientError`.
- `invalid_structured_response` for `NPCCognitionInvalidResponseError`.
- `invalid_decision` for a caught `TypeError` or `ValueError` at the direct
  cognition-decision boundary.

The diagnostic is required for `UNAVAILABLE` feedback and rejected for every
other invitation status. It contains no exception, provider response, request,
identifier, or engine data.

## Manual diagnostic evidence

Both opt-in council formatters retain `format_council_result(result) -> str`.
For unavailable feedback they render only a fixed sentence such as `No usable
reply: invalid structured response.` The offline formatter tests verify this
safe category is visible while a distinctive provider-error marker and internal
identifier are absent from output.

## Safety and limitation

No retry, fallback action, attendance inference, action-gateway change, event,
persistence, or NPC-readable context was added. A diagnostic category observes
the failure safely; it does not repair a non-compliant model response.

## Validation

- `make` — passed: Ruff, Black, and 321 pytest tests passed.
- `make examples` — passed: examples `001` through `022` passed.
- `git diff --check` — passed.

## Files changed

- `src/living_world/cognition/council.py`
- `src/living_world/cognition/__init__.py`
- `tests/test_council_invitation_diagnostics.py`
- `tests/test_council_invitation_feedback.py`
- `tests/test_manual_council_examples.py`
- `examples/manual/ollama_council_meeting.py`
- `examples/manual/llama_cpp_council_meeting.py`
- `docs/local_llm_setup.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- This report

## Boundary compliance

Only Task 13e council, export, manual example, documentation, report, and test
files were changed. No local cognition client, transport, decision engine,
information boundary, action resolution, persistence, HTTP API, or Makefile was
edited. No commit was created.
