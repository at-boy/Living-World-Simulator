# 20a — Proposal-to-work action gateway

## Status and dependency

Authorized after reviewed Task 20. This contract becomes binding when its
planning amendment is committed on `milestone/v0.6`; implement only on
`task/20a-work-action-gateway` created from that commit. Task 20b remains
blocked until Task 20a is independently reviewed, validated, merged, and pushed.

## Objective and non-goals

Translate a closed set of actor-scoped, engine-authored work offers into one
validated `WorkManager` mutation through the existing `NPCActionResolver`.
The LLM chooses only an offered action key and public label. It never supplies
an ID, quantity, priority, requirement, prerequisite, location, laborer, target
policy, deadline, outcome, or manager input.

Task 20a does not persist offers, change schema 9, add a system or scheduler
phase, select a crew, execute or progress work, charge or deduct resources,
apply a domain effect, change a goal/objective, inject work into `NPCContext`,
or change the generic resolver protocol. Task 20b retains automatic work
selection, multi-person labor assignment, charging, progress, and effects.

## Binding offer model and vocabulary

Add frozen, slotted engine-only records in `living_world.work.action`:

- `WorkCreationOffer(label, category, target, settlement_id, objective_id,
  location_id, prerequisite_work_ids=(), labor_required=0, tools=(),
  resources=(), required_progress=1, priority=0, deadline_tick=None)`;
- `WorkPriorityOffer(label, work_id, priority)`;
- `WorkAssignmentOffer(label, work_id)`.

A creation offer's `label` is also the created work's `public_label`. Every
other field is passed unchanged to the corresponding Task 20 manager API.
Offer constructors enforce the same strict scalar/tuple/typed-target rules as
the work records. They do not accept mappings, free-form payloads, aliases, or
callables.

The closed action keys are, in this deterministic order:

1. the six exact `WorkCategory.value` strings in enum declaration order;
2. `prioritize_work`;
3. `volunteer_for_work`.

Their exact fixed descriptions are:

| Key | Description |
| --- | --- |
| `gather_water` | `Propose gathering water for the settlement.` |
| `produce_food` | `Propose producing food for the settlement.` |
| `build_shelter` | `Propose building shelter for the settlement.` |
| `build_storage` | `Propose building storage for the settlement.` |
| `maintain_capability` | `Propose maintaining a settlement capability.` |
| `establish_external_trade_connection` | `Propose establishing an external trade connection.` |
| `prioritize_work` | `Propose changing the priority of one offered work order.` |
| `volunteer_for_work` | `Volunteer for one offered work order.` |

Each creation offer appears only under its exact category key. Priority and
assignment offers appear only under their lifecycle key. The handler exposes
only keys having at least one offer. Target labels within each `ActionOption`
are ordered by `(label.strip().casefold(), label)` and must be unique after
`strip().casefold()` within that key. Ambiguity fails handler construction; it
is never resolved by first match. Labels and fixed action descriptions must
pass both the repository canonical internal-ID matcher and the current
`NPCInformationBoundary` before becoming model-visible.

Construction also rejects two creation offers with the same duplicate identity
defined below, two priority offers for the same work ID, or two assignment
offers for the same work ID. The same work may have one priority and one
assignment offer because the action key keeps those operations distinct.

`ActionRequest.arguments` must be empty. `rationale` remains untrusted
NPC-authored prose and is ignored by validation/application and never recorded
in work events. Request values cannot override any offer field.

## Actor-bound composition and eligibility

`WorkActionHandler(state, definitions, manager, actor_id, creation_offers=(),
priority_offers=(), assignment_offers=())` is constructed for exactly one
engine actor. It provides deterministic `action_options` plus `supports()`,
`validate()`, and `apply()` for the existing resolver protocol. Construction
requires at least one offer and preflights every offer against current state.
Callers compose
`NPCActionResolver(handler.action_options, (handler,))`; no global resolver is
registered on `SimulationEngine`.

Every validation and application rechecks that the supplied resolver
`actor_id` equals the bound actor and that the actor:

- exists and is live;
- has a valid `NPCIdentity`;
- is not a maintenance capability;
- has a live placement within the offered work's settlement containment tree.

This spatial settlement scope is the current minimal proposal authorization;
the repository has no separate canonical settlement-membership/governance
record. Schedule, activity, travel, and availability remain Task 20b. A
handler/resolver built for actor A rejects actor B even when B repeats an exact
offered label. Council proposals remain caller-bound because the existing
council applies a majority proposal with its caller ID; no participant gains
another actor's authority.

