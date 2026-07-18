# NAS-008: Knowledge Intermediate Representation (KIR)

**Status:** Locked  
**Version:** 1.0  
**Depends on:** [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)  
**Depends on:** [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)  
**Depends on:** [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)  
**Depends on:** [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)  
**Depends on:** [NAS-005: Temporal Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-005-Temporal-Model.md)  
**Depends on:** [NAS-006: Provenance Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-006-Provenance-Model.md)  
**Depends on:** [NAS-007: Knowledge Compiler](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-007-Knowledge-Compiler.md)

---

## 1. Purpose
The Knowledge Intermediate Representation (KIR) is the canonical execution language of the NOVA Compiler. KIR does not represent stored or persisted knowledge; it represents the deterministic *construction* of organizational knowledge. It exists exclusively to support compilation, optimization, verification, replay, and commit generation, remaining entirely independent of database storage, runtime query systems, or user interfaces.

---

## 2. Scope
This specification defines the intermediate representation levels, symbol table structures, RVSDG dataflow model, compiler dialects, compiler instructions, canonicalization passes, optimization, verification, incremental compilation, and commit generation. It excludes physical database schemas, query engines, and API serialization models.

---

## 3. Definitions
* **KIR Module**: The complete, immutable semantic compilation unit for one Observation Bundle, containing operations, regions, symbol tables, diagnostics, and compiler metadata.
* **KIR Operation**: The fundamental execution unit containing an *opcode, operands, results, attributes,* and *regions*. Operations produce immutable semantic values.
* **Semantic Instruction Set**: The core operations: `ENTITY_DECLARE`, `IDENTITY_BIND`, `RELATION_CREATE`, `TRAIT_APPLY`, `TEMPORAL_SCOPE`, `PROVENANCE_ATTACH`, `IDENTITY_PHI`, and `DIAGNOSTIC_EMIT`.
* **Symbol Table**: Isolated metadata scopes including the *Identity Table, Ontology Table, Provenance Table,* and *Diagnostics Table*.
* **KIR Dialects**: Independent semantic operation namespaces:
  * *Ontology Dialect*: Entities, relationships, traits, constraints.
  * *Identity Dialect*: Identity binding, merge, lineage, canonical references.
  * *Temporal Dialect*: Occurrence, observation, assertion, and compilation times, temporal validity.
  * *Provenance Dialect*: Artifacts, evidence, compiler/inference lineage, human decisions.
  * *Diagnostics Dialect*: Warnings, info, verification failures.

---

## 4. Design Goals
* **Deterministic Execution & Immutability**: Identical compiler inputs must produce identical, side-effect-free KIR modules.
* **Static Single Assignment (SSA) & RVSDG**: Every value has exactly one definition. Compiler reasoning is declarative and dataflow-driven, representing dependencies like provenance, temporal ordering, and semantic constraints.
* **Strong Typing**: Semantic types derive directly from NAS-002, enabling compile-time type verification.
* **Incremental Compilation**: Supports query-based compilation where invalidation occurs at module granularity, fingerprinted for reuse.

---

## 5. Architecture
KIR sits between Observation IR and final commit generation:

$$\text{Observation Bundle} \rightarrow \text{Observation IR} \rightarrow \text{Lowering} \rightarrow \text{KIR Module} \rightarrow \text{Canonicalization} \rightarrow \text{Optimization} \rightarrow \text{Verification} \rightarrow \text{Knowledge Commit}$$

### Intermediate Representation Levels
* **Observation IR**: Represents extracted observations (raw facts, candidate entities, relationships) containing no semantic commitments.
* **Knowledge Intermediate Representation (KIR)**: The compiler's execution language. Encodes validated semantic calculations, identity/temporal bindings, provenance links, and diagnostics.

---

## 6. Components

### 6.1 Symbol Tables
Separate compiler metadata tables isolate compilation metrics (Identity, Ontology, Provenance, Diagnostics) from execution graph operations.

### 6.2 Canonicalization & Optimization
* **Canonicalization**: Performs duplicate normalization, structural simplification, and deterministic ordering to ensure semantically equivalent inputs produce matching KIR.
* **Optimization**: Executes duplicate elimination, dead assertion elimination, confidence propagation, transitive reduction, and semantic simplification without altering organizational meaning.

### 6.3 Verification
Mandatory compile-time validation verifying ontology rules, identity consistency, temporal correctness, provenance completeness, and semantic constraints. Verification failure aborts compilation.

### 6.4 Knowledge Commit Generation
The compiler backend lowers verified KIR operations into immutable Knowledge Commits (comprising additions, removals, identity/temporal/provenance updates, and diagnostics) for database integration.

---

## 7. Invariants

### 7.1 Compiler-Enforced Invariants
* KIR is immutable, deterministic, strongly typed, and side-effect free.
* Every semantic value has exactly one definition.
* Compiler passes, optimizations, and verification operate exclusively over KIR.
* KIR is runtime and database independent.
* KIR represents semantic computation history rather than stored knowledge.
* Every KIR module is replayable, explainable, and independently compilable.

### 7.2 Architectural Invariants
1. KIR is the canonical execution language of the NOVA Compiler.
2. KIR represents knowledge construction rather than stored knowledge.
3. Observation IR is lowered into KIR.
4. KIR Modules are the unit of compilation.
5. Dialects are used for compiler extensibility.
6. Compiler passes communicate exclusively through KIR.
7. Canonicalization precedes optimization.
8. Verification precedes commit generation.

---

## 8. Non-Goals
This specification does not define:
* Relational, graph, or vector database schemas.
* Database persistence models or storage optimization.
* Runtime query execution or retrieval systems.
* External API designs or serialization formats.

---

## 9. Future Extensions
Subsequent platform chapters extend the KIR model:
* [NAS-009: Compiler Passes](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-009-Compiler-Passes.md)
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
