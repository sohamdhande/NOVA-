# NAS-009: Compiler Pass Architecture

**Status:** Locked  
**Version:** 1.0  
**Depends on:** [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)  
**Depends on:** [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)  
**Depends on:** [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)  
**Depends on:** [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)  
**Depends on:** [NAS-005: Temporal Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-005-Temporal-Model.md)  
**Depends on:** [NAS-006: Provenance Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-006-Provenance-Model.md)  
**Depends on:** [NAS-007: Knowledge Compiler](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-007-Knowledge-Compiler.md)  
**Depends on:** [NAS-008: Knowledge Intermediate Representation (KIR)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-008-Knowledge-Intermediate-Representation.md)

---

## 1. Purpose
The Compiler Pass Architecture defines how the NOVA Compiler evolves Knowledge Intermediate Representation (KIR). It establishes a deterministic, modular execution model where the compiler core contains minimal logic, and all semantic compilation behaviors emerge from coordinated passes. Swapping or extending passes allows compiler evolution without core restructuring.

---

## 2. Scope
This specification defines the query engine, compiler passes, pass contracts, scheduling rules, caching frameworks, semantic transactions, verifier loops, and plugin registry. It excludes overall runtime query engines, physical databases, and API schemas.

---

## 3. Definitions
* **Compiler Pass**: The atomic, side-effect-free unit of deterministic calculation. Consumes and produces immutable KIR.
* **Pass Registry**: The compiler module responsible for pass discovery, versioning, dependency indexing, and plugin hooks.
* **Query Engine**: The coordinator that executes passes on-demand, resolving dependencies and caching results.
* **Analysis**: An immutable compiler artifact (computed by analysis passes) that is lazy, cached, and re-evaluated incrementally.
* **Semantic Transaction**: An immutable delta record outlining additions, removals, and rewrites. Applied to KIR only after verification passes succeed.

---

## 4. Design Goals
* **Deterministic Execution & Modularity**: Passes behave as pure mathematical functions on KIR models.
* **Query-Driven Incremental Compilation**: Recomputes only affected queries, invalidating caches at modular boundaries.
* **Verification-First Transactions**: All modifications are staged as transactions and verified before merging.
* **Safe Parallel Execution**: Permits concurrent execution of passes using spatial isolation and immutable data interfaces, prohibiting shared mutable state.

---

## 5. Architecture
NOVA coordinates compilation using a decoupled query-and-scheduler loop:

$$\text{Compiler} \rightarrow \text{Pass Registry} \rightarrow \text{Query Engine} \rightarrow \text{Scheduler} \rightarrow \text{Pass Manager} \rightarrow \text{Compiler Passes} \rightarrow \text{Semantic Transaction} \rightarrow \text{Verifier} \rightarrow \text{Updated KIR}$$

### Query-Driven Execution
Downstream systems query the compilation target. The Query Engine calculates dependencies backwards through the Pass Registry, schedules execution orders using the Scheduler, and runs passes under the Pass Manager.

---

## 6. Components

### 6.1 Pass Categories
The architecture defines six functional pass classes:
* **Analysis Passes**: Compute reusable stats without changing KIR (e.g., *Identity/Temporal/Provenance Analyses*).
* **Transformation Passes**: Rewrite KIR into semantically equivalent structures (e.g., *Canonicalization, Normalization*).
* **Optimization Passes**: Streamline KIR without altering meaning (e.g., *Dead Assertion Elimination, Confidence Propagation*).
* **Verification Passes**: Assert compiler invariants (e.g., *Ontology/Temporal Verification*).
* **Lowering Passes**: Convert KIR between abstraction levels.
* **Diagnostic Passes**: Produce compile-time warnings and errors.

### 6.2 Pass Contracts & Capabilities
Every pass registers a contract declaring:
* Pass name and version.
* Read/Write/Preserved dialects.
* Required and produced analyses.
* Support for incremental processing, purity, and determinism.

### 6.3 Scheduler & Pass Manager
The Scheduler defines execution trees, while the Pass Manager acts as the kernel, managing execution context, resolving transactions, gathering diagnostics, and writing outputs without executing semantic logic directly.

---

## 7. Invariants

### 7.1 Compiler Pass Invariants
Every compiler pass must:
* Be deterministic, side-effect free, and behave as a pure function.
* Declare explicit capabilities, dialect scopes, and analysis dependencies.
* Return structured diagnostics rather than printing them.
* Support offline replay testing.

### 7.2 Pass Manager Invariants
The Pass Manager must enforce:
* Query-driven execution and lazy analysis evaluation.
* Dependency-aware scheduling and deterministic execution.
* Safe parallel pass concurrency.
* Complete replayability of all compilation transactions.

### 7.3 Architectural Invariants
1. The Pass Manager is the execution kernel of the NOVA Compiler.
2. Compiler passes communicate exclusively through immutable KIR.
3. Every transformation produces a Semantic Transaction.
4. Verification precedes every KIR update.
5. Parallel execution never relies on shared mutable state.
6. Compiler evolution occurs by introducing new passes, analyses, and dialects.

---

## 8. Non-Goals
This specification does not define:
* Concrete compiler optimization algorithms.
* Runtime scheduling or thread management.
* Storage engine tables or database indices.
* Graph query APIs or serialization frameworks.

---

## 9. Future Extensions
The pass architecture defined here governs runtime context compilation:
* [NAS-010: Knowledge Runtime](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-III-Runtime/NAS-010-Knowledge-Runtime.md)
* [NAS-011: Reasoning Compiler](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-III-Runtime/NAS-011-Reasoning-Engine.md)

---

## 10. References
* [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)
* [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)
* [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)
* [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)
* [NAS-005: Temporal Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-005-Temporal-Model.md)
* [NAS-006: Provenance Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-006-Provenance-Model.md)
* [NAS-007: Knowledge Compiler](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-007-Knowledge-Compiler.md)
* [NAS-008: Knowledge Intermediate Representation (KIR)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-008-Knowledge-Intermediate-Representation.md)
