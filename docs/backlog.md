
# Living World Simulator Backlog

LN09a deterministic disturbances are independently reviewed and task-validated2311/10,
with exact recorded/restart/source-and-wheel serving checks; repeated feature integration
gates passed2311/10existing skips,39examples and identical compatibility evidence. Format-two work interruption resolves the canonical single-tick gap.
Original full real-provider acceptance is still incomplete.

LN09b deliverybb907a0 shared llama.cpp backend is reviewed and integrated after repeated
task/merged2373/10existing skips,39examples and exact recorded/restart/source-and-wheel
checks.
LN09c delivery76911a3 sealed trace storage is independently reviewed and task/merged
validated2469/10existing skips, actualChrome/39examples and exact compatibility gates.
LN09d delivery2781dd3 capture producer is reviewed/task+merged validated2526/10existing
skips, Chrome/39examples and exact compatibility gates. LN09e automatic archive wiring
and sealed trace reuse/replay is independently reviewed and task-validated2547/10existing
skips,39examples and exact compatibility gates; repeated feature gates passed the same
counts with unchanged reviewed source. Taskbranch62ea35c preserved/pushed.
Then9f admin/offlineanalysis/export and real BOTHprovider acceptance.
LN09f1 bounded read-only trace reader contract is ready for isolated implementation;
no API/UI/export yet. Full runtime validation remains unchanged; analysis exposes its
narrow metadata/selected-body integrity scope and explicit resource limits.
Postintegration90ef1e2 native diagnostic:20realcalls/9archives across bothproviders,
exacttrace/coldrestart/offlinereplay PASS; Ollama1acceptedwork, llama12nonnullworkproposals
rejected for nonemptyarguments. Keep gatewaystrict. Before finalacceptance, isolate
prompt/offer/argument-contract compatibility and preserve existing archive fingerprints/
replay semantics; no fixcontract/code yet. See current native probe report.
No complete backend/trace behavioral acceptance claim yet.

## Additional owner requirements — October26,2026

Before final live-runtime acceptance, verify both Ollama and the installed llama.cpp
backend through persistent worlds, controls, cold restart, archives and offline replay.
The existing standalone llama client is not complete persistent-runtime support.
Native llama-server and Qwen3.5-4B GGUF are available; normal llama acceptance should
use the owner's AMD Vulkan0 configuration. Root backend contract precedes implementation.

Also required: privileged per-inference exact request bytes, backend/model identity,
received response bytes (including invalid/error responses), statuses and clearly scoped
UTC/monotonic timing data in simulation archives for later analysis. Explicitly mark
partial/oversized/unavailable responses, preserve safety bounds and failed attempts,
and keep traces outside NPC context. This owner requirement supersedes earlier raw
invalid-response nonretention. Trace storage/capture and admin inspection/export need
bounded contracts and review before claiming implemented; historical traces unavailable
from older runs must not be fabricated.

Future only: configurable model profiles selecting Ollama or llama.cpp, GPU device(s),
context/memory limits and hardware compatibility. Current work uses external owned
server processes; no product GPU launcher or automatic driver changes are authorized.


