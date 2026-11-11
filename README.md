# Living World Simulator

Event-driven simulation engine for persistent worlds. Release candidate
`0.6.0rc1` adds a reproducible founding-settlement vertical slice: engine-owned
needs, work, goals, stages and external dispatch, with durable replay and a
privileged read-only browser inspector. Recorded proposal tapes drive bounded
unattended runs; they do not establish live-LLM strategy performance.

See the [release notes](docs/releases/v0_6_0rc1.md) for behavior, compatibility,
known limits and current release-readiness evidence. Owner integration, tagging
and publication are separate actions.

## Quick Start

From the root of this candidate source checkout, using Python >=3.11:

```bash
make install
source .venv/bin/activate
living-world run --founders success --database success.sqlite3
living-world run --founders stall --database stall.sqlite3
living-world run --founders failure --database failure.sqlite3
living-world inspect --founders --database success.sqlite3 --port 8000
```

Open [the local inspector](http://127.0.0.1:8000/inspector) after starting
inspection. It serves a fixed saved snapshot; it does not automatically reload
another process's database. `make install` installs this checkout and development
dependencies (including uvicorn) into `.venv`; activation selects its
`living-world` entry point. This sequence uses the unpublished checkout and
does not require an index release. Package publication is a separate action.

The [founders operator guide](docs/canonical_founders.md),
[HTTP API guide](docs/http_inspection_api.md),
[World Inspector guide](docs/world_inspector_ui.md) and
[NPC information boundary](docs/npc_information_boundary.md) explain the public
interfaces and the separation of engine truth from NPC interpretations.

## Run a live simulation on `codex/live-npc-runtime`

This section applies to the development branch, **not the tagged release or
`main`**. It runs the canonical founders world with real model decisions,
automatic archives and browser controls. Both providers have passed bounded
native probes; successful settlement development is not guaranteed, and broader
runtime acceptance is still pending.

### 1. Select the branch checkout and install

On this workstation the branch already has its own checkout. Use it directly;
there is no need to switch the primary checkout away from `main`:

```bash
cd /home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/live-npc-runtime
git branch --show-current
# Expected: codex/live-npc-runtime
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[server]'
living-world serve --help
```

Use Python 3.11 or newer. On another machine, check out
`codex/live-npc-runtime` in a separate working directory and run the same
installation commands there. In each new simulation/analysis terminal, return to
that checkout and activate `.venv` again.

Create a private directory for temporary administrator tokens. Archives will go
in the separate `runs` directory; keep this same archive path for later restarts:

```bash
mkdir -p "$HOME/.local/state/living-world-first-run/secrets"
chmod 700 "$HOME/.local/state/living-world-first-run/secrets"
```

### 2. Start one model backend

Choose **Ollama or llama.cpp**. Keep the selected server running while the
simulation uses it. The simulator does not launch or download models itself.

**Ollama:** if its service is already running, use that service. Otherwise start
`ollama serve` in a separate terminal. In another terminal, check/install the
model used in the native probe:

```bash
ollama list
# Only if the following model is missing (this downloads it):
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
```

**llama.cpp:** on this workstation, start the supplied Qwen3.5 GGUF on the AMD
card in a separate terminal:

```bash
/home/at-boy/Projects/codex/llama.cpp/build/bin/llama-server \
  -m /home/at-boy/Projects/codex/llm-models/gguf/Qwen3.5-4B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 \
  -ngl 99 -dev Vulkan0 --ctx-size 8192 --parallel 1 \
  --alias live-qwen35 --reasoning-budget 0
```

This is the previously tested AMD `Vulkan0` selection; check device mapping if
hardware changes. Wait for the server to finish loading before proceeding. The
simulator verifies the alias and backing model file, so keep both exactly as
shown. The Ollama model name and llama.cpp alias are different selections.

### 3. Launch the world, initially paused

In the activated simulation terminal, run **one** of these commands.

For Ollama:

```bash
living-world serve --preset founders \
  --driver ollama --model hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M \
  --base-url http://127.0.0.1:11434 \
  --request-contract founders_empty_arguments_v1 \
  --max-ticks 5 --max-requests 20 --timeout-seconds 180 \
  --archive-root "$HOME/.local/state/living-world-first-run/runs" \
  --admin-token-file "$HOME/.local/state/living-world-first-run/secrets/session-token" \
  --port 8000
```

For llama.cpp:

```bash
living-world serve --preset founders \
  --driver llama.cpp --model live-qwen35 \
  --model-file /home/at-boy/Projects/codex/llm-models/gguf/Qwen3.5-4B-Q4_K_M.gguf \
  --base-url http://127.0.0.1:8080 \
  --request-contract founders_empty_arguments_v1 \
  --max-ticks 5 --max-requests 20 --timeout-seconds 180 \
  --archive-root "$HOME/.local/state/living-world-first-run/runs" \
  --admin-token-file "$HOME/.local/state/living-world-first-run/secrets/session-token" \
  --port 8000
```

The explicit request contract is the tested founders-only schema for proposals
with empty arguments; normal engine validation still decides whether to execute
them. The limits bound this first trial to five ticks or twenty model requests.
A budget stop does not mean the settlement has completed its goals.

Open the printed `runtime_url`, normally
[http://127.0.0.1:8000/runtime](http://127.0.0.1:8000/runtime). In a second terminal,
read the generated token and paste it into **Administrator token**, then click
**Connect**:

```bash
cat "$HOME/.local/state/living-world-first-run/secrets/session-token"
```

Wait for the world to become ready; HTTP startup can precede model preflight.
Use **Step** to advance one tick, **Resume** to run within the budgets, and
**Pause** to pause at a safe boundary. A tick may contain several slow model
calls. Use the world preview to inspect state, and **Saved LLM Calls** to examine
exact requests, responses, provider/model metadata and timings. Re-enter the
administrator token when opening the analysis page. Model proposals may be
rejected or produce no action; the simulation remains authoritative.

The token file must not already exist. Normal shutdown removes its unchanged
owned token file; if a prior crash leaves one, choose a new token filename rather
than overwriting it. If port 8000 is occupied, use `--port 0` and follow the
printed URL. Provider errors pause the world; fix the server and use **Retry
model**. Do not launch a second owner for the same active attempt.

### 4. Shut down and resume on another day

Click **Pause**, wait until the browser reports a durable paused state, and note
the current attempt ID from **Current run** or **Saved attempts**. Press Ctrl+C
in the simulation terminal and let it finish shutting down. Keep the entire
archive root, including parent attempts. Closing the browser alone does not stop
the program. **Stop** ends the current run but leaves its saved checkpoints and
the browser server available until shutdown.

Later, start the same model server with the same model, reactivate `.venv`, and
replace `ATTEMPT_ID` below with the saved ID:

```bash
living-world serve --resume-attempt ATTEMPT_ID \
  --archive-root "$HOME/.local/state/living-world-first-run/runs" \
  --admin-token-file "$HOME/.local/state/living-world-first-run/secrets/resume-token" \
  --port 8000
```

Resume loads saved configuration and creates a child attempt, preserving the
source. Do not repeat fresh-world `--preset` options. To change model settings or
extend an exhausted budget, use `--fork-attempt ATTEMPT_ID` instead, with the
changed options (for example `--max-ticks 20 --max-requests 80`). See the
[archived runtime CLI guide](docs/canonical_founders.md#archived-headless-runtime-cli)
for checkpoint selection and replay.

### 5. Inspect saved runs without running a simulation

After stopping the runtime server, launch this from the same activated checkout;
no model server is required:

```bash
living-world analyze \
  --archive-root "$HOME/.local/state/living-world-first-run/runs" \
  --admin-token-file "$HOME/.local/state/living-world-first-run/secrets/analysis-token" \
  --port 8000
```

Open the printed `analysis_browser_url`, read `analysis-token` as above, and
connect. Select an attempt to browse saved LLM calls or explicitly inspect a saved
world checkpoint. This does not advance the simulation. See the
[saved-trace analysis guide](docs/trace_analysis.md) for details.

For bounded headless experiments with either backend, disturbances and exact
restart/replay commands, see the [live experiment guide](docs/live_npc_runtime.md).
For a model-free demonstration, run `PYTHONPATH=src python examples/040_live_npc_runtime.py`.

## Development

Before committing changes, run:

```bash
make
```

This command:

- formats the code
- runs static analysis
- executes the test suite
- runs every example

The examples serve as executable documentation and smoke tests.

## NPC cognition and local models

NPC-facing reasoning receives only holder-scoped, boundary-validated
perceptions and cognitive records. Ollama and llama.cpp clients are local and
loopback-only; their structured output remains an untrusted proposal until a
registered simulation handler validates and applies it through the action
gateway. Bounded conversations, meetings, and councils preserve the same
authority and information boundaries.

See the [local LLM setup guide](docs/local_llm_setup.md) for provider setup and
the opt-in manual council scenarios. These manual examples demonstrate a
settlement-wide concern, opposing interests, and opinions shaped by private
cognitive histories without granting the model world-state authority.

## HTTP inspection

The engine includes a privileged, GET-only HTTP API for inspecting a running
world. See the [HTTP inspection API guide](docs/http_inspection_api.md) for
startup instructions, endpoint examples, and security boundaries.
