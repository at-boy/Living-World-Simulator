# Task 13h — Deterministic council turn rotation report

## Result

Task 13h is implemented. `CouncilCall` now exposes the public field
`turn_order_offset: int = 0`. Construction rejects booleans and other
non-integers with `TypeError`, and rejects negative integers with `ValueError`.
The field follows the existing fields so their positional interface remains
unchanged.

When `called_speaker_ids` is empty, `CouncilService` rotates the confirmed
attendee tuple by `turn_order_offset % len(attendees)` and constructs exactly
`max_rounds` cyclic speaker calls. Offset zero therefore preserves caller-first
round-robin behavior. Values larger than the attendee count wrap
deterministically. Only confirmed attendees participate in this construction.

When `called_speaker_ids` is non-empty, it remains the exact explicit schedule.
The offset is ignored, the existing maximum-length validation remains, and an
explicitly called participant who did not attend is still rejected.

## Determinism evidence

The new focused tests establish zero-offset order, offsets one and two,
modulo-wrapped offset four, zero and bounded round counts, explicit precedence,
and exclusion of a non-attendee. An integration test convenes a council with
three confirmed attendees and verifies that offset one produces the visible
speaker order `Mira, Sana, Erik` instead of caller-first order.

No randomness, time source, persistence, or model-selected scheduling was
introduced. Policy for deriving offsets from deterministic simulation state is
deliberately deferred to a later task.

## NPC information-boundary compliance

The offset is used only while constructing an engine-side `MeetingRequest`
speaker schedule. It is not included in an NPC context, conversation prose,
cognitive record, event, world state, action proposal, or action resolution.
LLM output has no path to choose or authorize it. Existing holder-scoped
context assembly and the proposal-to-action-gateway flow are unchanged.

## Changed files

- `src/living_world/cognition/council.py`
- `tests/test_council.py`
- `tests/test_council_turn_rotation.py`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/13h_deterministic_council_turn_rotation-report.md`

`src/living_world/cognition/__init__.py` required no textual change because
`CouncilCall` was already part of its public imports and `__all__`; the new
dataclass field is therefore available through the existing public export.

## Validation

- `.venv/bin/pytest tests/test_council_turn_rotation.py tests/test_council.py`
  — passed, 18 tests.
- `make` — passed Ruff fix/check, Black formatting/check, all 352 tests, and all
  22 executable examples.
- `make examples` — passed all 22 executable examples.
- `git diff --check` — passed with no output.

The final diff was inspected. It stays within Task 13h's allowed-file boundary,
and no commit was created.
