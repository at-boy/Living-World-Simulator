# Task 18 — Goals and objective graphs report

## Delivered contract

Task 18 adds frozen goal/objective definitions for NPC, organization,
expedition, and settlement owners; six typed criterion variants; separate
immutable lifecycle/evidence records; manager-owned atomic graph creation and
state transitions; schema-v6 persistence with v1-v5 compatibility; deterministic
detached privileged inspection; and prose-only NPC interpretations.

The manager rejects missing owners, duplicate case-insensitive labels, invalid
deadlines/action categories, missing graph references, cycles, self-references,
duplicate objective identifiers and graph references, dependency/alternative
overlap, invalid runtime enum/tuple/numeric values, non-finite sustained-need
limits, and invalid evidence sources before mutation. Creation and transition
event failures roll back both state and any partially recorded event. Automatic
evaluation and work execution are not implemented.

Schema-v6 restoration revalidates case-insensitive label uniqueness per owner.
NPC-visible goal/objective labels and interpretations reject internal ID forms,
including goal/objective IDs, while operator-only purpose remains unrestricted.

## Files and interfaces

The new `living_world.goals` package exposes the definitions, states, criteria,
`NPCGoalInterpretation`, and `GoalManager`. `WorldState` owns four goal/objective
collections, `SimulationEngine.goals` composes the manager, SQLite uses schema
v6, and `GET /world/goals` exposes privileged snapshots. Example 029 demonstrates
creation, activation, and safe interpretation.

## NPC boundary

Engine truth includes owner/internal IDs, criteria, status, evidence, deadlines,
priority, and action categories. The NPC-safe record contains only label and
visible description; it has no reference to `WorldState` or privileged records.

## Validation

- Focused goal, inspection, and persistence suites: 65 tests passed.
- `make`: Ruff and Black passed, 547 tests passed, and examples 001-029 passed.
- Separate `make examples`: examples 001-029 passed.
- `git diff --check`: passed.
