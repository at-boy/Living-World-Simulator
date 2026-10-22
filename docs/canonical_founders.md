# Canonical founders acceptance

Release candidate `0.6.0rc1`: see [release notes](releases/v0_6_0rc1.md)
and [current closeout evidence](subagent_execution_plan/v0_6/24_v06_release_closeout-report.md).

The fixed `canonical_founders_v1` preset composes existing simulation managers,
work execution, needs, consequences, goals, stages and external dispatch. Its
three packaged proposal tapes are deterministic untrusted drivers. They do not
demonstrate that a live language model chooses a winning strategy.

Run a bounded outcome with a separate database:

```console
living-world run --founders success --database success.sqlite3
living-world run --founders stall --database stall.sqlite3
living-world run --founders failure --database failure.sqlite3
```

Success and failure stop on engine-owned terminal predicates. Stall defaults to
five additional ticks. Explicit `--max-ticks`, `--save-every`, `--continuous` and
`--checkpoint-only` retain per-invocation semantics. A checkpoint-only run avoids
finalizing unused proposal entries. To checkpoint stall at tick 3, use
`--max-ticks 3 --checkpoint-only`, then resume with `--max-ticks 2`. Explicit
canonical scenario paths require `--proposal-tape`; aliases supply their own tape.
Scenario identity fingerprints include the complete fixed policy and definition
contents; meaningful rule changes require a versioned preset.

Inspect an existing snapshot without advancing it:

```console
living-world inspect --founders --database success.sqlite3 --port 8000
```

Install the optional `living-world-simulator[server]` extra to serve at
`http://127.0.0.1:8000/inspector`. The repository opens in read-only mode and
requires an existing snapshot and scenario metadata. Inspection validates complete
canonical setup, restores only ephemeral definition vocabulary and serves a fixed
in-memory snapshot. It neither initializes missing setup nor automatically reloads
a database changed by a different process. Programmatic `create_app(engine)`
continues to read its supplied engine.

Initial graph binding, atomic canonical setup and replay configuration are
separate boundaries. Setup stages mutable entities/relationships and dictionary
collections, retains immutable events, validates domains and commits fields to
the original world object. A setup failure preserves the valid bound graph; it
is not a whole-engine rollback. Replay failure can leave complete setup in memory,
but does not advance/finalize/save. Resuming missing or contradictory setup fails
without repair. Maintenance and housing attach after actual shelter construction;
storage policy attaches after actual storage construction so startup stocks are
not discarded as overflow. Existing dynamic consequence states are retained.

Engine truth includes resources, work policy, IDs, need history, goal criteria,
maintenance and stages. Existing holder-scoped perception and retrieval assemble
immutable cognitive records into an ordinary filtered NPC context. The preset
adds no automatic observations, memories or inference. Qualitative options
translate currently authorized work/dispatch into labels; tools, labor, resource
quantities, deadlines, criteria and IDs stay engine-only. Each recorded proposal
passes `RecordedProposalClient`, `DecisionEngine`, `NPCActionResolver` and the
existing actor-bound domain handlers. Proposal arguments cannot set policy.
Inspector DTOs, raw attributes and the policy manifest never become NPC input.

The steady provision cycle is an existing abstract recipe model, not an
agricultural-realism claim. Population remains fixed at two; town growth is
intentionally unmet. No live LLM, weather, trade automation or population growth
is installed by this preset.

The fixed tapes currently end at tick 10 (`settlement_success`), tick 5 (stall
bound), and tick 13 (`founding_failure`). Success constructs shelter at tick 3
and storage at tick 4. Housing and maintenance attach at tick 4; storage policy
attaches at tick 5. Housing becomes visible to assessment at tick 5, settlement
promotion occurs at tick 7, and the dispatch created at tick 6 departs at tick 7
and arrives at tick 9. Complete boundary 10 observes that arrival. Supplies belong
to the acting founder, as required by the existing dispatch gateway; they do not
silently enter camp stocks. Food/water remain at 10/8 after the provision cycle
stabilizes; timber remains 6 after construction. These values describe this
abstract fixed preset, not a general strategy or physical realism guarantee.

Fresh runs and resumes after checkpoints at 1, 3, and 4 must store identical
schema version and full canonical JSON payload. Comparison excludes no domain
fields, IDs, events, resource charges or replay progress. SQLite page bytes are
not canonical state identity; read-only inspection separately preserves those
physical bytes. Success/failure already-terminal resumes add no ticks or events.
See `examples/039_canonical_founders.py` for bounded public composition and saved
snapshot loading without starting a server.

