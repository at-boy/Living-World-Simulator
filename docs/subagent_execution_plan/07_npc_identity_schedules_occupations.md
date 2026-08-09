# 07 — NPC identity, schedules, and occupations

## Task Description

Establish NPC identity, schedules, and occupations as validated domain data on
generic entities, ready for cognition but without yet introducing LLMs.

## Context Needed

- Create: `docs/subagent_execution_plan/07_npc_identity_schedules_occupations-report.md`.
- Create: `src/living_world/npc/identity.py`, `src/living_world/npc/schedule.py`,
  `src/living_world/systems/schedule_system.py`, `tests/test_npc_identity.py`,
  `tests/test_schedule_system.py`, `examples/016_npc_schedules.py`.
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
class ScheduleEntry:
    start_tick: int
    end_tick: int
    activity: str

class ScheduleSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...
```

- Identity/schedule data is stored under documented NPC entity attributes but
  validated through these value objects before use.
- Capability descriptions are prose such as “experienced woodcutter”; raw
  numeric skill scores remain engine data and are not an NPC-LLM interface.
- Schedule changes record events and do not themselves create beliefs or
  memories.

## Test Criteria

- Invalid, overlapping, or reversed schedule entries are rejected.
- The system deterministically selects the active entry at a tick.
- NPC identity never requires an internal ID in presentation data.
- Example and `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/07_npc_identity_schedules_occupations-report.md`.
Report validated NPC data conventions, schedule determinism, information-boundary
considerations, example result, and validation results.

## Boundary

- Touch only stated NPC/schedule files, fixtures, registration, tests, example,
  and docs, plus the approved report artifact.
- Do not implement perception, memory, retrieval, or LLM reasoning yet.
