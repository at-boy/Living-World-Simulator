
# Living World Simulator Backlog

Task 20 work orders and reservations, Task 20a's actor-bound proposal gateway,
and Task 20b deterministic execution are implemented.

Task 21's objective-backed settlement stages are independently reviewed,
validated, merged, and pushed to milestone/v0.6. Task 22 recorded proposal
replay is independently reviewed, validated and integrated; its strict
runtime/cursor contract and ADR-0025 remain authoritative. Task15
operator inspector is independently reviewed and integrated. Task15c spatial
view is independently reviewed, validated and integrated. Task23 canonical
composition is implemented on its isolated task branch with focused canonical
acceptance at success10, stall5 and failure13. Independent implementation review
and authoritative root validation remain pending. Legacy replay enablement on
populated saves without label bindings remains unsupported. Reusable
stage templates, decline/demotion, general scenario-YAML binding beyond the fixed
Task23 preset, and automatic NPC perception of stages remain deliberately deferred.

Task 19 settlement needs and pressure is complete for v0.6. Task 19a
consumption, storage, and maintenance consequences are reviewed and integrated
into milestone/v0.6.

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
Task 15d implements an engine-owned qualitative spatial and direct-road
perception translation layer and closes the stored-observation coordinate-leak
gap without adding navigation or visibility simulation.
ADR-0017 and Task 17 implement partial off-map references, deterministic contact
state, schema-v4 persistence, privileged inspection, and a filtered qualitative
interpretation. Dispatch and trade transfer remain assigned to Task 17a.
Task 17a now implements deterministic durable dispatches and safe offered-label
proposals; generic work, objectives, and remote-place simulation remain deferred.
Task 18 now implements durable goal/objective definitions, managed lifecycle
state, persistence, privileged inspection, and filtered NPC interpretations.
Task 18a implements deterministic criterion evaluation and evidence production
for resources, constructed capabilities, capacity, external connections, and,
after Task 19, sustained need pressure. Settlement-stage evaluation remains
Task 21 implementation is active under its decision-complete isolated plan.

Task 19 now implements authoritative food, water, shelter, and storage needs,
bounded assessment history, sustained-need objective evidence, schema-v7
persistence, privileged inspection, and qualitative NPC-safe interpretation.
Consumption, storage/spoilage, upkeep, and deterioration consequences remain
separately scoped to Task 19a; work selection remains Task 20 and later.

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
- **Inspector visualization follow-up:** Task 15 supplies packaged read-only
  world/entity/lifecycle details and event history. Statistical/time-series and
  relationship graphs remain future explicitly authorized operator work; they
  must never become a simulation, NPC, or LLM API.
- **Spatial inspector follow-up:** Task15c implements the canonical placement
  map and entity inspection; independent review and root acceptance are pending.
  Editing, inferred roads, and statistical overlays remain separately authorized
  work. Spatial views must consume engine-owned placements without inferring
  coordinates from arbitrary attributes.
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

Release audit checkpoint October17: Task23 is integrated58b6ba7. Task24 final
readiness is blocked by two P1 auditfindings, recorded in committed orchestrator
handoff auditreport. Correctexisting NPCgoalboundary/reservationID defects in
bounded isolatedtask before resuming uncommitted24metadata. These are release
blockers, not deferredfuturefeatures; full audit coverage/gates remainpending.

Task24a isolated existing-defect correction begins from7d75b20; Task24metadata
checkpoint preserved. Both audit findings and remaining wholeauditcoverage still
block release readiness until reviewed current validation.
