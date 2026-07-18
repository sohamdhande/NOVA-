# CHRONICLE Audit

## 1. Data Model Audit

### 1.1 `KnowledgeCommit`

- Definition: [nova/packages/compiler/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/compiler/__init__.py:21)
- Exact line range: `21-29`
- Immutability: `@dataclass(frozen=True)` at line `21`, so the dataclass itself is frozen.
- Fields:
  - `commit_hash: str`
  - `kir_nodes: list[KIRNode]`
  - `parent_hash: Optional[str]`
  - `created_at: datetime`
  - `trace: Optional[CompilerTrace] = None`
  - `verification_report: Optional[VerificationReport] = None`
  - `diagnostics: list[Diagnostic] = None`
- Reality mismatch:
  - The dataclass is frozen, but `kir_nodes` and `diagnostics` are mutable lists, so the object is only shallowly immutable.
  - `created_at` is not part of the hash input and is assigned with `datetime.now(timezone.utc)` during compile at lines `99-107`.

### 1.2 `KIRNode`

- Definition: [nova/packages/kir/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/kir/__init__.py:13)
- Exact line range: `13-21`
- Immutability: `@dataclass(frozen=True)` at line `13`.
- Fields:
  - `op: str`
  - `inputs: list[str]`
  - `output_id: str`
  - `metadata: dict[str, Any]`
  - `dialect: Dialect = Dialect.GENERIC`
  - `verification_status: str = "unverified"`
  - `verified_at: Optional[str] = None`
- Reality mismatch:
  - I could not locate per-category subclasses or variants for `Decision`, `Goal`, `Risk`, `Tradeoff`, `Constraint`, `Question`, `Principle`, `ActionItem`, or `Assumption`.
  - The code uses one generic `KIRNode`; semantic category is stored in `metadata["type"]` or `metadata["semantic_type"]`, not in subtype classes.
  - Like `KnowledgeCommit`, this is only shallowly immutable because `inputs` and `metadata` remain mutable containers.

### 1.3 Semantic category source of truth

- Definition: [nova/packages/ontology/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/ontology/__init__.py:4)
- Exact line range: `4-29`
- Relevant enum members present:
  - `DECISION`, `ASSUMPTION`, `RISK`, `GOAL`, `CONSTRAINT`, `TRADEOFF`, `ALTERNATIVE`, `QUESTION`, `ACTION_ITEM`, `PRINCIPLE`
- Reality mismatch:
  - `ASSUMPTION` exists, but `Hypothesis`, `Experiment`, `Metric`, `Task`, etc. also exist, so the ontology is broader than the prompt’s expected Chronicle categories.

### 1.4 Lowering from observations to KIR

- Definition: [nova/packages/kir/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/kir/__init__.py:44)
- Exact line range: `44-74`
- Behavior:
  - `lower_to_kir` produces one generic `KIRNode`.
  - `metadata` contains:
    - `"type": observation.type.value`
    - `"content": observation.content`
    - `"identity": observation.identity`
  - `op` is chosen from dialect heuristics, not semantic type hierarchy.
- Reality mismatch:
  - There is no dedicated relationship-node lowering path here.

### 1.5 Relationship / edge models

#### Lineage edges

- Definition and persistence: [nova/packages/runtime/persistence.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/persistence.py:51)
- Exact line ranges:
  - schema: `51-66`
  - insert/update: `198-219`
  - readers: `221-235`
- Storage:
  - SQLite table `lineage_edges(from_id, to_id, verb, created_at)`
  - SQLite table `node_lineages(node_id, lineage_id, occurrence_time)`
- Query methods:
  - `get_lineage(lineage_id) -> list[dict]`
  - `get_node_lineage(node_id) -> Optional[dict]`
  - `get_lineage_edges() -> list[dict]`
- Relationship verbs observed in code/tests:
  - `SUPERSEDES` is used explicitly in runtime integrity and tests.
- Reality mismatch:
  - I could not locate a typed enum/class for lineage verbs. They are stored as freeform strings.

#### Semantic relationship facts

- Runtime consumers: [nova/packages/runtime/integrity.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/integrity.py:113), [nova/packages/runtime/integrity.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/integrity.py:291)
- Exact line ranges:
  - relationship collection: `113-114`
  - contradiction handling for `"CONTRADICTS"`: `291-318`
