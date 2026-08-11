# 13h — Deterministic council turn rotation

## Task Description

Allow the engine to choose which confirmed council attendee opens an automatic
discussion, while retaining reproducible round-robin scheduling. This removes
the hard-wired caller-first pattern without letting an LLM control the order or
introducing ambient randomness into simulation behavior.

## Context Needed

- Create: `docs/subagent_execution_plan/13h_deterministic_council_turn_rotation-report.md`
  and `tests/test_council_turn_rotation.py`.
- Edit: `src/living_world/cognition/council.py`,
  `src/living_world/cognition/__init__.py`, `tests/test_council.py`,
  `docs/core_model.md`, `docs/engine_glossary.md`, `CHANGELOG.md`, and
  `docs/project_journal.md`.
- Know: `CouncilCall`, `CouncilService._schedule`, Task 12a directed dialogue,
  and the current automatic round-robin schedule used when
  `called_speaker_ids` is empty.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class CouncilCall:
    # Existing fields unchanged.
    turn_order_offset: int = 0
```

- `turn_order_offset` is a non-negative, engine-owned integer.
- When `called_speaker_ids` is empty, rotate the confirmed attendee tuple by
  `turn_order_offset % len(attendees)` before constructing the bounded
  round-robin sequence. Offset `0` preserves current caller-first behavior.
- When `called_speaker_ids` is non-empty, preserve Task 12a's explicit call
  schedule exactly; the offset has no effect.
- The offset is not sent to an NPC/LLM, stored as a cognitive record, treated
  as authority, or selected by model output. The engine may choose it per
  council from deterministic simulation state in a later task.

## Test Criteria

- Offset `0` preserves existing automatic scheduling.
- Different offsets rotate confirmed attendees deterministically, including
  offsets larger than the attendee count and a bounded number of rounds.
- Explicit call schedules override rotation; absent/declined invitees cannot
  enter the schedule.
- Invalid offsets reject with precise `TypeError`/`ValueError` behavior.
- `make`, `make examples`, and `git diff --check` pass.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13h_deterministic_council_turn_rotation-report.md`.
Report the public field, automatic/explicit scheduling distinction,
determinism evidence, tests/commands/results, changed files, boundary
compliance, and the deferred engine policy for choosing offsets.

## Boundary

- Touch only the listed council/export/test/documentation/report files.
- Do not add randomness, persistence, events, LLM-selected turn order, changes
  to meeting/conversation APIs, action-gateway behavior, or manual examples.
