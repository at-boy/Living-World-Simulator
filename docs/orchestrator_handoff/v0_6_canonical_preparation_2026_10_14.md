# Task23 root decisions under preparation (not binding task material yet)

Owner approved canonical integration in completion plan; worker dispatch awaits
reviewed Task15/15c and a decision-complete exact plan/prompt.

- No new scheduler phase: register canonical composition as an ordinary system
  after default ordinary systems and before recorded proposals/work. Shelter
  constructed in tick t gets housed_in edges and maintenance via managers at
  t+1; HousingSystem first reports allocation at t+2. Tests/documentation must
  assert this explicit delay. Never patch housing allocation or goal statuses.
- Existing settlement production recipe food input1/output4 and water output2,
  population2 and shelter food upkeep1 preserve bounded initialized stocks.
  With zero food startup recipe is inactive; ordinary produce_food/gather_water
  work establishes provisions through effects. Existing resource recipe is an
  engine abstraction and does not claim agricultural realism.
- Labor-three shelter construction offered with available materials and only
  two eligible founders creates valid blocked work through WorkActionHandler;
  bounded stall reports exact waiting-for-labor evidence. Do not manufacture a
  material-starved offer rejected during provider preflight.
- Success terminal requires authoritative settlement stage AND arrived homeland
  dispatch. Contactable reference alone is insufficient. Domain predicates are
  Task23 runtime composition, never browser logic or direct goal mutation.
- Failure terminal follows canonical configured deadline/goal failure. Stall
  bound precedes deadline. Exceptions remain execution errors.
- Keep canonical policy in versioned, closed engine-owned scenario attributes
  participating in existing scenario fingerprint, public entity labels only.
  Avoid an unrelated general scenario-schema expansion. Setup/resume validation,
  policy version, exact initial fixtures and factory offers require final design.

Initial setup atomicity probe resolved:
- Separate documented atomic boundaries: ScenarioRuntimeManager binds initial
  graph/metadata first; canonical setup deep-copies all WorldState fields and
  composes coherent existing managers on shadow. Validate every loaded domain
  before field-wise commit to the same original WorldState object. Failed setup
  leaves only the valid bound initial graph, never half-domain state or save.
- Do not stage initial work. WorkManager captures counters at construction and
  does not collision-scan work candidate IDs; no initial work is needed. Others
  skip committed IDs. Test next event/entity/relationship/reference IDs.
- One immutable engine-only canonical_setup_completed event at tick0 records
  closed policy version/fingerprint and settlement subject. Use this plus exact
  canonical definition/policy/program/reference and initial label checks as
  all-present/all-absent boundary. No new schema collection. On resume validate
  immutable setup definitions plus evolving-domain loaded validators; do not
  compare dynamic states to initial values, repair partial state, or duplicate
  events. Marker absent with any partial canonical domain state fails closed.
- Atomic replay preparation remains subsequent existing transaction. If replay
  config rejects, valid complete canonical setup may remain in memory, but runner
  must not advance/finalize/save. Document both transaction boundaries explicitly.

Candidate exact fixtures for contract feasibility review (tick predictions need
focused confirmation before publishing commands; no worker architecture choice):
- seed42, population2, initial food0/water0/timber10, producer settlement recipe
  inputfood1/outputfood4/water2; consumption food/water1 per person/tick;
  storage spoilage1 for each provision until owned capacity20; shelter upkeepfood1.
- food work adds10, water work adds8; modest shelter housing_capacity2 costtimber2
  labor1/progress1; storage capacity20 costtimber2 labor1/progress1; large shelter
  same materials butlabor3. StageTown requires population3 so canonical remains
  settlement while separate Task21 provesTown.
- explicit ordinal tapes: tick0speech for goalsactivation; tick1food;tick2water;
  success tick3modest shelter,tick4storage,tick5connection,tick6dispatch,
  ticks7–9speech; nominal stopendtick10 afterdispatch arrivesat9
  (created6,departed7,delay2,reliability1). Inbound food1 is received by the
  acting founder via existing actor-bound dispatch handler, not silently credited
  to settlement inventory; docs/inspection must show this exact source/beneficiary.
  Stall samefirst3entries, tick3large shelter,tick4speech; bound5. Failure13speech
  entries, goaldeadline12 -> nominalstopendtick13. Do not claim predictedticks as
  validated before executing; adjust contract if actual existing phases differ.
- Need window3/duration3, securemaximum0, strained0.5, requirementperperson1.
  Food/water goals use sustainedneedcriteria; shelter capacity2 plusconstructed;
  storage capacity20; maintenance maintainedshelter mincondition; homeland
  contactable objective plus terminal arrival proof. Goal failuredeadline12.
- All offers require active goals/objectives plus live actor NPCIdentity and
  canonical spatial containment. Tick0speech deliberately allows activation.
  Filter provider before constructing WorkActionHandler so completed/ineligible
  objectives do not cause offerconstruction exceptions. No hidden enginepolicy
  in ActionOptions; only qualitative labels/actions/emptyargument maps.

Runtime/acceptance interface decisions under contract preparation:
- Canonical terminal predicates supplied as closed engine-owned callbacks to
  ScenarioRunner; canonical selected names ordered founding_failure then
  settlement_success. Unknown/duplicate/conflicting names reject before prepare.
  Preserve existing tick_limit/operator_stop compatibility. Evaluate canonical
  domain predicates at complete initial/resume boundary and after each tick so
  already-terminal resume performs no extra tick. Operator request before tick
  retains cooperative stop precedence; aftertick failure->success->bound->operator.
- Root must finalize a minimal idempotent ordinary-system registration hook
  before Task23 dispatch: optional explicit key on register_system may replace
  exactly its existing registered list position, preserving unkeyed behavior.
  Canonical key singleton prevents duplicate composition across preparations;
  no new post-work phase. Amend exact engine/tests scope and independently review
  rather than let worker choose this architecture.
- Compare world_snapshots(schema_version,payload) id1 across fresh/resumed CLI
  databases. Repository payload is canonical JSON sortedkeys/separators. Preserve
  ALL world fields/events/order/work charges/cursor; normalize no domain fields.
  Operational RunResult start_tick/resumed may differ and aren't world payload.
  Physical SQLite bytes/page layout are not the canonical state artifact.

Operator saved-world composition preparation:
- ResourceDefinitionManager is ephemeral: restore canonical resource vocabulary
  only after successful setup validation/commit and on every valid resume/inspect.
  Definitions show vocabulary, quantities remain explicit entity attributes.
- Saved-world command should require scenario path plus database to reload
  definition vocabulary and verify exact run identity; no inferred scenario path
  from key/fingerprint. Host create_app(engine) snapshot on fixed loopback with
  configured valid port. It never steps, prepares replay, creates new domain setup
  or writes checkpoints. Other-process/live-run freshness remains explicit.
- Root must include minimal SQLiteRepository read_only option in exact Task23
  contract if needed: URI mode=ro, no schema creation during load, save rejects,
  missingfile/table invalid without creating anything. Default run persistence
  unchanged. Required regression compares database bytes and world snapshot
  before/after loading/GET; missing file remains absent. This is scoped snapshot
  inspection composition, not a general persistence redesign.
