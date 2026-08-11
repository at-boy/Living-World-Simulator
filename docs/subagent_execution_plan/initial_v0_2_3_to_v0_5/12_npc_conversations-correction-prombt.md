# Task 12 — Correction Prompt Before Commit

Task 12 is close, but do not commit yet. Make only the corrections below,
update the report, and leave all unrelated files untouched.

## Required Corrections

1. Preserve visible speaker attribution in the safe dialogue history.

   `ConversationTurn` explicitly consists of both `speaker_label` and
   `utterance`, and each later model must receive earlier *visible turns*, not
   un-attributed sentence fragments. After boundary validation, append a
   prose-only representation such as `"Erik: The grove feels peaceful."` to
   `conversation_history`. It must use the already safe display label, never a
   participant ID, and it must itself pass the conversation-prose boundary
   before later context assembly. Recipient `Observation.description` remains
   the utterance alone, with empty evidence and metadata.

2. Add direct boundary coverage in `tests/test_npc_information_boundary.py`.

   Construct an otherwise-valid `NPCContext` with `conversation_history` and
   prove `NPCInformationBoundary.validate_context()` rejects at least an
   internal ID and an authoritative numeric entity attribute in that field.
   This test must exercise the boundary directly, rather than only indirectly
   through `NPCContextAssembler` or `ConversationService`.

3. Update `docs/subagent_execution_plan/12_npc_conversations-report.md`.

   Record the labeled-history representation, the direct boundary test, exact
   files changed, and post-correction validation results.

## Validation and Boundary

Run `make`, `make examples`, and `git diff --check`; do not commit.

Only edit:

- `src/living_world/cognition/conversation.py`
- `tests/test_conversation.py`
- `tests/test_npc_information_boundary.py`
- `docs/subagent_execution_plan/12_npc_conversations-report.md`
- this correction prompt, if a minor factual update is necessary

Do not change action authority, observation metadata/evidence policy, engine
interfaces, LLM clients, or any domain behavior.
