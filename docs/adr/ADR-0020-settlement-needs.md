# ADR-0020: Settlement needs are authoritative pressure records

## Status

Accepted for v0.6.

## Decision

Food, water, shelter, and storage needs are immutable typed definitions with
bounded assessment histories owned by `NeedManager`. Assessment is deterministic
from population and authoritative resources or capacities. Ordinary systems run
first, needs assessment runs next, and goal evaluation remains last.

Need pressure describes world state; it does not consume resources, select work,
or authorize NPC action. `SustainedNeedCriterion` reads consecutive current need
history through the criterion evaluator protocol. SQLite schema 7 persists the
domain. Privileged inspection exposes exact records, while NPC projection exposes
only a kind label and fixed qualitative description.

## Consequences

Consumption, maintenance, and storage consequences run atomically after ordinary
systems and before needs assessment. Managers own resource and lifecycle
mutation; terminal capabilities cease contributing capacity. Later NPC action
still uses the cognition proposal and action gateway.
