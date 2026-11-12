# Future vision: explorable worlds and generational history

Recorded November 12, 2026, at the owner's request.

## Status and scope

This records a future discussion for reference. It is not an approved implementation
design, task plan, milestone, or new release requirement. The owner intends to return
to the current development path after logging off. Current live-runtime work remains
on `codex/live-npc-runtime`, integration `e454722`; its continuation brief remains the
execution entry point. Resolve and authorize future scope separately before coding.

## Intended uses

The simulator should eventually support many settings and scenarios:

- Ordinary aboveground settlements and their surrounding worlds.
- Multiple generational underground settlements, with a Fallout-like setting as
  one inspiration, without cruel experiments on the inhabitants.
- Settlements sending groups to explore, find resources, establish communication
  and trade, and connect with underground communities or the surface world.
- Persistent live worlds for interactive games, including later player interaction.
- Generating settlement history and lore for the owner's Dungeons & Dragons world,
  whose detailed timeline currently spans more than 2,200 years.
- Entirely new worlds with no pre-existing history.

## Starting worlds and established lore

Worlds may be small or large. A world can begin with only a defined first area,
then expand through random generation as NPCs explore. The owner also wants to
add authored areas and other world content when desired.

Three starting situations were described:

1. A new world without established history.
2. A new or unexplored settlement within an existing setting. Selected major world
   events may be relevant, but their involvement is optional and depends on the run.
3. An already defined settlement, importing its established people and history,
   then running the simulation to extend its future history and lore.

The owner explicitly chose **forward simulation only** from the last established
point. Filling gaps in, or resimulating, established earlier history is not requested.
Past history should remain available for viewing.

The owner wants to define both objective facts and what particular people know or
believe about those facts. Imported world history must not automatically become
universal NPC knowledge. The existing separation of engine truth, perception,
memories, beliefs and untrusted LLM proposals remains relevant.

## Exploration, maps and history

The owner wants to follow the whole world and navigate between levels of detail:

- Maps of the world, regions and settlements, in the present and the past.
- NPC travel, exploration, expansion, building, resource harvesting and whatever
  other activities inhabitants actually undertake.
- Settlement development, communication, trade and interactions between communities.
- Individual people, evolving families across generations, family trees and detailed
  member profiles.
- Connected timelines so a person, family, place or event can be followed through
  history and related to changes elsewhere in the world.

Broad regions are an acceptable starting point. Rich local detail is a central
long-term aspiration. The owner did not select a narrow list of activities to
visualize: the intention is to follow inhabitants doing whatever they are doing.
Exact map resolution, movement mechanics and visual style remain undecided.

## Authoring interface and source material

A browser-based editor will be needed to write and define world content. The owner's
existing lore includes quick notes, pictures, maps and assorted other material.
It should be possible to retain and associate these references with defined content.

Authoring needs discussed include geography, settlements, resources, buildings,
infrastructure, people, family relationships, established events, knowledge and
beliefs. The map may be defined before a simulation starts and expanded later.

The owner has not decided whether the editor should be its own browser interface
or part of another interface, and is open to whichever arrangement makes sense.
A dedicated editor workspace alongside runtime observation was the assistant's
recommendation, not an agreed implementation decision.

## Suggestions raised, requiring later design decisions

These were assistant proposals rather than settled requirements:

- Connected world, region, settlement and local map views backed by consistent state.
- A common timeline across maps, people, family trees and settlement inspection.
- Clear provenance distinguishing imported canon, generated events and NPC accounts.
- Notes and pictures retained as references alongside structured simulation data;
  assisted extraction presented for review rather than automatically becoming truth.
- Detailed live operation and faster historical operation using shared domain rules.
- Routine processes governed by engine systems, with richer LLM reasoning where
  appropriate; LLM cost and fidelity need explicit treatment over long histories.
- Separate alternative-history branches when trying a different continuation.
- Dated changes during active simulations, preserving earlier historical views.
- Setting-specific systems such as underground ventilation, power, water treatment
  and maintenance, plus expedition supplies, travel uncertainty and discoveries.

## Questions for a future design discussion

- Expected populations, geographical extent and duration for representative runs.
- Calendar and time progression, historical detail, storage and reconstruction costs.
- Map hierarchy, physical resolution, procedural generation and authored additions.
- Import formats and how incomplete notes become validated starting conditions.
- Family, aging, education, inheritance, migration and knowledge transmission rules.
- Treatment of major setting events and player interventions.
- Authoring workflow, historical inspection and the editor's relationship to admin UI.

No implementation, estimates or release commitments were approved in this discussion.
