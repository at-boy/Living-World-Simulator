# Local LLM Setup

## Purpose

Living World uses only locally hosted language-model providers. The
`OllamaPerceptionClient` and `LlamaCppPerceptionClient` call their respective
loopback HTTP servers through the common `LLMPerceptionClient` protocol.
`OllamaCognitionClient` and `LlamaCppCognitionClient` use the same loopback
transport for untrusted, structured NPC reasoning proposals. The simulation
itself does not start, manage, or download models.

## Safety Boundary

Bind the model server to a loopback address unless there is a deliberate,
secured deployment plan. A local model is a perception subsystem: it receives
curated engine-side data and returns a description and confidence. It must not
receive `WorldState`, internal entity identifiers, or a simulation mutation
interface.

The engine validates provider output and falls back to deterministic perception
when the provider is unavailable or returns invalid or unsafe content. A
cognition client receives only `NPCContext` prose and offered action labels. It
cannot receive `WorldState`, identifiers, raw attributes, evidence, metadata,
or raw capability values. Its response is only a speech/action proposal; it
does not execute an action or report authoritative success. The action gateway
performs later engine validation and application.

## Ollama

Install Ollama using its platform-specific instructions, then download the
recommended Qwen3 4B GGUF quantization:

```bash
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
ollama serve
```

Ollama serves its local API at `http://localhost:11434/api` by default. Verify
the running model server with a non-streaming request:

```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M","prompt":"Reply with OK.","stream":false}'
```

Run the real integration example from the repository root:

```bash
PYTHONPATH=src .venv/bin/python examples/manual/ollama_perception.py
```

The opt-in five-NPC council demonstration uses the same loopback server:

```bash
PYTHONPATH=src .venv/bin/python examples/manual/ollama_council_meeting.py
```

`OllamaPerceptionClient` defaults to `http://127.0.0.1:11434` and rejects
non-loopback URLs. It sends `think: false` so Qwen3 returns the required JSON
in the response field rather than its separate thinking field. See the official
[Ollama API introduction](https://docs.ollama.com/api/introduction) and
[generate endpoint](https://docs.ollama.com/api/generate) for current install
and request details.

## llama.cpp

Build or install `llama-server`, then have it download and serve the same
recommended Qwen3 quantization on loopback:

```bash
llama-server \
  -hf Qwen/Qwen3-4B-GGUF:Q4_K_M \
  --alias qwen3-4b-q4-k-m \
  --jinja \
  --host 127.0.0.1 \
  --port 8080
```

Verify the OpenAI-compatible server endpoint:

```bash
curl http://127.0.0.1:8080/v1/models
```

Run the real integration example from the repository root:

```bash
PYTHONPATH=src .venv/bin/python examples/manual/llama_cpp_perception.py
```

The corresponding five-NPC council demonstration is:

```bash
PYTHONPATH=src .venv/bin/python examples/manual/llama_cpp_council_meeting.py
```

`LlamaCppPerceptionClient` defaults to `http://127.0.0.1:8080` and rejects
non-loopback URLs. llama.cpp exposes OpenAI-compatible chat-completion routes
and structured JSON response support. See the official
[llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## Recommended Model

The official [Qwen3-4B GGUF release](https://huggingface.co/Qwen/Qwen3-4B-GGUF)
provides `Q4_K_M`; it is approximately 2.5 GB. This is the development default
used in the manual examples. It is a practical starting point, but its output
remains non-authoritative and is always validated by `LLMPerceptionEngine`.

## Client Configuration

Both clients accept explicit configuration for:

- provider (`ollama` or `llama_cpp`);
- loopback base URL;
- local model name or alias;
- request timeout;
- generation limits and deterministic sampling settings.

No cloud endpoint, API key, or remote default is supported. Tests use fake HTTP
transports and do not require a model server; the manual examples are optional
smoke tests for a locally running server.

The council demonstrations are deliberately opt-in and are not part of `make`.
They show five differentiated, attendance-friendly perspectives; a real model
may nevertheless decline, abstain, or fail to return schema-valid JSON. Such a
response is non-authoritative and does not change the world.

Each council invitation explicitly directs an invitee to return exactly one
offered attendance action in `action_request`, with a short NPC-visible reason
in `rationale`. The action keys remain exclusively in the separate structured
action vocabulary already supplied to the cognition client, so the invitation
prose can preserve the internal-identifier boundary. That reason remains only
the existing filtered, transient operator-debug invitation feedback; it is not
public world state, persisted, emitted as an event, or forwarded to another
NPC. A statement alone is not an attendance selection. This improves
local-model guidance only: omitted, malformed, or unavailable action requests
still do not cause attendance, and the engine does not infer a choice from
prose.

Each manual council example prints attendance, identifying the always-attending
caller separately from invited NPCs, invitation feedback for each invitee,
visible debate turns, collected agenda votes/proposals, the majority proposal,
and any resulting gateway resolution. Invitation feedback is an ephemeral
filtered record of the NPC's submitted attendance proposal: its status and any
safe statement or rationale, not a claim about private mental state. If no
invited NPC joins, it says that only the caller attended and that no invitee
joined; unavailable responses remain distinct from declines and expose no
provider error.
`Majority proposal: None` then means no strict majority was available, not that
the model changed the world.

Identical outcomes from successive local-model runs are valid. The examples
send equivalent constrained requests and rely on the provider and model's
sampling defaults; they do not promise varied or random results.

## NPC Cognition Configuration

The cognition clients use the same provider addresses and model names as their
perception counterparts: `OllamaCognitionClient` defaults to
`http://127.0.0.1:11434`, while `LlamaCppCognitionClient` defaults to
`http://127.0.0.1:8080`. Both reject non-loopback URLs.

They send a JSON request containing the filtered NPC identity, qualitative
self-knowledge, current perceptions, retrieved cognitive prose, and the action
keys/target labels offered for that decision. They require a JSON response with
`spoken_text` and `action_request`; an action request may be `null`, and any
proposal must use an offered key and target label. Invalid provider/network
responses raise a cognition-client error and remain non-authoritative.
