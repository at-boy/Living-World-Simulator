# Native NPC acceptance follow-up — November 12, 2026

This supplements the earlier LN09h native report. No decisions, work, labor,
offers or checkpoints were synthesized to satisfy native acceptance.

## Before the live trade fix

Evidence was captured on feature `53d48dd` (the same 358-file validated source
as `e454722`). All experiments used ordinary broker inference, canonical
founders and bounded request/tick limits. Models were already installed. Ollama
used isolated cache directories referencing existing blobs, preserving the
original model store. Servers bound to owned loopback ports; all nine owned
processes were verified exited and both ports closed on the host.

| Backend and check | Result |
| --- | --- |
| llama.cpp, original Qwen3.5 4B with reasoning budget 256 | Work boundary `no_eligible_work`; large shelter needs three workers. Exact offline replay passed. |
| Ollama, Llama 3.2 | Invalid response before first tick: non-null action with no offers, plus empty speech. |
| llama.cpp, cached Qwen3.5 2B | Server refused the GGUF's rope dimension layout. No simulation attempt. |
| Ollama, cached Qwen3.5 2B | Reached boundary with no eligible work; no work orders in the final saved world. |
| llama.cpp, cached Llama 3.2 | Invalid response before first tick: non-null action when no actions were offered. |
| Both, original models with temperature .35 and provider seed 43 | Still `no_eligible_work`. Canonical world seed and conditions unchanged; config retained through public runtime service, stock cold child and exact offline replay. |

The unattended public CLI campaigns requested up to 16 ticks and 40 model calls:

| Provider | Outcome | Source | Offline replay |
| --- | --- | --- | --- |
| Ollama Qwen3 4B | 4 committed ticks, 8 calls, exit 5 `tick_failed`. | `ac2b665df4944fe896a86c344de1d4fa` | `ee329c7c875a4156b44e18bd9871bd12` |
| llama.cpp Qwen3.5 4B | 4 committed ticks, 9 calls, exit 6 `invalid_response`: key was offered but target was not. | `f588291493f54610a78fae37f53d0f63` | `8ce1fdc52a7e4fb4abdbb42518dbe85f` |

Both replayed exact committed worlds, events and cursors with their providers
stopped, preserving source bytes and modification times. The llama.cpp rejection
is ordinary model-output validation. The Ollama stop happened before a tick-4
request and exposed a runtime defect: once the camp contacted the homeland,
production feedback rejected the exact public key `dispatch_external_trade`
as if it were a private identifier. A detached read-only restore reproduced
`invalid_feedback`, including the original exception at the option-key check.

The corresponding live response check treated that key as prose too. LN09i
isolates that prerequisite defect. Recorded proposal handling already recognizes
the structured public key. The fix preserves the existing offered key/target
check, gateway, execution eligibility, all prose filters and replay semantics.

Evidence directories are `ln09-native-*` under the feature worktree's ignored
`.superpowers/sdd/2026-10-19-live-npc-runtime/`, retaining model process identity,
logs, source provenance, archives and verification summaries. Prior unsuccessful
attempts remain unsuccessful. Neither backend has yet applied a native work
interruption at the prescribed boundary.

## After the reviewed live trade fix

Frozen source SHA256 `eed875df105f8f4281c56b556a19fc071f06ccdffc88e766aab2241a79e8ef6e`
across 358 source/test/example/packaging files. A read-only restore of the
original Ollama tick-4 checkpoint now prepares the public trade option for both
holders. Source bytes and modification times match before and after.

Both fresh unattended stock CLI runs used the canonical founders preset,
16-tick/40-request bounds and the opt-in founders empty-arguments contract.
Ollama used its original cached Qwen3 4B with the same request limits and a
five-minute server keep-alive; llama.cpp used the original AMD/Vulkan0 Qwen3.5
4B GGUF with reasoning budget 512 and maximum output 2048.

| Provider | Observed outcome | Source | Offline replay |
| --- | --- | --- | --- |
| Ollama | 13 committed ticks, 26 validated calls, exit 0 and authoritative `founding_failure` at the deadline. | `f722b5fd21af4864919c2bf47cb721d3` | `7a5211d68d084715b7f03a8b6f1d88cf` |
| llama.cpp | 4 committed ticks, 9 calls, exit 6 `invalid_response` for an unoffered target. | `f3d85116fa8c4cee9ec11d76393fe48e` | `eedca28094f74c8ab477a5d79263c2ec` |

Ollama passed the former tick-4 stop. It received 18 real requests containing
the structured trade offer at source ticks 4–12, but did not select it.
The accepted actions completed food, modest shelter and homeland contact;
maintenance also met its objective. Water and storage were still unmet and
the camp never advanced its stage. The model proposed no action in 21 of
26 calls. Engine-governed founding failure is a completed unattended outcome,
not a provider error or evidence of settlement success. Synthetic regression
tests separately establish accepted trade dispatch and stale rejection.

Both saved histories replayed exactly with the respective provider stopped,
comparing complete worlds (including events), driver and feedback cursors,
and retained response observations. Duplicate shutdown checkpoints in the
failed llama.cpp attempt were identical; replay compares the committed
simulation state rather than recreating its operator lifecycle. Source files
remained byte- and mtime-identical.

The declared higher-variance work check (temperature .8/provider seed 44, world
seed unchanged) failed on both backends before tick 1: each model proposed an
action while offered no actions. The archive IDs are
`b198a4af1f9a4e6f826e4539e1ac1c6e` (Ollama) and
`0a5fe3a19e6b454d9390241fa749277e` (llama.cpp). This is neither an applied
disturbance nor a boundary reached with no eligible work. Four further owned
server PIDs were verified gone and both ports closed before full validation.

The work-interruption gate remains **unmet** on both providers, and llama.cpp
has not demonstrated an unattended run reaching the founding deadline.
No further sampling search was used to force a pass. Keep the original acceptance
criteria and preserve all evidence. The trade defect fix does not close LN09,
change the active release scope, or authorize a new tag.
