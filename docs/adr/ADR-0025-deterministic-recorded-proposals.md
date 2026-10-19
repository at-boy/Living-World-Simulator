# ADR-0025 — Deterministic recorded proposals

## Status

Accepted for authorized Task 22, before implementation.

## Context

The reviewed v0.6 engine has authoritative needs, goals, work, dispatches and
settlement stages, but no unattended deterministic proposal driver. Model
responses must remain untrusted proposals, and reproducibility must cover
proposal progress as well as durable world effects.

## Decision

A strict version1 tape supplies public actor labels and ordinary immutable
speech/action decisions bound to the scenario configuration fingerprint. Tape
identity is canonical-content hashed. A stateless per-entry cognition adapter
receives only filtered NPCContext, offered ActionOptions and the expected
public entity-name identity. It receives no world, internal ID, header, cursor,
inspection or action-handler object.

ScenarioRuntimeManager retains initial public-label-to-entity bindings. Replay
manager owns immutable binding plus cursor progress in WorldState, persisted
with domain effects in one schema12 SQLite snapshot. Legacy schemas1–11 do not
invent labels or replay state. Mapped entities are retained as history; pending
actors must remain live, while consumed actors may later be destroyed.

One entry is attempted each tick, in explicit tape order, after ordinary
systems and before work, consequences, needs, goals and stages. Offer providers
use a read-only inspection interface and engine-authored handler factories.
Existing DecisionEngine and action resolver/handlers preserve their validation
and manager authority. Accepted, rejected and speech-only decisions consume;
malformed or unexpected failures do not. Exhausted runtime becomes idle.

A failed scheduler tick makes the engine refuse further advance or persistence
until rebuilt from its last checkpoint. This process-local guard preserves the
original failure; it does not disable inspection or direct manager operations.
Direct manager retry semantics and repository-save failures remain separate.
No general whole-world rollback framework is introduced.

Runner preparation binds/rechecks tape and reinstalls ephemeral runtime on
resume. Finalization occurs before a stopping tick is saved and rejects unused
entries for final runs. Explicit checkpoint-only bounds and operator stops keep
remaining entries resumable. Tape identity/cursor and domain state recover
together from the last durable checkpoint. The binding task plan specifies exact
ordering, typed records, guards and error diagnostics.

## Consequences

Automated runs are reproducible without a live model and cannot bypass domain
authority or hidden-information filtering. Replay progression is inspectable
without becoming NPC knowledge. Recorded tapes establish deterministic driver
behavior, not autonomous live-model planning quality.

Tick-level failure refusal is a deliberate compatibility change for callers
that previously reused partially failed engine instances. Public labels must
be retained with their initial entity records. Replay setup is unavailable on
legacy populated runs without durable bindings. Canonical setup, terminal
outcomes, live providers and administration remain separate tasks.
