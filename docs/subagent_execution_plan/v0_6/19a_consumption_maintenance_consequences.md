# 19a — Consumption, maintenance, and consequences

## Status and dependency

Authorized after reviewed Task 19. This contract becomes binding when committed
on `milestone/v0.6`; execute implementation only on
`task/19a-consumption-maintenance` created from that amended milestone head.
Task 20 remains blocked until this task is reviewed, validated, merged, and
pushed.

## Objective and non-goals

Add deterministic per-tick food/water consumption, capacity-bounded storage
overflow and configured spoilage, and resource-funded upkeep with bounded
capability deterioration/recovery. Consequences change authoritative resources,
typed consequence state, and capability lifecycle through managers. Task 19
needs assessment then reads the resulting same-tick world state, and Task 18a
goal evaluation reads the resulting need history.

This task does not add work selection or execution, settlement stages, scenario
YAML configuration, UI, run-success/failure decisions, proportional capability
effectiveness, repair of terminally destroyed capabilities, recursive
ownership, new cognition authority, LLM-selected consequences, or automatic
NPC-context injection. It never calls `GoalManager`, directly records goal
evidence, or directly completes/fails a goal, objective, run, or stage.

## Binding domain model

Add frozen, slotted records under `living_world.needs` with these exact fields:

- `ConsumptionPolicy(id, owner_id, food_per_person_per_tick,
  water_per_person_per_tick)`.
- `ConsumptionState(policy_id, last_processed_tick=None,
  food_shortage=False, water_shortage=False)`.
- `StorageResourceRule(resource, spoilage_per_tick)`.
- `StoragePolicy(id, owner_id, resources)` where `resources` is a tuple of
  `StorageResourceRule` values and tuple order is the authoritative overflow
  and spoilage processing order.
- `StorageState(policy_id, last_processed_tick=None, overflowing=False,
  spoiling=False)`.
- `MaintenanceRequirement(resource, amount)`.
- `MaintenancePolicy(id, owner_id, capability_id, label, upkeep,
  initial_condition, maximum_condition, deterioration_per_unpaid_tick,
  recovery_per_paid_tick)` where `upkeep` is a tuple of
  `MaintenanceRequirement` values.
- `MaintenanceState(policy_id, condition, last_processed_tick=None,
  upkeep_shortage=False)`.
- `NPCConsequenceInterpretation(label, description)` containing no engine ID,
  quantity, rate, capacity, condition, tick, threshold, policy, or event data.

Canonical policy IDs match respectively
`consumption_[A-Za-z0-9][A-Za-z0-9_-]*`,
`storage_[A-Za-z0-9][A-Za-z0-9_-]*`, and
`maintenance_[A-Za-z0-9][A-Za-z0-9_-]*`. IDs are unique within their
collections. There is at most one consumption policy and one storage policy per
owner and one maintenance policy per capability.

All IDs, owner/capability IDs, resource names, and labels are nonempty strings;
resource names within one tuple are unique. Resource-rule and upkeep tuple
order is preserved and authoritative. Every integer field rejects booleans.
Per-person rates and spoilage rates are nonnegative. At least one per-person
rate is positive. Upkeep is nonempty and every amount is positive.
`maximum_condition`, deterioration, and recovery are positive integers, and
`1 <= initial_condition <= maximum_condition`.

Consumption and storage owners must be live entities. A maintenance owner must
be live; its capability must be a different live entity, be directly targeted
by an active `owns` relationship from that owner at policy creation, and have
`is_constructed is True`. The policy retains authority if that ownership
relationship later changes, but both entity records remain referentially
protected. A maintenance capability cannot occupy any existing role whose
contract requires the entity to remain live: owner of a consumption, storage,
or maintenance policy; owner of a `NeedDefinition` or `GoalDefinition`; or
source of an `ExternalDispatch`. Maintenance-policy creation/load rejects a
capability already occupying any such role. Later consequence-policy, need,
goal, and external-dispatch creation rejects an owner/source named as a
maintenance capability. `EntityManager.mark_destroyed()` defensively rejects
the same conflicting references before mutation. These bidirectional
creation/load/mutation invariants ensure that terminal destruction cannot make
the subsequent need/goal phase fail or make a dispatch unschedulable or
unloadable. Policy configuration is through `ConsequenceManager` APIs and the
Python scenario/example surface only; Task 19a does not extend YAML.

## Authority, managers, and lifecycle

Add `ConsequenceManager` as the sole owner of consequence policy/state
creation, validation, application, safe interpretation, and loaded-state
validation. Creation installs the policy and matching initial state atomically:
consumption/storage state use their defaults, while maintenance state starts at
the policy's `initial_condition`.

