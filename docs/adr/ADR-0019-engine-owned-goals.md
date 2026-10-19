# ADR-0019: Engine-owned goals and objective graphs

## Status

Accepted.

## Context

Founding mandates need durable, inspectable structure without allowing an NPC
or LLM to declare authoritative progress.

## Decision

Goals and objectives are frozen definitions with a closed criterion vocabulary.
Separate frozen records hold manager-owned status and evidence. The graph is
validated atomically and persisted as schema v6. Privileged inspection may see
the complete graph; NPC pathways receive only an explicit prose interpretation
whose label and description reject internal ID forms.
Criteria are evaluated by a deterministic final simulation system through a
closed typed evaluator registry. Completion criteria require every result;
any satisfied failure criterion is sufficient. Dependencies and alternatives
are processed in stable graph order, and lifecycle mutation remains exclusive
to the goal manager. Known criteria whose authoritative domains do not yet
exist return unavailable and block progress rather than guessing from runtime
attributes. Materially changed normalized evaluation snapshots append progress
evidence without a lifecycle event; unchanged description and provenance are
idempotent across ticks. Task 18a still does not execute work.

## Consequences

The engine has stable, auditable goal truth and derives lifecycle state from
authoritative world state. Evaluator extensions must register a typed domain
implementation and retain deterministic evidence. Exact criteria, evidence,
status, identifiers, and runtime state remain outside NPC context.

## Task 23 clarification: accumulating need evidence

A short but authoritative need history is pending (unsatisfied), so the unchanged
ACTIVE-only work gateway can continue collecting real provisions. Pending requires
nonempty history shorter than the requested duration, an adequate configured
window, exactly one immutable matching `need_created` event, history covering
every tick from that event through the current tick, current equal to its final
entry and available pressure on every assessment. Empty, stale, gapped, truncated,
unavailable or ambiguously anchored histories remain unavailable. Full-duration
satisfaction still uses the existing consecutive-window rule. This classification
change adds no history/status mutation and preserves dependency/deadline/terminal
precedence. Explicit initial zero capacities distinguish known insufficiency from
absent data; no gateway authorization relaxation is needed.