- Storage model:
  - Relationship semantics are not stored in a dedicated table.
  - They are inferred from KIR node metadata where `type == "RELATIONSHIP"` and `content` contains keys like `source`, `target`, and `relation`.
- Reality mismatch:
  - I could not locate a first-class edge/relationship dataclass for semantic graph links such as `CONTRADICTS` or `INVALIDATES`.
  - `INVALIDATES` is mentioned in the prompt, but I did not find a concrete storage/query implementation for that verb.

### 1.6 `KnowledgeStore`

#### In-memory `KnowledgeStore`

- Definition: [nova/packages/runtime/store.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/store.py:9)
- Exact line range: `9-41`
- Methods present:
  - `subscribe(self, callback)`
  - `commit(self, kc: KnowledgeCommit)`
  - `get_latest(self) -> Optional[KnowledgeCommit]`
  - `get_chain(self) -> list[KnowledgeCommit]`
- Reality mismatch:
  - No methods for:
    - get all nodes
    - get nodes by category/type
    - get nodes changed since commit/timestamp
    - get latest commit by hash lookup
  - Reads are commit-chain-centric, not node-query-centric.

#### Persisted `SQLiteCommitStore`

- Definition: [nova/packages/runtime/persistence.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/persistence.py:13)
- Exact line range: `13-249`
- Methods present:
  - `subscribe`
  - `commit`
  - `get_latest`
  - `get_chain`
  - `add_lineage_edge`
  - `get_lineage`
  - `get_node_lineage`
  - `get_lineage_edges`
  - `register_fresh_lineage`
- Reality mismatch:
  - Still no general node query API by category, time window, or change-set.
  - `get_latest()` reconstructs the whole chain via `get_chain()` instead of using a direct indexed query.

## 2. Hashing & Determinism Audit

### 2.1 Actual `commit_hash` implementation

- Definition: [nova/packages/compiler/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/compiler/__init__.py:31)
- Exact line range: `31-53`
- Actual function:

```python
def compute_commit_hash(kir_nodes: list[KIRNode]) -> str:
    """
    SHA-256 over a deterministic serialization of the KIR nodes.
    Sort keys, no randomness, no timestamps inside the hash input.
    """
    serialized_nodes = []
    for node in kir_nodes:
        node_dict = {
            "op": node.op,
            "inputs": node.inputs,
            "output_id": node.output_id,
            "metadata": node.metadata,
            "dialect": node.dialect.value
            # Explicitly EXCLUDED: verification_status and verified_at
            # These are mutable review-states, not immutable assertion content.
            # They must never affect the commit_hash or parent_hash chain.
        }
        serialized_nodes.append(node_dict)
    
    serialized_nodes.sort(key=lambda x: x["output_id"])
    
    json_bytes = json.dumps(serialized_nodes, sort_keys=True).encode('utf-8')
    return hashlib.sha256(json_bytes).hexdigest()
```

- Findings:
  - Hash algorithm: `SHA-256`
  - Serialization: `json.dumps(..., sort_keys=True).encode("utf-8")`
  - Canonicalization:
    - node list sorted by `output_id`
    - object keys sorted recursively by `sort_keys=True`
  - Excluded mutable fields:
    - `verification_status`
    - `verified_at`
- Reality mismatch:
  - It does sort `kir_nodes`, but only by `output_id`, not by semantic category.
  - Mutable nested content inside `metadata` is included as-is; determinism depends on upstream dict/list ordering being stable.

### 2.2 Existing reusable hashing utilities

- Reusable commit hashing exists only as `compute_commit_hash(kir_nodes: list[KIRNode]) -> str` in [nova/packages/compiler/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/compiler/__init__.py:31).
- Related hashing patterns:
  - Daily Chronicle report hash in [nova/packages/runtime/daily_chronicle.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/daily_chronicle.py:221): JSON `sort_keys=True` + SHA-256
  - Integrity snapshot hash in [nova/packages/runtime/integrity.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/integrity.py:338): JSON `sort_keys=True` + SHA-256
  - LLM cache key in [nova/packages/llm/cache.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/llm/cache.py:47): raw string + SHA-256
- Conclusion:
  - There is no existing per-category utility like `hash_nodes(nodes: list[KIRNode]) -> str`.
  - A new section/category hash helper would need to be added, though it should mirror `compute_commit_hash` and the report/snapshot hashing pattern.

