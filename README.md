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
