# NAS-003: Core Semantic Ontology (CSO)

**Status:** Locked  
**Version:** 1.0  
**Depends on:** [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)  
**Depends on:** [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)

---

## 1. Purpose
The Core Semantic Ontology (CSO) defines the canonical semantic vocabulary of the NOVA ecosystem. It specifies the first-class semantic concepts that exist within the NOVA system and the rules governing their meaning. Its purpose is to provide a stable semantic language that enables deterministic compilation, reasoning, provenance tracking, and long-term architectural consistency, decoupled from physical storage or UI schemas.

---

## 2. Scope
This specification defines core semantic types, semantic domains, the canonical relationship taxonomy, semantic invariants, composition rules, lifecycle requirements, and ontology evolution boundaries. It intentionally excludes physical storage configurations, query implementations, and AI inference logic.

---

## 3. Definitions
The ontology is organized into six functional **Semantic Domains**:
* **Agents (Intentional Action)**: *Agent, Organization, Team*. Roles (Customer, Developer, Reviewer) are implemented as composition traits, not separate types.
* **Knowledge (Structured Understanding)**: *Observation, Assertion, Evidence, Decision, Hypothesis, Experiment, Outcome, Requirement, Constraint, Policy, Risk, Metric*.
* **Work (Intentional Execution)**: *Goal, Task*. Core work concepts like *Project, Program, Sprint, Epic,* and *Milestone* are represented as compositions of Goals, Constraints, and Tasks.
* **Assets (Persistent Resources)**: *Repository, Service, Component, API, Dataset, Model, Infrastructure, Document*.
* **Artifacts (Immutable Activity Records)**: *Transcript, Email, Chat Message, Pull Request, Git Commit, Issue, PDF, Diagram, Presentation, Spreadsheet, Screenshot, Recording*.
* **Events (Temporal Occurrences)**: *Meeting, Deployment, Release, Incident, Interview, Benchmark, Build, Test Execution*.

---

## 4. Design Goals
* **Semantic Minimality**: A concept becomes a first-class type only if it cannot be represented as a composition of existing types, possesses unique relationships, unique invariants, and distinct lifecycle behaviors. Otherwise, it must be modeled as a trait, relationship, metadata, projection, or composition.
* **Semantic Correctness & Orthogonality**: Ensuring concepts do not overlap semantically.
* **Temporal & Provenance Compatibility**: Compatibility with continuous timeline tracking and traceable audit logs.
* **Compiler Friendliness & Explainability**: Enabling deterministic validation checks.

---

## 5. Architecture
CSO establishes a structured, canonical relationship taxonomy used by compilers and runtime queries:

```text
Relationship Taxonomy
│
├── Structural: PART_OF, CONTAINS
├── Dependency: DEPENDS_ON
├── Traceability: REFERENCES, DERIVES_FROM
├── Ownership: OWNED_BY, ASSIGNED_TO
├── Evidence: SUPPORTED_BY, CONTRADICTED_BY, VALIDATED_BY, INVALIDATED_BY
├── Temporal: PRECEDES, SUCCEEDS, SUPERSEDES
└── Semantic: IMPLEMENTS, TARGETS, CAUSES, AFFECTS, PRODUCES, CONSUMES, BLOCKS
```

---

## 6. Components

### 6.1 Composition Rules
CSO mandates semantic composition over semantic type proliferation:
* `Customer` $\rightarrow$ `Agent` + `CustomerRoleTrait`
* `Developer` $\rightarrow$ `Agent` + `DeveloperRoleTrait`
* `Bug` $\rightarrow$ `Requirement` + `DefectTrait`
* `Feature Request` $\rightarrow$ `Requirement` + `RequestedBy(Agent)`
* `Sprint` $\rightarrow$ `Goal` + `Time Constraint` + `Task Collection`
* `Project` $\rightarrow$ `Goal` + `Assets` + `Tasks` + `Events`

### 6.2 Lifecycle Principles
State machines are restricted to semantic types that require explicit state changes: *Decision, Experiment, Goal, Task, Requirement*. Assets and Artifacts derive operational state from immutable events. Lifecycle history is append-only and never overwritten.

---

## 7. Invariants

### 7.1 Compiler-Enforced Type Invariants
* **Decision**: Must have at least one owner, supporting evidence, context, and reasoning status. May not supersede itself.
* **Experiment**: Must test at least one hypothesis and produce an outcome.
* **Assertion**: Must be derived from one or more observations.
* **Evidence**: Must reference one or more artifacts.
* **Goal**: Must define measurable success criteria (metrics).
* **Task**: Must contribute to a Goal, Decision, or another Task.

### 7.2 Architectural Invariants
1. The ontology shall remain semantically minimal.
2. Semantic identity determines type existence.
3. Composition is preferred over specialization. Roles are traits, not types.
4. Events and Artifacts are immutable.
5. Assertions, Evidence, Decisions, Experiments, and Relationships are first-class semantic objects.
6. Compiler validation is deterministic and operates under a closed-world assumption.
7. Runtime reasoning operates under an open-world assumption.
8. Storage technology shall never influence ontology semantics.

---

## 8. Non-Goals
This specification does not define:
* Parser or compiler implementations.
* Knowledge Intermediate Representation (KIR) serialization protocols.
* Identity resolution algorithms.
* Provenance metadata storage implementation.
* Temporal reasoning solvers.
* AI agent query planning and retrieval configurations.

---

## 9. Future Extensions
The core ontology defined in NAS-003 serves as the shared vocabulary for subsequent platform modules:
* [NAS-007: Knowledge Compiler](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-007-Knowledge-Compiler.md)
* [NAS-008: Knowledge Intermediate Representation (KIR)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-008-Knowledge-Intermediate-Representation.md)
* [NAS-009: Compiler Passes](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-009-Compiler-Passes.md)

---

## 10. References
* [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)
* [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)
* [NAS-008: Knowledge Intermediate Representation (KIR)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-008-Knowledge-Intermediate-Representation.md)
