# LN09b worker report — shared llama.cpp persistent runtime

Status: COMPLETE — reviewed deliverybb907a0, task/merged root validation passed.
Worker focused results below are followed by final root validation.
No worker VCS/index operations, full make/examples, installations, downloads,
real model/server launches, subagents or other-checkout writes were performed.

## Implementation and ownership

Exactly these twelve worker paths were changed/created:

- `src/living_world/cognition/llama_cpp_cognition_client.py`
- `src/living_world/runtime/broker.py`
- `src/living_world/runtime/preflight.py`
- `src/living_world/archives/model.py`
- `src/living_world/archives/catalog.py`
- `src/living_world/runtime/ollama_driver.py`
- `src/living_world/runtime/entrypoints.py`
- `src/living_world/cli.py`
- `tests/test_runtime_llama_cpp.py` (new central tests)
- `docs/npc_information_boundary.md` (new provider flow only)
- `docs/local_llm_setup.md` (new backend flow only)
- this report

The legacy `ollama` live archive mode, RuntimeService/controller ownership,
shared driver, real spawned broker, gateways and managers remain authoritative.
The typed payload-client protocol extends NPCCognitionClient, including its
provider_name property. Provider selection is an explicit `kind` inside that
existing mode. `provider_document` omits both new fields for Ollama and supplies
both for llama.cpp, preserving historical effective fingerprints. Setup validation
compares complete normalized nonidentity settings, including provider kind/path;
it cannot silently change a backend during preflight.

The llama client builds its complete existing structured chat request with output,
temperature, optional seed and disabled-thinking settings. Both the existing parent
preparation and spawned child measure this actual payload against 16000 characters.
No model file is opened during inference. Direct llama ProviderConfig callers supply
their local URL; fresh public CLI launches supply port 8080. Ollama retains 11434.

## Identity, bounds and trust

The spawned preflight uses bounded loopback HTTP GETs to `/v1/models` and `/props`,
requires the exact requested model ID and server alias, and resolves both local
paths for comparison. It opens a regular GGUF file read-only/nonblocking and streams
SHA256, comparing dev/inode/size/mtime_ns/ctime_ns before/after hashing and the
configured resolved path afterward. It repeats server properties and checks file
identity again. The parent's existing deadline/cancellation/reap logic bounds HTTP,
path resolution, reads and hashing together. Parent frame validation is closed and
checks exact model/canonical digest/pin independently without opening a child path.
Ollama `/api/tags` discovery remains unchanged; llama dummy tag digests are unused.

Configured absolute path spelling is retained in archive metadata/fingerprints;
resolution is only an identity check. This proves local file bytes plus the
server-reported alias/backing path, not cryptographic identity of resident GPU
memory. No model is copied into the archive. Tests use GGUF-prefixed byte fixtures
for identity mechanics, not valid inference models.

Safe existing error codes are retained. Missing file/model, invalid alias/path,
nonregular/bad GGUF or changing file, and digest mismatch are exercised. All seven
identity failure variants also retain truthful failed setup attempts when already
allocated. Parent malformed-frame, deadline/cancellation, process cleanup, response
limits and rejected oversized request bodies have focused evidence.

## Runtime, NPC and public-path evidence

Normal RuntimeService tests use actual fake-HTTP responses through genuine spawned
workers and action gateways, durable step ACK, cold resume and same-provider fork.
Both resource-loss and format-two work-blockage policies run through that service.
Offline replay compares exact source snapshots with forbidden transports and the
GGUF file removed; no provider call or file is needed. Separate actual-broker tests
retain validated decisions before commit, cold-fork reuse them without new requests
or duplicate request charges, and reject reuse across provider/file changes.

Public tests exercise run/serve prepared-launch defaults, option rejection before
allocation, exact resume inheritance, incompatible resume changes and provider-switch
fork pin/default cleanup. A real public `serve` subprocess proves paused startup,
HTTP single step, signal shutdown, paused cold resume and historical inspection.
A real headless public CLI run proves the same normal provider/runtime route.

Actual captured chat bodies are bounded and exclude private actor IDs, local file
paths and digest metadata. The existing filtered context, response parser, normal
action gateway and manager/world ownership remain unchanged; proposals cannot become
world truth without engine validation. Offline replay retains exact source provider
configuration rather than reconstructing a second runtime.

## Validation evidence

