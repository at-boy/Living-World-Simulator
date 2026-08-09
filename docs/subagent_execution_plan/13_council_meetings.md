# 13 — Council meetings

## Task Description

Implement councils as bounded, agenda-driven conversation orchestration whose
conclusions still require the standard simulation action gateway.

## Context Needed

- Create: `docs/subagent_execution_plan/13_council_meetings-report.md`.
- Create: `src/living_world/cognition/council.py`, `tests/test_council.py`,
  `examples/021_council_meeting.py`.
- Edit: `src/living_world/cognition/__init__.py`,
  `src/living_world/simulation/simulation_engine.py`, `Makefile`, and standard
  docs.
- Know: Task 12 conversation service, Task 11 action gateway, Task 05
  organization membership graph, and Task 09 context boundary.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class CouncilAgenda:
    topic: str
    action_options: tuple[ActionOption, ...]

class CouncilService:
    def convene(
        self,
        *,
        participant_ids: tuple[str, ...],
        agenda: CouncilAgenda,
        max_rounds: int,
    ) -> ConversationResult: ...
```

- A council is an orchestration of bounded conversation rounds, not a new
  authoritative governance subsystem.
- Agenda actions are predeclared by the simulation. Consensus is a proposal;
  every proposed action follows the same validation/application gateway.
- Membership eligibility is checked engine-side through relationships and does
  not expose membership IDs or scores to participants.

## Test Criteria

- Ineligible participants are rejected before context assembly.
- Participants only receive allowed agenda text and filtered dialogue/context.
- A consensus does not change state without an accepted handler result.
- Round limits and action-resolution order are deterministic; example and
  `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/13_council_meetings-report.md`. Report
membership-eligibility checks, agenda/context filtering, consensus-versus-action
validation evidence, and validation results.

## Boundary

- Touch only stated council files, integration, tests, example, and docs.
- The approved report artifact is also allowed.
- Do not create a special `Council` world primitive or direct state mutation.
- Preserve all conversation and action-boundary guarantees.
