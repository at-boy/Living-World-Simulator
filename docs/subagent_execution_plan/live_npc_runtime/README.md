# Live NPC runtime execution

Owner approved the [design](../../superpowers/specs/2026-10-19-live-npc-runtime-design.md)
and [plan](../../superpowers/plans/2026-10-19-live-npc-runtime.md) October19,2026.
Integration: codex/live-npc-runtime; no main/tag/milestone changes.

| Task | Current status | Material |
| --- | --- | --- |
| LN01 | Complete; delivery5f64056; task/merged gates passed | [plan](01_world_snapshot_codec.md), [saved prompt](01_world_snapshot_codec-prombt.md), [report](01_world_snapshot_codec-report.md) |
| LN02 | Complete; delivery099da9a; task/merged gates passed | [plan](02_archive_store.md), [saved prompt](02_archive_store-prombt.md), [report](02_archive_store-report.md) |
| LN03 | Complete; deliverye3d9faf; task/merged gates passed | [plan](03_attempt_lifecycle.md), [saved prompt](03_attempt_lifecycle-prombt.md), [report](03_attempt_lifecycle-report.md) |
| LN04 | Complete; delivery906d23f; task/merged gates passed | [plan](04_safe_controller.md), [saved prompt](04_safe_controller-prombt.md), [report](04_safe_controller-report.md) |
| LN05 | Complete; delivery64efb1e; task/merged gates1652/10,39examples passed | [plan](05_npc_feedback.md), [saved prompt](05_npc_feedback-prombt.md), [report](05_npc_feedback-report.md) |
| LN06a | Complete; delivery6469a38; reviewed task/merged gates1722/10,39examples passed | [plan](06a_journal_recovery.md), [saved prompt](06a_journal_recovery-prombt.md), [report](06a_journal_recovery-report.md) |
| LN06b | Implementation underway; review/full gates pending | [plan](06b_live_driver.md), [saved prompt](06b_live_driver-prombt.md), [report](06b_live_driver-report.md) |
| LN07–LN09 | Authorized sequence, not yet dispatched | See the master plan; materialize each exact contract just before execution. |

Execution uses one bounded worker and an independent reviewer per nontrivial task,
root-owned architecture/gates/integration, durable checkouts and truthful reports.
Stop before five-hour remaining usage drops below10%, with checkpoint and workers
stopped. Preserve the owner-local master-plan text edit separately from task work.

Usage checkpoint after LN02. No active worker; next LN03 attempt lifecycle.
Retain current-plan SDD evidence and all checkouts. Last pre-checkpoint usage16%remaining.

Owner resumed October21; LN03 contract prepared from0d04c1b. Earlier usage checkpoint is historical.
