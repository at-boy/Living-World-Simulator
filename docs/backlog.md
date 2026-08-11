
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

---

## v0.5 – AI Layer

- llama.cpp integration
- Local LLM client
- Decision engine
- Council meetings
- NPC conversations
- NPC Cognition Protocol
- NPC information boundary enforcement
- Retrieval and context assembly for NPC cognition
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
- World inspector UI
- Web administration interface
- Experience validation and confidence weighting
- Long-term memory decay and retrieval ranking

---

## Rule

An item moves from this backlog into active development only when its
scheduled milestone begins or when we both explicitly agree to change
the roadmap.

Until then, this document exists to prevent feature creep while ensuring
good ideas are never lost.
