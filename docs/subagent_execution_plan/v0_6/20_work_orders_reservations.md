# 20 — Work orders and reservations

## Status and dependencies

Authorized after reviewed Task 19a. This contract becomes binding when its
planning amendment is committed on `milestone/v0.6`; implement only on
`task/20-work-orders` created from that commit. Tasks 20a and 20b remain blocked
until Task 20 is reviewed, validated, merged, and pushed.

## Objective and non-goals

Add durable engine-owned work orders plus one atomic aggregate reservation per
assignment. Task 20 records intent, lifecycle, labor assignment, and locked
tool/consumable quantities. It does not select labor, deduct resources, advance
time automatically, execute domain effects, mutate goals/objectives, add action
handlers, call an LLM, or change scheduler order. Task 20a alone translates
offered proposals; Task 20b alone schedules selection/progress, charges locked
consumables exactly once, retains tools, and applies domain effects.

## Binding domain model

Add a `living_world.work` package with frozen, slotted records:

- `WorkCategory`: `gather_water`, `produce_food`, `build_shelter`,
  `build_storage`, `maintain_capability`,
  `establish_external_trade_connection`.
- `WorkStatus`: `proposed`, `ready`, `assigned`, `active`, `blocked`,
  `completed`, `cancelled`, `failed`.
- `ToolRequirement(tool, quantity)` and
  `ResourceRequirement(resource, quantity)`.
- `ResourceWorkTarget(resource, quantity)`,
  `CapabilityWorkTarget(definition_key, count)`,
  `MaintenanceWorkTarget(policy_id)`, and
  `ExternalConnectionWorkTarget(reference_id)`; their union is `WorkTarget`.
- `WorkDefinition(id, category, target, public_label, settlement_id,
  objective_id, location_id, prerequisite_work_ids, labor_required, tools, resources,
  required_progress, priority, deadline_tick, created_tick)`.
- `WorkState(work_id, status=PROPOSED, progress=0, reservation_id=None,
  status_reason=None, started_tick=None, resolution_tick=None)`.
- `WorkReservation(id, work_id, labor_entity_ids, tools, resources,
  created_tick, released_tick=None, release_status=None)`.
- `NPCWorkInterpretation(label, description)` with no engine ID, exact
  requirement, reservation, progress, priority, deadline, tick, or event data.

Manager-generated IDs are `work_000001` and `work_reservation_000001` with
monotonic six-digit suffixes, skipping existing IDs after load. Public labels,
tool/resource names, IDs, and reasons are nonempty strings. Public labels and
NPC interpretations reject every canonical repository engine-ID pattern.
The shared work-domain matcher explicitly covers `entity`, `relationship`,
`event`, `observation`, `memory`, `belief`, `experience`, `knowledge`,
`npc_relationship`, `placement`, `need`, `goal`, `objective`,
`external_reference`, `external_dispatch`, `dispatch`, `consumption`, `storage`,
`maintenance`, `work`, and `work_reservation` prefixes followed by underscore
and a nonempty canonical suffix.

Every integer rejects booleans. `labor_required` and `priority` are
nonnegative; requirement quantities and `required_progress` are positive;
progress is within `[0, required_progress]`; ticks are nonnegative. A creation
deadline is absent or later than the current tick. Loaded deadlines may be in
the past but cannot predate `created_tick`.

Prerequisite IDs, labor IDs, tools, and resources are stored in lexical order.
Duplicate IDs/names are rejected. Tool and resource names cannot overlap.
Empty requirement tuples and zero labor are valid. A reservation copies the
definition's complete tool/resource tuples exactly; callers cannot choose
different quantities.

