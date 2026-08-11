# Task 05a — Immutable Event History Report

## Outcome

Completed. `Event` now detaches and recursively freezes its attribute tree at
construction: mappings become read-only mappings, lists and tuples become
tuples, and sets become frozensets. This contract applies equally to direct
construction, `EventManager.record()`, and `SQLiteRepository` reloads.

SQLite event serialization now recursively converts the frozen tree into plain
JSON-safe mappings and lists. Event loading passes the decoded attributes to
`Event`, which reinstates the same recursive immutability contract.

## Exact Files Changed

- `src/living_world/core/event.py`
- `src/living_world/managers/event_manager.py`
- `src/living_world/repositories/sqlite_repository.py`
- `tests/test_event_manager.py`
- `tests/test_sqlite_repository.py`
- `docs/technical_debt.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/05a_immutable_event_history-report.md`

## Public Interfaces

`Event.attributes` is now declared as `Mapping[str, object]`:

```python
@dataclass(frozen=True, slots=True)
class Event:
    id: str
    tick: int
    kind: str
    subject_id: str | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)
```

`EventManager.record()` retains its existing public signature and accepts
caller-owned mutable dictionaries without retaining mutable aliases.

## Test Evidence

- Direct `Event` construction: verifies detachment from nested caller input
  and failed top-level/nested mapping, tuple, and frozenset mutation attempts.
- `EventManager.record()`: verifies later mutation of the supplied nested
  dictionary/list does not affect the event, and the event's nested tuple
  cannot be changed.
- SQLite reload: verifies the nested event mapping and tuple remain immutable;
  the repository round-trip equality assertion verifies nested data is
  preserved.

Validation completed successfully with Python 3.13.5:

```text
.venv/bin/ruff check src/living_world/core/event.py \
  src/living_world/managers/event_manager.py \
  src/living_world/repositories/sqlite_repository.py \
  tests/test_event_manager.py tests/test_sqlite_repository.py  # passed
PYTHONPATH=src .venv/bin/pytest tests/test_event_manager.py \
  tests/test_sqlite_repository.py                              # 9 passed
make                                                            # 158 passed
make examples                                                   # 15 passed
git diff --check                                                # passed
```

## Documentation Updated

The core model, glossary, technical-debt record, changelog, and project
journal now describe recursive event-attribute immutability and SQLite
reconstruction of that contract.

## Boundary Compliance

Only the files listed in Task 05a's boundary were changed, plus this approved
report artifact. No cognitive/history model outside `Event`, no event schema,
and no simulation system was changed.

## Blockers or Deferred Work

None.
