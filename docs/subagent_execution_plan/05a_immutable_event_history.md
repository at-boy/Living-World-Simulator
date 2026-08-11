# 05a — Immutable event-history attributes

## Task Description

Make immutable world history genuinely immutable by preventing mutation of an
event's attribute mapping and every nested mutable attribute value after an
event has been recorded or reloaded.

## Context Needed

- Create: `docs/subagent_execution_plan/05a_immutable_event_history-report.md`.
- Edit: `src/living_world/core/event.py`,
  `src/living_world/managers/event_manager.py`,
  `src/living_world/repositories/sqlite_repository.py`,
  `tests/test_event_manager.py`, `tests/test_sqlite_repository.py`,
  `docs/technical_debt.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
  `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: `Event`, `EventManager.record()`, `GraphRepository`,
  `SQLiteRepository`, and ADR-0004 immutable history.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class Event:
    id: str
    tick: int
    kind: str
    subject_id: str | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)
```

- Event attributes must be recursively frozen when an `Event` is constructed.
  Nested mappings become immutable mappings, lists/tuples become tuples, and
  sets become frozensets. The event retains JSON-compatible scalar values.
- `EventManager.record()` accepts caller-owned mutable input but must neither
  retain nor expose a mutable alias of it.
- SQLite serialization converts the frozen attribute tree into JSON-safe plain
  data; loading reconstructs an `Event` through the same immutable contract.
- Preserve the public `EventManager.record()` signature and event JSON meaning.

## Test Criteria

- Attempts to mutate top-level and nested event attributes after direct
  construction, `EventManager.record()`, and SQLite reload fail.
- Mutating the input attributes after `record()` does not alter the event.
- Event round-trips through SQLite without changing nested data or losing
  immutability.
- Existing events, managers, repository, and full `make` validation pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/05a_immutable_event_history-report.md`.
Report the freezing/thawing contract, aliasing and nested-immutability test
evidence, repository compatibility, exact files changed, boundary compliance,
and validation results.

## Boundary

- Touch only the listed event, manager, repository, test, documentation, and
  approved report files.
- Do not alter the event schema semantically, add event mutation APIs, or
  change unrelated cognitive/history models.
- This task resolves the event-history immutability gap before later systems
  rely on historical events as trustworthy records.
