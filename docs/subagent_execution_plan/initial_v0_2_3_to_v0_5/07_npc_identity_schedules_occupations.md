# 07 — NPC identity, schedules, and occupations

## Task Description

Establish NPC identity, schedules, and occupations as validated domain data on
generic entities, ready for cognition but without yet introducing LLMs.

## Context Needed

- Create: `docs/subagent_execution_plan/07_npc_identity_schedules_occupations-report.md`.
- Create: `src/living_world/npc/identity.py`, `src/living_world/npc/schedule.py`,
  `src/living_world/npc/occupation.py`,
  `src/living_world/systems/schedule_system.py`, `tests/test_npc_identity.py`,
  `tests/test_schedule_system.py`, `examples/017_npc_schedules.py`.
- Edit: `src/living_world/npc/__init__.py`, `src/living_world/simulation/simulation_engine.py`,
  YAML definitions/examples, `Makefile`, and standard docs.
- Know: an NPC is an `Entity`; occupations and schedules are domain data, not
  new engine primitives.  Task 05 organizations may provide employment
  relationships.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class NPCIdentity:
    name: str
    description: str
    capability_descriptions: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class Occupation:
    title: str
    description: str

@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    start_tick: int
    end_tick: int
    activity: str

class ScheduleSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...
```

- Store only JSON-compatible attribute values on an NPC entity. The validated
  value objects must convert to and from these exact attribute forms:

  ```python
  "npc_identity": {
      "name": str,
      "description": str,
      "capability_descriptions": list[str],
  }
  "occupation": {"title": str, "description": str}
  "schedule": list[{"start_tick": int, "end_tick": int, "activity": str}]
  "active_activity": str | None
  ```

  `start_tick` is inclusive and `end_tick` is exclusive. Entries must have
  non-negative ticks, a non-empty activity, `start_tick < end_tick`, and no
  overlaps after sorting by `(start_tick, end_tick, activity)`. The active
  entry is the sole entry satisfying `start_tick <= state.tick < end_tick`;
  no match sets `active_activity` to `None`.
- Identity, occupation, and schedule attributes are validated through these
  value objects before use. Identity presentation contains no entity ID.
- Capability descriptions are prose such as “experienced woodcutter”; raw
  numeric skill scores remain authoritative engine data and are not stored in
  or exposed through the NPC identity value object.
- `ScheduleSystem` updates `active_activity` only via `EntityManager` and
  records `npc_activity_changed` through `EventManager` only when that value
  materially changes. It does not create beliefs, memories, observations, or
  experiences.

## Test Criteria

- Invalid, overlapping, or reversed schedule entries are rejected.
- The system deterministically selects the active entry at a tick.
- NPC identity never requires an internal ID in presentation data.
- Occupation and schedule attribute serializations round-trip through their
  value-object validators; schedules never expose raw numeric engine skills.
- An unchanged active activity creates no duplicate event; a transition and a
  transition to no scheduled activity each record one event.
- Example and `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/07_npc_identity_schedules_occupations-report.md`.
Report validated NPC data conventions, schedule determinism, information-boundary
considerations, example result, and validation results.

## Boundary

- Touch only stated NPC/schedule files, fixtures, registration, tests, example,
  and docs, plus the approved report artifact.
- Do not implement perception, memory, retrieval, or LLM reasoning yet.
