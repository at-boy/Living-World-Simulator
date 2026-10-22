# LN07b implementation report

Implemented the bounded producer stage in the supplied isolated checkout. This
report records worker evidence; independent review, full repository gates, VCS,
integration, aggregate original Task 7 acceptance and LN07c remain root-owned.

## Result and boundaries

- `archives/catalog.py`: immutable setup reservation/failure documents, current-root
  and current-thread lease checks, one-time effective publication, shared intent
  validation on completion/open, and read-only pending/failure/partial discovery.
  Narrow allocation/lock/publication helpers preserve ordinary reserve/fork behavior.
- `archives/assets.py`: when SQLite is absent, validate retained reconstruction inputs
  against the valid setup intent in the reference's catalog. Existing hash, role,
  loader, path, content-addressed and source normalization checks remain active.
- `perception/local_llm_http.py`: GET and POST share bounded request/read/decode guards.
  Added finite float decoding so exponent overflow cannot introduce infinity.
- `runtime/broker.py`: extracted existing owned-process termination/join/kill/close
  policy for reuse; existing broker API is unchanged.
- New `runtime/preflight.py` and runtime exports: fresh spawn per GET, authoritative
  provider defaults, fixed model/digest matching, bounded atomic result frame, parent
  wall deadline/cancellation and owned-child cleanup. No archive mutation occurs here.
- Tests modified: `test_run_archive_catalog.py`, `test_local_llm_http.py`.
  New tests: `test_runtime_preflight.py`. Existing broker/client tests were exercised.
- No other source, domain, world/schema, driver/controller, CLI, dependency or common
  documentation changes. No install, real Ollama use, external research, VCS mutation,
  full `make`, or examples run by worker.

## Focused TDD evidence

Interpreter throughout:
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
Tests used `PYTHONPATH=src` and `-m pytest`.

- Catalog setup slice: `tests/test_run_archive_catalog.py -q -k setup` RED 9 missing
  setup methods; full catalog GREEN 69 after implementation.
- GET transport slice: `tests/test_local_llm_http.py -q -k get_uses` RED 1 missing GET;
  HTTP plus broker GREEN 20 after shared helper extraction.
- Spawn/model slice: `tests/test_runtime_preflight.py -q` RED 18 missing module;
  initial GREEN attempt had 17 passing and 1 malformed-digest classification failure.
  Corrected archive exception classification; GREEN 18.
- Defaults/input inspection: targeted catalog RED 2 (unrequested provider default
  accepted, pending retained tamper ignored); full catalog GREEN 71.
- Unicode/finite JSON: targeted HTTP/preflight RED 2 (control character and numeric
  exponent overflow); GREEN 2 after validation fixes.
- Final self-review regressions: targeted RED 3 (missing completed retained manifest,
  duplicate pending identity, raw local worker setup failure); GREEN 3 after fixes.
- Additional passing integration/regression coverage includes actual setup-owner
  process death; fault between attempt metadata and SQLite publication; immutable
  same-code failure and rejected divergence; lease/root/thread/config/timestamp
  parity; namespace/tag/pinned digest matching; safe IPC shape/size errors; actual
  GET guards; trickled headers/body and hung requests; pre-set and in-flight parent
  cancellation; injected KeyboardInterrupt after actual spawn; and retained inputs
  present before the first provider GET.

## Final validation

`PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_preflight.py
 tests/test_run_archive_catalog.py tests/test_local_llm_http.py
 tests/test_runtime_broker.py tests/test_ollama_cognition_client.py -q`

Initial handoff: PASS, 136 tests in 24.81 seconds; no warnings reported.
After review correction 1: PASS, 153 tests in 25.37 seconds; no warnings reported.

Scoped Ruff `check`: PASS. Black `--check`: PASS, nine files unchanged.
Both commands cover the nine modified/new Python files.
Scoped whitespace check asserts final newline and no trailing whitespace in each of
those files: PASS. Root retains authoritative `git diff --check` and full gate ownership.

## Self-review and limits

