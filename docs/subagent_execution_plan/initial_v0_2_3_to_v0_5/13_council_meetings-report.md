# Task 13 — Council meetings report

## Delivered

- Added bounded `CouncilService`, immutable agenda/call/result values, and
  engine delegation.
- Eligibility is checked against engine-side `member_of` relationships before
  invitation context assembly, including the required shared organization ID.
- Attendance proposals use a no-mutation handler. Declines are safe delegated
  social status only.
- Conversation can collect proposals without resolving them; a strict attendee
  majority is sent once through the normal resolver.

## Boundary evidence

Only display labels, agenda prose, filtered contexts, and visible dialogue are
provided to cognition. No council result creates a governance record or bypasses
the action gateway.

## Examples

`examples/022_council_meeting.py` is deterministic. The Ollama and llama.cpp
manual files document five differentiated local-model perspectives and are not
included in `make`.

## Validation

- Targeted Ruff and Black checks passed for all Task 13 Python files.
- `PYTHONPATH=src .venv/bin/pytest -q`: 299 passed.
- `PYTHONPATH=src .venv/bin/python examples/022_council_meeting.py`: passed.
- `git diff --check`: passed.
- `make`: passed (Ruff, Black, pytest, and examples).
- `make examples`: passed (examples 001 through 022).

## Correction

`CouncilCall.organization_id` requires every participant to be a member of the
same existing organization. Local cognition-client unavailability is safe
non-attendance. If no invitee attends, the caller receives a bounded empty
council result without observations, events, or a malformed meeting request.

Engine-supplied perspectives are now validated through the information boundary
for every participant before the first invitation call. Only provider failures
and malformed direct model decisions are treated as unavailable; assembler,
resolver, and other engine validation errors propagate.
