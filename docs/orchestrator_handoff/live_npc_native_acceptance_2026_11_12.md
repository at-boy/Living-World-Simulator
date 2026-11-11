# Native runtime acceptance evidence — November 12, 2026

The bounded helper works with both real providers. Baseline and resource-loss
checks pass, including ordinary accepted actions, changed safe feedback, cold
restart and exact offline replay. **Applied work-blockage acceptance remains
unmet for both models.** This report does not close original LN09, certify a
successful settlement campaign, or declare the whole branch release-ready.

## Provenance and scenario

Task BASE `e8bb26511ffaa0bb38866e64fb4bb6ab9d0c286d`, independently reviewed
uncommitted source SHA256
`48215a24be4adaff9ee3fb0ef3a6457ddfcff970be456df4e3e1484c31e93b45`
across 358 tracked/new source, test, example and pyproject files. Production
package code is unchanged by LN09h. Task and integration commit IDs belong in
the final task report and continuation brief.

Canonical founders seed42: Ada and Bryn, camp/valley, timber10, food/water0,
no housing/storage. Engine goals concern sustained needs, shelter, storage and
homeland trade. The native route receives filtered holder-owned context and
safe offers, never raw engine truth. All proposals pass the ordinary gateway.
No injected decisions, extra labor, fabricated work or automatic model retries.

Each main case commits one fresh tick, stops the process, resumes a cold child
from its exact checkpoint and commits three further ticks. Provider timeout120s,
output cap1024tokens, maxrequests24 and max-ticks3 (the existing per-attempt run
budget), outer helper deadline360s. Actual final child world tick4. These bounds
exercise runtime behavior rather than the full founding deadline/campaign.

## Main six-case results

Each row has eight real requests with complete exact request/response evidence.
All rows have ordinary accepted actions and exact initial child world/cursors.
Every saved child was replayed with its provider stopped; complete worlds,
events, cursors and retained response observations/timings match, and original
source bytes and modification times remain unchanged.

| Provider | Disturbance | Applied behavior gate | Source / child / replay IDs |
| --- | --- | --- | --- |
| llama_cpp | none | PASS | `14a61575b0ae46798f29373635669616` / `b028d664a79d400eac5da0f0cb92b199` / `54fc76c9024c4670ac7e6f329630c66b` |
| llama_cpp | resource_loss | PASS | `205dbbde37e041ed8e990098f9dece62` / `863d466a009347d8a476bb51d642e201` / `8ba6ba64285841d5ad5e7459c55d53ae` |
| llama_cpp | work_blockage | UNMET | `2904f531311b4d18b40b306b27a793e3` / `469127ce6b8d40dab382faac5a8d6ed4` / `c5487f7c576243029d6b3767d3d61b26` |
| ollama | none | PASS | `cd28d609af87432e958b0cb1925b8ca5` / `b084e416a9a94148806f1f7c44060664` / `8560576227fc49bebd92f0190bb8e682` |
| ollama | resource_loss | PASS | `ef61d3b82943453b907935891ceaf5c1` / `752380d096c14e56807a646b8ea2c224` / `b1bb320e1e01495595af7f2714722ff5` |
| ollama | work_blockage | UNMET | `e61f2ffd8697452b88377f51c7a533a0` / `a3e553f84c9149d5abe6869d0bb00049` / `82544a206bc64228a7c04ecc1eba37d3` |

Resource-loss cases remove timber at completed tick2, record exactly one audit
and show changed subsequent filtered requests with unavailable construction
offers removed. Exact quantities/audit IDs remain engine-only.

Both work cases record `no_eligible_work`. The native choice at the relevant
boundary is “Build a larger shelter group,” requiring three workers; the camp
has two. Work is naturally blocked with “Waiting for eligible labor.” The
format-two interruption correctly requires ordinary execution preflight to pass
before interrupting work, so this naturally blocked order is ineligible.
Independent read-only investigation confirmed that modest shelter and other
normal-labor offers can qualify through the unchanged scheduler. Synthetic
`ShelterBroker` tests explicitly choose the modest shelter; those passing tests
do not certify native target choice. Later completed eligible jobs do not repair
the fixed tick2 native gate. No product defect or decision repair is inferred.

## Actual browser controls and saved inspection

