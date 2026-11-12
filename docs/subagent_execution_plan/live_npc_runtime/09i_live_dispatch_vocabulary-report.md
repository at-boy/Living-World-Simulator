# LN09i implementation report

Base: `53d48dd`. The live runtime recognizes the exact existing
`DISPATCH_ACTION_KEY` as structured vocabulary for a prepared option key and
for a response action key after `DecisionEngine` validates the original offer.
Both sites call the same helper in `feedback.py`. All other keys and all prose
fields retain their state-aware checks. The recorded proposal pathway is
unchanged.

## Evidence

- RED before production edits: the new archived live regression earned
  contactability through ordinary founders work and then failed in
  `FoundersFeedback.prepare` with `invalid_feedback` at revision 2. With only
  the offer-side change, it reached the broker response and failed with
  `unsafe_response`.
- GREEN: the live driver committed one dispatch and its creation event through
  the ordinary gateway. Both founders received the option. Fresh revalidation
  rejected the second proposal after the first created the dispatch. Offline
  journal replay matched the complete snapshot and both complete cursors after
  each tick and started no provider requests.
- The targeted pytest selection `-k 'public_trade_action or live_trade_'`
  passed all 12 cases. Negative cases cover option descriptions and targets,
  response target, rationale, speech and argument names and values, another
  identifier-shaped key, and unoffered keys and targets. These cases exercise
  the validators with malformed inputs and leave production authority intact.
- The combined pytest run for `test_runtime_ollama_driver.py`,
  `test_runtime_founders_feedback.py`, `test_runtime_journal_replay.py`,
  `test_runtime_recorded.py`, `test_recorded_proposal_tapes.py` and
  `test_runtime_disturbances.py` passed 320 tests before the final focused
  assertions for fresh dispatch revalidation. The targeted run above includes
  those assertions. Both runs used the Task 24 Python environment and
  `PYTHONPATH=src`.
- Ruff and Black checks passed for the three touched Python files.
  `git diff --check` passed.

## Self-review and scope

Worker edits are limited to `feedback.py`, `ollama_driver.py`,
`test_runtime_ollama_driver.py`, the live flow addendum in
`docs/npc_information_boundary.md`, and this report. Fresh offers, actor
eligibility, resolver ordering and dispatch ownership stay with the existing
engine and managers. The change adds no perception, hidden data, memory, prompt
or archive schema. The live-path regression uses synthetic provider proposals.
The saved native source, native acceptance, full repository gates, independent
review and Git integration are root-owned.

## Root native proof and independent review

Independent spec and quality review: PASS, no substantive findings.
Worker final six-file aggregate on frozen source: 320 passed in 85.93 s.
Frozen 358-file SHA256 eed875df105f8f4281c56b556a19fc071f06ccdffc88e766aab2241a79e8ef6e.

The original failed Ollama source restores read-only at tick 4 and prepares the
real public trade offer for both founders, preserving all original bytes and
mtimes. On the reviewed source a fresh native Ollama stock run reached the
founding deadline at tick 13 (26 calls, engine founding failure), with 18 trade
offers actually sent. Exact offline replay passed. Native llama.cpp stopped
safely at tick 4 on an unoffered target; its committed history replayed exactly.
Applied native work interruption remains unmet on both. See
[the follow-up native evidence](../../orchestrator_handoff/live_npc_native_acceptance_followup_2026_11_12.md).

## Root task validation

Quiet full validation (session 38375, prefix ln09i-task) passed all 13 jobs
on unchanged reviewed source. `make`: 3041 passed, 10 existing skips,
763.32 s, actual Chrome and 40 examples; independent examples 40 and
whitespace passed. Canonical fresh/resume and zero-step, CLI/Serve, wheel/assets,
native trace reader, protected analysis APIs/browser/CLI and exact exports passed.
Python 3.11.2 offline-installed current wheel passed import/entrypoint, canonical
matrix, Serve/failure setup, example040 and exports. uv hardlink fallback to copy
was the only installation warning. Chrome using the task wheel inspected the
native 13-tick Ollama source at revisions 0 and 13 with nine protected HTTP
requests; source contents and metadata were preserved, no attempt was created and
no credential persisted.

Reviewed task ready for feature integration. Original LN09 work interruption
and unattended llama.cpp deadline outcome remain open. No release/tag changes.
