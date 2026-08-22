# ADR-0022 — Proposal-to-work action gateway

## Status

Accepted for Task 20a.

## Context

Work orders are authoritative engine records, while local-model output is
untrusted and may reason only from filtered NPC information. A proposal cannot
be allowed to invent manager policy or act for a different NPC.

## Decision

The engine may construct frozen, ephemeral creation, priority, and volunteer
offers for one actor. Each offer binds a qualitative public label to complete
hidden policy. `WorkActionHandler` exposes only closed action keys, fixed
descriptions, and boundary-validated labels, and requires empty proposal
arguments.

At construction, validation, and application, the handler rechecks the bound
live NPC's settlement placement, exact active settlement goal/objective
authorization, and side-effect-free `WorkManager` preflights. Acceptance makes
exactly one manager call. Volunteering is self-assignment for one-person work;
multi-person selection and all work execution remain outside this gateway.

Offers are not persisted, inspected, scheduled, or inserted into NPC context.
Manager events and rollback remain the sole authoritative mutation history.

## Consequences

NPC reasoning can influence settlement work without receiving or controlling
IDs, quantities, requirements, priorities, targets, deadlines, laborers, or
outcomes. Callers must reconstruct equivalent offers after loading and must
handle apply-time stale-state failures as authoritative errors.
