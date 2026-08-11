
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

## v0.4 – NPC System

- NPC identity, schedules, and occupations are implemented as validated
  JSON-compatible attributes on generic entities.
- Holder-scoped memory, experience, belief, and NPC relationship records are
  immutable and use internal provenance only.
- Knowledge
- Sleep-time cognitive consolidation creates memories, repeated-observation
  experiences, and candidate beliefs without asserting world truth.
- Deterministic holder-scoped retrieval and NPC context assembly now project
  only filtered cognitive interpretations.

---

## v0.5 – AI Layer

- llama.cpp integration
- Local LLM client
- Decision engine and proposal-to-action authority gateway are implemented;
  future domain actions must register explicit simulation-owned handlers.
- Council meetings
- NPC conversations are implemented as bounded, visible recipient observations
  with holder-scoped context and the existing action gateway.
- NPC meeting coordination is implemented as bounded, requester-initiated
  dialogue. The simulation may call eligible participants in a deterministic
  engine-only order without exposing invitation or participant IDs to LLMs.
- NPC Cognition Protocol
- NPC information boundary enforcement
- NPC-only context filtering for perception and memory retrieval
- LLM reasoning without direct world-truth authority

---

## Future Ideas

These are intentionally out of scope for the current milestone.

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
