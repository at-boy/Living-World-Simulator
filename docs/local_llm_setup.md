# Local LLM Setup

## Purpose

Living World uses only locally hosted language-model providers. Future provider
adapters will call either an Ollama or llama.cpp HTTP server through the
`LLMPerceptionClient` protocol. The simulation itself does not start, manage,
or download models.

The current `LLMPerceptionEngine` is provider-neutral. It has no HTTP client
yet, so this document prepares a local runtime for the later adapter commit.

## Safety Boundary

Bind the model server to a loopback address unless there is a deliberate,
secured deployment plan. A local model is a perception subsystem: it receives
curated engine-side data and returns a description and confidence. It must not
receive `WorldState`, internal entity identifiers, or a simulation mutation
interface.

The engine validates provider output and falls back to deterministic perception
when the provider is unavailable or returns invalid or unsafe content.

## Ollama

Install Ollama using its platform-specific instructions, then download a model
appropriate for the local machine:

```bash
ollama pull <model-name>
ollama serve
```

Ollama serves its local API at `http://localhost:11434/api` by default. Verify
the running model server with a non-streaming request:

```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"<model-name>","prompt":"Reply with OK.","stream":false}'
```

The future Ollama adapter will use this local endpoint only. See the official
[Ollama API introduction](https://docs.ollama.com/api/introduction) and
[generate endpoint](https://docs.ollama.com/api/generate) for current install
and request details.

## llama.cpp

Build or install `llama-server`, obtain a compatible local GGUF model file,
then start the HTTP server on loopback:

```bash
llama-server -m /absolute/path/to/model.gguf --host 127.0.0.1 --port 8080
```

Verify the OpenAI-compatible server endpoint:

```bash
curl http://127.0.0.1:8080/v1/models
```

llama.cpp exposes OpenAI-compatible completion and chat-completion routes;
future adapters should use its documented structured JSON response support.
See the official [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## Adapter Configuration (Future)

The first concrete local-provider commit should add explicit configuration for:

- provider (`ollama` or `llama_cpp`);
- loopback base URL;
- local model name or alias;
- request timeout;
- generation limits and deterministic sampling settings.

No cloud endpoint, API key, or remote default should be introduced. Tests must
continue to use fake `LLMPerceptionClient` implementations; an optional manual
smoke test may call a locally running server.
