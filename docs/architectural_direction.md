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

For post-v0.5 autonomous settlement development, a parallel engine-owned
planning loop is intended:

    Scenario mandate / settlement need
        ↓
    Persistent goal and objective graph
        ↓
    NPC-visible interpretation and proposed priority
        ↓
    Validated work assignment / domain action
        ↓
    Systems consume time and resources
        ↓
    Events and objective evidence
        ↓
    Engine evaluates goal and settlement-stage progress

Important principles:

-   Observation is not an Event.
-   Observation is a perception, not a raw attribute dump.
-   Internal evidence may be retained for debugging, but raw world data
    is not automatically exposed to an NPC.
-   `NPCPerceptionBoundary` validates an observation's visible prose before
    cognition can receive it. Engine-side perception validation may use
    `PerceptionContext`; later context assembly must use only the observation
    description, never its evidence, metadata, or engine context.
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
-   Goals, objective completion, and settlement-stage promotion are
    authoritative engine state. LLMs may propose means or priorities but may
    not declare them achieved.
-   A goal known by an NPC is an interpretation of an engine-recognized mandate
    or personal intention, not permission to expose the goal's hidden criteria,
    internal IDs, or exact world-state evidence.
-   Off-map homelands and markets may be represented by deliberately partial
    engine-owned interfaces. They must not masquerade as fully simulated places
    or leak hidden outcome probabilities to NPCs.
-   Shared agendas do not imply shared conclusions. Different NPCs may reason
    from the same allowed agenda and action vocabulary using different
    holder-scoped observations, memories, beliefs, experiences, and social
    knowledge.
-   Convening a council requires an engine-recognized caller/coordinator under
    the current API, but a settlement-wide issue need not be represented as
    that caller's personal idea or preferred outcome.
-   NPC-facing LLMs receive only filtered perception, memory, belief,
    experience and retrieval results. They do not receive raw world
    attributes, hidden engine identifiers, or direct access to simulation
    truth by default.
