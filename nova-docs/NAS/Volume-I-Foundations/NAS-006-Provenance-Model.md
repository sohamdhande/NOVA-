# NAS-006: Provenance Architecture

**Status:** Locked  
**Version:** 1.0  
**Depends on:** [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)  
**Depends on:** [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)  
**Depends on:** [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)  
**Depends on:** [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)  
**Depends on:** [NAS-005: Temporal Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-005-Temporal-Model.md)

---

## 1. Purpose
The Provenance Architecture defines how NOVA records, preserves, explains, and reproduces the origin of organizational knowledge. Provenance is not descriptive metadata; it is the causal history of knowledge compilation. Every assertion accepted by NOVA must be explainable through immutable provenance.

---

## 2. Scope
This specification defines the provenance graph, core provenance primitives, compiler execution records, evidence lineages, explainability rules, and distributed replication constraints. It excludes physical storage schemas, serialization formats (like RDF or JSON-LD), and graph database query implementations.

---

## 3. Definitions
The Provenance Graph consists of five irreducible primitives:
* **Artifact**: The immutable organizational object (e.g., *Git commit, transcript, chat message, email, PDF, issue, screenshot*) from which knowledge originates. These terminate every provenance chain.
* **Evidence**: Links one or more artifacts to semantic assertions, carrying metrics for *confidence, temporal scope, relevance,* and *validation status*.
* **Compiler Pass**: A record representing one deterministic execution step performed by the compiler.
* **Inference**: A record representing a logical derivation (e.g., *applied rule, antecedents, conclusion, justification*).
* **Human Decision**: A record representing an explicit human intervention (e.g., *manual override, validation approval, manual assertion*). These are accountable rather than reproducible.

NOVA distinguishes three categories of provenance producers:
* **Human**: Accountable, contextual, and irreproducible.
* **Rule-Based**: Deterministic, compiler-native, and fully reproducible.
* **AI**: Probabilistic, non-deterministic, and always provisional until validated.

---

## 4. Design Goals
* **Provenance is Foundational**: Assertions without provenance are ungrounded and not considered organizational knowledge.
* **Provenance is Immutable**: Provenance records are never overwritten or deleted; corrections append new records.
* **Explainability Emerges from Provenance**: Explanations are derived exclusively by traversing the provenance graph.
* **Provenance is Deterministic**: Identical compilation states must consistently generate matching provenance logs.

---

## 5. Architecture
NOVA separates Identity, Belief, and Provenance into three independent, referencing graphs:

```text
Identity Graph  ──► What exists.
Knowledge Graph ──► What is believed.
Provenance Graph ──► Why it is believed.
```

No graph owns another; they interact via immutable references.

### 5.1 Provenance Graph Topology
The Provenance Graph is a Directed Acyclic Graph (DAG). Every node represents a provenance event, and every edge represents derivation. Cycles are strictly prohibited.

---

## 6. Components

### 6.1 Compiler Provenance
Every compiler execution produces a **Compiler Pass Record** containing:
* Compiler identity, compiler version, and active ruleset.
* Consumed artifacts and prior assertions.
* Observation events, inference records, and validation outcomes.
* Generated output assertions, timestamps, and a determinism fingerprint.

### 6.2 Evidence Lineage
Evidence evolves through append-only actions (supporting, contradicting, superseding, or reinforcing). New evidence extends lineage paths rather than modifying existing metrics.

### 6.3 Explainability Graph Traversal
Explanations are calculated by running a graph traversal over the provenance chain to answer:
* *Why is this assertion believed?*
* *Which artifacts and evidence support or contradict it?*
* *Which compiler rules and version executed the compilation?*
* *Which human decisions or assumptions influenced the conclusion?*
* *Can this compilation outcome be reproduced?*

### 6.4 Distributed Provenance
Distributed compilation preserves provenance through append-only replication, causal consistency, and deterministic contradiction/resolution recording.

---

## 7. Invariants

### 7.1 Compiler-Enforced Invariants
* Every assertion must have a valid provenance record.
* Every provenance chain must terminate at one or more immutable Artifacts.
* Every compiler pass must write a provenance record.
* The Provenance Graph must remain acyclic.
* Human decisions must bind to authenticated user identities.
* AI-generated assertions remain provisional until validated.
* Merges and splits must preserve historical provenance.
* Every provenance edge must be temporally annotated.

### 7.2 Architectural Invariants
1. Provenance is a first-class architectural subsystem.
2. Knowledge without provenance is not organizational knowledge.
3. Provenance is immutable and records computational history.
4. Identity, Knowledge, and Provenance remain independent graphs.
5. Explainability is graph traversal.
6. Provenance supports deterministic replay.
7. Historical provenance is never destroyed.

---

## 8. Non-Goals
This specification does not define:
* Relational or graph database storage schemas.
* Serialization syntax (like RDF, JSON-LD, or Turtle).
* Graph index structures or query syntax.
* Frontend graph visualization dashboards.

---

## 9. Future Extensions
The provenance models defined here establish constraints for:
* [NAS-007: Knowledge Compiler](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-007-Knowledge-Compiler.md)
* [NAS-008: Knowledge Intermediate Representation (KIR)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-008-Knowledge-Intermediate-Representation.md)
* [NAS-010: Knowledge Runtime](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-III-Runtime/NAS-010-Knowledge-Runtime.md)

---

## 10. References
* [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)
* [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)
* [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)
* [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)
* [NAS-005: Temporal Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-005-Temporal-Model.md)
