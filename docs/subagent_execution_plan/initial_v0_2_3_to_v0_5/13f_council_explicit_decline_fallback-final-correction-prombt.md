# Task 13f — Final Correction Prompt: Boundary Record and Unavailable Proof

You are an isolated Subagent developer. Correct only Task 13f; do not commit.

## Required Corrections

1. Add an explicit test in `tests/test_council_explicit_decline_fallback.py`
   where at least one invitee is `UNAVAILABLE` and another explicitly declines.
   Assert that no caller fallback decision is requested, no proposal/resolution
   occurs, and no state mutation occurs. Do not use no-selection as a proxy for
   unavailable.
2. Update
   `docs/subagent_execution_plan/13f_council_explicit_decline_fallback-report.md`
   to include `tests/test_council_invitation_action_selection.py` in its exact
   changed-files list and record the explicit unavailable-case evidence.
3. Do not broaden implementation scope. The plan was amended to approve the
   existing invitation-guidance test update because Task 13f truthfully changes
   that invitation text; no other out-of-boundary files are approved.
4. Run and report:

```bash
make
make examples
git diff --check
```

## Boundary

Only edit:

- `tests/test_council_explicit_decline_fallback.py`
- `docs/subagent_execution_plan/13f_council_explicit_decline_fallback-report.md`

Do not modify policy, resolver, invitation, diagnostics, manual examples,
documents, or task plan files.
