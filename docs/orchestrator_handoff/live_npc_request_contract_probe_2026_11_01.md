# Native request-contract probes — November1,2026

LN09g delivery79b722002e371366065c1b0dec511b573ec16e58, reviewedsource302files
`ac9987f39532b33e97ffc8425d52fb563e0a3f4bb852f7ee90b831b211d9306f`.
Independent spec+quality review found no substantive issues; taskfull2872tests/
10existing skips/allchecks passed before these probes. These are bounded native
compatibility diagnostics, not final whole-runtime acceptance.

## Method and results

Opt-in `--request-contract founders_empty_arguments_v1` persisted through normal
CLI source, fresh-process cold child and provider-offline replay. Every normal
attempt and exact request/response body, backend/model identity and observed
HTTP timestamps/durations was retained automatically. No model outputs were
repaired or injected, no gateway/schema/parser authority was weakened.

| Backend / model | Real calls | Engine action outcomes | Cold restart / offline checkpoints |
| --- | ---: | --- | --- |
| llama.cpp / Qwen3.5-4B-Q4_K_M, alias live-qwen35 | 4 | 2no-action,1accepted,1rejected | exact /2exact |
| Ollama / hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M | 4 | 2no-action,1accepted,1rejected | exact /2exact |

All non-null proposals had exactly empty arguments; the previous duplicated-target
argument failure was absent. Each backend executed one proposal through the ordinary
work gateway. Other proposals remained subject to ordinary validation; this is not
a guarantee that every model proposal succeeds or a settlement reaches success.

Both prepared provider bodies contained the selected empty-arguments schema and
instructions. All8 requests/responses had matching IDs, actual backend/model,
verified exact BLOB digest/length, complete HTTP200 observation and positive broker
interval. Cold child's initial complete world and both cursors matched sourcefinal.
After stopping the owned server and verifying the port closed, replay matched every
child snapshot including events, driver/feedback cursors, response trace/digest/
elapsed values and retained exact body. Reused timings are original observations,
not new inference latency. Both source and child bytes/mtimes stayed unchanged.

Native llama command used the owner's installed binary and GGUF, loopback8080,
`-ngl 99 -dev Vulkan0 --ctx-size 8192 --parallel 1 --alias live-qwen35 --reasoning-budget 0`.
Fresh device discovery mapped Vulkan0 to AMD RX5700XT and Vulkan1 to GTX1060 6GB;
this probe requested AMD only. It does not certify every GPU buffer or multi-GPU
placement. Ollama used loopback11434 and `OLLAMA_KEEP_ALIVE=0`. No container, download,
driver change or public bind was needed. Different models/contexts/timings are not
a controlled performance comparison.

Both owned model servers and six owned CLI processes exited0; recorded PID/start
identities were gone and both ports free. No unrelated process was stopped.
Product source hash stayed unchanged.

## Retained evidence

W = feature `.superpowers/sdd/2026-10-19-live-npc-runtime` (project-local ignored).
`request_contract_native_probe.py`, `ln09g-device-list.log`, `ln09g-native-acceptance.json`
and outputdirs `ln09g-native-llama` / `ln09g-native-ollama` retain commands, PID/start/
UID/exit metadata, logs, sourceprovenance and native summaries; opaque bodies stay
privileged in archive BLOBs, not Git. Sessions52656/80554 completed.

Attempt source -> cold child -> offline replay:

- llama: 9a0c8ea7264f4557950c5e9af49c0f4e -> ba621a9950664fb6b8390b17ca6fcd95 -> 02869905c4bd45c88df6dacbe4dca1d2.
- Ollama: 1d3ab6a753564f159236228624aaa758 -> ddad34ccb1f140be8305d1deb11a4483 -> 1c644c1f44a24a93a01f6d1fb3dfc420.

Earlier LN09e20calls/9archives remain preserved unchanged. Legacy request selection
stays default and byte/hash compatible; new mode is explicit, current founding
scenario only. Existing archives/replay retain their selected contract.

## Still required

Feature integration/repeatedgates are recorded separately in the LN09g report.
Full original both-provider baseline/disturbance/browser controls/changed-feedback/
installedPython3.11 acceptance and final whole-branch review remain. Combined inert
historical-world selection and forensic/portable export also remain. No complete
live-runtime milestone or future GPU-profile capability is claimed here.
