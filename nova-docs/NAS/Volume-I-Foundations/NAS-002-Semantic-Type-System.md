# NAS-002: NOVA Semantic Type System (NSTS)

**Status:** Locked  
**Version:** 1.0  
**Depends on:** [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)

---

## 1. Purpose
The NOVA Semantic Type System (NSTS) defines the universal semantic language used by the Knowledge Compiler, Runtime, and all downstream subsystems. 

NSTS is **not an ontology**. The ontology describes concrete organizational concepts, while NSTS defines how those concepts behave. By separating semantic behavior from domain ontology, the compiler remains stable even as the underlying organizational models and types evolve.

---

## 2. Scope
This specification defines the six-layer abstraction model of semantic objects, specifies standard schemas for nodes and edges, describes runtime execution contracts via traits and capabilities, and outlines the semantic validation bounds inside the Knowledge Compilation pipeline.

---

## 3. Definitions
* **Semantic Object**: The atomic runtime representation of compiled knowledge. Only two exist: `SemanticNode` and `SemanticEdge`.
* **Semantic Kind**: A broad high-level role category used by the compiler to reason without understanding domain concepts. Examples include: *Actor, Artifact, Asset, Knowledge, Event, Observation, Evidence, Governance, Structure, Work, Resource*.
* **Semantic Type**: A declarative domain definition. Examples include: *Decision, Repository, Feature, Customer, Meeting, Project, Goal, Risk, Requirement*.
* **Traits**: Reusable, compositional blocks describing structural and behavioral contracts. Replaces class inheritance. Examples include: *IdentityTrait, TemporalTrait, LifecycleTrait, ProvenanceTrait, EvidenceTrait, VersionTrait, PermissionTrait, ValidationTrait, ProjectionTrait, CompilerTrait*.
* **Capabilities**: Executable behaviors exposed by traits. Systems execute actions using capabilities rather than concrete types. Examples include: *Versionable, Mergeable, Searchable, Queryable, Projectable, Reasonable, Temporal, EvidenceAware, Observable, Supersedable*.
* **Compiler Passes**: Stages that consume capabilities to process semantic graphs. Examples include: *Parsing, Validation, Canonicalization, Entity/Relationship Resolution, Temporal/Provenance Linking, Confidence Calculation, Inference, Projection*.

---

## 4. Design Goals
* **Composition over Inheritance**: Prohibits deep inheritance hierarchies. All semantic meaning is composed dynamically from traits:
  
  $$\text{Decision} = \text{SemanticNode} + \text{IdentityTrait} + \text{TemporalTrait} + \text{LifecycleTrait} + \text{EvidenceTrait} + \text{ConfidenceTrait} + \text{ProvenanceTrait} + \text{ProjectionTrait}$$
  
* **Storage & Graph Independence**: The type system must remain stable regardless of underlying database engines or schema representations.
* **Extensibility & Determinism**: New types can be introduced without modifying the execution runtime, while compilation outputs remain reproducible and predictable.
* **Traceable & Versionable**: Built-in support for time-validity tracking and provenance mappings.

---

## 5. Architecture
NSTS introduces a strict layered semantic mapping that flows from raw objects to compiler operations:

$$\text{Semantic Object} \rightarrow \text{Semantic Kind} \rightarrow \text{Semantic Type} \rightarrow \text{Traits} \rightarrow \text{Capabilities} \rightarrow \text{Compiler Passes}$$

### Compiler Pipeline Integration
NSTS sits at the boundary of semantic validation within the compilation pipeline:

$$\text{Artifacts} \rightarrow \text{Signal Extraction} \rightarrow \text{Observation Generation} \rightarrow \text{Assertion Construction} \rightarrow \text{Semantic Type Validation (NSTS)} \rightarrow \text{KIR} \rightarrow \text{Knowledge Graph} \rightarrow \text{Knowledge Runtime}$$

---

## 6. Components

### 6.1 Semantic Node Schema
Every node represents a first-class entity conforming to this conceptual format:
* `id`: Unique identifier signature.
* `kind`: Target Semantic Kind.
* `type`: Target Semantic Type.
* `traits`: List of active trait composition blocks.
* `properties`: Local data attributes.
* `relationships`: References to adjacent edges.
* `metadata`: Operational tracking tags.

### 6.2 Semantic Edge Schema
Edges are treated as first-class, provenance-rich links, not anonymous pointers:
* `id`: Unique edge identifier.
* `kind`: Target Semantic Kind.
* `type`: Target Semantic Type (e.g., *DependsOn*, *Implements*, *Supersedes*, *OwnedBy*, *References*, *Produces*, *Supports*).
* `source`: ID of the origin SemanticNode.
* `target`: ID of the destination SemanticNode.
* `traits`: Active trait composition blocks (e.g., `ConfidenceTrait`, `TemporalTrait`).
* `properties`: Association data.
* `metadata`: Administrative metrics.

### 6.3 Compiler Contracts
Every Semantic Type exposes a contract detailing how the Knowledge Compiler executes basic operations:
* `Parse`: Extract signals.
* `Validate`: Verify constraint parameters.
* `Normalize`: Format data states.
* `Resolve`: Link identities.
* `Infer`: Derivate new relationships.
* `Project`: Compile output views.

---

## 7. Invariants
All systems implementing NSTS must satisfy these locked invariants:
1. Every runtime object is either a `SemanticNode` or `SemanticEdge`.
2. Every semantic object belongs to exactly one Semantic Kind and has exactly one Semantic Type.
3. Semantic Types define meaning only; they contain no executable code.
4. Traits define semantic characteristics; capabilities expose executable behavior.
5. Compiler passes and runtime engines operate strictly on capabilities, never branching on concrete domain types (e.g., using `supports(EvidenceAware)` instead of `is_instance(Decision)`).
6. Relationships are first-class objects capable of carrying provenance, confidence, and temporal metadata.
7. Composition is always preferred over inheritance.
8. Semantic transformations and compiler passes must be deterministic and reproducible.

---

## 8. Non-Goals
This specification does not define:
* The concrete organizational ontology (classes and fields).
* Specific identity resolution algorithms or temporal logic solvers.
* Intermediate Representation (KIR) encoding formats.
* Database schemas or vector storage index tuning parameters.
* AI inference or reasoning engines.

---

## 9. Future Extensions
* **Dynamic Trait Registry**: Allow runtime plugins to register new capabilities and compile-time validation hooks.
* **Multi-Language Schema Bindings**: Auto-generate Protobuf, TypeScript, and Python schemas directly from the NSTS compiler specification.

---

## 10. References
* [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)
* [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)
* [NAS-008: Knowledge Intermediate Representation (KIR)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-008-Knowledge-Intermediate-Representation.md)