### 2.3 Determinism risks

- `compile()` in [nova/packages/compiler/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/compiler/__init__.py:68) claims deterministic behavior, but `created_at` is runtime-generated and excluded from the hash.
- `bundle_to_kir()` preserves incoming observation order at lines `57-66`; final hash determinism relies on `compute_commit_hash` resorting by `output_id`.
- `project_current_state()` in [nova/packages/runtime/projection.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/projection.py:43) contains debug `print()` statements and selects lineage winners by lexicographic `occ_time` string comparison, not parsed datetime comparison.

## 3. Existing Report Generators Audit

### 3.1 `generate_daily_chronicle`

- Definition: [nova/packages/runtime/daily_chronicle.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/daily_chronicle.py:85)
- Exact signature:

```python
def generate_daily_chronicle(
    store: KnowledgeStore,
    window: str = "today",
    start_dt_str: Optional[str] = None,
    end_dt_str: Optional[str] = None
) -> dict[str, Any]:
```

- Return type: `dict[str, Any]`
- Commit traversal:
  - Calls `store.get_chain()` at line `96`
  - Filters that list with `filter_commits_in_window(...)` at line `97`
  - Does not walk `parent_hash` manually
- Latest-state resolution:
  - It does not collapse multiple versions of the same node or lineage into a single latest state.
  - It iterates every node in every filtered commit at lines `119-199`.
  - Status is taken from the node’s current `content/status` field, not derived from lineage history.
- `ChronicleSnapshot` generation:
  - Dataclass defined at lines `11-17`
  - `report_hash` is SHA-256 of `raw_report_dict` serialized with `json.dumps(..., sort_keys=True)` at lines `245-246`
  - `snapshot_id = f"snap_{report_hash[:12]}"` at line `247`
- Reality mismatch:
  - This is not a persistent snapshot model; it is created transiently and returned as a dict.
  - Section-level incremental regeneration logic does not exist.

### 3.2 `compute_knowledge_health`

- Definition: [nova/packages/runtime/daily_chronicle.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/daily_chronicle.py:263)
- Exact signature:

```python
def compute_knowledge_health(store: KnowledgeStore) -> dict[str, Any]:
```

- Return type: `dict[str, Any]`
- Commit traversal:
  - Calls `store.get_chain()` at line `268`
  - Iterates every commit and every node at lines `281-343`
- Latest-state resolution:
  - None. This function evaluates each node occurrence independently.
  - A question/risk/goal appearing in multiple commits can contribute multiple health signals.
- Reality mismatch:
  - It is a monitor/reporting heuristic, not a lineage-aware current-state projection.

### 3.3 `compute_integrity_snapshot`

- Definition: [nova/packages/runtime/integrity.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/integrity.py:71)
- Exact signature:

```python
def compute_integrity_snapshot(store: KnowledgeStore) -> dict:
```

- Return type: `dict`
- Commit traversal:
  - Calls `store.get_chain()` at line `72`
  - Iterates every commit and every node at lines `82-123`
  - Also pulls lineage edges with `get_lineage_edges()` at line `128`
- Latest-state resolution:
  - Tracks `node_history[node_id]` and overwrites `latest_nodes[node_id] = trace_item` at lines `108-111`
  - This is latest-by-last-seen-node-id in chain order, not latest-by-lineage/category
  - If a later commit supersedes a decision by creating a new node ID, the old node is not replaced in `latest_nodes`; lineage is only used for volatility flags, not semantic state projection
- Snapshot ID generation:
  - `raw_dict` serialized with `json.dumps(..., sort_keys=True)` at lines `338-350`
  - `snapshot_id=f"integ_{report_hash[:12]}"` at line `353`
- Reality mismatch:
  - This is closer to a reusable pattern for `MasterReportState`, but it still returns transient dicts and does not persist them.

### 3.4 Current-state projection used by reasoning

- Definition: [nova/packages/runtime/projection.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/projection.py:12)
- Exact signature:

```python
def project_current_state(store: KnowledgeStore, temporal_idx=None) -> Projection:
```

- Return type: `Projection`
- State resolution:
  - Groups by lineage when lineage info exists.
  - For each lineage, keeps the metadata whose `occurrence_time` string is latest at lines `53-61`.
  - Otherwise keeps isolated node metadata.
