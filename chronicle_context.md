# NOVA Chronicle Context

This document chronicles the ideation, purpose, and technical implementation of **Chronicle**, a core subsystem of the NOVA ecosystem. It is intended to provide complete context to any AI or developer interacting with or extending the Chronicle feature.

## 1. Ideation: What and Why

### The Problem
In standard AI workflows and organizational setups, knowledge is ephemeral. Conversations contain critical context—decisions made, risks identified, assumptions held—but this context is easily lost or scattered. Over time, it becomes difficult to trace *why* a decision was made, *what* evidence supported it, or if assumptions have become stale.

### The Vision
**Chronicle** was built to solve this. It serves as an **immutable organizational knowledge graph**. Rather than relying on unstructured text, Chronicle continuously extracts, structures, and monitors the semantic state of a project or organization. It ensures that knowledge is not just stored, but is actively traceable, health-monitored, and cryptographically verified.

### Core Tenets
1. **Semantic Structure over Raw Text:** Converting conversations into distinct semantic objects (Decisions, Goals, Risks, etc.).
2. **Immutability and Traceability:** Every addition to the knowledge base is a "commit" (`KnowledgeCommit`), creating an append-only timeline.
3. **Determinism:** Report generation relies on deterministic algorithms rather than natural language generation to guarantee consistent insights.
4. **Knowledge Health:** Knowledge rots over time; Chronicle actively penalizes and surfaces "unhealthy" knowledge (e.g., stale assumptions, weak evidence).

---

## 2. Core Concepts: The Semantic Taxonomy

Chronicle structures knowledge into precise semantic categories. When an AI analyzes a conversation, it extracts objects that fit into these buckets:

- **Decisions:** What was decided, rationale, participants, and supporting evidence.
- **Goals:** Active objectives and their progress.
- **Risks:** Potential issues, their severity, and mitigation status.
- **Tradeoffs & Constraints:** System limits and sacrifices made.
- **Questions:** Unresolved or newly answered queries.
- **Principles:** Core rules or guidelines governing the work.
- **Action Items:** Tasks with assigned owners and statuses.
- **Assumptions:** Unvalidated beliefs that require monitoring.

As the Chronicle evolves, it tracks the lifecycle of these objects: *Knowledge Added, Updated, Superseded, Archived, or Invalidated.*

---

## 3. Technical Implementation

The Chronicle system is divided into an Extraction layer (Prompt/LLM), a Runtime Engine (Python Backend), and a User Interface (Dashboard).

### 3.1 Extraction Engine (`CHRONICLE_EXPORT_PROMPT`)
Located in `dashboard/src/constants/chronicleExportPrompt.ts`, this is the LLM instruction set. It prompts the AI to act as a "Knowledge Extraction Engine" and output a strict JSON payload containing the semantic objects (decisions, goals, risks, etc.) complete with confidence scores and evidence spans.

### 3.2 The Runtime Engine (`daily_chronicle.py` & `integrity.py`)
The heart of Chronicle lives in the runtime package (`nova/packages/runtime/`). It operates on a `KnowledgeStore` containing a chain of `KnowledgeCommit`s.

#### A. `generate_daily_chronicle`
This function is a pure, deterministic report generator. It parses a specific window of commits (e.g., "today", "7d") and outputs a structured aggregation of all new knowledge, memory evolution, and chronicle growth metrics (e.g., number of commits, artifacts, relationships).
* **Cryptographic Snapshotting:** The raw JSON report is sorted and hashed using SHA-256. This generates a `ChronicleSnapshot` (with a `snapshot_id`), ensuring the integrity and immutability of the report at a specific point in time.

#### B. `compute_knowledge_health`
This function monitors the "hygiene" of the knowledge base. It scans the entire commit chain and applies penalties for:
- Weak evidence (low confidence scores or missing evidence spans)
- Unresolved questions or open risks
- Unsupported decisions (missing supporting observations/artifacts)
- Stale assumptions (unvalidated for >= 30 days)
- Goals with 0% progress
- Action items missing owners

Based on these penalties, it calculates a `health_score` (0-100) and categorizes the knowledge base into a `health_zone` (`ROBUST`, `STABLE`, `DEGRADED`, or `CRITICAL`).

