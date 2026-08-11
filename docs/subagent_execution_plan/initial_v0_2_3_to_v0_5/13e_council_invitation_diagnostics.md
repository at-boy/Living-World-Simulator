# 13e — Council invitation diagnostics

## Task Description

Make opt-in manual council output diagnostically useful when an invitee has no
safe visible reply. In particular, distinguish local-provider unavailability,
invalid structured provider output, and an invalid direct decision without
printing raw provider payloads, exception messages, IDs, or private engine
data. This task observes a failure safely; it does not coerce, retry, or repair
a model response.

## Context Needed

- Create: `docs/subagent_execution_plan/13e_council_invitation_diagnostics-report.md`
  and `tests/test_council_invitation_diagnostics.py`.
- Edit: `src/living_world/cognition/council.py`,
  `src/living_world/cognition/__init__.py`,
  `tests/test_council_invitation_feedback.py`,
  `tests/test_manual_council_examples.py`,
  `examples/manual/ollama_council_meeting.py`,
  `examples/manual/llama_cpp_council_meeting.py`, `docs/local_llm_setup.md`,
  `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: `CouncilInvitationFeedback`, `CouncilInvitationStatus`,
  `NPCCognitionClientError`, `NPCCognitionInvalidResponseError`, and Task
  13b/13c manual formatter contracts.

## Interface Contract

```python
class CouncilInvitationDiagnostic(StrEnum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_STRUCTURED_RESPONSE = "invalid_structured_response"
    INVALID_DECISION = "invalid_decision"

@dataclass(frozen=True, slots=True)
class CouncilInvitationFeedback:
    participant_label: str
    status: CouncilInvitationStatus
    spoken_text: str | None
    rationale: str | None
    diagnostic: CouncilInvitationDiagnostic | None = None
```

- `diagnostic` is present only when `status is UNAVAILABLE`; it is a fixed,
  operator-safe category and contains no provider text. It is `None` for all
  other statuses.
- Map an `NPCCognitionInvalidResponseError` to
  `INVALID_STRUCTURED_RESPONSE`; another `NPCCognitionClientError` to
  `PROVIDER_UNAVAILABLE`; and a caught `TypeError`/`ValueError` from the
  direct cognition decision boundary to `INVALID_DECISION`.
- The manual formatters retain
  `format_council_result(result: CouncilResult) -> str`. For unavailable
  feedback, they render a clear fixed diagnostic, such as “No usable reply:
  invalid structured response.” They must never render `repr(error)`, an
  exception message, response JSON, request JSON, IDs, raw attributes, or
  hidden reasoning.
- No automatic retry, default action, attendance inference, action-gateway
  change, event, persistence, or new NPC-readable context is introduced.

## Test Criteria

- Tests cover every diagnostic mapping and prove the category is shown only
  for UNAVAILABLE feedback.
- Tests prove manual output shows the safe category but not a deliberately
  distinctive raw provider-error message or an internal identifier.
- Existing safe feedback prose filtering, no-selection behavior, attendance,
  and action resolution remain unchanged.
- `make`, `make examples`, and `git diff --check` pass.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13e_council_invitation_diagnostics-report.md`.
Report diagnostic mapping, manual debugging evidence, raw-data exclusion,
validation commands/results, files changed, boundary compliance, and the
limitation that a category does not itself remedy a non-compliant model.

## Boundary

- Touch only the listed council/export/tests/manual examples/docs/report files.
- Do not edit local cognition clients, their HTTP transport/format/schema,
  `DecisionEngine`, information-boundary validation, action resolution,
  persistence, HTTP APIs, or Makefile.
- Do not emit raw provider responses/errors into the result, docs, tests, or
  manual output.