Reviewed the actual changed publication, input, transport and worker code. Corrected
safe error classification, default preservation, Unicode control handling, finite
JSON exponent overflow, missing retained manifest validation, duplicate pending
identity handling, and local setup failure sanitization. Restored the legacy lock
creation failure boundary while factoring allocation/publication. Requested intent
is never rewritten; completed configuration is published once, and partial final
publication is never repaired or reconfigured.

All setup evidence remains engine-only. The child receives only resolved provider
configuration and its owned result path. IPC retains only selected name/digest or a
fixed safe failure code. No world state, NPC context, archive reference or retained
input paths cross that boundary. No deterministic generation or real-model success
claim is made. Changed-provider fork setup and entrypoint wiring are outside LN07b.

One fault-injection test initially failed because its process-method monkeypatch
itself interfered with spawn serialization; corrected the test to interrupt the
parent clock after real spawn, leaving the real process unmodified. The first independent review identified the publication-boundary issue below.


## Independent review correction 1

Reviewer finding: an owned setup whose SQLite path existed before schema/metadata
initialization was incorrectly reported failed/archive_invalid. The initial injected
fault stopped before SQLite creation and did not exercise this boundary. Root amended
the contract/prompt before this correction to require immutable completion evidence.

Read the complete amended contract/prompt and applied the receiving-code-review
workflow. Added genuine RED coverage for empty SQLite, schema-only SQLite, and valid
SQLite before completion evidence, plus the required completion document/tamper matrix:
11 failures. Implemented the amendment; the same targeted command passed 11 tests.

- `catalog.py`: publishes closed `setup_complete.json` only after ordinary metadata
  and SQLite creation/close succeed. Its canonical configuration SHA256, format,
  identity and fields are checked during setup-backed opens. Pending completion or
  failure cannot overwrite it. Unmarked publication is initializing while owned,
  failed/archive_incomplete when unowned with final paths, and cannot open/reconfigure.
  Present reservation metadata must still match intent, parent/error and timestamp.
- `assets.py`: before completion evidence exists, retained input identity uses the
  validated setup intent and validates any present reservation, without reading a
  partially initialized SQLite database. Marked archives use ordinary archive config.
- `test_run_archive_catalog.py`: 17 additional cases exercise the three publication
  windows, byte/mtime-identical inspection and safe open rejection, no fabricated
  revision/tick/repair/retry, marked marker/archive/config/failure corruption, and
  unmarked metadata/input tampering. Tampered metadata remains archive_invalid.

Final focused command above: PASS, 153 tests in 25.37 seconds. Scoped Ruff: PASS;
Black --check: PASS, nine Python files unchanged. Correction whitespace: PASS for
three Python files plus this report. This round changed only catalog, assets, their
catalog tests and this report. The root-owned staged baseline was not modified;
no VCS operations, full gates, installs, subagents, or other-checkout writes occurred.

Self-review: verified marker absence is authoritative even when both final files
exist; any published marker prevents a second publication; malformed marked evidence
fails closed; valid unmarked files remain analyzable through retained inputs; ordinary
archives without setup intent retain their existing behavior. No outstanding
worker-known issue after correction; independent re-review remains required.

## Root task acceptance

Independent review found one P2 incomplete SQLite publication classification issue.
Root confirmed it, amended the exact contract and saved prompt before correction,
and requested the completion marker. Scoped re-review: SPEC PASS / QUALITY PASS,
one addressed / zero open, NO SUBSTANTIVE FINDINGS.

- Full task `make` with task24 VENV: passed 1,876 tests / 10 existing skips,
  lint/format, actual Chrome and 39 examples.
- Separate task `make examples`: passed 39 examples.
- Exact canonical matrix: all three hashes, duplicate fresh runs, resume 1/3/4 and
  terminal zero-step checks passed; 26 CLI attempts persist readable checkpoints.
- Staged/unstaged whitespace checks passed; reviewed source unchanged by full make.

Evidence in current-plan ignored SDD workspace: ln07b-review-1.diff,
ln07b-fix-1.diff, ln07b-review-final.md, ln07b-task-make.log,
ln07b-task-examples.log, ln07b-task-matrix/results.json and retained state.
Delivery and feature merged gates follow; no service/browser/model acceptance claim.