#### C. `compute_integrity_snapshot` (`integrity.py`)
This function provides advanced monitoring of knowledge quality and cross-type contradiction detection. It computes:
- **Knowledge Quality Profiles:** Evaluates evidence strength, provenance depth, temporal freshness, and verification status for each node.
- **Contradiction Reports:** Identifies conflicting relationships (e.g., 'CONTRADICTS') across different semantic types, such as "Assumption invalidated by Evidence" or "Principle conflicts with Decision".
- **Lonely Knowledge:** Flags isolated knowledge like decisions without execution paths or goals without action items.

Based on these metrics, it outputs an `IntegritySnapshot` with an overall health score, evidence coverage, freshness, and consistency indices. This snapshot data is actively surfaced in the daily chronicle via `integrity_alerts`.

### 3.3 Dashboard Integration
The dashboard UI (`dashboard/src/components/panels/knowledge/`) surfaces this data dynamically. It features:
- **Chronicle Overview:** Visualizes growth stats and the latest snapshot.
- **Integrity View:** Surfaces the overall health score, contradiction reports, knowledge status ledger, and lonely knowledge alerts derived from the `IntegritySnapshot`.
- **Daily Chronicle Report:** Displays the evolution of memory (added, superseded, invalidated).
- **Export Tools:** Allows users to easily trigger the extraction prompt to ingest new knowledge from external interactions.
- **Reasoning Injection:** In `nova/packages/reasoning/__init__.py`, the AI's reasoning compiler listens for keywords (like "change", "growth", "chronicle") and can autonomously inject the `DAILY_CHRONICLE_REPORT` fact into its context, making the AI hyper-aware of recent organizational knowledge.

---

## 4. Technical Specifications & Developer Reference

For AI agents and developers interacting with Chronicle, here are the explicit technical schemas and APIs used to manipulate the knowledge graph.

### 4.1 Data Models (Python)
The core compiler output is the `KnowledgeCommit`, located in `nova/packages/compiler/__init__.py`:

```python
@dataclass(frozen=True)
class KnowledgeCommit:
    commit_hash: str                  # SHA-256 of KIRNodes
    kir_nodes: list[KIRNode]          # The compiled semantic objects
    parent_hash: Optional[str]        # Hash of the previous commit (creates the chain)
    created_at: datetime
    trace: Optional[CompilerTrace]
    verification_report: Optional[VerificationReport]
    diagnostics: list[Diagnostic]
```
*Note: `commit_hash` is computed deterministically by sorting `kir_nodes` and ignoring mutable review states (e.g. `verification_status`).*

### 4.2 Dashboard API Endpoints
The frontend interacts with the Chronicle Extraction Engine via these primary endpoints:

1. **`POST /api/knowledge/preview`**
   - **Payload:** `{ source_type: string, content: string, title: string }`
   - **Purpose:** Runs the extraction LLM on the unstructured content and returns a preview containing parsed observations, suggested entities, and diagnostics.
   - **Response Flags:** Returns `partial_extraction: true` and `failed_categories` if the LLM failed to parse certain groups.

2. **`POST /api/knowledge/preview/retry`**
   - **Payload:** `{ source_type, content, title, retry_groups: string[] }`
   - **Purpose:** Re-runs the LLM targeted strictly at the `failed_categories` from a previous partial extraction.

3. **`POST /api/knowledge/compile`**
   - **Payload:** `{ source_type, content, title, approved_observation_ids: string[], approved_observations: any[] }`
   - **Purpose:** Takes human-approved observations, runs the compiler pipeline (`LoweringPass`, `DeduplicationPass`), computes the cryptographic hash, and persists the new `KnowledgeCommit`. Returns `{ commit_hash: string }`.

### 4.3 Integrating AI with Chronicle
If you are an AI attempting to fetch or query the Chronicle:
- **Writing:** Do not attempt to generate new knowledge objects manually. Always route raw unstructured text through the `/api/knowledge/preview` -> `compile` pipeline to ensure proper hashing, deduplication, and schema validation.
- **Reading:** Retrieve the latest state by parsing the output of `generate_daily_chronicle()` or fetching the latest `KnowledgeCommit` from the persistence layer (`store.get_latest()`).
- **Reasoning:** Use the `DAILY_CHRONICLE_REPORT` fact injected into your context to ground yourself in the latest accepted truths of the organization.

---

## Conclusion
Chronicle is more than just a database; it is an active participant in maintaining the integrity and health of organizational context. By cryptographically signing snapshots, penalizing stale data, and enforcing strict semantic structures, it guarantees that any AI or human interacting with NOVA operates on a shared, verified, and transparent foundation of truth.
