# Real-provider archived trace probes — 2026-10-27

Scope: post-LN09e diagnostic evidence at feature integration `90ef1e2`. This is not
final LN09 behavioral/browser/installed acceptance. No production source changed.
The independently reviewed LN09e delivery is `62ea35c`; task and feature gates each
passed 2,547 tests / 10 existing deliberate skips, all 39 examples, separate examples,
exact recorded/archive/restart and source/wheel serving checks. See its reviewed report.

## Method and retained evidence

The project-local ignored plan workspace `.superpowers/sdd/2026-10-19-live-npc-runtime/`
retains `native_trace_probe.py`, the three output directories below and
`ln09e-native-analysis.json`. Raw request/response bytes remain in privileged format-two
archive BLOBs. They are not copied into Git. Each native/CLI process has exact owned PID,
UID, start time, argv, exit status and local logs. No container, model download, driver
installation, public bind or product server launcher was used.

The probe uses the actual CLI and RuntimeService. It starts a bounded real live world,
exits, resumes in a fresh CLI process, checks the child's initial complete world and
both cursors against the saved source, advances, and stops its owned model server.
With the port confirmed closed it replays the child and compares every complete world
snapshot (including events) and driver/feedback cursor, plus exact response trace,
digest, elapsed time and locally retained response bodies. Source files stay unchanged.
Every live request/response has matching identity, backend/model metadata, verified
body digest/length, complete HTTP200 observation and positive actual broker interval.

## Results

| Local output directory | Backend/model | Live calls | Actions | Cold restart / offline checkpoints |
| --- | --- | ---: | --- | --- |
| `ln09e-native-llama` | llama.cpp / Qwen3.5-4B-Q4_K_M, alias `live-qwen35` | 4 | 2 no-action, 2 rejected | exact / 2 exact |
| `ln09e-native-ollama` | Ollama / `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 4 | 2 no-action, 1 accepted, 1 rejected | exact / 2 exact |
| `ln09e-native-llama-3ticks` | same llama.cpp model, unchanged prompts/settings | 12 | 2 no-action, 10 rejected | exact / 4 exact |

All three diagnostics exited zero. Twenty real calls, nine normal archives and eight
compared replay checkpoints are retained. Original request/response evidence and timing
are preserved through replay, without new inference calls. Observed broker interval
ranges were 1.459–2.566 seconds, 5.753–8.050 seconds and 1.467–2.712 seconds respectively.
These include dispatch/capture overhead, use different models and lengths, and are not
a controlled performance comparison or token-generation timing.

Native llama command used the owner's installed binary and GGUF, loopback port8080,
`-ngl 99 -dev Vulkan0 --ctx-size 8192 --parallel 1 --alias live-qwen35 --reasoning-budget 0`.
Current device discovery maps Vulkan0 to the AMD RX5700XT. This records requested device
configuration; this low-verbosity run does not separately certify GPU buffer placement.
Ollama used loopback11434 and `OLLAMA_KEEP_ALIVE=0`. All three owned native servers exited0;
owned PIDs were absent afterward and both ports were free. No other server was stopped.

Attempt IDs (source → cold child → offline replay):

- llama short: `8b995ecdb1e74612841cfbb35ef58e79` → `aa6edae6dd64483184bcb3d47c95c351` → `ac980c0cba66444f8dad56f4c25b9add`.
- Ollama: `6ca5b569b4e14a6b84971f46b8bb80dc` → `9b085c5a8f97426ba68f1c19304fcb5b` → `7f024f0a3dfb41e5a3246ff7b5e33be1`.
- llama longer: `7a42c1bfb172445fab6d6fc0d6e271d4` → `b37a32a3c1e74aeda2c97843bd597ec5` → `4cc97bf9dcf54aa48c6051c75552f386`.

## Open behavioral acceptance issue

Ollama produced one accepted ordinary work proposal and its event. llama.cpp returned
valid structured proposals, but all twelve non-null proposals across the two probes
had nonempty `arguments`, including duplicated target labels. `WorkActionGateway.validate`
correctly rejects nonempty arguments before any world mutation (`src/living_world/work/action.py`).
The shared system prompt already requests `{}` when no arguments are needed; the generic
response schema accepts string-valued argument mappings. Context offers expose action
keys/descriptions/target labels, without an explicit per-offer argument contract.

The longer unchanged six-tick world reproduced rejection after qualitative feedback.
This supports a model/proposal-contract compatibility issue; it does not demonstrate
an archive or HTTP transport fault. No invalid proposal was repaired, stripped of
arguments, injected or executed. Do not weaken the gateway to make this gate pass.
Any prompt/offer/schema improvement needs a separate bounded contract, RED/GREEN,
independent review and real rerun. Preserve old archived request/context fingerprints
and replay composition through an explicit compatibility decision; do not globally
change shared descriptions and invalidate recorded tapes or earlier archives.

## Still required

Authenticated read-only/offline trace analysis, forensic spool distinction, portable
export and browser UI remain LN09f. Root investigations are saved in
`trace-analysis-root-notes.md` and `trace-reader-seams.md`; no implementation contract
is active yet. Analysis must use bounded-memory metadata/selected-body verification
without weakening full runtime archive validation or claiming unchecked world validity.

Original LN09 requires both providers to make valid world-changing decisions and show
changed safe observations/offers under baseline/disturbances; durable pause/step/browser
controls, cold restart, offline replay, failed/interrupted archive inspection, installed
Python3.11 compatibility and final whole-branch review also remain. These diagnostics
prove transport/archive/cold-restart/replay behavior, not all those acceptance criteria.
