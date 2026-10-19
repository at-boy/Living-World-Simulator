# Live NPC runtime execution

Owner approved the [design](../../superpowers/specs/2026-10-19-live-npc-runtime-design.md)
and [plan](../../superpowers/plans/2026-10-19-live-npc-runtime.md) October19,2026.
Integration: codex/live-npc-runtime; no main/tag/milestone changes.

| Task | Current status | Material |
| --- | --- | --- |
| LN01 | Complete; delivery5f64056; task/merged gates passed | [plan](01_world_snapshot_codec.md), [saved prompt](01_world_snapshot_codec-prombt.md), [report](01_world_snapshot_codec-report.md) |
| LN02–LN09 | Authorized sequence, not yet dispatched | See the master plan; materialize each exact contract just before execution. |

Execution uses one bounded worker and an independent reviewer per nontrivial task,
root-owned architecture/gates/integration, durable checkouts and truthful reports.
Stop before five-hour remaining usage drops below10%, with checkpoint and workers
stopped. Preserve the owner-local master-plan text edit separately from task work.
