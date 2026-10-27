# LN09d implementation report — capture producer

Status: implementation frozen for root independent review; root owns approval,
full validation and Git transitions. Producer APIs only; no archive driver,
reuse/replay, admin, offline export or real-provider acceptance is claimed.

## Scope and behavior

The seven authorized paths contain immutable prepared request/response evidence,
an optional transport observer, a durable bounded self-contained spool, bound
broker lifecycle and explicit acknowledgement, focused tests, boundary wording
and this report. No dependencies, other checkout files, model servers, model
files or downloads were used. HTTP fixtures ran locally without escalation.

- `inference_trace.py` builds original sorted compact ASCII provider bytes for
  both providers and validates/freezes closed LN09c metadata. Empty, incomplete
  prefix and unavailable bodies remain distinct. Parent settlement fills only
  parent UTC/monotonic fields without deriving duration from wall clocks.
- `local_llm_http.py` preserves the default paths and adds original-byte POST
  plus frozen observations before opening, after headers, at first client byte,
  on bounded prefixes and at observed end. Invalid bytes, HTTPError bodies,
  oversized max+1 prefixes, truncated Content-Length, timeout and slow drip are
  captured. Synchronous observer failure is fatal `worker_failed`. The observed
  path checks a monotonic total deadline between reads, with socket timeout
  bounding a currently blocked read. Complete response digest semantics remain
  separate from prefix hashes.
- `inference_spool.py` uses private exclusive job leaves, regular nonsymlink
  bounded reads, duplicate-free closed frames, strict canonical base64, request
  digest and observed-body validation. Exclusive partial writes are flushed and
  fsynced before atomic replacement and directory fsync. Old published evidence
  survives an interrupted replacement. Partial files are never evidence.
- `broker.py` preserves `start` and old positional results/unbound behavior.
  Bound spawn receives primitive original bytes and canonical metadata JSON,
  never frozen mapping proxies or parent engine objects. The adapter validates
  rebuilt payload/URL/timeout and sends original prepared bytes. Parent reaps
  before snapshot harvest, retains timeout/cancel precedence over complete
  bodies, caches settlement and rejects successful real decisions without
  complete matching 2xx evidence. Corruption becomes safe unavailable failure
  and remains retained. Crash-prefix evidence is retained without inventing a
  finished worker duration. Ack revalidates unchanged harvested evidence and
  removes only the owned job leaf after caller-import promise.
- The root amended task and saved prompt for optional `acknowledge_trace(...,
  result=...)` before implementation: real workers require their cached settled
  result/reaping; no-super injected brokers can provide matching result evidence.
  This does not bypass real-worker checks. Binding identities remain single-use.
- Boundary wording authorizes privileged bounded raw retention and explicitly
  leaves public runtime archive wiring/admin views to later tasks.

## TDD evidence

Runtime for all commands below:
`VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`;
commands ran in this task worktree with `PYTHONPATH=src` where required.

1. RED: `$VENV/bin/python -m pytest -q tests/test_runtime_inference_capture.py`
   — 10 failed, expected missing inference models/spool, observer POST and binding.
2. First GREEN: same command — 10 passed, 5.21 s, including both actual spawned
   provider variants receiving exact prepared bytes through fake loopback HTTP.
3. Expanded RED: same command — 3 failed, 21 passed, 7.10 s. Truncated
   Content-Length was incorrectly marked complete; optional root-approved ack
   result was still absent. Both were corrected.
4. Expanded GREEN: same command — 30 passed, 9.95 s.
5. RED: same command with `-k 'binding_cannot or invalid_bound_result'`
   — 2 failed, 30 deselected, 1.14 s. Rebinding after injected ack and deleting
   corrupt bound result evidence were corrected. An intermediate correction run
   had 1 failed, 1 passed, 30 deselected because corrupt-result retention was not
   yet applied to the formatted exception branch. GREEN: 2 passed, 30 deselected,
   1.10 s.
6. Additional capture coverage GREEN: complete capture file — 47 passed, 20.32 s.
7. RED: capture file with `-k crashed_worker` — 1 failed, 47 deselected, 1.13 s;
   missing result publication after process crash discarded valid prefix evidence.
   It now differs from a present corrupt result. GREEN with
   `-k 'crashed_worker or invalid_bound_result'` — 2 passed, 46 deselected, 1.91 s.
8. RED: capture file with `-k changed_valid` — 1 failed, 48 deselected, 1.13 s;
   ack accepted a valid but changed snapshot after settlement. Ack now compares
   against harvested worker evidence. GREEN with
   `-k 'changed_valid or bound_spawn_exact'` — 3 passed, 46 deselected, 2.73 s.

The earlier combined compatibility command passed 140 tests in 72.23 s with
24 capture tests then present. Final current-tree focused command and result
are recorded below after completion.

## Final focused validation

`PYTHONPATH=src $VENV/bin/python -m pytest -q
 tests/test_runtime_inference_capture.py tests/test_runtime_broker.py
 tests/test_local_llm_http.py tests/test_ollama_cognition_client.py
 tests/test_llama_cpp_cognition_client.py tests/test_runtime_llama_cpp.py
 tests/test_runtime_ollama_driver.py`

Result: **165 passed in 87.22 s** (49 capture tests plus existing compatibility
coverage); no warnings/failures in the final run.

Scoped Ruff and Black check both passed for the five Python paths. Formatting
passes initially found and corrected style issues; no unresolved style failure.
Root performs authoritative whitespace and full repository/task/merged gates.