`ConsequenceManager` uses the existing `ResourceSystem` only as the validated
resource-operation dependency, `EntityManager` for authoritative entity
attribute/lifecycle changes, and `EventManager` for immutable history. Systems
must not directly edit resources, consequence collections, condition, or
`destroyed_tick` during forward execution.

Add an idempotent `EntityManager.mark_destroyed(entity_id, tick)` mutation
boundary. It accepts a known entity and requires a non-boolean, nonnegative
`tick` equal to the current `WorldState.tick`; any other tick is rejected. It
sets `destroyed_tick` when the entity is live, returns without change when it
was already destroyed at that same tick, and rejects a different existing
destruction tick. It does not emit an event itself. Extend physical
entity removal guards so an entity cannot be removed while any consequence
policy names it as owner or maintenance capability. Do not cascade-delete
policies, state, relationships, placement, or history.

Every consequence event uses the policy ID as `Event.subject_id`; policy ID is
not duplicated in attributes. Exact event attributes are binding:

| Kind | Exact attributes |
| --- | --- |
| `consumption_policy_created` | `owner_id`, `food_per_person_per_tick`, `water_per_person_per_tick` |
| `storage_policy_created` | `owner_id`, `resources`, where `resources` is an ordered tuple of `{resource, spoilage_per_tick}` mappings |
| `maintenance_policy_created` | `owner_id`, `capability_id`, `label`, `upkeep` as an ordered tuple of `{resource, amount}` mappings, `initial_condition`, `maximum_condition`, `deterioration_per_unpaid_tick`, `recovery_per_paid_tick` |
| `consumption_applied` | `owner_id`, `food`, `water`, where each resource mapping has exactly `required`, `consumed`, `shortage` |
| `consumption_shortage_started` | `owner_id`, `resource`, `shortage` |
| `consumption_shortage_recovered` | `owner_id`, `resource` |
| `capability_upkeep_applied` | `owner_id`, `capability_id`, `requirements` as an ordered tuple of `{resource, amount}` mappings, `paid` |
| `maintenance_shortage_started` | `owner_id`, `capability_id` |
| `maintenance_shortage_recovered` | `owner_id`, `capability_id` |
| `capability_deteriorated` | `owner_id`, `capability_id`, `previous_condition`, `current_condition` |
| `capability_recovered` | `owner_id`, `capability_id`, `previous_condition`, `current_condition` |
| `capability_destroyed` | `owner_id`, `capability_id` |
| `storage_spoilage_applied` | `owner_id`, `capacity`, `total_before`, `overflow`, `resources`, where `resources` is an ordered tuple of `{resource, overflow, routine}` mappings |

Creation emits exactly the one applicable `*_policy_created` event. Event
attribute mappings contain no additional keys.

A creation failure, including a partially recorded event, restores policy,
state, and newly appended event history.

## Deterministic consequence phase and scheduler

Add one `ConsequenceSystem`. `SimulationEngine` owns it as a special phase,
parallel to its existing need and goal phases. `_rebuild_scheduler()` must
produce this exact order:

```text
all built-in ordinary systems in their existing order
then every later register_system() system in registration order
then ConsequenceSystem
then NeedAssessmentSystem
then GoalEvaluationSystem
```

Consequences therefore observe same-tick dispatch, production, trade, housing,
and any later registered ordinary system. Needs observe same-tick consequences;
goals observe same-tick needs. Registering a late ordinary system must not move
it after consequences.

Within one consequence phase, process exactly:

1. consumption policies by lexical policy ID;
2. maintenance policies by lexical policy ID;
3. storage policies by lexical policy ID.

The manager validates every policy, state, cross-reference, and authoritative
input needed by the complete phase before the first mutation. It takes
deep-detached snapshots of every affected entity's complete attribute mapping
and destruction tick, plus all consequence state collections and the pre-phase
event-ID set. Restoration replaces only those affected entity values and does
not replace unrelated entities or collections. Any later arithmetic, mutation,
or event failure restores the complete consequence phase and removes every
event appended by it. Earlier ordinary systems are outside this rollback
boundary. Event-manager allocator internals are not part of authoritative
rollback, which matches existing manager behavior.

