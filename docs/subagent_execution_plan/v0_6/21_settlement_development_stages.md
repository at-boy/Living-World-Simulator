# 21 — Settlement development stages

## Status and dependency

Authorized after reviewed Task 20b. Execute on the pushed
`task/21-settlement-development-stages` branch created from reviewed
`milestone/v0.6` commit `32bc83e`.

Task 21 is one isolated implementation task. It must be independently reviewed,
corrected where necessary, fully validated, committed, merged with `--no-ff`
into `milestone/v0.6`, and pushed there before Task 22 begins. It must never be
committed, merged, or pushed to `main`.

## Objective

Add configurable engine-owned `founding_camp`, `settlement`, and `town`
development stages for one explicitly configured settlement. Promotion is
derived only from completed, settlement-owned goal objectives and their
authoritative evidence. Population or an LLM assertion alone can never promote
a settlement.

## Non-goals

- No decline, demotion, abandonment, or recovery policy.
- No reusable/global stage templates, template bindings, or per-settlement
  overrides.
- No scenario-YAML stage configuration; Task 23 owns canonical founders
  scenarios.
- No automatic stage interpretation injection into `NPCContext` or LLM input.
- No LLM, cognition proposal, work system, or ordinary system authority to
  configure or mutate stage state.
- No direct stage-system reevaluation of raw needs, resources, capabilities,
  maintenance, external references, or population.
- No multi-stage promotion in one tick.
- No Task 15/15c inspector UI work beyond the existing privileged inspection
  protocol and HTTP API.

## Authoritative model

Create `src/living_world/stages/` with frozen, slotted records and closed enums.

`SettlementStage(str, Enum)` has exactly these values in this order:

1. `FOUNDING_CAMP = "founding_camp"`
2. `SETTLEMENT = "settlement"`
3. `TOWN = "town"`

`StageRequirementKind(str, Enum)` has exactly `WATER`, `FOOD`, `SHELTER`,
`STORAGE`, `MAINTENANCE`, `EXTERNAL_CONNECTION`, `POPULATION`, and `CAPABILITY`
with their lowercase values.

Durable records are:

- `StageObjectiveRequirement(kind: StageRequirementKind, objective_id: str)`;
- `SettlementStageDefinition(stage: SettlementStage, requirements:
  tuple[StageObjectiveRequirement, ...])`;
- `SettlementStageProgram(settlement_id: str, stages:
  tuple[SettlementStageDefinition, ...])`, bound directly to one settlement
  with no separate program ID or template indirection;
- `SettlementStageState(settlement_id: str, current_stage: SettlementStage,
  entered_tick: int, last_transition_tick: int | None = None)`;
- `StageRequirementEvidence(kind: StageRequirementKind, objective_id: str,
  source_event_ids: tuple[str, ...])`, used only to normalize one transition
  event and not duplicated in durable stage state;
- `NPCSettlementStageInterpretation(label: str, description: str)`, rejecting
  empty text and internal engine-ID forms.

Records contain no callbacks, expressions, prompt text, raw runtime objects, or
arbitrary attributes. `WorldState` owns `settlement_stage_programs` and
`settlement_stage_states` dictionaries keyed by settlement entity ID. Records
are immutable; only `SettlementStageManager` mutates the dictionaries.

## Objective-backed requirement contract

Stage promotion does not inspect raw domain state. A requirement is satisfied
only when its referenced `ObjectiveState.status` is `GoalStatus.COMPLETED`.
Configuration resolves each objective to exactly one `GoalDefinition` whose
owner kind is `SETTLEMENT` and owner ID equals the program settlement ID.

The declared kind must match at least one referenced objective completion
criterion:

| Requirement kind | Required completion criterion |
| --- | --- |
| water | `SustainedNeedCriterion(need="water", ...)` |
| food | `SustainedNeedCriterion(need="food", ...)` |
| shelter | `SustainedNeedCriterion(need="shelter", ...)` |
| storage | `SustainedNeedCriterion(need="storage", ...)` |
| maintenance | new `MaintainedCapabilityCriterion` |
| external connection | `ExternalConnectionCriterion` |
| population | new `PopulationMinimumCriterion` |
| capability | `ConstructedCapabilityCriterion` or `CapacityCriterion` |

Add these frozen records to the closed `GoalCriterion` vocabulary:

- `PopulationMinimumCriterion(minimum: int)` requires the live owner's
  non-negative integer `population` attribute to meet the positive minimum.
  Missing population is unavailable; invalid types fail loudly.
- `MaintainedCapabilityCriterion(capability: str, count: int,
  minimum_condition: int)` requires at least `count` live directly owned,
  constructed entities whose definition key exactly matches `capability`, each
  with one owner-matching maintenance policy and condition at least the
  positive minimum. Missing matching state is unsatisfied; malformed or
  contradictory authoritative records fail loudly.

Register both deterministic evaluators in the closed goal registry and add
strict manager validation and schema-11 serialization. Results use normalized
descriptions and lexically sorted source event IDs through the existing frozen
`CriterionEvaluation` contract.

