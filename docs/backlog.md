
# Living World Simulator Backlog

This document is intentionally **not** a specification.

It is a parking lot for ideas that have been agreed upon but are
deliberately postponed until the appropriate milestone.

---

## v0.2 – World Simulation

- Resources
- Regions
- Terrain
- Weather
- Population
- Organizations / Groups

---

## Completed v0.3 – Settlement Simulation

Construction, roads, housing, economy, production, and trade are implemented
through generic entities, relationships, resources, progress, systems, and
events. Further settlement features belong in a future milestone rather than
this completed scope.

---

## Completed v0.4 – NPC System

NPC identity, schedules, occupations, holder-scoped cognitive records,
knowledge, sleep consolidation, deterministic retrieval, and filtered context
assembly are implemented. Further NPC lifecycle and social capabilities remain
future work below.

---

## Completed v0.5 – AI Layer

Loopback-only Ollama and llama.cpp perception and cognition clients, the NPC
Cognition Protocol, filtered retrieval and context enforcement, the decision
engine and action gateway, bounded conversations and meetings, and council
coordination are implemented. The opt-in manual council scenarios demonstrate
a settlement-wide concern, opposing interests, and opinions shaped by isolated
cognitive histories. Local-model output remains an untrusted proposal, and
future domain actions still require explicit simulation-owned handlers.

---

## Future Ideas

Items assigned to v0.6 move into active development only through the approved
isolated v0.6 task sequence. Items assigned to later milestones remain out of
scope.

Every item below is placed in the milestone/track matrix in
`docs/post_v05_settlement_evolution_roadmap.md`. That placement preserves the
idea and its dependencies but does not activate it; a feature still requires
an approved task plan and saved prompt.

- **Autonomous settlement evolution roadmap:** a staged post-v0.5 program for
  reproducible scenarios, engine-owned goals, off-map external references,
  needs and maintenance, work execution, settlement-to-town development,
  population continuity, governance, and regional growth. The agreed direction
  and sequencing are recorded in
  `docs/post_v05_settlement_evolution_roadmap.md`; individual implementation
  v0.6 tasks are now authorized only through their isolated, dependency-ordered
  plans; later-milestone portions remain inactive.
- **Founding mandates and objective graphs:** initial settlers may arrive with
  personal and collective goals such as securing water, building shelter,
  establishing food production, or opening a trade route. Completion,
  progress, and failure are engine-owned and evidence-based, never LLM claims.
- **Off-map external-world references:** a homeland or distant market may exist
  only through a deliberately limited trade, travel, or communication
  interface. It must not imply a secretly complete simulated place and must be
  promotable through an explicit future on-map migration contract.

The versioned scenario/run identity foundation is implemented in Task 16, and
Task 16a adds checkpoint execution plus continuous/bounded operator control.
ADR-0016's canonical local spatial contract and Task 15b's domain, persistence,
and privileged inspection are implemented; pathfinding, terrain, motion, and
regional-scale geography remain deferred.
ADR-0017 and Task 17 implement partial off-map references, deterministic contact
state, schema-v4 persistence, privileged inspection, and a filtered qualitative
interpretation. Dispatch and trade transfer remain assigned to Task 17a.
Task 17a now implements deterministic durable dispatches and safe offered-label
proposals; generic work, objectives, and remote-place simulation remain deferred.
Task 18 now implements durable goal/objective definitions, managed lifecycle
state, persistence, privileged inspection, and filtered NPC interpretations.
Deterministic criterion evaluation and evidence production remain Task 18a.

- Births
- Childhood and apprenticeships
- Old age
- Death and inheritance
- Families and genealogies
- Culture
- Religions
- Migration
- Disease
- Reputation
- Dynamic factions
- Historical figures
- Ruins created by simulation
- Emergent quests
- Dynamic rumours
- Player influence on history
- **Read-only World Inspector UI** backed exclusively by the HTTP inspection
  API, with world/entity detail views, deterministic time-series/statistical
  graphs, event/history views, and relationship graphs. It must remain an
  operator observability client, never a simulation, NPC, or LLM API.
- **Spatial World Inspector visualization** showing areas, settlements,
  buildings, and other placed world elements with click-through inspection.
  This requires a canonical engine-owned spatial layout/placement contract
  before a map renderer is implemented; no UI should infer coordinates from
  arbitrary attributes.
- Web administration interface, separately authorized from the read-only
  inspector and subject to explicit command/action authorization design.
- **Council opposition and political realignment:** NPCs may later organize
  against a council conclusion, form factions, withdraw support, or leave to
  establish a settlement. This requires a dedicated post-v0.5 design for
  collective intent, relationship/reputation consequences, membership changes,
  resources, population movement, construction, and settlement authority; a
  council conversation or declined invitation must never cause these outcomes
  directly.
- **Institution-specific meeting and decision rules:** settlements, towns,
  organizations, and future groups may define their own eligible attendees,
  quorum, notice, voting threshold, delegated authority, and categories of
  rules/tasks that a meeting may approve. This needs an engine-owned governance
  policy model and auditable decision records; it must not be inferred from a
  generic conversation or council transcript.
- **Invitation claims, deception, and contested participation:** an NPC may
  later claim that it invited, excluded, or spoke for another NPC, including
  intentionally deceptive claims. The engine must distinguish an actual
  delivered invitation/attendance record from an NPC-visible claim, observation,
  memory, belief, or rumour about it. This requires a dedicated social
  communication and trust/reputation design; an LLM assertion must never alter
  verified attendance or governance eligibility.
- Experience validation and confidence weighting
- Long-term memory decay and retrieval ranking

---

## Rule

An item moves from this backlog into active development only when its
scheduled milestone begins or when we both explicitly agree to change
the roadmap.

Until then, this document exists to prevent feature creep while ensuring
good ideas are never lost.
# Council implementation note

The v0.5 council coordination layer is bounded and non-authoritative. Rules for
institutional quorums, legitimacy, factions, and secession remain future work.
The temporary unanimous explicit-decline caller fallback must be replaced by
engine-owned, organization-specific governance rules and auditable records.
