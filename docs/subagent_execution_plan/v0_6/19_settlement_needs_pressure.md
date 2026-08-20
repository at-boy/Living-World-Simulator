# 19 — Settlement needs and resource pressure

## Status and dependencies

Authorized after reviewed Tasks 18a and 15d. Execute on
`task/19-settlement-needs`.
Task 19a depends on its reviewed merge.

## Task description

Add configured food, water, shelter, and storage needs for settlements and
households. Frozen definitions describe thresholds and assessment windows;
managed state records hold current qualitative level, deficit/surplus, and
satisfaction history derived deterministically from authoritative resources,
population, housing, and capacity.

## Contract and boundary

- Managers own definitions/state and a system assesses needs in stable order.
- Provide typed need kinds and levels, immutable transition events, SQLite
  migration, deterministic detached inspection, and filtered qualitative NPC
  perceptions. Hide exact engine thresholds/quantities unless translated by an
  authorized perception.
- Validate owner/type/threshold/window configuration, missing capability,
  zero population, destroyed owners, idempotence, legacy saves, and detachment.
- Cover sustained-need completion/blockage, stable-level pressure progress that
  changes goal evidence, and a subsequent unchanged evaluation that does not.
- Update engine/state/repository/API, tests/example, ADR/docs, changelog,
  journal, backlog, and report. Do not consume resources, add maintenance,
  select actions, create work, or implement stage progression.
- Run `make`, `make examples`, and `git diff --check`.

## Binding domain model and arithmetic

- Add frozen, slotted records with these exact fields:
  `NeedDefinition(id, owner_id, kind, requirement_per_person,
  secure_maximum, strained_maximum, assessment_window_ticks)`,
  `NeedAssessment(tick, level, available, required, balance, pressure)`,
  `NeedState(need_id, current, history)`, and
  `NPCNeedInterpretation(label, description)`. `current` starts as `None` and
  `history` as an empty tuple. Assessment numeric fields and pressure are all
  `None` only when level is unavailable; otherwise quantities are integers and
  pressure is a finite float in `[0, 1]`. Every assessment, including an
  unavailable one, occurs exactly once in `history`; nonempty history requires
  `current == history[-1]`, and empty history requires `current is None`.
  History has at most the definition's window length and strictly increasing,
  unique, nonfuture ticks. Typed `NeedKind` values are `food`,
  `water`, `shelter`, and `storage`, while `NeedLevel` values are `unavailable`,
  `critical`, `strained`, `secure`, and `surplus`.
- A definition ID must match `need_[A-Za-z0-9][A-Za-z0-9_-]*` and be unique.
  The definition also has a live `owner_id`,
  unique `(owner_id, kind)`, positive integer `requirement_per_person`, finite
  pressure thresholds `0 <= secure_maximum < strained_maximum <= 1`, and a
  positive integer `assessment_window_ticks`. Reject booleans as numbers.
- Population is the owner's nonnegative integer `population` attribute. A
  missing population produces an unavailable assessment; a present malformed
  value fails loudly. Zero population has required quantity zero and pressure
  zero without division.
- Food and water availability read the corresponding nonnegative integer from
  the owner's `resources` mapping. A missing attribute is an empty mapping; a
  present non-dictionary fails loudly; an absent selected resource is zero; a
  present selected value must be a nonnegative integer. Shelter sums
  nonnegative `housing_allocated`; storage sums nonnegative
  `storage_capacity` across the live owner and live entities connected by a
  direct active `owns` relationship. Missing shelter/storage attributes
  contribute zero; malformed authoritative values fail loudly. Ownership is
  never recursive.
- `required = population * requirement_per_person`, `balance = available -
  required`, and `pressure = 0` when required is zero or availability meets
  requirement, otherwise `(required - available) / required`. A positive
  balance is `surplus`; otherwise pressure at or below `secure_maximum` is
  `secure`, at or below `strained_maximum` is `strained`, and higher pressure
  is `critical`.
- One assessment may exist per need per tick. Repeating an identical assessment
  is idempotent; a conflicting second assessment at the same tick is rejected
  before mutation. `NeedManager.record_assessment` accepts only an assessment
  whose tick equals current `WorldState.tick`; any past or future assessment is
  rejected. Retain only the latest `assessment_window_ticks` entries in
  ascending tick order and persist the current assessment plus that history.

## Manager, events, and scheduler

- `NeedManager` alone creates definitions/states and records assessments. It
  validates both new and loaded records, provides deterministic ID ordering and
  owner/kind queries, and makes creation/assessment plus their events atomic.
- Creation emits `need_created`. The first available assessment and every real
  qualitative-level transition emit exactly one `need_level_changed` event
  with detached previous/current level and authoritative assessment values.
  The first unavailable assessment updates current/history without a level
  event. After any assessment exists, every level change, including to or from
  unavailable, emits one event; unchanged levels never emit one. A failed event
  or later failure in one assessment pass rolls back all need-state and newly
  appended event changes from that pass.
- `NeedAssessmentSystem` visits definitions lexically by need ID. It runs after
  ordinary registered domain/cognition systems and before goal evaluation.
  Later registered systems remain before needs, and goal evaluation remains
  last, so Task 19a can add consumption before assessment without reordering
  this contract.
- Prevent entity removal while any need definition names it as owner. Destroyed
  owners or malformed loaded definitions/states fail validation; no cascade or
  silent need deletion is permitted.

