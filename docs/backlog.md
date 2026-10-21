
# Living World Simulator Backlog

The next approved design scope is live NPC decisions and an observable run lifecycle,
not demographic v0.7 work. Existing recorded scenarios remain supported. The
[live runtime design](superpowers/specs/2026-10-19-live-npc-runtime-design.md) covers
Ollama, qualitative feedback, controls and automatic run archives. Written design
is owner-approved and pushed; the [implementation plan](superpowers/plans/2026-10-19-live-npc-runtime.md)
is owner-approved for execution. LN01 shared snapshot codec has passed independent review and task/merged validation;
delivery5f64056 and integration evidence are recorded in its report. LN02 atomic archive storage delivery099da9a passed independent review and task/merged
gates1503/10 with39examples; integration evidence is recorded in its report. LN03 attempt catalog/input ownership deliverye3d9faf passed independent review and
task/merged gates1551/10,39examples. LN04 safe-controller contract is prepared; implementation/review/gates pending.
Live decisions, controls and automatically archived entrypoints are not yet implemented. Future player commands remain separate from current operator controls.


October19 owner integration: milestone6bf4c63 merged to main092715c and tagged
v0.6.0rc1; both pushed, milestone branch preserved. Followup agent-path cleanup
keeps the same role files and introduces no domain capability or deferred work.
See the [maintenance report](subagent_execution_plan/maintenance/agent_config_paths-report.md).
The Task24 evidence below remains the pre-integration candidate record.

Task 24 delivery `a5c275f`, integrated as `badd5f9`, completes the reviewed `0.6.0rc1`
candidate on `milestone/v0.6`. Root task and merged gates each passed 1,416 tests / 10
existing deliberate skips, 76 Chrome cases and examples 001–039. Separate examples and
whitespace checks passed. Source and installed Python 3.13.5 / 3.11.2 canonical runs
preserve identical complete schema-12 payloads across fresh runs and resume ticks 1, 3
and 4. Wheel, exports, eight assets, health, read-only APIs, actual console/loopback
inspection and all-outcome browser checks passed.
All 21 authorized tasks are complete; see the
[current closeout report](subagent_execution_plan/v0_6/24_v06_release_closeout-report.md).
These corrections add no deferred domain capability.

Task 20 work orders and reservations, Task 20a's actor-bound proposal gateway,
and Task 20b deterministic execution are implemented.

Task 21's objective-backed settlement stages are independently reviewed,
validated, merged, and pushed to milestone/v0.6. Task 22 recorded proposal
replay is independently reviewed, validated and integrated; its strict
runtime/cursor contract and ADR-0025 remain authoritative. Task15
operator inspector is independently reviewed and integrated. Task15c spatial
view is independently reviewed, validated and integrated. Task23 canonical
composition is independently reviewed, fully validated and integrated as58b6ba7,
with deterministic success10, stall5 and failure13. Task24 completes0.6.0rc1; reviewed final
root gates and integration evidence are in its
[report](subagent_execution_plan/v0_6/24_v06_release_closeout-report.md).
Live-model strategy validation remains future work. Legacy replay enablement on
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
  map and entity inspection; independent review and root acceptance passed in
  reviewed merge0a81a11.
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

## Historical October17 audit checkpoint — superseded

The paragraphs below retain the pre-correction checkpoint. Their pending findings,
audit-coverage and correction-integration instructions are superseded by reviewed
Task24a mergec1d93cd and the current status at the top of this document. All four
code findings and final Task24 release gates are now resolved.

Task24 release closeout in progress from reviewed Task23 merge58b6ba7; no main
integration or tag authorized. Final release-readiness report/gates pending.
Release audit checkpoint October17: Task23 is integrated58b6ba7. Task24 final
readiness is blocked by two P1 auditfindings, recorded in committed orchestrator
handoff auditreport. Correctexisting NPCgoalboundary/reservationID defects in
bounded isolatedtask before resuming uncommitted24metadata. These are release
blockers, not deferredfuturefeatures; full audit coverage/gates remainpending.

Task24a isolated existing-defect correction begins from7d75b20; Task24metadata
checkpoint preserved. Both audit findings and remaining wholeauditcoverage still
block release readiness until reviewed current validation.