Category and target type are exact: gather-water and produce-food use
`ResourceWorkTarget`; build-shelter and build-storage use
`CapabilityWorkTarget`; maintain-capability uses `MaintenanceWorkTarget`; and
establish-external-trade-connection uses `ExternalConnectionWorkTarget`.
Resource/capability quantities are positive. At creation, a maintenance target
names an existing policy whose owner is the settlement, whose matching state
has positive condition, and whose capability is live. Later deterioration to
zero/destruction remains valid durable target history; loaded validation
requires the policy/state/capability references to exist but does not reapply
that creation-only positive/live predicate. External targets name an existing
reference. Capability definition keys are nonempty and remain
scenario-definition references, matching goal capability criteria; snapshot
loading does not invent or serialize definitions. This typed target is the
complete future effect intent: Tasks 20a/20b may not add free-form payloads and
must amend their own plans/schema if later behavior requires more parameters.
Gather-water requires resource `water`; produce-food requires resource `food`.
Tagged target kinds are exactly `resource`, `capability`, `maintenance`, and
`external_connection`.

## References and spatial compatibility

`settlement_id` is a live entity and is the owner of exactly one goal containing
`objective_id`; that goal has `owner_kind == SETTLEMENT` and the same owner ID.
The objective and its state exist. Creation requires the goal/objective to be
nonterminal, but later terminal goal state does not invalidate durable work
history and work never changes goal state directly.

`location_id` is a live placed entity equal to the settlement or a descendant
of it through `Placement.containing_entity_id`. Every prerequisite exists,
belongs to the same settlement, differs from the new work, and predates it by
`(created_tick, id) < (WorldState.tick, allocated_candidate_work_id)`; this
makes forward references and cycles impossible at creation. Loaded validation
enforces the same strict ordering and also rejects cycles. Work becomes ready
only after every prerequisite is completed. Cancelled, failed, blocked, or
otherwise incomplete prerequisites merely make `mark_ready()` reject; Task 20
does not automatically block, cancel, or fail a dependent order.

An assigned laborer is a distinct live entity with a valid `NPCIdentity`, is
not a maintenance capability, and is placed at the settlement or anywhere in
its containment tree. Exact co-location, travel, schedules, and activity
availability remain Task 20b. One laborer may appear in only one active
reservation globally.

Tools and consumables are aggregate integer quantities in the settlement's
authoritative `resources` mapping. For each name:

```text
available = current nonnegative settlement quantity
            - tool and resource quantities in every other unreleased
              reservation with that same name
```

The requested definition quantity must be available. Tool and consumable locks
have distinct future semantics but draw from one physical aggregate pool, so a
name locked in either kind reduces availability for both kinds across all work.
Task 20 never calls `ResourceSystem.remove()` and never changes resource
quantities. Task 20b later retains tool quantities and charges consumables
exactly once.

These locks prevent allocation to another work order; they do not change the
authority of existing consequence or resource operations, which do not consult
the work ledger. Later authoritative depletion may therefore leave an existing
lock above current stock. That is a valid blocked-work input, not malformed
persistence: no new assignment may use the negative remainder, and Task 20b
must deterministically block/release or otherwise handle the shortage before
execution. Loaded validation enforces cross-work lock arithmetic and exact
records but does not require later current stock to cover every retained lock.

To preserve live/spatial invariants, work creation/assignment rejects
maintenance capabilities in required live roles. Maintenance-policy creation
rejects a target used as a nonterminal work location or in an unreleased labor
reservation. Entity destruction and spatial replace/unplace/remove reject a
nonterminal work location or unreleased laborer. Physical entity removal
rejects every settlement, location, or labor entity named anywhere in durable
work/reservation history; records are never cascade-deleted.

The settlement must remain live for all work history. A nonterminal work
location and every laborer in an unreleased reservation must remain live,
placed, and compatible. After work is terminal, its location may be destroyed,
replaced, or reparented; loaded validation then requires only that the historical
entity still exists. After a reservation is released, its laborers may be
destroyed or moved; loaded validation requires only existence and does not
reapply current eligibility. This is why removal remains forbidden while
destruction/spatial change becomes legal for released history.

## Manager authority and lifecycle