Both providers passed actual Chrome login, world inspector, one-tick Step,
Resume into real inference, Pause with durable applied receipt, Ctrl+C shutdown,
cold stock-CLI Serve child at the exact complete checkpoint and another browser
Step. Each uses four additional real requests across its source and child.
Both paused at tick1 and their children advanced to tick2. Cold reuse of a sealed
response is retained as reuse; it is not counted as a new model request.

- llama source `49ec244a09ec4d71b75c358073e37039`, child
  `4fc00924b6a846118fc8c37ef8d2e142`.
- Ollama source `ff939fc291244c4b94c3e846c5299414`, child
  `74cae1f4785047d49de1d29f064bd47e`.

Offline browser-child replay matches every distinct adjacent complete simulation
checkpoint and final world/cursors, including exact reused/new trace metadata.
Serve shutdown adds a duplicate complete checkpoint for its operator receipt;
simulation replay does not recreate unrelated operator command history.
Original source bytes/mtimes remain unchanged. Browser session tokens are removed
on shutdown and absent from archive files, browser storage and cookies.

Installed-wheel actual Chrome inspected nine saved native attempts, two revisions
each: both baselines, both resource cases, both unmet work cases, both browser
children, and the failed/interrupted exploratory llama attempt. Protected HTTP
checks pass; complete source file/directory inventory, modes, bytes and mtimes
remain unchanged; no new attempt is created by inspection.

## Preserved unsuccessful exploration and verifier corrections

The first llama browser exploration correctly rejected a stale Pause envelope
(expected version6, current8), then reached `invalid_response` at tick4. The
verifier had polled HTTP tick2 ahead of its browser display; it subsequently
acted on the browser's refreshed state and checked the applied Pause receipt.
The invalid-response and rejected command evidence is preserved, including failed
attempt `d6e54ca07a1941178b62310e46aa5385`; it is not relabeled successful.

Initial root-only browser replay assertions incorrectly assumed operator-control
checkpoint counts and counted only newly validated responses. Read-only evidence
showed exact duplicate shutdown worlds and a sealed response reused by the cold
child. Corrected assertions compare complete simulation worlds/cursors and both
original reused/new response observations. Fresh replay proofs then passed with
providers stopped throughout. Production and reviewed helper code never changed.

## Backends, ownership and detailed evidence

- llama.cpp: Qwen3.5-4B-Q4_K_M.gguf, AMD `Vulkan0`, GPU layers99,
  context8192, parallel1, alias `live-qwen35`, reasoning-budget0;
  owned loopback endpoint `127.0.0.1:18080`.
- Ollama: cached `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M`, owned
  `OLLAMA_HOST=127.0.0.1:11435`, `OLLAMA_KEEP_ALIVE=0`.

These are different model/version/backend configurations, not a controlled
performance comparison. Archive traces retain actual engine/model, precise HTTP
request and observed response bytes/hashes, original timestamps and monotonic
client/broker durations. Replays retain original timing observations.

The owner authorized temporary model servers conditional on cleanup. Root tracks
owned PID/UID/start-time/argv; all owned model servers and simulation processes
have stopped. No unrelated service was stopped. No downloads, system installs,
driver changes or containers were required.

Evidence W is the feature worktree's ignored
`.superpowers/sdd/2026-10-19-live-npc-runtime/` directory. Main case directories
are `ln09h-native-{llama,ollama}-{none,work}`, `ln09h-native-llama-resource-r2`
and `ln09h-native-ollama-resource`; each contains preserved logs, process
identities, actual run catalogs and machine-readable result metadata. Browser
proofs live under the resource cases' `browser-controls/`. Work `unmet-summary`
files explicitly distinguish passing evidence checks from unmet applied behavior.
`ln09h-six-case-results.json`, `ln09h-native-saved-browser-results{1,2}.json` and
`ln09h-native-work-eligibility.md` are the compact indexes.

Earlier same-day bounded probes on committed featuree8bb265/corea9695bb3 are
separate compatibility evidence: eight real calls total, both accepted actions,
exact cold restart/replay, and both new saved children opened/downloaded through
the installed analysis browser. Their `ln09h-probe-native-*` archives remain.

## Remaining acceptance

Applied native work interruption is unmet for these model choices; a genuine
eligible native decision is required. Portable world/recursive-parent closure,
uncommitted spool forensic exports and independent final whole-branch review
remain pending. Full task/integration validation results are recorded separately
in the LN09h task report; synthetic example040 is explicitly model-free evidence.
