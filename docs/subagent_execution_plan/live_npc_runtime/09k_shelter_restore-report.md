# LN09k implementation report

In live canonical founders, constructed camp-owned shelters with a terminal
maintenance state remain part of attachment validation. They retain the same
exact policy, housing and composition-marker checks as standing shelters.
A collapsed shelter is never given attachments during staged composition.
The consequence manager keeps lifecycle ownership and the existing active
capacity predicate still excludes collapsed shelters. The recorded route and
storage selection keep their previous behavior.

Serena confirmed that both existing callers of the attachment validator were
updated. On the unchanged base the ordinary-collapse regression failed with
`setup_mismatch` and six malformed-history checks passed. The production
and test diff passes scoped Ruff, Black and whitespace checks.

Focused `pytest` for runtime founders feedback and canonical founders passed
125 tests in 39.97 seconds. The reviewed 358-file source digest is
`681be2d2fb4f89b59fd3824be83a5b42c7baa83cd4ce0060ccf47950428905d7`.

Checkpoint 14 of the original llama.cpp attempt restored byte-for-byte.
With both temporary provider ports closed, the stock CLI replayed a separate
copy of attempt `cfc9162ae95b4db1ac8a228d8430f6c0` into
`b0ba049fc02b4ff6873ec947bb1728bb`. All 15 snapshots, including ordered
world events and domain charges, and both cursors at each revision matched.
All 28 reused responses matched the retained body bytes, timing and digest.
The original catalog and copied source attempt inventories were unchanged.

Independent review found no substantive issues and independently passed the
same 125 focused tests.

A fresh AMD llama.cpp Qwen2.5 7B campaign `bbbd96167dfe4712ab3a48716284f458`
completed with exit 0 at its explicit tick-16 cap, in settlement stage,
with all 32 responses validated and eight actions accepted. The engine did
not publish a named terminal outcome. The first replay CLI exited 0, but
the diagnostic's final closed-port check collided with the next bounded
llama.cpp work trial. After all servers exited, a separate copied-catalog
replay `9b9714ad137c471b80eb1e14b24baaa2` verified all 17 snapshots, cursors
and 32 retained responses with both ports closed. It left both source
inventories unchanged.

The fixed tick-2 work interruption returned `no_eligible_work` on Ollama
(child `4e26e6af`, replay `ba8f4c01`) and llama.cpp (child `0db697ae`,
replay `44f6459e`). Each matched four cold-resumed checkpoints offline.
Both work-interruption gates and the named llama.cpp terminal outcome
remain open. Host verification confirmed all three owned servers exited 0
and their ports were closed.

Python 3.11.2 installed the built wheel offline and passed its six import,
console, canonical matrix, serve, example and export checks.
The packaged browser opened revisions 0 and 14 of the copied original
llama.cpp attempt in Chrome. All nine requests passed, and the copy's
inventory remained unchanged.

All 13 task validation jobs passed. `make` passed 3,080 tests with 10
existing skips in 787.76 seconds and ran all 40 examples. A separate
`make examples` and `git diff --check` passed. The recorded payload hash
matrix, installed wheel and CLI/browser/archive/export compatibility passed
on the unchanged reviewed source.
