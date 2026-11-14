# LN09j implementation report

Base `9b6dbee`. Canonical live founders can select
`founders_offer_bound_v1` with either provider. Each request specializes an
independent empty-arguments schema to the filtered offer order and per-action
target labels. The existing runtime factory builds the provider payload for live
inference, size checks and sealed replay. The parser, action gateway, prompts,
work policy and archive schemas are unchanged.

## Worker evidence

- Before production changes, the focused selector/helper regression selection
  returned 15 expected failures and 9 passes. Both full stock runtime-path
  regressions also failed against the baseline CLI's missing selector.
- Baseline legacy hashes were retained. Exact request body and input hashes
  for the previous empty-arguments selector were measured on the base and then
  pinned for both providers.
- The final Task 24 environment run of `PYTHONPATH=src pytest -q
  tests/test_cognition_request_contract.py tests/test_runtime_request_contract.py`
  passed all 89 cases, including the complete request ceiling and unoffered
  targets from provider responses. The first GREEN run passed 83 cases.
- The two providers exercise the same stock launch, spawned broker, retained
  archive and cold-resume paths with synthetic loopback HTTP responses. Exact
  request bytes match the retained BLOBs. Replay after provider shutdown
  preserves the complete snapshot, both cursors, event references and captured
  request identity through the sealed source boundary. The llama.cpp fixture
  exposes parsed bodies, which the test encodes with the production wire
  serializer. The Ollama fixture captures the actual raw bytes.
- Spawned tests confirm the response parser rejects unoffered targets, preserves
  unexpected arguments for ordinary gateway rejection, and prevents HTTP when
  the full encoded request crosses 16,000 characters due to duplicated labels.
- Scoped Ruff and Black checks passed for all eight worker-owned Python files.
  `git diff --check` passed.

## Worker scope

Changes are confined to the six approved production modules, the two
request-contract test files, the short NPC information-boundary addition and
this report. Native provider evidence, independent review, full repository
validation and Git integration are root-owned.

## Independent review and native evidence

Independent review found no substantive specification or quality issues.
Its focused selection passed 37 tests with 52 deselected. Native runs used
reviewed source `0a1636eff1266db848c8036c5e834c47e40ba5ffd763659d0871f80fa42813fd`
(358 files), the stock founders scenario, and the unchanged acceptance criteria.

| Provider | Unattended result | Offline replay |
| --- | --- | --- |
| Ollama, Qwen3 4B Q4_K_M | `33bc9b0e` reached the founding deadline at tick 13 with `founding_failure`, 26 validated responses and four accepted actions. | `0c109b1d` reproduced the complete committed world, events, cursors and retained response evidence. |
| llama.cpp, Qwen2.5 7B Instruct Q3_K_M, AMD Vulkan0 | `cfc9162a` reached settlement stage with 28 validated responses and eight accepted actions, then reported `tick_failed` after committing tick 14. | Latest checkpoint replay `d19bed37` rejected `incompatible_save`. Explicit checkpoint 13 replay `60a22b31` matched all 14 checkpoints through revision 13, with 26 retained responses. |

All 54 campaign requests had the exact schema for their archived public offers,
including null-only requests. Archived request and response bodies matched their
retained digests and lengths. All 54 responses included HTTP 200 and positive
broker timings. In the llama.cpp campaign the engine destroyed two
shelters at tick 13 and retained their maintenance records. The canonical founders
restore validator rejects that combination at revision 14. The same detached
snapshot fails with the base `9b6dbee` composition. Revision 13 restores on the
base. Repairing that state transition requires a separate task.

Both stock work-interruption runs recorded `no_eligible_work` at the fixed
tick-2 boundary. Each had eight real provider requests across its original and
cold-resumed attempt and reproduced all four resumed checkpoints offline.
Ollama child `dbad5bd8` replayed as `724964d8`. llama.cpp child `d00762f6`
replayed as `1bddd1c5`. Neither work-interruption gate passed.

The host verified that all four temporary server processes had exited and both
owned ports were closed. Exact attempt IDs, archives, process logs, and the
restore diagnosis are preserved under the feature worktree’s
`.superpowers/sdd/2026-10-19-live-npc-runtime/ln09j-native-*` outputs and
`ln09j-llama-tick14-root-cause.txt`.

## Package checks

The wheel installed offline on Python 3.11.2 passed all six compatibility
checks, including selector visibility, the canonical matrix, stock serve,
example 040 and archive export. The installer fell back from hardlinks to
copies. The packaged saved-world viewer opened revisions 0 and 13 of the native
Ollama attempt in Chrome. All nine requests passed and the archive inventory
remained unchanged.

`make` passed 3,073 tests with 10 existing skips in 790.52 seconds and ran
all 40 examples. The separate `make examples` and `git diff --check` passed.
All 13 task validation jobs passed, including the existing CLI and archive
compatibility checks, packaged serve, browser, and analysis and export checks.
The reviewed 358-file source digest was unchanged.
