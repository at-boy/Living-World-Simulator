# Task 13 — Correction Prompt Before Commit

Do not commit yet. Correct only the following Task 13 defects and update the
plan/report accordingly.

1. Add `organization_id: str` to `CouncilCall`. The caller and every invitee
   must have a live `member_of` relationship whose `target_id` is exactly this
   organization ID. Being a member of an unrelated organization is ineligible.
   Validate the organization exists and all eligibility before any invitation
   context/model call. Update tests and examples.

2. Treat `NPCCognitionClientError`/`NPCCognitionInvalidResponseError` during
   an invitation response as non-attendance, exactly like a missing or rejected
   response. Do not catch unrelated programming errors broadly.

3. If every invitee declines or is unavailable, the caller may still convene a
   bounded council with no dialogue. Return an attendance result and empty
   `ConversationResult`/no majority/no resolutions; do not construct an invalid
   `MeetingRequest` with zero invitees and do not write observations/events.

4. Update the Task 13 plan and report with the same-organization eligibility,
   unavailable-response rule, and caller-only outcome. Retain and verify the
   documented manual commands in `docs/local_llm_setup.md` for both five-NPC
   examples.

Run `make`, `make examples`, and `git diff --check`; report exact results and
do not commit. Only use Task 13's existing file boundary plus this correction
prompt.