## Coverage and limits

Tests include actual spawned both-provider success, raw invalid UTF8/JSON/envelope,
HTTPError, empty and max+1 response, Content-Length truncation, prefix/socket timeout,
headers-only timeout, slow-drip total deadline, fatal callbacks at multiple stages,
private modes, partial-only crash, atomic/fsync failure, previous-frame retention,
duplicate/oversized/digest/base64/null/nonfinite/symlink/nonregular frame rejection,
real crash-prefix salvage, close and deadline after complete response, cancellation
and reap-before-harvest, process start failure, no-super injected binding/ack,
ack-before-settlement, corrupt result/snapshot retention, successful real-result
rejection for missing/incomplete/non-2xx/mismatched evidence, unchanged-snapshot ack,
request/config mismatch and idempotent settlement. UTC rollback is accepted without
negative derived durations. Unknown stage timestamps remain null.

No real models/network endpoints beyond test loopback fixtures were used.
Durability tests exercise fsync/replacement behavior and failure injection, not a
physical power-loss test. Capture overhead is part of observed client pipeline
intervals. A killed worker may leave earlier prefix evidence or unavailable bytes;
no missing bytes or stage completion is inferred. Full repository validation and
independent review remain root responsibilities. Consumers are deliberately absent.

## Independent review correction round 1/5

Root confirmed both P2 findings and authorized only their bounded corrections.
No scope expansion, Git operations, subagents or full gates were performed.

1. **Plain-broker pre-dispatch ack bypass:** absent inherited-start bookkeeping
   no longer suffices for the injected-broker exception. Ack now also requires
   the concrete class to genuinely override `start`. Plain brokers and subclasses
   inheriting the original `start` reject supplied settlement before dispatch.
   Real inherited-start jobs still require cached settlement, matching supplied
   result and reaping. Existing no-super fixtures now explicitly override `start`
   to represent the contracted injected broker rather than merely skipping init.
2. **Directory-entry durability:** spool creation creates missing ancestors one
   at a time, syncing each newly created directory's parent before creating the
   next descendant. It also syncs the root after exclusive job-leaf creation.
   Parent sync descriptors use directory/nosymlink flags and close even on
   failure. Any creation-sync failure returns the fixed safe failure, does not
   register a binding or dispatch a worker, and preserves created/existing paths
   without attempting cleanup.

RED command:
`PYTHONPATH=src $VENV/bin/python -m pytest -q
 tests/test_runtime_inference_capture.py
 -k 'plain_broker_cannot or create_spool_syncs or spool_creation_fsync'`

Result: **7 failed, 49 deselected in 0.39 s**, expected missing pre-start
protection and missing directory-entry fsync/failure handling.

Initial targeted GREEN, including injected compatibility:
`PYTHONPATH=src $VENV/bin/python -m pytest -q
 tests/test_runtime_inference_capture.py
 -k 'plain_broker_cannot or create_spool_syncs or spool_creation_fsync or no_super or binding_cannot'`

Result: **9 passed, 47 deselected in 0.28 s**. An additional new-root-only case
was then added alongside existing-root and new-root/new-ancestor ordering cases.

Final covering GREEN:
`PYTHONPATH=src $VENV/bin/python -m pytest -q
 tests/test_runtime_inference_capture.py tests/test_runtime_broker.py
 tests/test_local_llm_http.py`

Result: **77 passed in 24.95 s**, including all 57 current capture tests and
20 existing broker/HTTP tests. No warnings/failures in the final run.
Scoped Ruff and Black check passed for the three changed Python paths.
Four correction-round paths (those three plus this report) have no trailing
whitespace. Code is frozen again for root independent re-review and full gates.

## Root review and task validation

Independent astrahigh review identified two P2 issues; original worker correction round1
addressed both, original reviewer scoped re-review NO SUBSTANTIVE FINDINGS. Final
SPEC/QUALITY PASS. Fixpkg914eb0d8f5221b85960ce8b2c6a0ad0d46e2b9762e14b7ae61f9423b65486887.
Root make passed2526 tests/10existing deliberate skips,454.12s, actualChrome/39examples;
separate make examples passed. Exactcanonical26/latestcomplete read-only archives/prior
payloadhashes/CLI7/sourceServe4/wheel11+actualServe4 passed;41normalattempts retained.
Reviewed source/tests/pyproject SHA720a35b26006ce29d556e1a8f49670a23c87824ec1ccbadfcf769c98667af29f
unchanged after formatters; whitespace/cached checks passed. Logs ln09d-task-* retained
in ignored root evidence. Feature integration/repeatedgates pending. Consumers absent.

## Root merged validation and resume checkpoint

Owner resumed with fresh allowance. Pending merged make session40117 exited0:2526
passed/10existing skips450.51s, actualChrome/39examples. Separate make examples passed.
Canonical26/read-only archive/priorhash, CLI7/sourceServe4/wheel11+actualServe4 gates
all passed,41normalattempts retained. ReviewedsourceSHA720a35b26006ce29d556e1a8f49670a23c87824ec1ccbadfcf769c98667af29f
and ownerpatchSHA unchanged; whitespace/cached checks passed. Delivery2781dd3 branch
and checkout preserved/pushed. Root finalizes noff featuremerge/push after this record.
No new model/server run or trace-consumer completion claim. Next9e archive wiring,
9f admin/offlineanalysis/export, realBOTHprovider acceptance and wholebranch review.