- Important limitation:
  - This uses lineage tables, not semantic category grouping.
  - The daily chronicle and knowledge health functions do not reuse this logic.

## 4. Persistence Layer Audit

### 4.1 Knowledge persistence

- Primary persistence implementation: [nova/packages/runtime/persistence.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/persistence.py:13)
- Backend store type: SQLite
- Tables:
  - `commits` at lines `37-43`
  - `node_review_state` at lines `45-50`
  - `lineage_edges` at lines `52-59`
  - `node_lineages` at lines `61-66`
- Runtime API singleton path:
  - `_get_store()` creates `SQLiteCommitStore(os.path.join(_nova_root, "nova", "knowledge.db"))` in [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:49)
- Conclusion:
  - Chronicle persistence is SQLite-backed, not Postgres/Redis/file-JSON/in-memory-only.

### 4.2 Related persistence stores

- Temporal state: [nova/packages/temporal/persistence.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/temporal/persistence.py:9), backing file `nova/temporal.db` via [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:70)
- Identity registry: [nova/packages/identity/persistence.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/identity/persistence.py:11), backing file `nova/identity.db` via [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:79)

### 4.3 Caching layer reuse potential

- I could not locate a Redis cache, disk-cache abstraction, or Chronicle-specific section cache in `nova/packages/runtime`.
- The closest reusable behavior is:
  - in-memory singleton reuse of `_store`, `_temp`, `_id`, `_prov` in [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:42)
  - LLM cache utilities elsewhere in `nova/packages/llm`, but not tied to Chronicle report storage
- Conclusion:
  - There is no existing section-level caching layer for report regeneration.

### 4.4 Snapshot/report persistence

- `ChronicleSnapshot` is defined in [nova/packages/runtime/daily_chronicle.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/daily_chronicle.py:11) and returned at lines `249-260`.
- `IntegritySnapshot` is defined in [nova/packages/runtime/integrity.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/integrity.py:56) and returned at lines `352-357`.
- Neither snapshot is written to a table or file.
- `SQLiteCommitStore._compute_integrity()` caches the latest integrity snapshot in memory on the store instance at lines `71-76`, but does not persist it.

## 5. API Layer Audit

### 5.1 Framework and route locations

- Framework: FastAPI
  - Router import in [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:11)
  - App mounting in [core/api_server.py](/Users/sohamdhande/Docs_Local/NOVA/core/api_server.py:86)
- Router mounted with:
  - `app.include_router(knowledge_router, prefix="/api/knowledge")` in [core/api_server.py](/Users/sohamdhande/Docs_Local/NOVA/core/api_server.py:94)

### 5.2 `POST /api/knowledge/preview`

- Request model: [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:602), lines `602-605`
- Handler: [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:692), lines `692-837`
- Behavior:
  - Parses artifact input with `_parse_input`
  - Calls `provider.extract_organizational_knowledge(...)`
  - Builds transient preview observations/entities/relationships
  - Does not write commits to the store

### 5.3 `POST /api/knowledge/preview/retry`

- Request model: [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:840), lines `840-844`
- Handler: [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:847), lines `847-917`
- Behavior:
  - Re-runs extraction for requested groups only
  - Returns more transient preview suggestions
  - Does not write commits to the store

### 5.4 `POST /api/knowledge/compile`

- Request model: [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:608), lines `608-611`
- Handler: [api/knowledge_routes.py](/Users/sohamdhande/Docs_Local/NOVA/api/knowledge_routes.py:920), lines `920-949`
- Behavior after success:
  - Parses input
  - Gets identity registry, temporal index, provenance graph, and store
  - Builds bundle with `build_multi_bundle(...)` if `req.approved_observations` exists and is truthy; otherwise `build_bundle(...)`
  - Calls `nova_compile(bundle)`
  - Calls `store.commit(commit)`
  - Returns commit metadata
- Important mismatch:
  - `CompileRequest` does not declare `approved_observations` or `approved_observation_ids`.
  - The frontend sends both fields in [dashboard/src/components/panels/knowledge/NewArtifactView.tsx](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/components/panels/knowledge/NewArtifactView.tsx:73).
  - Because the request model only declares `source_type`, `content`, and `title`, the reviewed preview payload is not part of the typed request model. In the current code, that likely means the compile route falls back to `build_bundle(parsed, ...)` instead of compiling the reviewed suggestions. This is a real behavior risk for any feature that assumes compile consumes reviewed category data.