All commands used Python
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`
from the task checkout, with `PYTHONPATH=src` for pytest.

- RED: `python -m pytest -q tests/test_runtime_llama_cpp.py` — 2 failed as expected:
  actual missing ProviderConfig.kind dispatch and missing llama output-budget API.
- Initial focused implementation run: 35 passed, 1 fixture failure (explicit null
  seed in the new archive test); corrected the fixture to use actual effective data.
- Early central run: 41 passed, 4 fixture failures; corrected existing safe-code and
  journal-kind expectations and the canonical founders seed. A focused service/setup
  rerun passed 5 tests (40 deselected).
- Later central run: 48 passed, 1 startup-race fixture failure; corrected readiness
  polling to wait for populated live status after HTTP listener readiness.
- Named regression command:
  `python -m pytest -q tests/test_runtime_llama_cpp.py tests/test_llama_cpp_cognition_client.py tests/test_runtime_broker.py tests/test_runtime_preflight.py tests/test_runtime_ollama_driver.py tests/test_runtime_journal_replay.py tests/test_runtime_launch_request.py tests/test_runtime_serve.py tests/test_runtime_disturbances.py`
  — 285 passed in 161.30s, no warnings. This preceded final additional central
  cases and the normalized setup-keyset hardening; those final changes are covered
  by the final focused rerun below. Root full final-tree validation remains pending.
- An added historical-hash fixture initially omitted its required disturbance label
  (58 passed, 2 fixture failures); the fixture now supplies the existing policy label.
- Exact historical hashes are asserted for unscheduled Ollama, resource loss and
  format-two work blockage; new provider/file fingerprints are distinct.
- Final focused command:
  `python -m pytest -q tests/test_runtime_llama_cpp.py tests/test_llama_cpp_cognition_client.py tests/test_runtime_broker.py tests/test_runtime_preflight.py`
  — 96 passed in 66.39s, no warnings, on the final production/test tree. An immediately
  preceding run passed 95 tests before the added setup-kind/path regression.
  The final central module contributes 62 tests.
- Scoped `python -m ruff check` and `python -m black --check` over the eight
  changed production files plus central test module — passed; nine files unchanged
  by the final format check, no warnings. Formatting/lint issues introduced while
  adding the tests were corrected before these final checks.

## Root-owned pending gates and limitations

Independent contract/quality review, any scoped corrections/re-review, final full
make and separate examples, whitespace verification, canonical/CLI/source/wheel
serving checks, feature integration and repeated merged-tree gates remain root-owned.
No real-provider acceptance, Python 3.11 installed compatibility, source/wheel serving
certification or final whole-branch review is claimed by this worker.

Exact privileged raw per-inference request/response/model/backend/timing tracing is
a required subsequent bounded task and is neither implemented nor claimed here.
Backend/GPU/model profiles remain future backlog scope. No server/GPU management or
driver installation was introduced. No missing producer or scope amendment was needed.

## Root independent review and task gates

Fresh solhigh review of package SHA256
d5ebb4ce4e7754d2942c80b84d762505b6472aea8ff210ba635592d68b0e7048:
SPEC PASS / QUALITY PASS, NO SUBSTANTIVE FINDINGS.

- make VENV=.../task24/.venv: PASS2373tests/10existing deliberate skips,427.57seconds;
  actualChrome and39numberedexamples, no new warnings.
- Separate make examples after fullmake: PASS39.
- Canonical matrix: PASS26retained attempts with exact prior fullpayload hashes,
  fresh/resume1,3,4/terminalzero-step and all latestcompletecheckpoints readonly-opened.
- Archived CLI: PASS7normalattempts including2expectedfailed-uninitialized, exact
  childworld/cursors and uninterrupted/resume/fork equivalence, sourcebytesunchanged.
- Sourcepublicserve: PASS4normalattempts including1failedsetup, paused/Step/INT/TERM,
  exactcoldrestart/fork, authenticated historicalinspection, no credentialleak.
- Offlinewheel: PASS11resources/import/routes/CLI plus4actualwheel-serve attempts
  with same lifecycle/history checks.41normalattempts retained acrossroothelpers.
- Whitespace/cached checks and reviewed source/tests/pyproject equality: PASS.

No new native model calls or downloads. Integration must repeat gates. Exact private
inference traces and real BOTHprovider world acceptance remain required; no main/tag
actions, GPUprofile implementation or final wholebranch certification claimed here.

## Root merged validation and final task disposition

Deliverybb907a0 integrated cleanly. Repeated make: PASS2373tests/10existing deliberate
skips428.71seconds, actualChrome/39examples, no new warnings. Separateexamples PASS39,
whitespace/cached checks and reviewed source/tests/pyproject equality PASS. Repeated
canonical26readonly/exacttaskhashes,CLI7/sourceServe4/wheel11resources+actualServe4PASS;
41normalattempts retained including expected failures. Protected remote refs verified
unchanged, owner-local masterplan patch SHA unchanged. No nexttask/source expansion.

Backend task complete; exact private per-inference traces and admin analysis still
require bounded contracts/implementation before original BOTH-real-provider acceptance,
Python3.11installed compatibility and final wholebranch review. GPUprofiles futureonly.
