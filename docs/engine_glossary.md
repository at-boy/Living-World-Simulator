# Engine Glossary

## Definition

**Purpose**

Template describing what may exist.

**Owns**

- key
- initial_attributes
- participating systems

**Does Not Own**

- runtime state
- relationships
- history

---

## Entity

**Purpose**

Runtime instance created from a Definition.

**Owns**

- identity
- definition_key
- attributes
- lifecycle

**Does Not Own**

- relationships
- simulation logic
- history

---

## Relationship

**Purpose**

Runtime connection between two Entities.

**Owns**

- source entity
- target entity
- relationship attributes

**Does Not Own**

- entity state
- simulation logic

---

## WorldState

**Purpose**

Represents the current objective state of the simulation.

**Owns**

- entities
- relationships
- current tick

**Does Not Own**

- simulation logic
- definitions

---

## DefinitionManager

**Purpose**

Registry of available definitions.

---

## EntityManager

**Purpose**

Owns the lifecycle of runtime entities.

Responsible for creating, validating, registering and removing entities.