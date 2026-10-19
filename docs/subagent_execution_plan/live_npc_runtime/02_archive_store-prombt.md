# LN02 saved worker prompt

Work only in .worktrees/live-npc-ln02, codex/live-npc-ln02-archive-store.
Read AGENTS.md, 02_archive_store.md and root-supplied exact task brief. Your
requirements are the contract, including root architecture resolutions and exact
closed journal/config schemas. LN01 codec is available; preserve its interface
and bytes. Implement only the four named create paths and update the canonical
02_archive_store-report.md using focused TDD. No other source/docs/dependency
edits, full make, staging/commits/merge/push or subagent dispatch. Root owns final
architecture, independent review and full gates. Ask root about genuinely missing
choices before implementing them. Return a stable uncommitted diff and a concise
DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED status with focused evidence.

Root clarification: lifecycle stores exact strings initializing/paused/running/awaiting_model/pause_requested/provider_error_paused/stepping/completed/stopped/failed/interrupted; terminal completed/stopped/failed/interrupted. RuntimeState enum belongs to LN04.

Root clarification: queued control receipt refers to latest completed revision at admission (0 before initial). Persist nullable engine-only journal revision_context for exact read-side reconstruction; append/record uses current, commit entries new revision. Validate context/checkpoint references; closed payload keys stay unchanged.

Root-approved correction seam: internal nullable lifecycle.journal_sequence FK binds each attempt_finished mandatory effect one-to-one; validate state/reason correspondence, preserve public four-field lifecycle records.