The next approved design scope is live NPC decisions and an observable run lifecycle,
not demographic v0.7 work. Existing recorded scenarios remain supported. The
[live runtime design](superpowers/specs/2026-10-19-live-npc-runtime-design.md) covers
Ollama, qualitative feedback, controls and automatic run archives. Written design
is owner-approved and pushed; the [implementation plan](superpowers/plans/2026-10-19-live-npc-runtime.md)
is owner-approved for execution. LN01 shared snapshot codec has passed independent review and task/merged validation;
delivery5f64056 and integration evidence are recorded in its report. LN02 atomic archive storage delivery099da9a passed independent review and task/merged
gates1503/10 with39examples; integration evidence is recorded in its report. LN03 attempt catalog/input ownership deliverye3d9faf passed independent review and
task/merged gates1551/10,39examples. LN04 safe controller/recorded adapter passed independent review and task/merged gates1589/10,39examples; delivery906d23f and integration evidence in04report.
LN05 feedback/live composition passed independent review and task gates1652/10,
39examples; delivery64efb1e and task/merged evidence recorded in05report.
LN06a archive delivery6469a38 and LN06b runtime delivery5a3f58a are reviewed and
integrated; LN06b task/merged gates1758/10,39examples and exact recorded matrices
passed. Original Task6 delivery is reviewed; consumer integration exposed a bounded06c
shutdown same-world response-reuse correction, now independently reviewed with
task/mergedgates1767/10,39examples; delivery0eca121 integrated by the merge
containing its report. LN07 is split into7a archived legacy CLI,7b setup/model-preflight producer and
7c controller-owned live/service/restart entrypoints. LN07a deliverycd5e40d is reviewed; task1800/10,39examples/exactmatrix and26retained
CLIattempts passed. Merged1809/10,39examples,separateexamples/whitespace/exactmatrix
and26readable archives passed. Original Task7 remains incomplete; bounded setup/model
preflight deliverya4d7e41 now integrated after independent correction review and
task/merged1876/10,39examples, separateexamples/whitespace/exactmatrix with26archives.
Parent-aware deferred fork setup LN07c is reviewed afterone corrected allocation
failure; deliveryada9b8b integrated with task/merged1956/10,39examples and exactmatrix before
service/generic recorded restart ownership (LN07d, independently reviewed and
validated delivery1c2c2fc; task/merged2018/10,39examples/exactmatrix passed) and CLI consumers (LN07e deliveryf9281f9 independently reviewed/task-validated and pushed;
task/merged2055/10,39examples,canonical26archives/newCLI7cases passed; integrated
by the merge containing this entry).
Runtime service and archived CLI are integrated. LN08a exact reusable-router/revision
source deliverybcbff33 integrated after independent review and task/merged2087/10,
39examples/exactacceptance. LN08b authenticated operatorAPI is independently reviewed after one corrected P2;
root taskmake2105/10existing skips,39examples,separateexamples/whitespace and exact
canonical/newCLI acceptance PASS. Delivery8731bbf is integrated by the merge containing this entry after repeated
merged2105/10/39examples/exactacceptance PASS. Auth/control API is integrated. LN08c authenticated inspector is independently reviewed and task-validated
(2115/10existing skips,39examples/exactarchiveacceptance); deliveryc3a5b69 integrated after repeated merged2115/10/39examples/exactacceptancePASS; LN08d parent control/archive page is independently reviewed after three corrected
P2s and task-validated:2140/10existing skips,39examples,exactarchive checks and wheel11
resources PASS. Deliveryfdfeecf integrated after repeated merged2140/10/39examples,
exactarchive/CLI and wheel11resources PASS. Shared prepared-launch producer followed
by public CLIserve and installed-Ollama acceptance remain upcoming. LN08e shared
prepared-launch task is independently reviewed and task-validated2173/10/39examples/
exactarchive+wheelchecks; delivery8651a53 integrated after repeatedmerged2173/10/
39examples/archive/CLI/wheel11 PASS. LN08f publicCLIserve independently reviewed after
onecorrectedP2 and taskvalidated2230/10/39examples plus source/wheelserve8retained
attempts. Delivery362c383 integrated after repeatedmerged2230/10/39examples/archive/CLI/
source-and-wheelserve PASS. OriginalLN07/LN08 delivered. LN09 needs a bounded deterministic
disturbance/journal/replay producer prerequisite before full realmodelacceptance;
LN09a exact bounded contract now authorized, actualacceptance/harness follows LN09b.
legacy generic/taped/raw-database CLI and injected engine/state-reference hooks must
remain compatible. Add an explicit archive observer to the existing runner, not a
second copied loop. New live entrypoints retain RunController ownership. LN07 must
share replay composition.source_point with driver. Browser controls remain LN08 and
actual installed-Ollama/operator acceptance LN09. Future player APIs are separate.



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
