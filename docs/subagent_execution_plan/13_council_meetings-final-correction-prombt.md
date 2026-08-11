# Task 13 — Final Correction Prompt

Make this narrow correction only; do not commit.

`CouncilService.convene()` currently catches `TypeError` and `ValueError`
around attendance context assembly, decision, and resolver work. That masks
invalid engine input/boundary violations as ordinary non-attendance, contrary
to the documented validation boundary.

- Validate all `participant_self_knowledge` prose for the caller and every
  invitee through the existing information boundary before the first invitation
  model call. Unsafe/invalid engine-supplied perspectives must raise and make
  no model calls, observations, events, or actions.
- Do not broadly catch `TypeError` or `ValueError`. Catch
  `NPCCognitionClientError` for unavailable/invalid provider responses only;
  a malformed direct client decision may be treated as non-attendance only at
  the exact decision boundary, not by wrapping assembler/resolver code.
- Add tests proving unsafe perspective input fails loudly with no side effects,
  while an unavailable client still yields non-attendance.
- Update the report with this correction and validation results.

Run `make`, `make examples`, and `git diff --check`; do not commit. Remain
within the existing Task 13 file boundary plus this prompt.
