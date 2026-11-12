# LN09i — Preserve the public trade action in live NPC decisions

## Authorization and observed failure

Continuation of the owner's November 12 authorized native acceptance and the
approved LN09 rule to isolate any prerequisite defect in its owning contract.
Base: `53d48dd`. This task does not change the work-interruption requirement.
Real unattended Ollama source `ac2b665df4944fe896a86c344de1d4fa` committed tick 4,
then returned `tick_failed` before the next request. Detached, read-only restore
and production `FoundersFeedback.prepare` reproduced `invalid_feedback`; the
underlying exception at feedback's option-key check rejected the engine-owned
public action key `dispatch_external_trade` as identifier-shaped prose.
The same mistaken check exists on the live response action key, shared with
offline replay. Recorded proposal handling already distinguishes this public
structured key from prose. Do not modify the recorded path.

## Exact change

- Recognize only the exact existing `DISPATCH_ACTION_KEY` constant as structured
  public vocabulary at the live option-key validation site and at the live
  response action-key site. Implement one small runtime helper in `feedback.py`
  reused by `ollama_driver.py`, following the existing recorded exception.
- Response-side recognition occurs **after** ordinary `DecisionEngine` checks
  the original offered key and target. It grants no authority: existing fresh
  offers, actor eligibility, `NPCActionResolver` and dispatch manager still
  decide effects. No offered targets/handlers/order/schema/response changes.
- All other keys go through the existing prose check. All option descriptions,
  target labels, decision speech, request rationale, argument names/values and
  NPC context still go through unchanged state-aware validation. The public key
  remains forbidden in those prose fields; no prefix or global exemption.
- Engine truth remains exact references, inventories, dispatch IDs/quantity,
  actor IDs, work and lifecycle. The engine publishes only the fixed public
  action key plus already filtered labels/descriptions when ordinary offers
  permit. No new perception, cognition record, memory, hidden field, actor
  access or raw state. Live and sealed replay reuse the same validation.
- No archive schema, configuration, model prompt, feedback retention, data
  migration, compatibility policy, broader product behavior or other refactor.

## Worker boundary

Modify only:
- `src/living_world/runtime/feedback.py`
- `src/living_world/runtime/ollama_driver.py`
- `tests/test_runtime_ollama_driver.py`
- `docs/npc_information_boundary.md` (short addendum near live provider flow)
- create `docs/subagent_execution_plan/live_npc_runtime/09i_live_dispatch_vocabulary-report.md`

Root owns this contract/prompt, common docs (CHANGELOG, journal, backlog,
continuation brief), and the follow-up evidence document
`docs/orchestrator_handoff/live_npc_native_acceptance_followup_2026_11_12.md`.
Root owns Git, actual native model servers, validation and integration. Do not run native models, write outside those five
paths, make Git changes, or run full gates. No cross-worktree data fixtures
committed; saved native source is root evidence, not a dependency of tests.

## Verification

- [x] Meaningful RED first: canonical archived live path earns ordinary trade
  eligibility via engine work/gateway, prepares the genuine dispatch offer,
  accepts a vocabulary-valid proposal through the existing gateway and commits
  dispatch evidence. Include exact complete world/driver/feedback replay equality
  using existing archive/driver test utilities. Synthetic test proposals are
  regression evidence only. No patches to the real information boundary or
  authority in tests.
- [x] Show the key remains forbidden as prose (e.g. option description/target
  and returned rationale/speech/argument) and rejected when not offered; use
  parameterization and targeted checks where helpful. Other ID-like action keys
  stay rejected. Preserve stale revalidation and existing recorded tests.
- [x] GREEN: focused changed tests plus affected runtime feedback/driver,
  recorded proposals and disturbance regressions; scoped Ruff and Black.
  Report meaningful RED reason, GREEN counts, file boundaries and limits.
- [x] Freeze worker paths and independent spec/quality review. Root actual
  previously saved tick-4 source verifies preparation read-only after fix;
  native unattended campaigns and interruption probes remain separate.
- [x] Root `make`, separate `make examples`, whitespace, retained compatible
  package/CLI/replay/browser gates. Then commit/push task and repeat merged
  validation before feature push. Preserve all branches/worktrees and owner edit.

No current production release, main merge, tag, or future-vision implementation.
