# Living World Simulator

Event-driven simulation engine for persistent worlds.

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

## HTTP inspection

The engine includes a privileged, GET-only HTTP API for inspecting a running
world. See the [HTTP inspection API guide](docs/http_inspection_api.md) for
startup instructions, endpoint examples, and security boundaries.