The generic goal evaluator now treats a short, available need-history prefix as
pending only when its unique `need_created` event anchors every assessment from
creation through the current tick. Missing, stale, gapped, truncated or unavailable
history remains unavailable. This allows ordinary ACTIVE-only work authorization
while real history accumulates, with no synthetic history or gateway exception.
Replay accepts `dispatch_external_trade` as the existing structured action key;
that string remains forbidden in prose, labels, descriptions and arguments.

Every `living-world run` invocation now creates an independent recorded attempt
under `$XDG_STATE_HOME/living-world/runs` (or `~/.local/state/living-world/runs`).
Use `--archive-root PATH` to choose another catalog. Stderr reports its attempt
identity and absolute directory before engine initialization. The archive retains
scenario, definitions and tape and saves the initial prepared world plus every
complete tick, independently of `--save-every`. Finalization may add another
revision at the same tick. `--checkpoint-only` records `finalize_proposals=false`;
older recorded attempt metadata without that flag means true.

`--database` remains the existing SQLite mirror, with its existing save cadence.
An archive checkpoint can remain authoritative after a mirror save fails; the
invocation reports persistence failure rather than success. Partial failed ticks
and failed finalization are never published. Configuration failures are discoverable
as failed attempts, including a metadata-only `uninitialized` attempt when scenario
identity could not be loaded. Parser errors and `inspect` create no attempts.
Raw SQLite continuation creates a new independent attempt whose initial revision
is the prepared resumed world. This archival stage adds no archive-based resume,
live provider service, browser control, or replay command.

## Archived headless runtime CLI

The recorded aliases above still use the established scenario runner. Every new
recorded attempt now records its actual `--continuous` intent. An existing database
continues that legacy route; a database alone never selects the live driver.

Run the canonical founders with an already installed Ollama model:

```bash
living-world run --preset founders --driver ollama --model MODEL
living-world run --preset founders --driver ollama --model MODEL --max-ticks 5 --max-requests 20 --archive-root ./runs
```

Providers must use credential-free loopback HTTP(S). Optional overrides are
`--base-url`, `--timeout-seconds`, and `--max-output-tokens`. No model is downloaded.
The live defaults are 20 ticks and 40 requests. `--continuous` removes the tick
budget while retaining the request budget. Each launch prints its attempt ID and
archive directory on stderr before provider requests, including failed startup.
Provider failures exit 6 without an automatic retry. SIGINT cooperatively stops and
cleans up startup or generation. A request-budget stop exits successfully and prints
`stop_reason=request_budget_exhausted`; this is an operational stop, not settlement
completion. Failed runs retain their known attempt, or a metadata-only failed
uninitialized attempt if failure precedes allocation.

Explicit archive restart commands create children with captured parent/checkpoint
lineage and leave the source attempt unchanged:

```bash
living-world run --resume-attempt ATTEMPT_ID --archive-root ./runs
living-world run --resume-attempt ATTEMPT_ID --checkpoint 2 --archive-root ./runs
living-world run --fork-attempt ATTEMPT_ID --max-ticks 10 --archive-root ./runs
living-world run --fork-attempt ATTEMPT_ID --model OTHER_MODEL --archive-root ./runs
living-world run --replay-attempt LIVE_ATTEMPT_ID --archive-root ./runs
```

Resume preserves the exact saved configuration; explicit equal options are accepted,
but a changed configuration requires `--fork-attempt`. Fork permits provider and
budget changes within the saved driver/scenario binding. Changing the model explicitly
resolves a new installed-model identity; resuming keeps the original digest pin.
Recorded attempts can change tick limits through a fork while preserving retained
tapes, replay cursors, finalization policy, and scenario definitions. Offline replay
uses the captured live journal without contacting Ollama and rejects configuration
overrides. `--checkpoint` selects a source checkpoint for restart or replay.

The archive is authoritative. On new archived run routes an optional explicit
`--database` writes a secondary SQLite mirror at the inherited/default save cadence;
it never supplies restart state. The legacy route still defaults to `world.sqlite3`.
Mirror failures exit 4 while retaining the authoritative archive checkpoint.

Inspect a selected archive checkpoint through the existing read-only HTTP inspector:

```bash
living-world inspect --attempt ATTEMPT_ID --archive-root ./runs --port 8000
living-world inspect --attempt ATTEMPT_ID --checkpoint 0 --archive-root ./runs
```

Inspection reconstructs the exact retained scenario/definitions and selected snapshot,
checks equality, and serves existing GET-only endpoints. It neither acquires an owner
lease nor steps, repairs, writes the archive, or contacts a model. Missing worlds fail
with exit 4. The optional server dependency is required only for inspection. Existing
`inspect SCENARIO --database PATH` and `inspect --founders --database PATH` remain
available. Archive inspection cannot combine a scenario or database target.

Browser runtime controls and final serve acceptance remain LN08 work; installed-Ollama
acceptance belongs to LN09. This stage adds no `serve` placeholder.
