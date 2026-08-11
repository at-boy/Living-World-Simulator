# 13b — Manual council-example observability

## Task Description

Correct the opt-in Ollama and llama.cpp council demonstrations so their
operator-facing output accurately distinguishes the always-attending caller
from invited attendees, and explains why an otherwise valid run can repeat the
same outcome. This is a manual-example usability correction only; it must not
alter council attendance, cognition sampling, or simulation authority.

## Context Needed

- Create: `docs/subagent_execution_plan/13b_manual_council_example_observability-report.md`
  and `tests/test_manual_council_examples.py`.
- Edit: `examples/manual/ollama_council_meeting.py`,
  `examples/manual/llama_cpp_council_meeting.py`, `docs/local_llm_setup.md`,
  `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: `CouncilResult` and `CouncilAttendance` in
  `src/living_world/cognition/council.py`; neither type may be changed for
  this task. The first attendance entry is the caller, who attends by the
  current Task 13 contract; subsequent entries represent invitees.

## Interface Contract

```python
def format_council_result(result: CouncilResult) -> str: ...
```

- Each manual module exports this helper. It accepts a `CouncilResult` and
  returns the complete human-readable output currently printed by the manual
  script. It raises `TypeError` for another input type.
- `main()` and `_run()` retain their current signatures and make the real
  loopback provider call only when the script is explicitly run.
- Attendance output identifies the first entry as the `caller`; all later
  entries are invitees. It continues to show safe attendance and delegation
  status only.
- When the caller is the sole attendee, output must say that only the caller
  attended and that no invited NPC joined, rather than saying that nobody
  attended. It must not diagnose whether an invitee declined, failed, or
  returned malformed model output because `CouncilResult` intentionally does
  not expose that information.
- Documentation explains that identical successive local-model outcomes are
  valid: the clients send equivalent constrained requests and rely on the
  provider/model sampling defaults. The examples do not promise random or
  varied outcomes, and this task must not add seed, temperature, or other
  sampling controls to cognition clients.

## Test Criteria

- Tests load each manual example without contacting a model server and verify
  its formatter output for a caller-only `CouncilResult`, including the caller
  marker and the accurate no-invitee wording.
- Tests also cover an invited attendee with a visible debate turn and proposal
  so output continues to include attendance, dialogue, and vote/proposal
  information.
- Both manual formatters reject a non-`CouncilResult` argument with
  `TypeError`.
- `make`, `make examples`, and `git diff --check` pass. Manual examples remain
  excluded from automated execution.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13b_manual_council_example_observability-report.md`.
Report the precise caller/invitee rendering change, local-model repeatability
guidance, test evidence proving the examples do not contact a provider during
test collection, validation commands/results, changed files, boundary
compliance, and blockers/deferred work.

## Boundary

- Touch only the two named manual examples, the named test, documentation
  files, and approved report artifact.
- Do not edit `CouncilService`, `CouncilResult`, local cognition clients,
  action resolution, test fixtures for council behaviour, or the Makefile.
- Do not expose internal IDs, raw model responses/errors, hidden invitation
  rationale, cognition records, or world state in the manual output.
- Preserve the NPC information boundary and the ordinary action gateway.
