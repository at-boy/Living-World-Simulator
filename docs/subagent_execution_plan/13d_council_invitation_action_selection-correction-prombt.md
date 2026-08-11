# Task 13d — Correction Prompt: Preserve Internal-Identifier Boundary

You are an isolated Subagent developer. Correct only Task 13d; do not commit.

## Required Correction

The literal action key `attend_council` contains the current world's internal
organization identifier `council`. It therefore cannot appear in text passed
through `NPCContextAssembler.validate_conversation_prose`.

1. Change the invitation guidance to say that the invitee must return exactly
   one **offered attendance action** in `action_request`; retain the instruction
   to include a short reason in `rationale`, and the statement-alone warning.
2. Do not include `attend_council`, `decline_council`, or any other action-key
   literal in the validated invitation prose. The cognition client already
   receives the action keys in its separate structured action vocabulary.
3. Update capturing tests to assert the safe generic guidance, verify it has no
   action-key/internal-ID literal, and restore all existing council tests and
   example 022 to passing.
4. Update `docs/local_llm_setup.md`, `docs/project_journal.md`, and the Task
   13d report. The report must replace the blocked validation outcome with the
   final exact passing results and mention why action keys remain only in the
   structured vocabulary.

## Boundary

Only edit the Task 13d files listed in
`13d_council_invitation_action_selection.md` plus its approved report. Do not
change `NPCInformationBoundary`, world/entity identifiers, cognition-client
format, action keys, or manual examples.

Run and report:

```bash
make
make examples
git diff --check
```