For sustained-need stage requirements, configuration requires a unique current
owner `NeedDefinition` of the matching `NeedKind`, and the referenced
`duration_ticks` must not exceed `assessment_window_ticks`. Otherwise reject
configuration instead of accepting a permanently unavailable requirement.

The existing `SettlementStageCriterion` remains a goal criterion. Its default
evaluator reads only managed stage state: satisfied at or beyond the requested
canonical stage, unsatisfied below it, and unavailable for an unconfigured
owner or unsupported legacy stage string. A goal sees promotion on the next
tick because stage evaluation follows goal evaluation; same-phase circular
reevaluation is forbidden.

## Manager ownership and validation

`SettlementStageManager` is the exclusive configuration and mutation boundary.
It provides these exact public signatures:

- `configure(program: SettlementStageProgram) -> SettlementStageProgram`
- `get(settlement_id: str) -> SettlementStageProgram | None`
- `state_for(settlement_id: str) -> SettlementStageState | None`
- `all() -> tuple[SettlementStageProgram, ...]`
- `transition_to_next(settlement_id: str, evidence:
  tuple[StageRequirementEvidence, ...]) -> SettlementStageState`
- `npc_interpretation(settlement_id: str) ->
  NPCSettlementStageInterpretation`
- `validate_loaded_state() -> None`
- `validate_entity_removal(entity_id: str) -> None`
- `validate_entity_destruction(entity_id: str) -> None`

`all()` is ordered lexically by settlement ID. Evidence records are ordered by
`(kind.value, objective_id)`, have unique objective IDs, and contain lexically
sorted unique nonempty source event IDs.

Configuration rejects:

- non-record inputs or unsupported enum values;
- an unknown or destroyed settlement owner;
- objectives not owned through exactly one settlement goal for that owner;
- duplicate configuration for one settlement;
- anything other than the exact three unique canonical stages in order;
- nonempty `founding_camp` requirements;
- empty `settlement` or `town` requirements;
- duplicate objective references within one stage;
- incompatible requirement kinds and objective criteria;
- missing/ambiguous owner needs or excessive sustained windows;
- a promotion stage whose requirements are population-only;
- persisted key/owner mismatches, impossible stages, negative/future ticks,
  or a non-`None` `last_transition_tick` unequal to `entered_tick`; both ticks
  must be no later than the world tick.

`configure()` atomically stores the program plus initial `FOUNDING_CAMP` state
with `entered_tick` equal to the current tick and `last_transition_tick=None`.
It emits one `settlement_stage_program_configured` event and rolls back records
and new events on failure. Initial configuration is not a promotion.

Entity removal or destruction is rejected while an entity owns a stage program
or state. Extend existing `EntityManager` checks without weakening current
consequence, need, goal, dispatch, spatial, or work guards.

## Deterministic evaluation and events

`SettlementStageEvaluationSystem` evaluates programs in lexical settlement-ID
order and considers only the definition immediately after the current stage.

- Every next-stage objective must be completed.
- Inactive, active, blocked, or failed objectives change nothing and emit
  nothing.
- At most one adjacent transition occurs per settlement per world tick.
  `last_transition_tick == WorldState.tick` makes reevaluation idempotent.
- If both higher-stage sets are already complete, the first evaluation reaches
  `settlement` and `town` cannot be reached before the next tick.
- `TOWN` is terminal and repeated evaluation is a no-op.

Each transition emits exactly one immutable `settlement_stage_transitioned`
event, subject to the settlement, with exactly these attributes:

- `previous_stage`
- `current_stage`
- `requirements`: a tuple ordered by `(kind.value, objective_id)`; each item
  contains exactly `kind`, `objective_id`, and sorted unique `source_event_ids`

Sources are the union of normalized progress evidence source IDs and immutable
objective lifecycle event IDs. These exact IDs and criteria are privileged.

The whole stage phase snapshots stage states and pre-phase event IDs. Any
unexpected error restores every stage state and removes every phase event.
Earlier tick phases remain outside this transaction. Manager-level transition
failure also restores the individual prior state and new events.

## Scheduler ordering

Compose and expose the manager in `SimulationEngine`, and rebuild in this order:

```text
registered ordinary systems
  -> WorkExecutionSystem
  -> ConsequenceSystem
  -> NeedAssessmentSystem
  -> GoalEvaluationSystem
  -> SettlementStageEvaluationSystem
  -> tick increment
```

Only goal evaluation produces objective completion/evidence; stage evaluation
consumes it. Work and ordinary systems never mutate stage state.

## Persistence and migration

Advance SQLite snapshots from schema 10 to schema 11.

- Persist programs and states as strict JSON-safe records in stable owner and
  stage order, plus the two new goal criteria.
- Schemas 1–10 load empty stage collections. Never invent legacy
  `founding_camp` programs without objective-role mappings.
- Legacy worlds write schema 11 on the next save.
- Reconstruct prerequisite entities, goals/objectives, needs, consequences,
  external references, and events before validating stages.