## Goal and category authorization

For every operation, recover the one settlement-owned goal that owns the
offer/work objective. At offer construction, validation, and application:

- the goal owner is the same settlement and both goal and objective states are
  exactly `GoalStatus.ACTIVE`;
- the goal's `authorized_action_categories` contains the exact umbrella value
  `settlement_work`;
- the objective's `authorized_action_categories` contains the exact
  `WorkCategory.value`.

Empty tuples authorize nothing. There are no inferred aliases or wildcard
rules. Existing Task 20 history remains valid if a goal later becomes terminal,
but a stale offer cannot create, prioritize, or assign work after either state
ceases to be active.

## Operation semantics

### Creation

Creation uses the exact complete offer and calls `WorkManager.create()` once.
Before mutation it rechecks all Task 20 record, target, settlement, objective,
location, prerequisite, deadline, and canonical-order rules plus:

- a capability target's `definition_key` exists in the supplied authoritative
  `DefinitionManager` registry (definitions remain runtime/scenario vocabulary,
  not snapshot state);
- every requested tool/resource quantity is currently available after all
  unreleased cross-kind work locks are subtracted;
- no nonterminal work has the same `(settlement_id, objective_id, category,
  target, location_id)`.

`PROPOSED`, `READY`, `ASSIGNED`, `ACTIVE`, and `BLOCKED` are nonterminal for
duplicate detection. Label, prerequisites, labor, requirements, progress,
priority, and deadline do not alter identity. Completed/cancelled/failed
history does not block a new offer. The affordability check is admission only:
accepted creation neither reserves nor deducts stock, and Task 20b must still
handle later shortage.

### Priority

A priority offer identifies one existing nonterminal work order and one fixed
nonnegative changed priority. Validation rechecks actor/category authorization
and calls `WorkManager.set_priority()` once on acceptance. The model cannot
choose the number and a no-op or terminal target is rejected.

### Assignment

`volunteer_for_work` means self-assignment only. The offered work must be
`READY` with `labor_required == 1`; application calls
`WorkManager.assign_and_reserve(work_id, (actor_id,))` once. The manager owns
the exact live/spatial labor, global double-booking, and shared-stock checks.
Task 20a never names or selects another laborer and never assigns a multi-person
crew.

## Manager preflight, stale offers, and rollback

Add public side-effect-free `WorkManager` preflight APIs for creation, priority,
and assignment:

```python
def validate_create(
    *,
    category: WorkCategory,
    target: WorkTarget,
    public_label: str,
    settlement_id: str,
    objective_id: str,
    location_id: str,
    prerequisite_work_ids: tuple[str, ...] = (),
    labor_required: int = 0,
    tools: tuple[ToolRequirement, ...] = (),
    resources: tuple[ResourceRequirement, ...] = (),
    required_progress: int = 1,
    priority: int = 0,
    deadline_tick: int | None = None,
    require_available_inputs: bool = False,
    reject_nonterminal_duplicate: bool = False,
) -> None: ...

def validate_set_priority(work_id: str, priority: int) -> None: ...
def validate_assign_and_reserve(
    work_id: str, labor_entity_ids: tuple[str, ...]
) -> None: ...
```

`WorkManager.create()` calls `validate_create()` with both policy flags false,
preserving direct Task 20 semantics. `set_priority()` and
`assign_and_reserve()` call their exact preflight before mutation. The handler
calls creation preflight with both flags true in `validate()` and immediately
before `create()` in `apply()`; it likewise calls the priority/assignment
preflight both before and during application. Candidate ID inspection in a
preflight never advances an allocator.

The resolver is synchronous and inserts no callback between validation and
application. If authoritative state nevertheless changes or a failure is
injected, apply-time preflight/manager failure propagates; it is not converted
into a false accepted or post-validation rejected resolution. WorkManager's
existing atomic rollback remains authoritative over work collections, events,
resources, and allocators. Handler diagnostics, if any, update only after a
successful manager return.

Rejected validation uses one exact safe reason by operation:

- creation: `That work proposal is not currently available.`;
- priority: `That priority proposal is not currently available.`;
- assignment: `That volunteer proposal is not currently available.`.

A request with nonempty arguments uses
`Work proposals cannot set engine policy.`. Accepted application returns,
respectively, `The work proposal was accepted.`,
`The work priority proposal was accepted.`, or
`The volunteer proposal was accepted.`. Rejection records no event, creates no
work/reservation, changes no priority/resource/allocator, and never echoes
engine exception text or hidden identifiers. Only the existing exact manager events are
emitted: `work_order_created`, `work_order_priority_changed`, or
`work_reservation_created` then `work_order_assigned`. Task 20a adds no proposal
or rationale event.

