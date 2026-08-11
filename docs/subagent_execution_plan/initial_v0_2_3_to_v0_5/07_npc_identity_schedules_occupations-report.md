# Task 07 — NPC identity, schedules, and occupations report

## Outcome

Implemented validated NPC presentation and scheduling data without adding an
NPC runtime type, state store, persistence model, cognition pathway, or LLM
integration. NPCs remain generic entities with JSON-compatible attributes.

`ScheduleSystem` deterministically derives each NPC entity's engine-owned
`active_activity` at the current scheduler tick. It performs state changes
through `EntityManager` and records only material changes as immutable
`npc_activity_changed` events through `EventManager`.

## Files Changed

- `src/living_world/npc/__init__.py`
- `src/living_world/npc/identity.py`
- `src/living_world/npc/occupation.py`
- `src/living_world/npc/schedule.py`
- `src/living_world/systems/schedule_system.py`
- `src/living_world/simulation/simulation_engine.py`
- `tests/test_npc_identity.py`
- `tests/test_schedule_system.py`
- `examples/017_npc_schedules.py`
- `CHANGELOG.md`
- `docs/backlog.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/07_npc_identity_schedules_occupations-report.md`

The pre-existing task-plan and prompt artifacts remain orchestrator-owned and
are not implementation changes from this task.

## Public Interfaces and Attribute Contract

- `NPCIdentity(name, description, capability_descriptions=())` validates
  NPC-facing presentation data and provides `to_attribute()` and
  `from_attribute(value)`.
- `Occupation(title, description)` provides the same validated conversion
  boundary.
- `ScheduleEntry(start_tick, end_tick, activity)` validates an inclusive-start,
  exclusive-end activity interval. `schedule_to_attribute(entries)` and
  `schedule_from_attribute(value)` provide canonical sorted conversion and
  reject overlap.
- `ScheduleSystem(entities, events)` implements `SimulationSystem.step(state)`
  and is registered by `SimulationEngine`.

The only stored NPC scheduling values are:

```python
{
    "npc_identity": {
        "name": str,
        "description": str,
        "capability_descriptions": list[str],
    },
    "occupation": {"title": str, "description": str},
    "schedule": [
        {"start_tick": int, "end_tick": int, "activity": str},
    ],
    "active_activity": str | None,
}
```

Schedule entries are sorted by `(start_tick, end_tick, activity)` for
validation. They require non-negative integer ticks, `start_tick < end_tick`,
and non-empty activity text. The sole matching entry satisfies
`start_tick <= state.tick < end_tick`; no match produces `None`.

## Tests and Example Evidence

- `tests/test_npc_identity.py` verifies identity presentation has no entity ID,
  direct construction rejects non-string identity and occupation text,
  non-tuple capability collections, strings used as capability collections,
  and non-string capability entries. It also verifies capability descriptions
  cannot contain numeric skills, occupation/schedule serialization round-trips,
  and invalid, reversed, or overlapping schedules are rejected.
- `tests/test_schedule_system.py` verifies deterministic activity selection,
  no duplicate event for unchanged activity, transition-to-none history,
  invalid schedule rejection before state mutation, and ignoring non-NPC
  entities.
- `examples/017_npc_schedules.py` loads only a YAML `person` definition,
  creates the runtime entity through `EntityManager`, and demonstrates the
  schedule transitions. Automatic numeric-example discovery included it; no
  `Makefile` change was necessary.

## Information-Boundary Evidence

- `NPCIdentity` stores prose capability descriptions only. It rejects numeric
  capability values; numeric skills such as `woodcraft` remain separate,
  authoritative entity attributes.
- `active_activity` is runtime engine status and is not added to observation,
  memory, belief, experience, retrieval, perception, or LLM code.
- The implementation introduces no direct `WorldState` read path for an NPC,
  and no cognition or LLM integration.
- `ScheduleSystem` reads the scheduler tick, delegates all entity mutations to
  `EntityManager`, and records transitions solely through `EventManager`.

## Validation

All commands ran with Python 3.13.5 and passed.

    .venv/bin/ruff check src tests
    .venv/bin/black --check src tests
    PYTHONPATH=src .venv/bin/pytest -q tests/test_npc_identity.py tests/test_schedule_system.py
    PYTHONPATH=src .venv/bin/python examples/017_npc_schedules.py
    make
    make examples
    git diff --check

`make` passed Ruff, Black, and the complete pytest suite: **189 passed**.
It also ran examples `001` through `017`; the explicit `make examples` repeat
passed the same complete set.

## Validation Correction

The first handoff did not deliberately validate all direct-construction type
failures. This correction added explicit type checks before string operations
in `NPCIdentity` and `Occupation`, plus focused pytest coverage for every
invalid direct-construction input named in the correction request. The
correction touched only `identity.py`, `occupation.py`,
`tests/test_npc_identity.py`, and this report; it did not alter schedule
semantics, engine registration, information-boundary behavior, or task-plan
artifacts.

## Documentation Updated

Updated `CHANGELOG.md`, `docs/backlog.md`, `docs/core_model.md`,
`docs/engine_glossary.md`, and `docs/project_journal.md` with the generic NPC
attribute model, schedule timing semantics, event convention, and the fact
that numeric skills remain engine-only data.

## Boundary Compliance

Only the task's NPC value objects, schedule system, engine registration,
tests, example, standard documentation, backlog, and this approved report were
changed. No `Makefile` change was made because it already discovers every
numbered top-level example. No perception, cognition, memory, retrieval, LLM,
action handling, NPC subclass, or special persistence work was introduced.

## Blockers or Deferred Work

None. Memory, belief, experience, knowledge, cognitive consolidation,
retrieval, perception filtering, and LLM cognition remain intentionally
deferred to their scheduled tasks.
