# Task 15d — NPC-safe spatial perception translation report

## Delivered perception contract

- Added a strictly typed `SpatialPerceptionEngine` implementing the existing
  `PerceptionEngine` protocol and a typed fail-closed
  `SpatialPerceptionError`.
- The engine accepts one caller-selected `PerceptionContext`, requires its
  observer, subject, placements, and any translated road to match live
  authoritative state, and returns one unpersisted immutable `Observation`.
- Point coordinates and doubled bounds centers produce stable co-location or
  eight-direction compass prose. Positive x is east and positive y is north.
  Explicit subject/shared containment is described with public entity names.
- One active direct `road` is described only when that authoritative
  relationship is present in the caller-filtered context. Unrelated,
  duplicated, future, destroyed, detached, or omitted roads add no prose.
- Detached evidence contains only qualitative relation-code strings; metadata
  contains only the translator name. Neither contains placement snapshots,
  coordinates, dimensions, or internal IDs.

## Information-boundary correction

Perception-time validation now rejects every authoritative placement coordinate
and dimension, all current spatial/entity/relationship IDs, raw coordinate
notation, and unambiguous privileged spatial vocabulary. Final
`NPCInformationBoundary` validation applies the same coordinate/vocabulary
protection to every NPC prose field and includes placement geometry in its
authoritative numeric set. Therefore an unsafe manually or historically stored
observation such as `The well is at 47, 83.` cannot enter `NPCContext`.

The first full test pass exposed that bare `coordinate` is legitimate existing
NPC prose as a verb. The correction narrowed privileged vocabulary to
unambiguous forms such as `coordinates`, `coordinate pair`, `coordinate value`,
`bounds`, `placement record`, and `overlap policy`; the existing council
contexts and the new leak regressions then passed together.

Independent review found that textual decimal equivalents of authoritative
integers, such as `47.0` for coordinate `47`, could bypass the initial exact
string comparison. Both boundaries now tokenize standalone decimal/scientific
numeric literals and compare their `Decimal` values with authoritative values.
Thus equivalent forms fail closed while embedded prose tokens such as
`Route47.0` remain valid. Perception-time and stored-context regressions cover
the correction.

The review also found that container lookup validated the placement mapping key
and bounds but not the placement record's embedded entity ID. Spatial
perception now requires those identities to match and has a fail-closed
malformed-container regression.

A second review found that an attached sign could prevent the numeric matcher
from consuming the sign and then let it restart at the digits, so negative
coordinates could appear as `x-47.0` or `x-4.7e1`. Numeric tokenization now
forbids restarting immediately after a sign, and both boundaries explicitly
reject signed x/y-attached decimal or scientific coordinate notation. New
perception-time and stored-context regressions cover both forms while the
`Route47.0` token-boundary case remains allowed.

A third review applied the same signed-attached form to authoritative bounds
dimensions. The explicit notation guard now covers `x`, `y`, `width`, and
`height`, including positive or negative decimal and scientific forms.
Perception-time and stored-context regressions prove `width+20.0` and
`height+3e1` fail closed without changing the embedded-token behavior.

A fourth review found that the explicit-label matcher still required a sign.
The same x/y/width/height grammar now makes the sign optional, rejecting
directly attached unsigned decimal and scientific forms such as `x47.0`,
`y8.3e1`, `width20.0`, and `height3e1`. Both enforcement layers have explicit
regressions, while `Route47.0` remains outside the spatial-label grammar.

Holder scoping is unchanged: callers record through `ObservationManager`, and
`NPCContextAssembler` selects only observations owned by the requested holder.
Privileged inspection continues returning exact detached geometry. No
visibility enumeration, proximity, pathfinding, navigation, movement, terrain,
travel, persistence, HTTP, UI, work, or action behavior was added.

## Tests and executable documentation

`tests/test_spatial_perception.py` covers all compass directions, point/bounds
center comparison, co-location, subject and shared containment, deterministic
clause order, insertion-order independence, direct-road filtering and
deduplication, detached evidence, protocol compatibility, unknown/mismatched/
destroyed/unplaced state, malformed contexts, and internal-ID rejection.

The existing perception/context tests now regress coordinate notation,
geometry values, privileged vocabulary, stored-observation revalidation, and
holder isolation. The focused spatial/domain/context suite passed 69 tests; a
combined Task 15d and prior council-compatibility regression passed 43 tests.

`examples/031_npc_spatial_perception.py` records a qualitative containment,
direction, and direct-road observation, assembles the holder's safe context,
and separately demonstrates exact operator-only inspection.

## Documentation and allowed-file audit

Updated ADR-0016, the changelog, backlog, core model, engine glossary, NPC
information boundary, and project journal. Production, test, example, and
documentation changes remain entirely within the Task 15d allowed-file
boundary. The task plan and saved prompt required no implementation amendment.

## Final validation

- `make`: passed Ruff, Black, 610 pytest tests, and examples 001–031.
- Separate `make examples`: examples 001–031 passed.
- `git diff --check`: passed.

No blockers remain. The work is intentionally uncommitted for independent
orchestrator review.