`WorkManager` is the sole writer of work definitions, states, and reservations.
Systems and handlers may only call its APIs. Each operation validates all input
before mutation and snapshots every touched definition, state, reservation,
both manager ID allocators, and the event-ID set. Any failure—including a
successful release event followed by a failed work event—restores all three
collections and allocators and removes every event from that operation. Work ID
and reservation ID allocation is not consumed by a failed operation; existing
EventManager allocator-gap behavior remains unchanged.

Exact APIs and transitions:

- `create(...)`: constructs the next definition plus proposed state atomically.
- `mark_ready(work_id)`: `PROPOSED|BLOCKED -> READY`, requires completed
  prerequisites, clears `status_reason`, and retains progress/first start tick.
- `assign_and_reserve(work_id, labor_entity_ids)`: `READY -> ASSIGNED`; requires
  exactly `labor_required` sorted unique eligible laborers, atomically creates
  one reservation from definition requirements, and stores its ID.
- `activate(work_id)`: `ASSIGNED -> ACTIVE`; requires its reservation still
  unreleased and sets `started_tick` only on first activation.
- `record_progress(work_id, amount)`: `ACTIVE -> ACTIVE`; positive amount may
  not exceed remaining progress. This is a manager boundary reserved for Task
  20b and performs no domain effect or auto-completion.
- `set_priority(work_id, priority)`: replaces the immutable definition for any
  nonterminal work.
- `block(work_id, reason)`: `READY|ASSIGNED|ACTIVE -> BLOCKED`.
- `complete(work_id)`: `ACTIVE -> COMPLETED` only at exact required progress.
- `cancel(work_id, reason)` and `fail(work_id, reason)`: any nonterminal status
  to the respective terminal status.

`BLOCKED`, `COMPLETED`, `CANCELLED`, and `FAILED` release an unreleased
reservation atomically before the work transition and clear `reservation_id`.
Blocked recovery returns to ready and requires fresh assignment. Cancellation
and failure reasons and block reasons are nonempty; `status_reason` exists only
for blocked/cancelled/failed state. `resolution_tick` exists only for terminal
state. Terminal work has no outgoing transition. Completion changes only work
state and releases locks; it performs no construction, production, maintenance,
dispatch, resource, need, goal, objective, stage, or run mutation.

Every lifecycle mutation stamps `WorldState.tick`; a supplied/noncurrent tick
is never accepted. `created_tick <= started_tick/resolution_tick <= world.tick`
when those fields exist, and start cannot follow resolution. Exact state matrix:

- proposed: zero progress and all optional state fields absent;
- ready: no reservation/reason/resolution; start may be absent or retained from
  earlier activation, and progress must be zero when start is absent;
- assigned: one unreleased reservation, no reason/resolution; start may be
  absent or retained after blocked recovery;
- active: one unreleased reservation, nonfuture start, no reason/resolution;
- blocked: no reservation, nonempty reason, no resolution; start is optional;
- completed: no reservation/reason, nonfuture start and resolution, and exact
  required progress;
- cancelled/failed: no reservation, nonempty reason, nonfuture resolution, and
  optional nonfuture start.

Noncompleted progress may equal required progress only while active or blocked;
other noncompleted statuses remain below it. Deadlines are metadata after
creation: Task 20 readiness, assignment, activation, and progress do not expire
or fail work. Task 20b alone may define deterministic deadline failure.

`release_status` is `WorkStatus | None`. A reservation is unreleased only when
both `released_tick` and `release_status` are absent. A released reservation has
both fields, `release_status` is exactly blocked/completed/cancelled/failed, and
`created_tick <= released_tick <= world.tick`. Each work may have multiple
released historical reservations after block/reassignment but at most one
unreleased reservation. Exactly assigned/active state references that one
unreleased reservation; all other states have no `reservation_id`. Even work
with zero labor and empty inputs creates one reservation on assignment, so the
assignment and release contracts never have a special case.

## Exact immutable events

