# NAS-007: Knowledge Compiler

**Status:** Locked  
**Version:** 1.0  
**Depends on:** [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)  
**Depends on:** [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)  
**Depends on:** [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)  
**Depends on:** [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)  
**Depends on:** [NAS-005: Temporal Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-005-Temporal-Model.md)  
**Depends on:** [NAS-006: Provenance Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-006-Provenance-Model.md)

---

## 1. Purpose
The NOVA Compiler is the deterministic semantic execution engine of the platform. Its responsibility is to transform organizational observations into validated, explainable, and reproducible organizational knowledge. The compiler starts *after* observations have been extracted, acting as a deterministic compiler rather than an ETL pipeline, workflow orchestrator, or probabilistic AI process.

---

## 2. Scope
This specification defines the compiler boundaries, input observation formats, the compilation pipeline phases, intermediate representations, compilation execution passes, code optimization boundaries, validation diagnostics, knowledge commits, and linking stages. It excludes observation extraction systems, AI parser implementation, intermediate representation binary schemas, and storage layer tables.

---

## 3. Definitions
* **Observation Bundle**: The atomic compilation unit of NOVA, containing originating artifact data, observations, extracted entities/relationships, extraction confidence, and parser metadata.
* **Compiler Pass**: An independent, side-effect-free, deterministic execution unit that consumes immutable input and produces immutable output.
* **Diagnostics**: Structured compiler warning and error objects classifying issue classes (Error, Warning, Info, Deferred Compilation) with affected semantic scopes.
* **Knowledge Commit**: The immutable, append-only compilation output containing compiled assertions, relationships, identity updates, temporal indices, and validation diagnostics.
* **Knowledge Linker**: The compiler subsystem responsible for integrating Knowledge Commits into the canonical Knowledge Graph.

---

## 4. Design Goals
* **Deterministic Semantic Compilation**: Meaning is created by deterministic compilation passes rather than probabilistic inference.
* **Incremental & Parallel Compilation**: Re-compiling only affected Observation Bundles and dependent Knowledge IR regions. Independent bundles may compile concurrently, provided execution ordering never affects the resulting graph.
* **Correctness Over Performance**: Compiler execution correctness and invariant verification take absolute precedence over execution speed.
* **Explainability & Reproducibility**: Ensuring all compilation steps are fully reproducible and explainable via the provenance graph.

---

## 5. Architecture
NOVA separates parsing from compilation at the Observation IR boundary:

$$\text{Artifacts} \rightarrow \text{Adapter} \rightarrow \text{Parser} \rightarrow \text{Bundle} \rightarrow \text{Observation IR} \;\mathbf{\big|\; Determinism\; Boundary\; \big|}\; \rightarrow \text{Validation} \rightarrow \text{Assertion IR} \rightarrow \text{Semantic Analysis} \rightarrow \text{Knowledge IR} \rightarrow \text{Knowledge Commit} \rightarrow \text{Linker} \rightarrow \text{Graph}$$

### AI Boundary Rules
Artificial Intelligence exists strictly outside the compiler boundary. AI may extract observations or detect candidate structures, but it must **never** create canonical identities, construct authoritative assertions, resolve contradictions, write provenance, or write directly to the Knowledge Graph.

---

## 6. Components

### 6.1 Compilation Pipeline
Compilation proceeds through three sequential phases:
1. **Observation Validation**: Verifies bundle integrity, required metadata, and schema correctness.
2. **Assertion Construction**: Converts observations into semantic assertions. This is the first stage where semantic commitments exist.
3. **Semantic Analysis**: Consists of:
   * *Ontology Validation*: Asserts type and relationship rules.
   * *Identity Resolution*: Resolves canonical identities and maintains lineage.
   * *Temporal Binding*: Assigns Occurrence, Observation, Assertion, and Compilation times.
   * *Provenance Binding*: Attaches artifacts, evidence, and rules.

### 6.2 Intermediate Representation (IR) Flow
* **Observation IR**: Represents raw observations containing no semantic commitments.
* **Assertion IR**: Represents semantic assertions supporting validation and reasoning.
* **Knowledge IR**: Represents fully validated organizational knowledge, containing resolved identity, temporal semantics, and provenance relationships.

### 6.3 Pass Manager & Optimization
The Pass Manager coordinates compiler execution. Permitted optimizations include duplicate elimination, semantic normalization, confidence propagation, and graph simplification. Optimization must never alter organizational meaning.

### 6.4 Verification
Mandatory compile-time validation of ontology, semantic, identity, and temporal invariants, as well as provenance completeness. Compilation fails if verification fails.

---

## 7. Invariants

### 7.1 Compiler-Enforced Invariants
* Observation IR is the compiler entry point.
* The compiler is deterministic; compiler passes are pure functions.
* Every assertion is compiler-generated and validated.
* Every assertion has a resolved canonical identity, temporal semantics, and provenance.
* Every compilation produces an append-only Knowledge Commit and ends with verification.
* Every compilation is replayable and explainable.

### 7.2 Architectural Invariants
1. The NOVA Compiler is the execution engine of the platform.
2. AI is not part of the deterministic compiler.
3. Observation IR defines the determinism boundary.
4. Semantic meaning is created by deterministic compilation.
5. Knowledge IR is the canonical compiler representation.
6. Knowledge Commits are immutable.
7. The Knowledge Linker integrates compiler output into the Knowledge Graph.
8. Compiler correctness takes precedence over performance.

---

## 8. Non-Goals
This specification does not define:
* Concrete KIR representation schemas or serialization protocols.
* Optimization algorithms.
* Parser and adapter plugin codes.
* Storage engine tables or database indices.
* Runtime query execution.

---

## 9. Future Extensions
Subsequent compiler and runtime modules extend this specification:
* [NAS-008: Knowledge Intermediate Representation (KIR)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-008-Knowledge-Intermediate-Representation.md)
* [NAS-009: Compiler Passes](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-009-Compiler-Passes.md)
* [NAS-010: Knowledge Runtime](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-III-Runtime/NAS-010-Knowledge-Runtime.md)

---

## 10. References
* [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)
* [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)
* [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)
* [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)
* [NAS-005: Temporal Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-005-Temporal-Model.md)
* [NAS-006: Provenance Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-006-Provenance-Model.md)