Every policy, including terminal maintenance, participates in phase
bookkeeping and may be applied at most once at the current `WorldState.tick`.
A phase is complete for same-tick no-op detection only when every policy state
has `last_processed_tick == WorldState.tick`; all states then remain unchanged.
At the start of a new application, every state must have an absent or earlier
`last_processed_tick`. Historical ticks need not match, so a newly configured
policy with an unprocessed state can join older policies on the next phase. A
mix of states processed at the current tick and states not processed at the
current tick is a partial/conflicting phase and fails before mutation. Each
successful application advances every policy state's `last_processed_tick` to
the world tick. A stored tick must be absent or a nonnegative tick no later
than the world tick.

## Consumption arithmetic and events

Population is the owner's required nonnegative integer `population` attribute.
Unlike Task 19 assessment, a missing population is invalid for an enabled
consumption policy and fails loudly. Zero population is valid.

For food and then water, in that fixed order:

```text
required = population * configured_per_person_per_tick
available = current nonnegative integer owner resource quantity, default zero
consumed = min(available, required)
shortage = required - consumed
remaining = available - consumed
```

Remove exactly `consumed`; partial supply is consumed and resources never
become negative. A resource has shortage state exactly when `shortage > 0`.
After both resources are applied, record one `consumption_applied` event with
the exact attributes above. Then, in food/water order, emit
`consumption_shortage_started` when a resource changes from no shortage to
shortage, or `consumption_shortage_recovered` when it changes from shortage to
no shortage. First processing counts as no prior shortage; continued shortage
or continued supply does not repeat a transition event. This fixes consumption
emission order as applied, food transition if any, then water transition if any.

## Maintenance arithmetic, deterioration, and events

For each live, nonterminal capability, validate every configured upkeep
resource against the maintenance policy owner's authoritative `resources`
mapping through `ResourceSystem`; the capability's own inventory is untouched.
Upkeep is all-or-nothing: it is paid only if the owner can currently afford
every requirement; paid upkeep removes each full requirement from the owner in
configured tuple order, while unpaid upkeep removes nothing.

```text
if paid:
    current = min(maximum_condition,
                  previous + recovery_per_paid_tick)
else:
    current = max(0, previous - deterioration_per_unpaid_tick)
```

Record `capability_upkeep_applied` every nonterminal processed tick with the
exact attributes above. Then emit
`maintenance_shortage_started` or `maintenance_shortage_recovered` only when
the upkeep-shortage boolean changes. Emit `capability_deteriorated` or
`capability_recovered` only for a real condition change. The exact order is
upkeep-applied, shortage transition if any, condition-change event if any, and
destroyed event if condition first reaches zero.

When condition first reaches zero, call `EntityManager.mark_destroyed()` and
then emit exactly one `capability_destroyed` event. The destroyed capability
immediately ceases contributing to Task 19
shelter/storage assessment because those queries already exclude destroyed
owned entities. Condition changes above zero do not proportionally scale
capacity, construction, production, or housing. A terminal capability has
condition zero and has `destroyed_tick` set to the tick on which destruction
first occurred. On every later successful consequence tick it performs no
resource, condition, or destruction mutation and emits no event, but its
`last_processed_tick` still advances for complete-phase bookkeeping. Its
invariant is `destroyed_tick <= last_processed_tick <= WorldState.tick`, with
equality between destruction and processing ticks when destruction first
occurs. An already destroyed target is valid only with this consistent
terminal state; any other destroyed/state combination fails loudly.

## Storage capacity, overflow, and spoilage

Do not introduce a second storage-capacity truth. Derive current capacity
exactly as Task 19 does: sum nonnegative integer `storage_capacity` across the
live owner and live directly owned targets of active, already-created `owns`
relationships, exclude self-ownership duplication, ignore destroyed targets,
and do not recurse. Refactor a shared helper inside the allowed need domain if
needed so assessment and consequences cannot drift.

Only resources named by the storage policy participate. For every rule, read a
nonnegative integer owner-held resource quantity, defaulting to zero. First:

```text
total_before = sum(configured resource quantities)
overflow = max(0, total_before - capacity)
```

Discard exactly `overflow` by walking rules in configured tuple order and
removing `min(current_resource, overflow_remaining)` until no overflow remains.
Tuple order is therefore an explicit lowest-retention-first overflow policy.
Then walk the same rules in the same order and remove routine spoilage of
`min(remaining_resource, rule.spoilage_per_tick)` for each resource.

Update `StorageState.overflowing` to whether overflow was positive and
`spoiling` to whether any overflow or routine spoilage was removed. When any
amount is removed, emit one `storage_spoilage_applied` event with the exact
attributes above. Emit no storage event when nothing is removed. Task
19's storage need remains capacity-per-population; this task does not redefine
it as an occupancy need.

## Persistence and loaded validation