### 5.5 Hook/event/callback extension points after compile

- Existing hook in store:
  - `KnowledgeStore.subscribe(...)` in [nova/packages/runtime/store.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/store.py:14)
  - `SQLiteCommitStore.subscribe(...)` in [nova/packages/runtime/persistence.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/persistence.py:68)
  - `commit(...)` invokes subscriptions after persistence at lines `145-146`
- Current route usage:
  - `compile_artifact` directly calls `store.commit(commit)` and does not register any post-commit subscribers.
- Conclusion:
  - There is a callback mechanism in the store layer that could host report regeneration, but no current registry/wiring in the API route.

### 5.6 Auth and permissions model

- Frontend sends bearer tokens from `useApi()` in [dashboard/src/hooks/useApi.ts](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/hooks/useApi.ts:13)
- Chronicle routes are protected by global middleware, not per-route decorators:
  - [core/api_server.py](/Users/sohamdhande/Docs_Local/NOVA/core/api_server.py:97)
  - Middleware requires `Authorization: Bearer ...` for non-whitelisted endpoints at lines `108-139`
- Auth types accepted:
  - password token validated by `auth_manager.validate_token(token)` at line `130`
  - biometric session accepted via `biometric_auth.is_session_valid()` at line `131`
- Reality mismatch:
  - There is no Chronicle-specific role/permission layer on these routes.
  - Matching conventions for a new `/api/knowledge/master-report` endpoint means inheriting the same global bearer/biometric middleware.

## 6. PDF Generation Audit

### 6.1 Existing PDF generation utilities

#### `tools/pdf_tool.py`

- Definition: [tools/pdf_tool.py](/Users/sohamdhande/Docs_Local/NOVA/tools/pdf_tool.py:245)
- Public interface:

```python
def create_pdf(topic: str, content: str) -> str:
```

- Exact line range: `245-320` for the main creation path shown in the inspected segment
- Library: ReportLab Platypus
- Expected input:
  - freeform markdown-ish text with headings/bullets
  - internally parsed into sections by `_parse_sections` and `preprocess_content`
- Output:
  - writes a styled PDF into `/documents`
  - returns the absolute path string

#### `core/document_engine.py`

- Definition: [core/document_engine.py](/Users/sohamdhande/Docs_Local/NOVA/core/document_engine.py:340)
- Public interface:

```python
def create_pdf(self, title: str,
               content: str,
               path: str = None) -> str:
```

- Exact line range: `340-448`
- Library: `fpdf2`
- Behavior:
  - creates a title page and content pages
  - can parse JSON sections or plain text
  - saves to a Desktop path by default
  - opens the PDF locally with `open`

### 6.2 Chronicle-specific PDF export

- I could not locate any Chronicle route or runtime function that renders Chronicle data to PDF.
- `ChronicleExportSection` in the frontend is only a prompt-copy helper, not a PDF export UI:
  - [dashboard/src/components/panels/knowledge/ChronicleExportSection.tsx](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/components/panels/knowledge/ChronicleExportSection.tsx:4)
- `SettingsView` exports JSON only:
  - [dashboard/src/components/panels/knowledge/SettingsView.tsx](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/components/panels/knowledge/SettingsView.tsx:9)

### 6.3 Conclusion

- Existing reusable PDF libraries/utilities do exist: ReportLab and fpdf2-based generators.
- No Chronicle-specific PDF generator, template, or export endpoint exists today.

## 7. Dashboard Frontend Audit

### 7.1 Chronicle panel entry and navigation registration

- Global dashboard panel registration:
  - sidebar item `knowledge` in [dashboard/src/components/Sidebar/Sidebar.tsx](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/components/Sidebar/Sidebar.tsx:3)
  - panel metadata in [dashboard/src/layouts/DashboardLayout.tsx](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/layouts/DashboardLayout.tsx:25)
  - render switch case `case "knowledge": return <KnowledgePanel />;` in [dashboard/src/layouts/DashboardLayout.tsx](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/layouts/DashboardLayout.tsx:56)
