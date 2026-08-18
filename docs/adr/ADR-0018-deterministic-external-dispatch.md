# ADR-0018 — Deterministic External Dispatch

## Status

Accepted for Task 17a implementation.

## Context

The founding settlement needs durable exchanges with Task 17's deliberately
partial off-map anchors. Cognition may propose a qualitative offered exchange,
but cannot select hidden policy, destination IDs, timing, success, or inventory
mutation.

## Decision

Frozen dispatch records use `pending`, `in_transit`, `arrived`, `rejected`, and
`lost` states. A dispatch manager alone validates an existing live source,
contactable anchor, directional goods policy, positive quantity, per-dispatch
capacity, and local resources. Creation atomically reserves outbound goods and
the deterministic monetary cost. Rejection before departure restores both;
loss consumes reservations; successful inbound arrival adds the requested
good. Every successful lifecycle transition records one immutable event.
Dispatch records are durable history, including terminal records. Entity
removal is rejected while any dispatch names that entity as its source; Task
17a provides no history deletion or cascade, so referential integrity cannot be
silently broken through direct `EntityManager` composition.

The scheduler departs pending records in lexical dispatch-ID order. Once the
anchor delay has elapsed, it derives a stable fraction from SHA-256 over the
persisted scenario seed, anchor ID, and dispatch ID and compares it with the
anchor reliability. Terminal records are never processed again. This makes
save/resume and replay independent of process-random hash state.

An action handler maps an engine-authored qualitative target label to a frozen
`DispatchOffer`. Model arguments are forbidden. The actor ID arrives separately
from the gateway, while anchor ID, direction, good, quantity, cost, delay,
reliability, and outcome remain engine-owned.

SQLite schema version 5 persists dispatches; versions 1–4 load an empty
collection. Privileged inspection exposes detached exact records. The separate
NPC perception contains only anchor name and fixed qualitative lifecycle prose
and is not automatically injected into `NPCContext`.

## Consequences

Task 17a does not simulate an off-map place, generic work, goals, UI, route
geometry, or model-selected outcomes. Later work may use safe perceptions and
dispatch evidence without weakening the gateway or partial-world boundary.
