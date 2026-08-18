# Post-v0.5 settlement-evolution roadmap

## Destination

The target is an operator-started simulation in which a small founding group
can establish a settlement, respond to changing conditions, grow into a town
and later a larger community, and accumulate inspectable history without an
operator scripting every tick.

This is not one feature. It requires a runnable scenario, durable collective
objectives, needs and work execution, settlement development criteria,
population continuity, governance, and observability. The milestones below
originated as proposed post-v0.5 work. The user has now authorized planning and
execution of v0.6 only; later milestones remain unauthorized.

## Architectural model

The engine remains authoritative over goals and their consequences:

```text
scenario seed
  -> authoritative settlement needs and founding mandate
  -> engine-owned goals and objective criteria
  -> NPC-visible interpretations and proposals
  -> validated work/action assignments
  -> systems consume time and resources
  -> events and world-state changes
  -> engine evaluates objective progress and settlement stage
  -> NPCs perceive and remember the results
```

An LLM may propose priorities, negotiate, explain a preference, or request an
allowed action. It does not mark goals complete, create resources, promote a
settlement to a town, or decide that an off-map trade connection succeeded.

## Goals and objectives

A goal should be a durable engine record rather than an NPC prompt string. The
initial contract should distinguish:

- the goal owner: expedition, settlement, organization, household, or NPC;
- a human-readable purpose and NPC-visible interpretation;
- engine-owned completion and failure criteria;
- objective dependencies and optional alternatives;
- current status, progress evidence, priority, and relevant deadlines;
- authorized action categories that may advance it;
- events recording activation, progress, blockage, completion, or failure.

Example founding mandate:

```text
Establish Oakford
  - secure a dependable water source
  - provide minimum shelter for the founding households
  - establish renewable food production
  - create usable storage
  - connect to the homeland trade network
```

The objective graph allows the simulation to recognize partial progress and
blocked paths. “Build a town” must not be a single LLM judgment or a checklist
that mutates itself.

NPCs need not agree with a collective goal. A settler can misunderstand it,
oppose its priority, pursue a personal goal, or propose a different means. The
engine-owned record and an NPC's belief about it are separate.

## Off-map places and external connections

Some scenario concepts are important but do not justify simulating another
region in detail. An `ExternalWorldReference`-style contract can represent a
homeland, distant market, crown, migrating population source, or trade network
as an engine-owned off-map anchor.

An off-map anchor should contain only the authoritative interface required by
the active simulation, such as:

- a stable internal identity and an operator-facing name;
- qualitative relationship or role, such as homeland or regional market;
- allowed imports, exports, travel delay, capacity, reliability, and costs;
- explicit discovery/contact state;
- event-producing rules for dispatch, delay, arrival, rejection, or loss.

It is not a hidden fully simulated settlement. It has no invented population,
buildings, politics, or resource ledger unless a later task explicitly models
those things. It can later be promoted into an on-map region through a defined
migration path rather than silently changing meaning.

NPCs receive only perceived or communicated descriptions of an external place
and its outcomes. They do not receive its engine configuration, exact hidden
probabilities, internal ID, or future result.

## Proposed milestone sequence

### v0.6 — Autonomous founding settlement vertical slice

The first milestone should make one settlement scenario runnable and
inspectable end to end.

1. **Scenario and run contract**
   Define reproducible scenario seeds, simulation configuration, bounded and
   continuous run modes, save/resume behavior, deterministic seeds where
   randomness is introduced, and operator stop conditions.
2. **External-world references**
   Add deliberately partial off-map anchors and validated travel/trade message
   lifecycles without pretending to simulate the remote world.
3. **Engine-owned goals and objective graphs**
   Add durable personal and collective goals, dependencies, evidence-based
   progress evaluation, failure/blockage, events, persistence, and inspection.
4. **Needs, maintenance, and resource pressure**
   Model food, water, shelter, storage, upkeep, and other minimum pressures so
   settlement choices have consequences over time.
5. **Work planning and domain action handlers**
   Convert authorized priorities into engine-owned tasks that reserve labor,
   time, locations, tools, and resources and execute through validated
   simulation systems. NPC/LLM output remains a proposal.
6. **Settlement development stages**
   Define explicit, configurable criteria for founding camp, settlement, and
   town stages. Stage changes are derived from durable capabilities and emit
   auditable events; population alone is insufficient.
7. **Founders scenario and unattended-run acceptance test**
   Ship a canonical scenario whose settlers must establish shelter, food,
   storage, and a homeland trade route. Demonstrate deterministic bounded runs,
   save/resume, meaningful failure, goal progress, stage progression, and HTTP
   inspection.

The v0.6 acceptance target is: start one command, let the canonical scenario
run for a bounded period without operator intervention, inspect why it
succeeded, stalled, or failed, and replay the same configured seed.

### v0.7 — Population continuity and social development

After the founding loop works, add households and families, births, childhood,
apprenticeship, aging, death, inheritance, migration, skill development,
reputation, and durable social roles. Cognitive maturation in this milestone
also covers experience validation/confidence weighting and long-term memory
decay and retrieval ranking. These systems create labor and care constraints
and allow the settlement to outlive its founders.

