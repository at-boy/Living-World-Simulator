# ADR-0023 — Deterministic work execution

## Status

Accepted for Task 20b.

## Context

Task 20 records immutable work definitions, lifecycle state, and aggregate
reservations. Task 20a permits an NPC to submit only a filtered, actor-bound
proposal that becomes one validated `WorkManager` mutation. Neither task
selects labor, charges inputs, advances progress, or applies a domain effect.

Execution crosses several authoritative managers. It must remain deterministic
across save/resume, charge consumables exactly once, retain tool locks while
work is active, and roll back a failed work phase without granting either the
LLM or an execution system direct authority over goals or settlement stages.

## Decision

### Phase and transaction boundary

`WorkExecutionSystem` is an engine-owned deterministic system registered after
all ordinary systems and before consequences, needs, and goals:

```text
ordinary systems
  -> work execution
  -> consequences
  -> need assessment
  -> goal evaluation
  -> tick increment
```

It deep-copies the post-ordinary-system `WorldState`, composes the existing
managers against that shadow state, executes the complete work phase there,
and replaces the live state's fields only after the phase succeeds. Expected
domain conditions become authoritative work transitions; unexpected
exceptions discard the shadow state and leave the live work phase unchanged.

The scheduler does not provide tick-wide rollback. Effects from ordinary
systems earlier in the tick are outside this Task 20b transaction.

### Stable lifecycle and labor

Work is considered in descending priority, then ascending creation tick, then
ascending work ID, using `WorkManager.all()`.

- Proposed work becomes ready when every prerequisite is completed. If a
  prerequisite is cancelled or failed, the dependent work fails.
- Ready work receives the lowest sorted eligible entity IDs not already locked
  by earlier work in the same phase.
- An eligible laborer is a live NPC inside the settlement and not reserved by
  another work order. An NPC with no schedule is eligible. An NPC with a
  nonempty schedule is eligible only while `active_activity == "working"`.
- Assignment always binds exactly `labor_required` laborers. Zero-labor work
  uses an empty assignment and advances autonomously.
- Assigned work activates and may progress in the same tick. Active work gains
  `max(1, labor_required)` progress per tick, capped at remaining progress.
- Reaching or passing the exclusive `deadline_tick` before completion fails
  the work before that tick's assignment or progress.
- Temporary loss of labor, tools, or uncharged consumables blocks work and
  releases its reservation. Recovery occurs only when the complete preflight
  can succeed; it readies, reassigns, and may reactivate in that tick.
- Cancellation remains an explicit `WorkManager` operation. The execution
  system does not invent automatic cancellation policy.

Blocking releases labor and tool locks, matching ADR-0021. “Tools remain
reserved” means throughout an active reservation, not while work is blocked.
If tool stock later undercollateralizes multiple active locks, stable work
order determines which locks retain stock; later work blocks. Initial readiness
emits `work_order_ready`; a blocked-to-ready transition instead emits exactly
one `work_order_recovered` event with the ordinary previous/current-status
payload.

### Charge-once and progress evidence

`WorkState.inputs_charged_tick` is authoritative persisted evidence that the
work's consumable requirements were deducted. On first activation, the shadow
transaction removes every required consumable from the settlement and records
`work_inputs_charged` before activation. The marker remains through blockage,
recovery, and terminal history. Reassignment never locks or charges those
consumables again. Tools are never deducted and remain aggregate locks until
the reservation is released.

`work_inputs_charged` uses the work ID as subject and contains exactly
`reservation_id` plus the sorted `resources` requirement payload. It is also
recorded with an empty resource tuple for input-free work, making first
activation explicit. Schema-9 or directly managed active work without a marker
is charged before its next progress mutation.

SQLite schema 10 persists the marker. Schema versions 1–9 load it as `None`;
an active schema-9 work order is therefore treated as not yet charged.

Each progress mutation keeps the existing exact progress event and also emits
one `work_progress_threshold_reached` event when it first crosses each of 25,
50, and 75 percent. Crossings are derived from persisted previous and current
progress, so no threshold marker is persisted. Completion is the 100-percent
event.

The threshold event uses the work ID as subject and contains exactly
`threshold_percent`, `previous_progress`, `current_progress`, and
`required_progress`.

### Domain effects

Only fully progressed active work applies an effect. The effect and
`WorkManager.complete()` occur in the same shadow transaction.

- `GATHER_WATER` and `PRODUCE_FOOD` add exactly the target quantity to the
  settlement through `ResourceSystem`. Their effect event is attached to the
  settlement so later goal evidence can cite it. `work_resource_produced`
  contains exactly `work_id`, `category`, `resource`, and `quantity`.
- `BUILD_SHELTER` and `BUILD_STORAGE` create exactly the target count through
  `EntityManager`, set `is_constructed=True`, create an `owns` relationship
  from the settlement, and place each new capability at a deterministic point
  derived from the work location. A point location is reused with its parent;
  a bounds location uses `x + (width - 1) // 2, y + (height - 1) // 2` and the
  bounds entity as parent. Names are `<Definition key title> <ordinal>` in
  ordinal creation order. Each `work_capability_constructed` event is attached
  to the created entity and contains exactly `work_id`, `settlement_id`,
  `definition_key`, `ordinal`, and `location_id`.
- `MAINTAIN_CAPABILITY` calls a new atomic `ConsequenceManager.restore()`
  operation for exactly `recovery_per_paid_tick`, capped at
  `maximum_condition`. `capability_condition_restored` uses the policy ID as
  subject and contains exactly `capability_id`, `previous_condition`,
  `current_condition`, and actual bounded `amount`. A destroyed/zero-condition
  target is permanently invalid and fails the work.
- `ESTABLISH_EXTERNAL_TRADE_CONNECTION` transitions a `KNOWN` or
  `UNAVAILABLE` external reference to `CONTACTABLE` through
  `ExternalWorldReferenceManager`. A reference already made contactable by an
  earlier authoritative action needs no duplicate contact event; the work may
  still complete. `UNKNOWN` is not a valid executable connection target.

Work execution never creates an external dispatch. Dispatches remain a later
validated exchange operation.

### Authority and information boundary

Domain managers remain the mutation owners; `WorkExecutionSystem` owns only
selection, ordering, and phase behavior. Events remain frozen records.
Execution never mutates goal/objective status or settlement stage state.

Task 20b creates no NPC-facing pathway. Work IDs, exact requirements,
reservations, charge state, progress, ticks, failure/blockage reasons, domain
effects, and events remain engine-only. Task 20a offers remain ephemeral and
LLM output remains an untrusted proposal.

## Consequences

Save/resume can distinguish uncharged from charged active or recovered work,
and completed work cannot repeat its effect. Schema 10 is required. New
capabilities use deliberately minimal deterministic construction semantics;
future richer blueprints or geometry require a separately authorized task.
