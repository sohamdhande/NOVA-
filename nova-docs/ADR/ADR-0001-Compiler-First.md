# ADR-0001: Compiler-First Architecture

## 1. Context
Traditional organizational databases and knowledge tools (e.g., Notion, Confluence, wikis) model knowledge as static, manually maintained records. Over time, these records drift from actual operations, lack verifiable provenance, fail to track contradictions, and decay. In building NOVA, we need a data architecture that guarantees that the system's operational understanding is always derived from raw, audit-ready source material (Slack chats, meeting transcripts, commits).

## 2. Decision
We decide to adopt a **Compiler-First Architecture**. 
* Instead of storing knowledge as primary, editable database objects, knowledge is compiled on-demand or incrementally from immutable historical logs (Artifacts).
* The core system consists of a parser pipeline that transforms artifacts into a standardized intermediate representation (KIR) which is then resolved by a constraint solver into an operational state of understanding.
* Knowledge history is append-only. No deletion of truth history is supported; instead, the compiler resolves superseded claims based on chronological event logs.

## 3. Consequences
* **Positive**: 
  * Operational docs (PRDs, readmes) are reconstructible and provably correct.
  * Every decision or assumption has an audit trail (Provenance) leading to the specific chat transcript or document.
  * Contradictions can be flagged programmatically at compile-time when updating specifications.
* **Negative**:
  * Higher computational overhead because compilation passes must be executed over raw inputs.
  * Writing custom parsers and state solvers is more complex than standard CRUD database implementations.
* **Neutral**:
  * Storage engine choice (SQL vs. Graph DB) is decoupled from the conceptual specification layer.

## 4. Alternatives
* **CRUD Database Model**: Storing editable documents with database triggers. *Rejected* because it leads to documentation drift, loses historical logic, and breaks provenance tracing.
* **Raw Vector Storage Search**: Indexing raw documents and using standard RAG. *Rejected* because it lacks deterministic invariants, cannot resolve logical contradictions, and returns low-confidence averages.

## 5. Status
Accepted
