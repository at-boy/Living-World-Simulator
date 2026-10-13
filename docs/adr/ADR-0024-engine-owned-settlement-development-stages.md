# ADR-0024 — Engine-owned settlement development stages

## Status

Accepted for Task 21.

## Context

The v0.6 founding loop now has engine-owned goals, sustained settlement needs,
maintenance consequences, authoritative work proposals, and deterministic work
execution. It still lacks one durable engine decision that distinguishes a
founding camp from an established settlement and later a town.

Stage promotion must not be an LLM judgment, mutable entity label, population
threshold, or second independent interpretation of raw goal domains. It must
reuse evidence already produced by the authoritative objective graph, remain
deterministic across save/resume, and preserve the NPC information boundary.

## Decision

### Per-settlement program and managed state

Each explicitly configured settlement owns one immutable stage program and one
manager-owned state. The program contains exactly the canonical ordered stages
`founding_camp`, `settlement`, and `town`. Requirements are configurable, but
the v0.6 names and order are not. There are no reusable templates or bindings.

Configuration creates the initial founding-camp state. Only
`SettlementStageManager` may replace state, and configured settlement entities
cannot be removed or destroyed while the records refer to them.

### Objective-backed typed requirements

Every promotion requirement has a closed semantic kind and references one
objective owned by a settlement goal for the same settlement. Stage evaluation
considers the requirement satisfied only when that objective is authoritatively
completed. It reuses normalized objective evidence and never reevaluates raw
needs, resources, maintenance state, external references, capabilities, or
population.

Water, food, shelter, and storage roles require matching sustained-need
criteria. External-connection and capability roles reuse existing goal
criteria. Task 21 adds population-minimum and maintained-capability criteria to
the closed goal evaluator vocabulary so those domains also produce ordinary
objective evidence before they can contribute to promotion.

Population-only promotion configuration is invalid. Missing, contradictory,
cross-owner, mistyped, or unsustainable objective mappings are rejected when a
program is configured or loaded.

### Monotonic deterministic evaluation

The stage system executes after goal evaluation:

```text
ordinary systems
  -> work execution
  -> consequences
  -> need assessment
  -> goal evaluation
  -> settlement-stage evaluation
  -> tick increment
```

Programs are evaluated in settlement-ID order. A settlement may move only to
the immediately adjacent stage and at most once per tick. Repeated evaluation
at the same tick is idempotent. Town is terminal; decline and demotion remain
future policy.

A stage transition emits exactly one immutable event with the previous and
current stages plus ordered requirement kinds, objective IDs, and sorted source
event IDs. The complete stage phase rolls back its state and new events if an
unexpected evaluation failure occurs. Earlier tick phases are not rolled back.

Because goals evaluate before stages, a goal criterion referring to a stage
observes a promotion on the following tick. This avoids a circular same-phase
fixpoint.

### Persistence and inspection

SQLite schema 11 persists programs, managed state, and the new goal criteria.
Schemas 1 through 10 load empty stage collections and write forward. Migration
does not invent stage configuration because legacy snapshots contain no
objective-role mapping.

Privileged inspection exposes exact detached program and state through a
GET-only endpoint. Save/resume must preserve the same transition sequence as an
uninterrupted run.

### NPC and LLM boundary

Exact stage programs, objective IDs, criteria, thresholds, enum state, ticks,
evidence, and transition events remain engine-only. The only NPC-safe stage
projection is explicitly selected fixed qualitative prose. Task 21 does not
automatically inject that prose into observations, cognition, retrieval,
`NPCContext`, or prompts.

LLM output has no stage action or mutation gateway. It remains an untrusted
proposal and cannot configure, complete, or promote settlement stage state.

## Consequences

Settlement development becomes durable, inspectable, deterministic, and
grounded in the existing objective authority path. Stage semantics do not
diverge from goal evidence, and future scenario work can configure the
canonical founders lifecycle without granting cognition new authority.

The direct binding duplicates configuration if later worlds contain many
identical settlements. Reusable templates, decline policy, scenario-YAML
binding, and automatic NPC perception require separate future tasks.
