# 13c — Council invitation-feedback trace report

## Delivered

Added public `CouncilInvitationStatus` and `CouncilInvitationFeedback` types,
plus `CouncilResult.invitation_feedback`. The tuple is invitee-ordered and has
no caller record. Statuses identify accepted attendance, accepted decline, no
selection, and unavailable provider output. Existing council pre-validation and
the offered attendance vocabulary make a resolver-rejected invitation
unreachable, so feedback does not alter attendance semantics to invent one.

## Safety and output

Submitted speech and attendance rationales pass
`NPCContextAssembler.validate_conversation_prose` before becoming feedback.
Invalid prose is suppressed without error or raw provider payload exposure.
The two manual formatters now render an Invitation feedback section containing
each safe invitee label, status, submitted safe fields, or a generic missing
text indication. The trace remains result-only and is not persisted or used as
engine authority.

## Tests and validation

`tests/test_council_invitation_feedback.py` covers deterministic order, all
four statuses, safe attendee/decliner/no-selection fields, unavailable error
suppression, provider-error privacy, and suppression of internal/numeric prose.
Manual output tests cover invitee-only feedback and safe generic rendering.

- `PYTHONPATH=src .venv/bin/pytest tests/test_council.py tests/test_council_invitation_feedback.py tests/test_manual_council_examples.py`: 16 passed.
- `make`: passed; Ruff and Black passed, 310 tests passed, and numbered examples passed.
- `make examples`: passed; examples `001` through `022` passed.
- `git diff --check`: passed.

## Files and boundary

Changed only the specified council/export/tests/manual examples/docs and this
report. Feedback-specific service coverage is isolated in
`tests/test_council_invitation_feedback.py`; `tests/test_council.py` remains
focused on existing council behaviour. No cognition client, information-boundary,
action-resolution semantics, scheduling, persistence, HTTP, or Makefile code
was changed. The trace is operator-visible ephemeral result output and is not
forwarded to NPCs, retrieval, context assembly, or cognition. No blockers or
deferred work.

Task files changed: `src/living_world/cognition/council.py`,
`src/living_world/cognition/__init__.py`, `tests/test_council.py`,
`tests/test_council_invitation_feedback.py`,
`tests/test_manual_council_examples.py`, both manual council examples,
`docs/local_llm_setup.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
`CHANGELOG.md`, `docs/project_journal.md`, and this report.
