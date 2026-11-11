# Bounded live NPC experiments

The headless helper composes the production archived launcher and runtime owner.
It neither runs a web listener nor changes model decisions. Models propose actions;
the simulation validates them through the ordinary action gateway. Use the
[serve controls in the README](../README.md) for browser operation.

Run from the repository root with the project environment active and `PYTHONPATH=src`.
The literal `--` is required: helper options precede it, production **run options**
follow it, without the word `run`. The helper deadline and provider request timeout
are separate options on opposite sides of this separator.

## Fresh native runs

Start your existing local provider separately; see [local model setup](local_llm_setup.md).
Use your actual installed model names and, for llama.cpp, the exact locally served
GGUF file. The harness does not install/download a model or start a native server.

```sh
PYTHONPATH=src python examples/manual/local_founders_runtime.py \
  --steps 3 --timeout-seconds 600 --disturbance resource_loss -- \
  --preset founders --driver ollama --model YOUR_OLLAMA_MODEL \
  --base-url http://127.0.0.1:11434 \
  --request-contract founders_empty_arguments_v1 \
  --max-requests 40 --max-ticks 20 --timeout-seconds 120 \
  --archive-root ./native-runs

PYTHONPATH=src python examples/manual/local_founders_runtime.py \
  --steps 3 --timeout-seconds 600 --disturbance work_blockage -- \
  --preset founders --driver llama.cpp --model YOUR_SERVED_MODEL \
  --model-file /absolute/path/to/model.gguf --base-url http://127.0.0.1:8080 \
  --request-contract founders_empty_arguments_v1 \
  --max-requests 40 --max-ticks 20 --timeout-seconds 120 \
  --archive-root ./native-runs
```

Both disturbances are fixed at completed tick 2. `resource_loss` uses the existing
resource policy. `work_blockage` only affects eligible existing work. A model
that never proposes eligible work can produce `no_eligible_work`; this leaves
that native acceptance condition **unmet**. The helper never creates work,
substitutes actions, or relabels this outcome. Inspect the retained
`boundary_disturbance` journal entry, not merely the process exit code.

Use `--disturbance none` for an explicitly undisturbed fresh run. Omit it to use
the factory's defaults or inherit the saved policy. The production request contract
is explicit above; the helper never injects a different contract or provider default.

## Cold resume, fork, and offline replay

Copy the saved attempt identifier from the JSON result or stderr announcement.
The following commands start separate processes, retaining exact archived
configuration, world state and cursors under the production resume/fork rules.
The source checkpoint remains unchanged. Omitted `--checkpoint` selects the
latest checkpoint; a number selects that source revision.

```sh
PYTHONPATH=src python examples/manual/local_founders_runtime.py \
  --steps 3 --timeout-seconds 600 -- \
  --resume-attempt SOURCE_ATTEMPT_ID --archive-root ./native-runs

PYTHONPATH=src python examples/manual/local_founders_runtime.py \
  --steps 3 --timeout-seconds 600 -- \
  --fork-attempt SOURCE_ATTEMPT_ID --checkpoint 2 --archive-root ./native-runs

# Stop the provider first. Replay consumes saved responses and makes no model call.
PYTHONPATH=src python examples/manual/local_founders_runtime.py \
  --steps 3 --timeout-seconds 60 -- \
  --replay-attempt SOURCE_ATTEMPT_ID --archive-root ./native-runs
```

Resume/fork inherit the disturbance; an explicit disturbance must match the
saved policy. Already completed tick-2 disturbances are not applied again.
Replay does not accept an explicit disturbance. Its checkpoint selector limits
the captured source history; replay begins at that history's initial checkpoint.
A child initial checkpoint is never counted as an advancing step. A replay can
end normally before all requested steps when its captured source ends.

## Results, cancellation, and evidence

The helper prints one JSON object on stdout with format
`living-world-native-experiment-v1`. Fields include attempt/lineage IDs,
initial/final durable ticks and revisions, requested/completed step counts,
final runtime state, a closed error code, and exit code. Unknown checkpoints
remain null, including failed startup with no initialized world. Admission of
a step is not completion: only a committed advancing tick increments the count.
No checkpoint, prompt, response body, credentials, or diagnostic exception text
is serialized into this summary.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Requested bounded steps committed, or normal early terminal/request-budget stop |
| 2 | Invalid configuration; malformed arguments create no attempt |
| 3 | Incompatible saved configuration |
| 4 | Archive/storage/initialization failure |
| 5 | Service/adapter failure |
| 6 | Provider/setup failure or provider-error pause |
| 124 | Outer deadline (`experiment_deadline`) |
| 130 | Cooperative SIGINT/SIGTERM/KeyboardInterrupt cancellation (`cancelled`) |

Exit 0 does **not** establish settlement success, eligible work interruption, or
native acceptance. Inspect terminal state, ticks, disturbance audit and archived
requests/responses together. Request-budget exhaustion settles to `stopped` and
may commit zero steps. Provider errors are retained without automatic retries.
SIGINT and SIGTERM request the existing runtime shutdown, including during
startup and inference. Deadlines are cooperative: cleanup may extend the elapsed
wall time. Cleanup failures are reported; an earlier failure retains priority.

Stderr announces `attempt=... archive=...` once when an identity becomes known.
This privileged path is intentional. Archives live under
`ARCHIVE_ROOT/LINEAGE_ID/ATTEMPT_ID`; omitting the root uses the production
`$XDG_STATE_HOME/living-world/runs` or `~/.local/state/living-world/runs` default.
Even valid failed launches retain an attempt identity when storage permits.
The archives are the authoritative detailed evidence and can contain privileged
engine/provider data. Use the existing inspection/analysis/export tools to review
saved evidence; the helper adds no admin-token protocol.

## Deterministic model-free example

```sh
PYTHONPATH=src python examples/040_live_npc_runtime.py
```

This numbered example runs a clearly synthetic no-action Ollama-compatible HTTP
fixture on an ephemeral loopback port. The real broker contacts that fixture;
three advancing ticks and saved request/response entries are required. It then
closes the fixture and checks exact checkpoint world and cursor equality through
offline replay, preserving source bytes and modification times. Its temporary
catalog and owned server are cleaned up. Importing it starts nothing. The native
manual helper never selects this fixture.

The example and synthetic acceptance tests demonstrate harness behavior only.
Actual Ollama and llama.cpp acceptance, native disturbance outcomes, restart,
replay, browser checks and final release gates remain separately required and
must be backed by root-owned native evidence. A passing synthetic run cannot
satisfy those gates.