Advance SQLite snapshots to schema version 8 and support versions 1 through 8.
Versions 1–7 load all six consequence collections as empty even if stray newer
payload fields are present; the next save writes schema 8. Schema 8 serializes
every policy/state collection as an ID-sorted list with exact-field
serializers. Every schema-8 policy, state, nested resource-rule, and nested
maintenance-requirement mapping must have exact key-set equality: both missing
and additional keys are rejected. Nested resource/upkeep tuples preserve their
configured order.

After all entities, relationships, needs, goals, and consequence collections
are reconstructed, `ConsequenceManager.validate_loaded_state()` enforces:

- exact policy/state key correspondence and mapping-key/embedded-ID equality;
- uniqueness constraints and exact field/type/range validation;
- live consumption/storage/maintenance owners, existing maintenance targets,
  and the complete live-required-role exclusion for every maintenance
  capability across consequences, needs, goals, and external dispatches;
- maintenance creation invariants that remain applicable without requiring a
  now-historical ownership relationship;
- state ticks absent or nonfuture; if any policy is processed at the loaded
  world tick, all policies must be processed at that tick, while differing
  earlier historical ticks are permitted;
- unprocessed consumption state has both shortage flags false; unprocessed
  storage state has both `overflowing` and `spoiling` false; unprocessed
  maintenance state has initial condition, false upkeep shortage, and a live
  target;
- maintenance condition bounds and terminal equivalence: condition zero iff
  the target is destroyed by a nonfuture tick, with
  `destroyed_tick <= last_processed_tick <= world.tick`; a live positive target
  is required for nonterminal state;
- no destroyed nonterminal capability and no live zero-condition capability.

Malformed schema-8 data raises `RepositoryLoadError` without returning partial
state. Persistence does not redefine policy arithmetic and must not claim to
validate an arbitrary in-memory world before save. Save/resume from a completed
tick must produce the same subsequent authoritative resources, consequence
state, need history, goal evidence, events, and tick as uninterrupted execution.

## Privileged inspection and NPC boundary

Add `WorldInspector.consequences()` and read-only
`GET /world/consequences`, returning this exact detached shape:

```text
{
  "consumption": [{"policy": ..., "state": ...}, ...],
  "storage": [{"policy": ..., "state": ...}, ...],
  "maintenance": [{"policy": ..., "state": ...}, ...]
}
```

Each list is ordered by policy ID. Add `consumption_policy_count`,
`storage_policy_count`, and `maintenance_policy_count` to the world summary.
Inspection is privileged and may expose all exact IDs, rates, quantities,
condition, configuration, state, and event linkage. Returned mappings/lists are
detached and the HTTP surface remains GET-only.

`ConsequenceManager.npc_interpretation(policy_id)` returns only
`NPCConsequenceInterpretation`:

- consumption label `Food and water`; description is one of `Food and water
  use has not yet been assessed.`, `Food and water use is currently supplied.`,
  `Food use cannot currently be fully supplied.`, `Water use cannot currently
  be fully supplied.`, or `Food and water use cannot currently be fully
  supplied.`;
- storage label `Stored supplies`; description is one of `Storage conditions
  have not yet been assessed.`, `Stored supplies are currently stable.`,
  `Stored supplies exceed available capacity.`, or `Some stored supplies are
  being lost.`; overflow takes precedence over other spoilage;
