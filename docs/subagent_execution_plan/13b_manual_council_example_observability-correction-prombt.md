# Task 13b — Correction Prompt: Caller-only Result Rendering

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black.

Correct only Task 13b's manual council-example observability implementation.
Do not write code outside the boundary below and do not commit.

## Defect

`CouncilService` returns one `CouncilAttendance` for the caller **and** one for
every invitee, including invitees who did not attend. Consequently,
`len(result.attendance) == 1` is false in the actual five-NPC caller-only case.
The current formatter will still say “No invitee attended, so no debate was
held,” without the required caller-only clarification.

## Required Correction

1. In both manual formatters, determine whether any **invitee** attended from
   entries after the first attendance entry. Do not infer this from the total
   attendance-record count.
2. If the caller is attending and no invitee attended, render the exact clear
   meaning that only the caller attended and no invited NPC joined. Do not
   expose an absence reason.
3. The ordinary empty-debate message must not contradict that statement. It
   may say that no debate was held because no invitee joined, but must not say
   merely “No invitee attended” in isolation.
4. Update the offline formatter tests to construct a realistic caller-plus-
   absent-invitee `CouncilResult` and assert the corrected output in **both**
   manual modules.
5. Update the Task 13b report with the correction and new exact validation
   results. Its earlier claim that caller-only output was covered is false
   until the realistic result shape is tested.

## Boundary

Only edit:

- `examples/manual/ollama_council_meeting.py`
- `examples/manual/llama_cpp_council_meeting.py`
- `tests/test_manual_council_examples.py`
- `docs/subagent_execution_plan/13b_manual_council_example_observability-report.md`

Run and report:

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_manual_council_examples.py
make
make examples
git diff --check
```
