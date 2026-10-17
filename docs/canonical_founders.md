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
