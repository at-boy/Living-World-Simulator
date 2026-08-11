# NPC Information Boundary

## Purpose

The Living World Simulator must maintain a strict boundary between **authoritative engine state** and the **information an NPC is allowed to perceive and reason about**.

An NPC LLM must **not** be given raw simulation attributes, engine facts, internal identifiers, or precise numerical values simply because those values exist in `WorldState`.

The simulation knows more than the NPC does.

The NPC should receive a representation of the world that corresponds to what that NPC could reasonably perceive, understand, remember, infer, or retrieve.

---

## Core Principle

> **The engine knows the world. The NPC knows only its interpretation of the world.**

The engine may know:

```text
Tree:
    growth = 87
    health = 92
    wood = 120
    species = "oak"
```

The NPC should not automatically receive:

```text
growth=87
health=92
wood=120
```

Instead, the perception system might produce something such as:

> "The old oak appears mature and healthy. It is a substantial tree and looks suitable for harvesting."

That description is what enters the NPC's cognitive world.

The NPC can then reason from that perception.

It does not magically know that the tree contains exactly 120 units of wood.

An experience is the NPC's retained learning from such repeated or
significant lived interaction. It can be created manually or later
produced by cognitive consolidation from repeated observations, but it
still remains an NPC-readable interpretation rather than engine truth.

---

# Information Flow

The intended architecture is:

```text
                 AUTHORITATIVE WORLD
                         │
                         ▼
                    WorldState
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
       Engine Systems          Object Attributes
              │                     │
              └──────────┬──────────┘
                         ▼
                 Perception Engine
                         │
            observer capabilities/skills
                         │
                         ▼
                 NPC Perception
                         │
                         ▼
                    Observation
                         │
                         ▼
               NPC Cognitive System
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           Memory      Belief    Experience
              │          │          │
              └──────────┼──────────┘
                         ▼
                  Cognitive Context
                         │
                         ▼
                      NPC LLM
```

The LLM should sit **at the end of this information-filtering process**, not directly against `WorldState`.

---

# Raw Engine State Is Not NPC Knowledge

The following distinction must be preserved:

| Engine concept          | NPC interpretation                                            |
| ----------------------- | ------------------------------------------------------------- |
| `wood = 120`            | "This is a substantial tree."                                 |
| `growth = 87`           | "The tree appears mature."                                    |
| `health = 92`           | "The tree looks healthy."                                     |
| `completion = 74`       | "The building looks well underway."                           |
| exact coordinates       | "The village is roughly north of here."                       |
| relationship score      | "Erik seems to trust her."                                    |
| hidden entity attribute | Potentially completely unknown                                |
| internal entity ID      | Never meaningful to the NPC                                   |
| event record            | Only if perceived/remembered through an appropriate mechanism |

The engine may use exact numbers to perform simulation.

The NPC does not automatically get those numbers.

---

# Perception Is a Translation Boundary

`PerceptionEngine` is not simply an attribute reader.

Its purpose is to transform:

```text
authoritative world state
+
observer capabilities
+
observer skills
+
observer context
```

into:

```text
what this NPC perceives
```

For example, two NPCs looking at the same tree may receive different perceptions.

### Experienced woodcutter

```text
"The oak is mature and healthy. The trunk is thick and straight,
with good timber potential. It looks ready for harvesting and should
yield a useful amount of wood."
```

### Inexperienced villager

```text
"It's a large old oak tree. It looks healthy."
```

### NPC with poor visibility

```text
"An old tree stands ahead, but the details are difficult to make out."
```

All three can be looking at the exact same authoritative object.

The difference comes from the observer.

---

# Skills Affect Perception

Skills should influence what an NPC can recognize or estimate.

For example:

```text
woodcraft = 90
```

might allow an NPC to recognize:

* species
* maturity
* health
* suitability for harvesting
* approximate timber quality
* approximate usefulness

Whereas:

```text
woodcraft = 10
```

might only allow:

* "large tree"
* "appears healthy"

The important point is that the engine does not simply expose:

```text
woodcraft=90
growth=87
health=92
wood=120
```

and ask the LLM to figure it out.

The **Perception Engine performs the information translation first**.

---

# Exact Numbers Should Be Treated Carefully

Humans generally do not perceive many physical quantities as exact engine values.

An NPC looking at a tree does not normally know:

```text
wood = 120
```

It might estimate:

```text
"perhaps enough timber for several small structures"
```

or:

```text
"likely to provide a good amount of usable lumber"
```

If an NPC has an appropriate skill, it may produce increasingly accurate estimates.

However, an estimate is still an **observation/perception**, not direct access to the authoritative value.

This distinction is important.

The engine can retain the authoritative value for simulation and debugging while giving the NPC only the perceptual result.

---

# Internal Evidence

The simulator may retain the raw information used to produce a perception for debugging, testing, auditing, and development.

For example an `Observation` may internally contain:

```text
description:
    "The old oak appears mature and healthy and looks suitable
     for harvesting."

confidence:
    0.92

metadata/internal evidence:
    subject_attributes:
        growth: 87
        health: 92
        wood: 120

    observer_capabilities:
        woodcraft: 80
```

This is acceptable **provided the internal evidence is never included in the NPC LLM context**.

The distinction is:

```text
Observation record
    ├── NPC-visible perception
    │      └── description
    │
    └── engine/debugging information
           └── raw attributes/evidence
```

The engine can know how an observation was produced without giving that information back to the NPC.

---

# Observation Is Not Belief

An observation represents a perception.

It should not automatically become an objective fact.

For example:

```text
Observation:
"The tree appears healthy."
```

The NPC may later form:

```text
Belief:
"Old oaks in this area are usually healthy."
```

Or:

```text
Belief:
"This particular oak is probably ready to harvest."
```

The belief can later be confirmed, weakened, or disproven.

The engine's actual value:

```text
health = 92
```

is neither the observation nor the belief.

It is authoritative simulation state.

---

# Memory Is Also NPC Knowledge

A Memory should contain what the NPC retained from its experience, not a hidden dump of engine state.

For example:

```text
Memory:
"I remember that the old oak near the village was ready
for harvesting."
```

rather than:

```text
Memory:
tree_00042.health = 92
tree_00042.growth = 87
tree_00042.wood = 120
```

The NPC may remember an approximate amount, an impression, an event, or a conclusion.

The memory should reflect the NPC's cognitive representation.

---

# Beliefs Must Not Become Engine Facts

A belief can be wrong.

For example:

```text
Belief:
"That oak will probably yield enough wood to repair the barn."
```

The engine may know that the actual available wood is insufficient.

The NPC should not receive the authoritative answer unless it has some legitimate perception or other information source that reveals it.

This allows beliefs to actually matter.

The simulation can therefore contain:

```text
World truth:
    wood = 120

NPC belief:
    "There should be plenty of wood."

Later:
    belief confirmed or disproven
```

That is an important part of the cognitive simulation.

---

# NPC LLM Context

When activating an NPC LLM, context should be assembled from NPC-accessible information.

Conceptually:

```text
NPC Context
├── identity
├── capabilities/skills
├── current perceptions
├── recent observations allowed by perception/retrieval rules
├── important memories
├── core memories
├── important beliefs
├── core beliefs
├── important experiences
├── core experiences
├── relevant relationships
├── retrieved relevant cognitive information
└── filtered cognitive lineage for reasoning and traceability
```

It should **not** contain:

```text
WorldState
EntityManager
raw entity attributes
resource quantities
internal IDs
simulation event internals
hidden attributes
engine-only metadata
```

unless some explicit future mechanism says that the NPC legitimately has access to such information.

---

# LLM Perception Engine

The LLM-based perception engine follows the same boundary as the deterministic perception engine.

Conceptually:

```text
WorldState
    +
Observer
    +
Observer Skills
    +
Relevant Context
        │
        ▼
Perception Engine
        │
        ▼
NPC-readable perception
        │
        ▼
Observation
        │
        ▼
NPC Cognition
```

The LLM used for perception may receive more structured engine-side information than the NPC itself receives, because it is acting as a **simulation subsystem translating reality into perception**.

That distinction must remain explicit.

The perception LLM is not the NPC.

It is part of the simulation machinery that produces what the NPC perceives.

The implementation enforces this translation boundary twice. Perception
engines validate a produced `Observation.description` against their
engine-only `PerceptionContext`, including protected nested numeric values and
internal IDs. `NPCContextAssembler` then asks the same boundary only for the
visible description; it neither receives `PerceptionContext` nor reads an
observation's evidence or metadata. Thus engine debugging evidence may remain
on an observation without becoming NPC cognition.

---

# Deterministic and LLM Perception

Both implementations must obey the same conceptual contract:

```text
DeterministicPerceptionEngine
        │
        ├── produces NPC perception
        │
        ▼
Observation


LLMPerceptionEngine
        │
        ├── produces NPC perception
        │
        ▼
Observation
```

The difference is how the translation is performed.

Neither should bypass the perception boundary.

---

# Actions Follow the Same Principle

The information boundary also applies in the other direction.

The NPC LLM should not directly modify the world.

Instead:

```text
NPC LLM
   │
   ▼
Cognition Protocol
   │
   ▼
Structured Action Request
   │
   ▼
Simulation validates action
   │
   ▼
WorldState changes
   │
   ▼
NPC eventually perceives result
```

For example, the LLM should request:

```text
"Harvest the oak."
```

rather than:

```text
tree_00042.wood -= 40
```

The simulation determines what actually happens.

---

# Important Architectural Rule

When implementing future systems, always ask:

> **Would a real NPC actually know this value, or are we accidentally giving the NPC access to engine truth?**

If the information is engine truth, it should normally remain behind the appropriate perception/cognition boundary.

The preferred approach is:

```text
Engine truth
    ↓
Perception / interpretation
    ↓
Observation
    ↓
Memory / Belief / Experience
    ↓
Cognitive retrieval
    ↓
NPC LLM
```

Not:

```text
Engine truth
    ↓
NPC LLM
```

---

# Development Rule for Future Commits

Any future feature that supplies information to an NPC LLM must explicitly document:

1. **What does the engine know?**
2. **What can the NPC perceive?**
3. **What information is transformed or abstracted?**
4. **What information is hidden?**
5. **What can the NPC remember?**
6. **What can the NPC infer or believe?**
7. **What information is supplied to the LLM?**
8. **What information remains engine-only for simulation/debugging?**

Do not implement a new NPC-facing information pathway until these boundaries are clear.

---

# Summary

The Living World Simulator intentionally models a difference between:

```text
WORLD TRUTH
```

and:

```text
NPC KNOWLEDGE
```

The simulation has authoritative facts.

NPCs have perceptions, memories, beliefs, experiences, and relationships.

Those are **not interchangeable**.

The NPC LLM must operate on the latter.

The engine must retain authority over the former.

This separation is essential for NPCs to have:

* incomplete knowledge
* different skill levels
* imperfect perception
* incorrect beliefs
* memories that differ between NPCs
* learning
* uncertainty
* disagreement
* discovery
* meaningful experiences

and ultimately for the world to feel like a world that NPCs actually **live in**, rather than a database that they can inspect.