All nested values are detached. Attribute mappings contain no additional keys.
Enums serialize as `.value`; optional deadline is present with `None`; target is
a tagged mapping: resource `{kind, resource, quantity}`, capability
`{kind, definition_key, count}`, maintenance `{kind, policy_id}`, or external
connection `{kind, reference_id}`. Tools/resources are ordered tuples of
`{tool, quantity}` / `{resource, quantity}` mappings; ID tuples remain tuples.

| Kind / subject | Exact attributes |
| --- | --- |
| `work_order_created` / work ID | `category`, `target`, `public_label`, `settlement_id`, `objective_id`, `location_id`, `prerequisite_work_ids`, `labor_required`, `tools`, `resources`, `required_progress`, `priority`, `deadline_tick` |
| `work_order_ready` / work ID | `previous_status`, `current_status` |
| `work_reservation_created` / reservation ID | `work_id`, `labor_entity_ids`, `tools`, `resources` |
| `work_order_assigned` / work ID | `previous_status`, `current_status`, `reservation_id` |
| `work_order_activated` / work ID | `previous_status`, `current_status` |
| `work_order_progressed` / work ID | `previous_progress`, `current_progress` |
| `work_order_priority_changed` / work ID | `previous_priority`, `current_priority` |
| `work_reservation_released` / reservation ID | `work_id`, `release_status` |
| `work_order_blocked` / work ID | `previous_status`, `current_status`, `reason` |
| `work_order_completed` / work ID | `previous_status`, `current_status` |
| `work_order_cancelled` / work ID | `previous_status`, `current_status`, `reason` |
| `work_order_failed` / work ID | `previous_status`, `current_status`, `reason` |

Creation emits its one event. Assignment emits reservation-created then
work-assigned. A releasing transition emits reservation-released first, then
the applicable work event. Event status/category/kind values are lowercase enum
values, including `release_status`. No-op transitions are not accepted.

## Ordering, persistence, and inspection

`get()` is by ID. `all()` orders by descending priority, then creation tick,
then work ID; this is the binding future Task 20b selection order.
`reservations_for()` orders by reservation ID; `active_reservations()` orders by
reservation ID. Task 20 adds no system and scheduler registration/order remains
byte-for-byte behaviorally unchanged.

Advance SQLite snapshots to schema 9 with exact-key serializers for every
record and nested requirement. Lists are ID-sorted; semantic tuples use the
canonical order above. Versions 1–8 ignore stray work fields, load all three
collections empty, and write forward as schema 9. Schema 9 requires
`work_definitions`, `work_states`, and `work_reservations` lists. Persistence
does not redefine or repair arbitrary in-memory state before save.

After entities, placements, goals, and work collections load,
`WorkManager.validate_loaded_state()` enforces exact record types and key/ID
correspondence; all model/reference/order/graph invariants; status/progress/tick
field combinations; reservation ownership and current-state correspondence;
exact target/requirement records; no cross-kind active overbooking; all three
history/reference rules above; and released/terminal/blocked consistency. Here
`no active overbooking` means no duplicate labor plus internally consistent
nonnegative aggregate lock arithmetic; because historical stock is not
persisted separately, current resource coverage is deliberately not re-proved
on load.
Manager allocators resume above existing canonical numeric suffixes. Malformed
data raises `RepositoryLoadError` without partial state.
Save/reload followed by the same manager operation must produce identical work,
reservations, resources, events, and IDs.

Add privileged detached `WorldInspector.work_orders()` and GET-only
`/world/work-orders` returning an ID-sorted tuple of:

```text
{"definition": ..., "state": ..., "reservations": [...]}
```

Nested reservations are ID-sorted. Add `work_order_count` and
`work_reservation_count` to the world summary. Inspection exposes exact engine
truth and is never reused as NPC context.

## NPC boundary