## Task 18a integration

- Implement the concrete `SustainedNeedCriterion` evaluator behind Task 18a's
  existing evaluator protocol; do not special-case needs inside the generic
  goal evaluation system.
- Register needs assessment before goal evaluation in engine scheduler order so
  goals read current authoritative need state from the same tick.
- Keep the criterion result/evidence privileged and normalized. The separate
  NPC need perception remains qualitative and contains no exact thresholds,
  deficit/surplus quantities, windows, internal IDs, or goal evidence.
- Replace only the registered unavailable sustained-need evaluator. Resolve the
  unique owner/kind state, require `duration_ticks` consecutive assessments
  ending at the current engine tick, and return unavailable when the definition
  is absent, the window is too short, history is incomplete/nonconsecutive, or
  an assessment is unavailable. Otherwise satisfy only when every retained
  pressure in the requested duration is `<= criterion.maximum`; any higher
  pressure is unsatisfied. The evaluator reads the final `duration_ticks`
  history entries. Task 19 does not narrow Task 18 validation: a finite
  nonnegative maximum greater than 1 remains valid for schema-v6 compatibility
  and necessarily passes once sufficient available history exists. Source IDs
  include only events with this need ID as subject and kind `need_created` or
  `need_level_changed`, returned unique and lexically sorted.
- Available evaluator results use deterministic normalized privileged prose
  containing the need kind, requested duration, criterion maximum, and ordered
  pressure values from the evaluated duration. Unavailable results use stable,
  reason-specific prose. Do not include current tick merely to force evidence
  churn. A materially changed pressure sequence therefore appends Task 18a
  progress evidence even when the qualitative need level and source-event
  provenance are unchanged; an identical sequence/provenance remains
  idempotent.

## Persistence, inspection, and NPC projection

- Advance SQLite snapshots to schema version 7. Versions 1–6 load empty need
  collections; schema 7 round-trips definitions, current state, and bounded
  history and rejects duplicates, invalid references, malformed enums/numbers,
  future/out-of-order history, or definition/state mismatch.
- Loaded validation enforces mapping-key/embedded-ID and definition/state
  correspondence, the exact current/history invariant, history length no
  greater than the definition window, strictly increasing unique nonfuture
  ticks, all-or-none unavailable numeric fields, `balance == available -
  required`, the binding pressure formula, and a level matching the definition
  thresholds. Historical availability is not recomputed from current entities.
- Add `GET /world/needs`, a `need_count` world-summary field, and deterministic
  detached privileged DTOs ordered by need ID. Each record is exactly
  `{"definition": <NeedDefinition snapshot>, "state": <NeedState snapshot>}`;
  enum values use their lowercase strings and records/tuples become detached
  JSON objects/arrays. Inspection may expose exact thresholds, quantities,
  pressure, history, owner IDs, and need IDs.
- `NeedManager.npc_interpretation(s)` returns only a public kind label and fixed
  qualitative prose. Labels are exactly `Food`, `Water`, `Shelter`, and
  `Storage`; descriptions are exactly `This need cannot yet be assessed.`,
  `This need is critically unmet.`, `This need is under strain.`, `This need is
  currently met.`, and `This need has more provision than currently required.`
  for unavailable, critical, strained, secure, and surplus respectively. The
  record has no ID, owner ID, numeric value, window, history, exact level field,
  or goal evidence. Public labels/prose reject internal-form IDs. Strengthen the
  final NPC information boundary so every persisted need ID and authoritative
  need threshold/assessment number is rejected from any stored prose before
  entering `NPCContext`.
- Task 19 does not automatically grant an NPC knowledge of every owner need;
  callers must deliberately select a safe interpretation and record or offer it
  through an authorized later workflow. Spatial/location prose, if ever
  composed by a caller, must use Task 15d's qualitative projection rather than
  IDs or coordinates.

## Allowed-file boundary

- `src/living_world/needs/`
- `src/living_world/goals/evaluation.py` and
  `src/living_world/goals/__init__.py` only for the concrete sustained-need
  evaluator and registry integration
- `src/living_world/state/world_state.py`,
  `src/living_world/simulation/simulation_engine.py`, and
  `src/living_world/managers/entity_manager.py` for owner lifecycle guarding
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/api/inspection.py`, `src/living_world/api/server.py`, and
  `src/living_world/__init__.py`
- `src/living_world/cognition/information_boundary.py` only for need-ID and
  authoritative-need-number rejection
- `tests/test_settlement_needs.py`, `tests/test_goal_evaluation.py`,
  `tests/test_sqlite_repository.py`, `tests/test_inspection_api.py`, plus
  schema-version expectation updates in `tests/test_scenario_run_contract.py`
  and `tests/test_spatial_domain.py`, and focused need-boundary additions in
  `tests/test_npc_context.py`
- `examples/032_settlement_needs.py`
- `CHANGELOG.md`, `docs/adr/ADR-0020-settlement-needs.md`,
  `docs/backlog.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/http_inspection_api.md`, `docs/npc_information_boundary.md`, and
  `docs/project_journal.md`
- This plan, its saved `-prombt.md`, and the Task 19 `-report.md`

No other file may change without first amending this plan and saved prompt.

## Report

Create `docs/subagent_execution_plan/v0_6/19_settlement_needs_pressure-report.md`.
