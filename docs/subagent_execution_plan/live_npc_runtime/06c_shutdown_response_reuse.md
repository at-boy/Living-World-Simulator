# LN06c — Reuse validated responses across same-world shutdown checkpoints

Status: owner-authorized bounded correction to original LN06 recovery, discovered
while preparing LN07 consumers. Reviewed LN06b delivery5a3f58a/integration2da047f
remains preserved; this correction does not replace its architecture or reviews.
Root reproducer in current SDD workspace/ln07-shutdown-reuse-probe/results.json:
base0 -> RunController.close checkpoint1, exact same world/cursors; child fork from1
makes2 fake provider calls despite2 validated parent responses at0 (expected0).

## Scope and invariants

Modify ONLY src/living_world/runtime/ollama_driver.py,
tests/test_runtime_ollama_driver.py and this -report.md. Root owns plan/prompt/common
docs/VCS. No controller/archive/feedback/broker/CLI/other source/test changes.
Python>=3.11, strict types, ordinary gateway authority/NPC boundaries, immutable
journal entries, exact world/cursors, no raw provider/CoT. No dependency/provider
calls, main/milestone/tag/owner-edit/branch deletion.

## Exact decision

RunController.close creates an operational final checkpoint even when live
finalization leaves complete snapshot, semantic driver cursor and feedback cursor
unchanged. Selected parent revision1 is semantically identical to response base0.
A revision number alone must not invalidate full actor/input/config identity.

Current-attempt reuse remains STRICT actual base_revision equality. For an EXTERNAL
verified parent source only, a request base revision <= selected source revision may
match if source.checkpoint(request.base_revision) has EXACT snapshot, semantic driver
cursor and feedback cursor equal to the selected source checkpoint. Use existing
_same_checkpoint comparison (intentionally ignores operational revision). No loose
world subset/normalized state/tick-only comparison. Missing/invalid source checkpoint
fails closed, not a best guess. No source reads beyond selected revision for alias
eligibility; source journal records remain limited by the verified sealed boundary.

Keep all existing actor/source_tick/request/input/config fingerprint/decision checks,
validated/imported-only eligibility, committed-response preference otherwise latest,
parent continuity/cycle guard/seal verification/postseal exclusion. Config changes or
any semantic cursor/world change still invalidate reuse. Never mutate source archive
or its rows; import response_reused with NEW local request ID/base and actual verified
source attempt/request/seal, not relabeled request_started. Imports count0HTTPstarts.
Failure/uncertain source requests at an eligible same-world old base still pause first
and require explicitRetry; no automatic inference/retry/fallback. No local request
identity or action audit relaxation. Effects still execute once via ordinary gateway
and complete tick commit. No public API change required; private lookup may accept
source archive/selected checkpoint or a prevalidated eligible revision set.

## Required TDD and proof

1. Add RED through actual public RunController pause/close + catalog.fork(latest):
   prepare/save validated decisions without tick effects, pause/discard candidate,
   close controller; prove final revision advances but complete world/cursors exact.
   Restart child at latest checkpoint and demand ready with0new provider calls,
  2local response_reused rows/new IDs/base0,0request_started, source bytes unchanged
   by child work. Before correction expect2newcalls. Use deterministic fake IO only.
2. GREEN with smallest source-lookup change. Apply child proposals/commit once and
   prove no duplicate actions/work charges; a later real tick remains a real tick.
3. Pin equivalent-base failed/pending request still requiresRetry; changed world,
   driver/feedback cursor/config cannot alias; current-attempt distinct base remains
   strict. Existing sealed/fork/config/replay tests must retain assertions.
4. Focused final: PYTHONPATH=src "$TASK_PY" -m pytest
   tests/test_runtime_ollama_driver.py tests/test_runtime_journal_replay.py
   tests/test_runtime_controller.py -q. Scoped Ruff/Black/whitespace on twoPythonfiles.

Worker records actual RED/GREEN/counts/warnings/changes/limitations in own report,
no VCS/subagents/fullmake/examples/install. Root independent read-only SPEC/QUALITY
review, bounded corrections/rereview, task/merged make,separateexamples,whitespace,
exact canonical matrices before commit/integration. Do not claim full live CLI or
actualOllama acceptance. LN07a is parallel but disjoint; do not touch its checkout.
