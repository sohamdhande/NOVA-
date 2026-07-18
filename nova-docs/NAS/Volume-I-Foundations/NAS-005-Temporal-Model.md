# NAS-005: Temporal Architecture

**Status:** Locked  
**Version:** 1.0  
**Depends on:** [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)  
**Depends on:** [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)  
**Depends on:** [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)  
**Depends on:** [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)

---

## 1. Purpose
The Temporal Architecture defines how NOVA models the evolution of organizational reality, knowledge, and compiler state over time. Time is not metadata; it is a first-class architectural subsystem. This specification ensures that the organization's complete history can always be reconstructed deterministically without mutating past knowledge.

---

## 2. Scope
This specification defines temporal primitives, temporal dimensions, temporal identity, event ordering rules, historical reconstruction targets, and temporal relationships. It excludes database timestamp formats, SQL-specific clock variables, and physical indexing logic.

---

## 3. Definitions
* **Instant**: A zero-duration point within a temporal dimension.
* **Interval**: A bounded period between two instants, modeled conceptually as a half-open interval: `[start, end)`.
* **Duration**: The measurable distance between two instants.
* **Event**: An immutable occurrence in time that produces change.
* **Temporal Stage**: An immutable snapshot of a semantic object immediately following an event.
* **Change**: The transition between two temporal stages caused by one or more events.

---

## 4. Design Goals
* **Temporal Immutability**: History is never modified; new knowledge is appended and nothing is overwritten.
* **Event-Centric Time**: Time attaches directly to events; semantic objects do not change, but events create new temporal stages.
* **Historical Reconstructability**: Complete organizational state must be reconstructible for any historical instant.
* **Deterministic Replay**: Replaying the same sequence of events must reconstruct the identical historical knowledge state.
* **Reality Independence**: Separating reality changes from the compiler's operational understanding updates.

---

## 5. Architecture
NOVA adopts a four-dimensional temporal architecture mapping different milestones of reality and observation:

```text
Temporal Dimensions
│
├── 5.1 Occurrence Time (Tocc)  ──► When the event happened in reality.
├── 5.2 Observation Time (Tobs) ──► When the event was first observed.
├── 5.3 Assertion Time (Tasr)   ──► When an actor formally asserted a claim.
└── 5.4 Compilation Time (Tcmp) ──► When the compiler accepted the assertion.
```

### Event-Centric Temporal Model
Time links to events rather than the semantic objects themselves:

$$\text{Identity} \rightarrow \text{Event} \rightarrow \text{Temporal Stage} \rightarrow \text{Event} \rightarrow \text{Temporal Stage}$$

---

## 6. Components

### 6.1 Temporal Identity & Lineage
Identity remains stable across temporal stages. Revisions create new immutable stages for a stable identity, while supersessions generate new successor identities linked through lineage graphs.

### 6.2 Historical Reconstruction
The runtime compiles and resolves the complete knowledge graph, including relationships, decisions, identities, and evidence, for any historical instant. This reconstruction is completely deterministic.

### 6.3 Event Ordering & Relationships
Event ordering preserves causal consistency (monotonic progression, causal ordering). Temporal relationships follow interval-based reasoning: *PRECEDES, SUCCEEDS, MEETS, OVERLAPS, STARTS, FINISHES, DURING, CONTAINS, EQUALS*.

### 6.4 Late-Arriving Knowledge
Late-arriving evidence does not rewrite history. Instead, new assertions are appended, preserving the original compilation timeline and keeping past states reproducible.

---

## 7. Invariants

### 7.1 Compiler-Enforced Invariants
* **Identity Precedence**: Events cannot reference an identity before its creation event exists.
* **Observation Consistency**: Observation Time ($T_{\text{obs}}$) cannot precede Occurrence Time ($T_{\text{occ}}$).
* **Assertion Consistency**: Assertions ($T_{\text{asr}}$) cannot precede observations ($T_{\text{obs}}$).
* **Compilation Consistency**: Compilation Time ($T_{\text{cmp}}$) must never precede Assertion Time ($T_{\text{asr}}$) and must progress monotonically.
* **No Temporal Orphans**: Every temporal stage must trace to an originating event.

### 7.2 Architectural Invariants
1. Time is a first-class architectural subsystem.
2. Events are the sole drivers of temporal evolution.
3. Semantic objects are reconstructed from temporal stages.
4. History is immutable.
5. Reality and operational knowledge are separate.
6. Historical reconstruction must always be deterministic and reproducible.
7. Temporal reasoning is interval-based.
8. Temporal contradictions preserve provenance.
9. Late-arriving knowledge never rewrites history.
10. Compilation ordering must preserve causality.

---

## 8. Non-Goals
This specification does not define:
* Logical clock implementation details (vector clocks, Lamport timestamps).
* Physical database timestamp encoding formats.
* SQL database temporal table parameters or indexing logic.

---

## 9. Future Extensions
The temporal foundations defined here govern future runtime and compiler modules:
* [NAS-006: Provenance Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-006-Provenance-Model.md)
* [NAS-007: Knowledge Compiler](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-II-Compiler/NAS-007-Knowledge-Compiler.md)

---

## 10. References
* [NAS-001: Theory of Organizational Knowledge](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-001-Theory-of-Organizational-Knowledge.md)
* [NAS-002: NOVA Semantic Type System (NSTS)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-002-Semantic-Type-System.md)
* [NAS-003: Core Semantic Ontology (CSO)](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-003-Core-Ontology.md)
* [NAS-004: Identity Architecture](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/NAS/Volume-I-Foundations/NAS-004-Identity-Model.md)