## Persistence, inspection, scheduler, and NPC boundary

Offers and handlers are ephemeral host policy reconstructed after load. No
WorldState collection, SQLite field, schema version, migration, inspection
endpoint, HTTP mutation route, or scheduler registration changes. Accepted
work persists through the existing schema-9 records; reconstructed equivalent
offers after resume produce the same operation and next IDs.

The model-visible projection contains only closed keys, fixed qualitative
descriptions, and validated public labels. Hidden offer fields, manager
objects, state, IDs, quantities, requirements, priorities, deadlines, exact
availability, and validation causes remain engine-only. Task 20a does not add
work interpretations to context, observations, retrieval, conversations,
prompts, or LLM clients. Expand the static ActionOption/ActionRequest
internal-ID matcher to cover all canonical repository record prefixes; final
state-aware validation still uses `NPCInformationBoundary`.

## Required tests and example

Add `tests/test_work_action_gateway.py` and extend relevant existing tests for:

- strict frozen offer records, canonical tuples, safe normalized labels, stable
  eight-key ordering, and all six exact category/target families;
- serialized options containing no hidden IDs or authoritative numbers;
- malformed, unoffered, ambiguous, wrong-key/target, nonempty-argument, and
  canonical-ID-bearing option/request values;
- actor binding plus unknown, destroyed, non-NPC, maintenance-capability,
  unplaced, and foreign-settlement actors;
- inactive/blocked/completed/failed goals/objectives, exact umbrella/category
  authorization, and cross-NPC/council-caller isolation;
- stale/missing targets, locations, prerequisites and deadlines;
- aggregate cross-kind affordability, duplicate identity for every
  nonterminal state, differing identity fields, and terminal-history allowance;
- priority success, no-op, terminal and rollback cases;
- self-assignment success, multi-labor rejection, unavailable/double-booked
  labor and inputs, and exact reservation/assignment event order;
- validation and every rejection leaving work, reservations, events, resources,
  and allocators unchanged; apply-time event failure restoring manager state and
  IDs; exact manager events and fixed safe resolutions;
- schema staying 9, accepted work round-trip, reconstructed post-resume offers
  producing equivalent work/reservation IDs and results, no inspection or
  scheduler change, and no automatic context injection.

Add `examples/035_proposal_work_gateway.py` showing filtered NPC context, safe
actor-bound offers, an untrusted label-only creation proposal, resolver
acceptance, and manager-created proposed work without execution, reservation,
resource deduction, raw state, or LLM call.

## Documentation and allowed-file boundary

Implementation may change only:

- new `src/living_world/work/action.py`;
- `src/living_world/work/manager.py`, `src/living_world/work/__init__.py`, and
  `src/living_world/__init__.py`;
- `src/living_world/cognition/npc_cognition_client.py`;
- new `tests/test_work_action_gateway.py` plus
  `tests/test_work_orders.py`, `tests/test_action_resolution.py`,
  `tests/test_npc_cognition_client.py`, `tests/test_local_llm_cognition_format.py`,
  `tests/test_simulation_engine_actions.py`, `tests/test_council.py`,
  `tests/test_npc_context.py`, `tests/test_npc_information_boundary.py`,
  `tests/test_sqlite_repository.py`, and `tests/test_simulation_scheduler.py`;
- `examples/035_proposal_work_gateway.py`;
- `CHANGELOG.md`, new
  `docs/adr/ADR-0022-proposal-work-action-gateway.md`, `docs/backlog.md`,
  `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/npc_information_boundary.md`, and `docs/project_journal.md`;
- this plan, its saved `-prombt.md`, and the Task 20a report.

Do not modify `WorldState`, persistence implementation/schema, inspection/HTTP
APIs, scheduler implementation, resource/consequence systems, goal evaluation,
conversation/council implementation, prompts, cognition clients, YAML loaders,
or Task 20b domain systems. Any additional file requires a milestone planning
amendment before editing.

## Validation and delivery

Run focused tests during implementation, then current `make`, separate
`make examples`, and `git diff --check`. Create the truthful Task 20a report but
do not commit, push, merge, or change branches. Independent review must cover
this full contract, exact file boundary, trust/NPC boundary, manager preflight
and rollback, tests, docs, example, and report before integration.

## Report

Create `docs/subagent_execution_plan/v0_6/20a_proposal_work_gateway-report.md`.
