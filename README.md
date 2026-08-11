# Living World Simulator

Event-driven simulation engine for persistent worlds. Version 0.5 provides
deterministic world and settlement systems, persistent NPC cognition, local
LLM perception and reasoning, and a simulation-owned action authority gateway.

## Quick Start

```bash
make install
make fix
make check
make examples
```

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