`WorkManager.npc_interpretation(work_id)` returns the public label and exactly
one fixed description: proposed `This work is being considered.`; ready `This
work is ready to begin.`; assigned `People and supplies have been set aside for
this work.`; active `This work is underway.`; blocked `This work cannot
currently proceed.`; completed `This work is complete.`; cancelled `This work
will not proceed.`; failed `This work could not be completed.`

The final NPC information boundary enumerates work/reservation IDs and every
authoritative work number. Task 20 does not inject interpretations into
`NPCContext`, observations, cognition, retrieval, conversations, prompts, or
LLM calls. A later authorized perception workflow must establish legitimate
holder knowledge.

## Required tests and example

Add `tests/test_work_orders.py` for all record validation, canonical ordering,
category/target pairings, references, prerequisites, lifecycle transitions,
the exact per-status/tick matrix, illegal/no-op transitions,
priority/progress, labor eligibility/exclusivity, aggregate tool/resource
overbooking without deduction, exact events/order, deterministic IDs/queries,
event-failure rollback including release-then-transition failure, multiple
historical reservations, zero-input reservation, every release path, metadata-
only deadlines, historical destruction/movement rules, and fixed interpretation.

Extend entity, spatial, consequence, goal, SQLite, inspection, NPC context,
NPC information-boundary, scenario/spatial schema, and scheduler tests for:
bidirectional live-role/removal guards; objective ownership and terminal-history
behavior; schema-9 exact round-trip; versions 1–8 defaults/write-forward;
missing/extra keys for all records/nested requirements; malformed references,
graphs, status/ticks/reservations/overbooking; lifecycle save/resume equivalence;
assignment followed by consequence depletion and valid save/reload despite an
undercollateralized retained lock;
exact detached inspection/counts/GET-only; ID/number filtering and no automatic
context injection; and unchanged scheduler order.

Add `examples/034_work_orders.py` showing creation, prerequisite readiness,
atomic assignment/reservation without resource deduction, activation/progress,
blocking/release/reassignment/completion, privileged inspection, and separately
selected NPC-safe prose. It performs no domain effect or LLM call.

## Documentation and allowed-file boundary

Implementation may change only:

- new `src/living_world/work/`;
- `src/living_world/state/world_state.py`,
  `src/living_world/simulation/simulation_engine.py`, and
  `src/living_world/__init__.py`;
- `src/living_world/managers/entity_manager.py`,
  `src/living_world/spatial/manager.py`, and
  `src/living_world/needs/consequence.py`;
- `src/living_world/repositories/sqlite_repository.py`;
- `src/living_world/api/inspection.py` and `src/living_world/api/server.py`;
- `src/living_world/cognition/information_boundary.py`;
- `tests/test_work_orders.py`, `tests/test_entity_manager.py`,
  `tests/test_spatial_domain.py`, `tests/test_consumption_maintenance.py`,
  `tests/test_goals.py`, `tests/test_sqlite_repository.py`,
  `tests/test_inspection_api.py`, `tests/test_npc_context.py`,
  `tests/test_npc_information_boundary.py`, `tests/test_scenario_run_contract.py`,
  `tests/test_simulation_scheduler.py`;
- `examples/034_work_orders.py`;
- `CHANGELOG.md`, new `docs/adr/ADR-0021-work-orders-and-reservations.md`,
  `docs/backlog.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/http_inspection_api.md`, `docs/npc_information_boundary.md`, and
  `docs/project_journal.md`;
- this plan, its saved `-prombt.md`, and the Task 20 report.

No action-resolution, cognition-client, scheduler implementation,
`ResourceSystem`, goal-evaluation, consequence arithmetic, YAML, or domain-effect
file may change. Any additional file requires a milestone planning amendment.

## Validation and delivery

Run focused tests during implementation, then current `make`, separate
`make examples`, and `git diff --check`. The worker creates the truthful report
but does not commit, push, merge, or change branches. Independent review must
cover the full binding contract, file boundary, persistence/migration,
information boundary, tests, docs, example, and report before integration.
