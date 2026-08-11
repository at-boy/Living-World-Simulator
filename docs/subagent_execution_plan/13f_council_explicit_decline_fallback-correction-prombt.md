# Task 13f — Correction Prompt: Preserve Call Contract and Accurate Output

You are an isolated Subagent developer. Correct only Task 13f; do not commit.

## Required Corrections

1. Restore the existing `CouncilCall` invariant that
   `invited_participant_ids` is non-empty. Restore the prior
   `_identifiers(..., True)` behaviour and update tests accordingly. Do not
   broaden the council-call API simply to exercise an impossible fallback case.
2. In both manual council formatters, when
   `result.decision_basis is CouncilDecisionBasis.EXPLICIT_DECLINE_CALLER_FALLBACK`,
   label `result.majority_proposal` as **Caller fallback proposal**. Retain
   **Majority proposal** for an attendee-majority (and the existing no-basis
   behaviour). The output must not imply a fallback proposal won a majority.
3. Update manual-output tests for both formatters, Task 13f report, and any
   affected docs to reflect the restored non-empty-call contract and accurate
   proposal label.
4. Run and report:

```bash
make
make examples
git diff --check
```

## Boundary

Only edit the files listed in Task 13f's Context Needed/Boundary plus its
approved report. Do not alter fallback eligibility, action resolution,
information-boundary behavior, diagnostics, persistence, or HTTP APIs.