- Chronicle sub-navigation:
  - `NAV_ITEMS` inside [dashboard/src/components/panels/knowledge/KnowledgePanel.tsx](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/components/panels/knowledge/KnowledgePanel.tsx:20)
  - Current tabs/views:
    - `home`
    - `integrity`
    - `new_artifact`
    - `explorer`
    - `timeline`
    - `search`
    - `commits`
    - `reasoning`
    - `explain`
    - `settings`
- Conclusion:
  - New Chronicle tabs are registered by editing the `SubView` union, `NAV_ITEMS`, and the conditional render block inside `KnowledgePanel`, not by route config.

### 7.2 Data-fetching pattern

- Shared hook: [dashboard/src/hooks/useApi.ts](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/hooks/useApi.ts:6)
- Pattern:
  - plain `fetch`
  - wrapped in a `useApi()` hook
  - bearer token attached manually
  - view-local `useState`, `useEffect`, and `useCallback`
- Reality mismatch:
  - No React Query, SWR, Redux, or centralized Chronicle data client is used.

### 7.3 Existing Chronicle components and purpose

- `KnowledgePanel.tsx`
  - Chronicle shell with left-side subnav, active view selection, and right-side inspector.
- `HomeView.tsx`
  - Aggregates Chronicle overview, daily report, health, and evolution; loads `/stats`, `/health`, and `/report`.
- `ChronicleOverview.tsx`
  - Top summary cards and “New Artifact” CTA.
- `DailyChronicleReport.tsx`
  - Windowed report view for new decisions/risks/goals/principles and assumption changes.
- `KnowledgeHealthSection.tsx`
  - Health signal view for unresolved questions, open risks, unsupported decisions, stale assumptions, goals without progress.
- `EvolutionSection.tsx`
  - Recent commits/entities and memory evolution counters.
- `IntegrityView.tsx`
  - Integrity snapshot dashboard: health score, contradictions, lonely knowledge, profile issues.
- `NewArtifactView.tsx`
  - Ingestion workflow: input, preview review, compile success.
- `ReviewCategorySection.tsx`
  - Per-category approval UI for preview suggestions.
- `ChronicleExportSection.tsx`
  - Copies a Chronicle export prompt to clipboard; no backend export action.
- `ExplorerView.tsx`
  - Graph-style exploration from `/api/knowledge/explore`.
- `TimelineView.tsx`
  - Timeline list from `/api/knowledge/timeline`.
- `SearchView.tsx`
  - Search UI hitting `/api/knowledge/search`.
- `ListView.tsx`
  - Generic list renderer used for commits/artifacts/entities/relationships/observations.
- `ReasoningView.tsx`
  - Intent-based reasoning and streaming answer UI.
- `ExplainView.tsx`
  - Provenance explain-chain viewer using `/api/knowledge/explain/...`.
- `InspectorCard.tsx`
  - Detailed object inspector with cross-links.
- `SettingsView.tsx`
  - JSON export and local reset controls.

### 7.4 Existing export behavior

- Chronicle’s current “export” closest analog is not a PDF export tab.
- What exists:
  - `ChronicleExportSection` copies a prompt string for manual reuse.
  - `SettingsView` downloads raw JSON from `/api/knowledge/export`.
- Conclusion:
  - There is no existing Chronicle frontend panel that calls a backend PDF export endpoint.

## 8. Reasoning Injection Audit

### 8.1 `DAILY_CHRONICLE_REPORT` injection mechanism

- Definition: [nova/packages/reasoning/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/reasoning/__init__.py:186)
- Relevant line ranges:
  - keyword planning: `17-27`
  - dependency keyword match: `34-46`
  - chronicle injection trigger: `195-210`
  - priority ranks: `74-86`
- Actual behavior:
  - `build_plan()` lowercases intent, strips punctuation, removes stopwords, and keeps raw keywords.
  - `compile_reasoning_context()` checks if any hard-coded chronicle substrings are present in `intent.lower()`:
    - `{"change", "changed", "new", "week", "today", "yesterday", "evolved", "growth", "chronicle", "health", "happened", "summary", "snapshot"}`
  - If any match, it computes:
    - `generate_daily_chronicle(store, window="7d" if "week" in intent.lower() else "today")`
    - `compute_knowledge_health(store)`
  - Then it prepends a synthetic fact:
    - `{"identity": snapshot_id, "type": "DAILY_CHRONICLE_REPORT", ...}`
