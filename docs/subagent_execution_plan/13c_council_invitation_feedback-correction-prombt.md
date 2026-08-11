# Task 13c — Correction Prompt: Preserve Attendance Semantics

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black.

Correct only Task 13c. Do not commit.

## Architectural Corrections

1. Remove `CouncilInvitationStatus.REJECTED` and all code/tests/docs/report
   references to it. The approved Task 13c plan now has four statuses.
2. Restore `_AttendanceHandler` exactly to its pre-Task-13c behaviour: after
   the existing eligible-actor check, it accepts either offered attendance
   action. In particular, do **not** reject `ActionRequest.arguments`.
   Task 13c is output observability, not a change to invitation acceptance.
3. Delete the artificial resolver-rejection test case and replace it with
   legitimate coverage of the four possible Task 13c outcomes only.
4. Create the required dedicated
   `tests/test_council_invitation_feedback.py` file. Move or add the
   feedback-specific service tests there; it must cover invitee-order,
   ATTENDING/DECLINED/NO_SELECTION/UNAVAILABLE, validated prose, unsafe prose
   suppression, and provider-error privacy. Keep `tests/test_council.py`
   focused on the existing council behaviour unless a minimal integration
   assertion is needed.
5. Update the report with the corrected four-status contract, exact changed
   files, and fresh validation results.

## Boundary

Only edit:

- `src/living_world/cognition/council.py`
- `src/living_world/cognition/__init__.py` (only if required by status removal)
- `tests/test_council.py`
- `tests/test_council_invitation_feedback.py`
- `tests/test_manual_council_examples.py`
- `examples/manual/ollama_council_meeting.py`
- `examples/manual/llama_cpp_council_meeting.py`
- `docs/local_llm_setup.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/13c_council_invitation_feedback-report.md`

Run and report:

```bash
make
make examples
git diff --check
```