Town growth must remain possible without being guaranteed. Shortages, unsafe
conditions, political conflict, demographic imbalance, or loss of external
connections can cause stagnation, decline, abandonment, or recovery.

### v0.8 — Governance, institutions, and collective conflict

Add engine-owned institutions, offices, jurisdiction, decision categories,
quorum and voting policies, auditable decisions, collective intent, factions,
political realignment, law/rule effects, and authorized public works. Council
dialogue can inform these systems but cannot substitute for them. This
milestone also distinguishes verified invitations and attendance from claims,
deception, rumours, and contested participation.

### v0.9 — Regional growth and historical emergence

Add multiple simulated settlements, spatial travel and logistics, settlement
specialization, inter-settlement trade, diplomacy and conflict, culture,
religion, disease, ruins, historical figures, rumours, and promotion of
selected off-map references into simulated regions. Emergent quests are
derived from world conditions, histories, needs, and NPC interpretations
rather than inserted as unsupported LLM facts.

### v1.0 — Mature observable sandbox and player influence

Consolidate the simulation into a supported long-running sandbox with stable
scenario/run interfaces, compatibility and migration policy, richer failure
and recovery behavior, and an operator experience built on the read-only and
spatial inspectors. Add player influence on history only through explicit,
authorized commands and world actions; the web administration interface
remains separate from read-only inspection and must have its own authority and
audit model.

## Backlog placement

Every current future idea has a roadmap home. Placement records intent and
dependency order; it does not authorize implementation or promise that the
scope cannot be refined during task planning.

| Backlog idea | Planned milestone or track |
| --- | --- |
| Autonomous settlement evolution, founding mandates, objective graphs | v0.6 |
| Off-map homelands, markets, trade/travel/communication references | v0.6, with promotion to simulated regions in v0.9 |
| Read-only World Inspector UI | v0.6 supporting observability track (existing Task 15 candidate) |
| Spatial World Inspector and canonical placement | Begin as a v0.6 supporting contract; expand for regional simulation in v0.9 (existing Task 15a candidate) |
| Births, childhood, apprenticeships, old age | v0.7 |
| Death, inheritance, families, genealogies | v0.7 |
| Migration | v0.7 local/population continuity; v0.9 inter-settlement movement |
| Reputation | v0.7 personal/social foundation; consumed by v0.8 politics |
| Experience validation and confidence weighting | v0.7 cognitive maturation |
| Long-term memory decay and retrieval ranking | v0.7 cognitive maturation |
| Dynamic factions | v0.8 |
| Council opposition, political realignment, withdrawal, and secession | v0.8, using v0.7 migration and v0.6 settlement foundations |
| Institution-specific meeting and decision rules | v0.8 |
| Invitation claims, deception, and contested participation | v0.8 |
| Culture and religions | v0.9 |
| Disease | v0.9, building on v0.7 demography and care constraints |
| Historical figures and ruins created by simulation | v0.9 historical emergence |
| Dynamic rumours | v0.9, building on verified communication and belief boundaries |
| Emergent quests | v0.9 |
| Player influence on history | v1.0 |
| Web administration interface | v1.0 authorized-control track, separate from inspection |

## Observability and user experience

The read-only inspector and spatial inspection work are complementary to this
roadmap. The operator should eventually be able to see:

- current needs, resources, work, and bottlenecks;
- settlement goals, dependencies, progress evidence, and failures;
- population, households, occupations, and institutions;
- construction, production, trade routes, and external dispatches;
- stage changes and the event history that caused them;
- individual NPC perceptions and cognitive history without crossing the NPC
  information boundary.

Administrative commands, scenario controls, and read-only inspection must stay
separate. A visualization must not become an undocumented mutation API.

## Planning rules for follow-up tasks

- Each numbered implementation task needs its own plan, saved `-prombt.md`,
  report, tests, examples, documentation, and allowed-file boundary.
- The first task for each new domain must define persistence and inspection
  together with lifecycle ownership; neither may be bolted on afterward.
- Goal criteria and settlement-stage criteria must be engine-testable and must
  not depend on free-form LLM output.
- New NPC-visible information must document world truth, perception,
  interpretation, and hidden fields before implementation.
- Randomness, when introduced, must be seedable and replayable enough to debug
  unattended simulations.
- The canonical vertical slice comes before broad feature expansion.

## Branching transition

Use the milestone-plus-task branch workflow in `docs/development_workflow.md`
beginning with v0.6. `milestone/v0.6` is the first integration branch and its
implementation tasks use short-lived pushed branches created from it. The
orchestrator may merge reviewed task work to that milestone branch, never to
`main`. This transition does not authorize v0.7.

Task 14a reorganized the historical execution-plan artifacts after Task 14
closed v0.5. Tasks 01–14b and Task 14a form the
`initial_v0_2_3_to_v0_5/` archive; Tasks 15 and 15a are in `v0_6/`. Milestone
overview files and the root cross-milestone index establish the layout used by
later milestone and task branches.