- Conclusion:
  - This is simple keyword-triggered injection, not embeddings or semantic similarity.

### 8.2 Minimal change for a `MASTER_REPORT` injection

- The smallest consistent change would be:
  - generate a master-report payload in `compile_reasoning_context()`
  - prepend a synthetic fact like `{"type": "MASTER_REPORT", ...}`
  - add `"MASTER_REPORT": 0` or similar in the ranking map in `optimize_reasoning_ir()`
- No general injection registry exists today; this would be another inline conditional in `compile_reasoning_context()`.

## 9. Gaps & Risks Report

### 9.1 Places where code does not match the prompt’s expected architecture

- There are no per-category `KIRNode` subtypes; Chronicle uses one generic `KIRNode` with semantic type in metadata.
- Relationship semantics are not modeled as a typed edge system. Lineage edges are SQLite rows with freeform `verb`, while semantic relationships are just KIR nodes whose metadata says `type == "RELATIONSHIP"`.
- `KnowledgeStore` does not have node query APIs by category, change-since, or latest commit beyond `get_latest()`.
- Daily Chronicle and health reporting are not lineage-aware current-state projections; they iterate raw commit history.
- `ChronicleSnapshot` and `IntegritySnapshot` are not persisted for later retrieval.
- There is no Chronicle PDF renderer or Chronicle PDF API endpoint.
- Chronicle “export” in the dashboard means prompt copy or JSON download, not PDF export.

### 9.2 Missing pieces needed for the Master Report feature

- Category-based node query helpers or an equivalent projection layer for all report sections.
- A robust per-section hashing utility over selected node sets.
- Persistent storage for master-report metadata and section hashes if regeneration decisions must survive process restarts.
- A Chronicle-specific PDF rendering/template pipeline.
- A new API endpoint for master-report generation and retrieval.
- Likely a post-compile subscriber or hook registration point if report regeneration should happen automatically.

### 9.3 Reusable code that could be extended

- Commit hashing pattern in [nova/packages/compiler/__init__.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/compiler/__init__.py:31)
- Snapshot hashing/id generation patterns in:
  - [nova/packages/runtime/daily_chronicle.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/daily_chronicle.py:221)
  - [nova/packages/runtime/integrity.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/integrity.py:338)
- Store subscription callback mechanism in:
  - [nova/packages/runtime/store.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/store.py:14)
  - [nova/packages/runtime/persistence.py](/Users/sohamdhande/Docs_Local/NOVA/nova/packages/runtime/persistence.py:68)
- ReportLab PDF generator in [tools/pdf_tool.py](/Users/sohamdhande/Docs_Local/NOVA/tools/pdf_tool.py:245)
- Chronicle dashboard tab wiring in [dashboard/src/components/panels/knowledge/KnowledgePanel.tsx](/Users/sohamdhande/Docs_Local/NOVA/dashboard/src/components/panels/knowledge/KnowledgePanel.tsx:15)

### 9.4 Complexity / risk estimates

- `(a) category-hash-based section caching`
  - Risk: Medium-High
  - Why:
    - no existing category query API
    - current report generators are history scans, not reusable section projections
    - lineage/latest-state semantics are inconsistent across runtime modules

- `(b) PDF template + rendering`
  - Risk: Medium
  - Why:
    - PDF utilities already exist
    - Chronicle-specific layout and stable section rendering still need to be designed
    - persistence and retrieval semantics are separate concerns

- `(c) new dashboard tab`
  - Risk: Low-Medium
  - Why:
    - Chronicle subnav is local and straightforward
    - existing `useApi` pattern is simple
    - most risk is backend contract design, not tab wiring

- `(d) new API endpoint`
  - Risk: Medium
  - Why:
    - route wiring and auth conventions are simple
    - hard part is defining durable report state, regeneration policy, and PDF/output storage

### 9.5 Additional high-signal implementation risk found during audit

- The compile review flow appears inconsistent between frontend and backend:
  - frontend sends approved preview data in `NewArtifactView`
  - backend `CompileRequest` does not declare those fields
  - compile handler branches on `req.approved_observations`
- That mismatch should be resolved before building Master Report features on top of “approved compiled category data,” because current compile behavior may not actually compile the reviewed preview payload.