- maintenance uses the policy's public `label`; description is one of `Upkeep
  has not yet been assessed.`, `This capability is sound and maintained.`,
  `This capability is recovering but remains worn.`, `This capability lacks
  required upkeep and is deteriorating.`, or `This capability is no longer
  usable.`.

The final information boundary must enumerate all new policy/state IDs and all
authoritative consequence numbers so stored prose containing them fails before
entering `NPCContext`. Policy labels and interpretation prose reject canonical
internal IDs. Task 19a does not automatically add consequence interpretations
to any NPC context, observation, memory, belief, experience, retrieval result,
conversation, prompt, or LLM request. A later authorized perception workflow
must establish legitimate holder knowledge before doing so.

## Required tests and example

Add `tests/test_consumption_maintenance.py` covering:

- frozen/slotted record validation, canonical IDs, uniqueness, references,
  bidirectional live-required owner/source role exclusion, tuple ordering, bool
  rejection, and manager creation rollback;
- full, partial, zero-population, missing/malformed-population, and malformed
  stock consumption with exact event subject/attribute/transition behavior;
- all-or-nothing upkeep, deterministic recipe order, shortage/recovery,
  owner-funded resource removal without capability-inventory mutation, bounded
  deterioration/recovery, terminal destruction once, later terminal tick
  advancement without events, consistent already-destroyed state, and removal
  guards;
- capacity aggregation, self-ownership, destroyed targets, below/equal/above
  capacity, multiple ordered resources, zero/positive routine spoilage, and
  exact removal/event arithmetic;
- policy insertion-order independence, newly configured policy joining older
  historical state, same-tick no-op, conflicting current-tick partial state
  rejection, prevalidation, event failure, deep nested-resource restoration,
  and whole-phase rollback without unrelated replacement;
- ordinary/late systems before consequences, exact internal phase order,
  consequences before needs, and needs before goals;
- uninterrupted versus schema-8 save/resume equivalence.

Extend:

- `tests/test_settlement_needs.py` for same-tick reduced food/water, destroyed
  capacity exclusion, and the four-phase scheduler contract;
- `tests/test_goal_evaluation.py` for consequence-to-need-to-sustained-evidence
  flow without direct goal-manager calls;
- `tests/test_goals.py` and `tests/test_external_dispatch.py` for rejecting a
  maintenance capability as a later goal owner or dispatch source and for
  rejecting maintenance creation over pre-existing live-required roles;
- `tests/test_sqlite_repository.py` for schema-8 round-trip, versions 1–7 empty
  defaults/write-forward, stray legacy fields, missing and additional keys in
  exact records, malformed references, unprocessed-state defaults, terminal
  tick invariants, and unsupported schema 9;
- `tests/test_inspection_api.py` for exact shape/order/counts/detachment,
  GET-only access, and no NPC-context expansion;
- `tests/test_npc_context.py` and `tests/test_npc_information_boundary.py` for
  new IDs/numbers failing closed and safe selected prose passing;
- `tests/test_entity_manager.py` for manager-owned current-tick destruction,
  bool/negative/noncurrent-tick rejection, and consequence reference removal
  guards;
- schema-version assertions in `tests/test_scenario_run_contract.py` and
  `tests/test_spatial_domain.py`.

Add `examples/033_consumption_maintenance.py`. It must run at least two ticks
and demonstrate exact operator-visible resources/policies/state/events, the
subsequent need assessment, terminal or recovering maintenance behavior,
privileged detached inspection, and separately selected qualitative NPC-safe
interpretations. It must not invoke an LLM or auto-inject interpretations into
NPC context.

## Documentation and allowed-file boundary

Update the changelog, journal, backlog, core model, glossary, HTTP inspection
documentation, NPC information-boundary documentation, and ADR-0020. Create the
truthful Task 19a report. Do not claim a current test count until validation is
run.

Implementation may change only:

- `src/living_world/needs/`;
- `src/living_world/state/world_state.py`;
- `src/living_world/simulation/simulation_engine.py`;
- `src/living_world/managers/entity_manager.py`;
- `src/living_world/goals/manager.py`;
- `src/living_world/external_world/dispatch_manager.py`;
- `src/living_world/repositories/sqlite_repository.py`;
- `src/living_world/api/inspection.py` and `src/living_world/api/server.py`;
- `src/living_world/cognition/information_boundary.py`;
- `src/living_world/__init__.py`;
- `tests/test_consumption_maintenance.py`, `tests/test_settlement_needs.py`,
  `tests/test_goal_evaluation.py`, `tests/test_goals.py`,
  `tests/test_external_dispatch.py`, `tests/test_sqlite_repository.py`,
  `tests/test_inspection_api.py`, `tests/test_npc_context.py`,
  `tests/test_npc_information_boundary.py`, `tests/test_entity_manager.py`,
  `tests/test_scenario_run_contract.py`, and `tests/test_spatial_domain.py`;
- `examples/033_consumption_maintenance.py`;
- `CHANGELOG.md`, `docs/adr/ADR-0020-settlement-needs.md`, `docs/backlog.md`,
  `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/http_inspection_api.md`, `docs/npc_information_boundary.md`, and
  `docs/project_journal.md`;
- this plan, its saved `-prombt.md`, and
  `docs/subagent_execution_plan/v0_6/19a_consumption_maintenance_consequences-report.md`.

The existing `ResourceSystem` API is sufficient and must not change. No other
file may change without first amending this plan and saved prompt together on
the milestone branch.

## Validation and delivery

Run focused Task 19a tests during implementation. Before approval run current
`make`, separate `make examples`, and `git diff --check`. The implementation
worker creates the truthful report but does not commit, push, merge, or change
branches. Independent review must cover contract/file-boundary compliance,
manager/system authority, phase ordering, arithmetic, event immutability,
rollback, schema migration/load validation, resume equivalence, inspection
detachment, NPC filtering, tests, docs, and report accuracy.
