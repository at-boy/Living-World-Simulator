# Task 13a — HTTP inspection coverage report

## Delivered surface

- Extended `WorldInspector` and `EngineWorldInspector` with NPC presentation,
  memory, knowledge, and holder-scoped cognitive-history methods while adding
  the previously implementation-only persisted collection methods to the
  protocol contract.
- Added GET-only `/world/npcs`, `/world/memories`, `/world/knowledge`, and
  `/world/cognitive-history/{holder_id}` routes. Existing observation, belief,
  and experience routes continue to expose their full persisted records.
- Extended `/world` with memory, knowledge, and NPC-relationship counts while
  preserving every existing summary key.

NPC presentation contains the entity ID and validated generic attribute forms
for identity, occupation, schedule, and current activity. All collection and
holder-category records are ordered by record ID. Empty collections return
200 arrays, known empty holders return all empty categories, and unknown
holders return 404.

## Isolation and information boundary

The existing recursive snapshot conversion is applied to each new response,
including nested mappings and sequences, so callers cannot mutate live state.
Tests directly mutate nested metadata and provenance returned by
`EngineWorldInspector`, then confirm both live `WorldState` and a fresh
inspector snapshot are unchanged.

Inspection remains a privileged operator-only output path. No inspection DTO
or method is imported by retrieval, context assembly, perception, or cognition.
The boundary test seeds a second holder's core cognition, which would ordinarily
be retrieved, then confirms it is absent from the primary holder's non-empty
core and topic-query results. Privileged payload assertions separately confirm
that provenance, metadata, and belief/experience history shapes remain
inspectable. Holder history filters every category before snapshotting and
includes no other holder's records.

Conversation results, meetings, council calls/results, invitation feedback,
and action resolutions remain ephemeral return values. This task deliberately
adds no conversation/council persistence and no `/world/conversations` or
`/world/councils` route.

## Executable example

`examples/023_http_inspection.py` constructs manager-owned NPC and cognitive
records and inspects the world summary, NPC presentation, memory and knowledge
collections, and one holder's complete persisted cognitive history. Existing
Makefile wildcard discovery already includes it, so the Makefile was unchanged.

## Validation

- Focused inspection tests: 6 passed.
- `make`: passed Ruff, Black, 392 tests, and all 23 numbered examples.
- `make examples`: all 23 numbered examples passed, including example 023.
- `git diff --check`: passed.
