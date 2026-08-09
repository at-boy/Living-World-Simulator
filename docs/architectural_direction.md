# Architectural Direction

The intended progression is:

    Perception
        ↓
    Observation
        ↓
    Memory / Belief / Experience
        ↓
    YAML World Definition
        ↓
    World Definition Loader
        ↓
    World State
        ↓
    Cognitive Consolidation
        ↓
    Retrieval
        ↓
    NPC Cognition Protocol
        ↓
    LLM NPC
        ↓
    Action request
        ↓
    Simulation validates and applies action
        ↓
    New world state

Important principles:

-   Observation is not an Event.
-   Observation is a perception, not a raw attribute dump.
-   Internal evidence may be retained for debugging, but raw world data
    is not automatically exposed to an NPC.
-   Memories, beliefs and experiences are NPC-specific cognitive
    records.
-   Experience is not a synonym for memory or belief. It represents the
    NPC's learning from lived interaction, including repeated exposure,
    interpretation, and retained consequence.
-   Experiences may be created manually at runtime and may later be
    generated automatically from repeated observations during cognitive
    consolidation.
-   Beliefs can be wrong.
-   Beliefs have validation history.
-   Belief validation policy is itself a recorded fact for the NPC.
-   Memories, beliefs, experiences and relationships can be important or
    core.
-   Important and core are distinct.
-   Core context should be selected by policy rather than hard-coded
    into individual objects.
-   The initial context target is the top 10 core memories, beliefs and
    experiences.
-   NPCs should be able to request relevant prior cognitive information.
-   A future RAG/vector implementation should sit behind a retrieval
    abstraction rather than dictate the cognitive model.
-   Cognitive Consolidation occurs during NPC sleep and processes the
    previous day's cognitive material.
-   LLMs reason and propose; the simulation remains authoritative.