- Reject missing/extra fields, invalid discriminators, noncanonical ordering,
  duplicates, invalid owners, definition/state mismatch, and future state.
- Serialization/validation failure leaves the prior database snapshot intact.
- Save/resume produces the same stage, tick, and transition sequence as an
  uninterrupted run.

## Privileged inspection

Extend `WorldInspector` and `EngineWorldInspector` with
`settlement_stages() -> tuple[Mapping[str, object], ...]` and
`world_summary()["settlement_stage_program_count"]`. Output is settlement-ID
ordered, recursively detached, JSON-safe, and contains exact privileged program
and state. Add GET-only `/world/settlement-stages` to FastAPI.

## NPC information boundary

The engine knows exact programs, IDs, thresholds, enum state, ticks, evidence,
and events. An NPC may receive only explicitly selected fixed prose describing
a newly established community, established settlement, or developed town.
The projection contains no IDs, exact criteria, status record, thresholds,
ticks, evidence, or arbitrary state and is never automatically injected into
observations, memory, retrieval, `NPCContext`, or prompts.

Extend `NPCInformationBoundary` so stage collections, identifiers, and numeric
state participate in fail-closed validation. There is no LLM action or gateway
for promotion; only the evaluation system may request a manager transition.

## Required tests

Add `tests/test_settlement_stages.py` and focused affected-test additions. Prove:

1. strict frozen records, canonical order, configuration, and safe prose;
2. every validation and contradiction above;
3. both adjacent transitions, one per tick, with exactly one event each;
4. every requirement kind independently blocks while incomplete;
5. unsustained needs and invalid need windows cannot promote;
6. population-only rejection and no LLM/prose mutation authority;
7. deterministic population/maintenance evaluators, normalization, loud invalid
   state failure, and sorted sources;
8. all `SettlementStageCriterion` dispositions and next-tick goal visibility;
9. same-tick and terminal-town idempotence;
10. manager and whole-phase rollback;
11. entity removal/destruction guards;
12. schema-11 round trip, schemas 1–10 empty defaults/write-forward, malformed
    records, failed-save preservation, and save/resume equivalence;
13. inspection ordering, detachment, empty output, summary, and GET-only API;
14. NPC prose, no auto-injection, and boundary rejection of IDs/numbers;
15. exact scheduler placement.

Add `examples/037_settlement_development_stages.py` showing explicit
configuration, objective-backed adjacent promotions, privileged inspection,
and qualitative NPC prose without hidden evidence.

Use focused tests during implementation. Before approval run the complete
focused matrix, then `make`, separate `make examples`, and `git diff --check`.
Record commands, results, counts, and meaningful warnings only.

## Documentation and report

- Keep the accepted
  `docs/adr/ADR-0024-engine-owned-settlement-development-stages.md` accurate;
  amend it only if review requires a contract correction before the matching
  implementation change.
- Update `CHANGELOG.md`, `docs/project_journal.md`, `docs/backlog.md`,
  `docs/core_model.md`, `docs/engine_glossary.md`, and
  `docs/npc_information_boundary.md`.
- Create a truthful
  `docs/subagent_execution_plan/v0_6/21_settlement_development_stages-report.md`
  with files, behavior, review corrections, validation counts, warnings, and
  remaining non-goals.

## Allowed-file boundary

- `src/living_world/stages/__init__.py`
- `src/living_world/stages/model.py`
- `src/living_world/stages/manager.py`
- `src/living_world/stages/system.py`
- `src/living_world/goals/model.py`
- `src/living_world/goals/manager.py`
- `src/living_world/goals/evaluation.py`
- `src/living_world/goals/__init__.py`
- `src/living_world/state/world_state.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/managers/entity_manager.py`
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/api/inspection.py`
- `src/living_world/api/server.py`
- `src/living_world/cognition/information_boundary.py`
- `src/living_world/__init__.py` only if the established root public API needs
  a Task 21 export
- `tests/test_settlement_stages.py`
- focused additions to `tests/test_goal_evaluation.py`, `tests/test_goals.py`,
  `tests/test_entity_manager.py`, `tests/test_simulation_engine.py`,
  `tests/test_sqlite_repository.py`, `tests/test_inspection_api.py`,
  `tests/test_npc_information_boundary.py`, and `tests/test_npc_context.py`
- `examples/037_settlement_development_stages.py`
- `docs/adr/ADR-0024-engine-owned-settlement-development-stages.md`
- `CHANGELOG.md`, `docs/project_journal.md`, `docs/backlog.md`,
  `docs/core_model.md`, `docs/engine_glossary.md`, and
  `docs/npc_information_boundary.md`
- this plan, its saved `-prombt.md`, and required `-report.md`

Amend this plan and prompt before touching anything outside this boundary.
Record unrelated discoveries for later rather than fixing them.

## Report

Create
`docs/subagent_execution_plan/v0_6/21_settlement_development_stages-report.md`.
