import sys
from pathlib import Path
from pprint import pprint

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.ingestion import IngestionRegistry, SlackAdapter, GitCommitAdapter, PlaintextAdapter
from nova.packages.observation import build_bundle
from nova.packages.compiler import compile, KnowledgeCommit
from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex
from nova.packages.provenance import ProvenanceGraph
from nova.packages.ontology import SemanticType
from nova.packages.runtime import reconstruct_as_of, KnowledgeStore, project_current_state
from nova.packages.runtime.dependencies import DependencyGraph, compute_tracked_projection
from nova.packages.reasoning import compile_reasoning_context
import time
from datetime import datetime, timezone
from datetime import datetime, timezone

def main():
    print("--- Milestone 1 & NAS-010 Runtime & Ingestion Example ---\n")
    
    # Setup Registries
    ingest_registry = IngestionRegistry()
    ingest_registry.register(SlackAdapter())
    ingest_registry.register(GitCommitAdapter())
    ingest_registry.register(PlaintextAdapter())
    
    identity_registry = IdentityRegistry()
    temporal_index = TemporalIndex()
    provenance_graph = ProvenanceGraph()
    dependency_graph = DependencyGraph()
    
    store = KnowledgeStore()
    
    # Wire DependencyGraph into Subscriptions
    def on_commit_invalidate(commit: KnowledgeCommit):
        for node in commit.kir_nodes:
            fact_id = node.output_id[4:] if node.output_id.startswith("kir_") else node.output_id
            stale = dependency_graph.invalidate(fact_id)
            if stale:
                print(f"  [Dependency Tracker] Fact {fact_id} changed. Stale projections: {stale}")
    
    store.subscribe(on_commit_invalidate)
    
    def on_commit(commit: KnowledgeCommit):
        print(f"  [Subscriber] New commit received: {commit.commit_hash}")
    store.subscribe(on_commit)
    
    # 1. Slack Input
    raw_slack = {
        "channel": "general",
        "user": "Soham",
        "text": "Let's build a deterministic knowledge compiler."
    }
    print("1. Processing Slack Input:")
    parsed_slack = ingest_registry.ingest("slack", raw_slack)
    pprint(parsed_slack)
    
    bundle_1 = build_bundle(parsed_slack, identity_registry, temporal_index, provenance_graph)
    commit_1 = compile(bundle_1)
    store.commit(commit_1)
    print(f"  -> Lowered to Dialect: {commit_1.kir_nodes[0].dialect.value}, Op: {commit_1.kir_nodes[0].op}")
    
    # 2. Git Input
    raw_git = {
        "author": "Alice",
        "message": "Add runtime subscriptions and projection.",
        "sha": "abc1234"
    }
    print("\n2. Processing Git Input:")
    parsed_git = ingest_registry.ingest("git", raw_git)
    pprint(parsed_git)
    
    bundle_2 = build_bundle(
        parsed_git, 
        identity_registry, 
        temporal_index, 
        provenance_graph,
        derived_from_ids=[(bundle_1.observations[0].id, "implements")]
    )
    commit_2 = compile(bundle_2)
    store.commit(commit_2)
    print(f"  -> Lowered to Dialect: {commit_2.kir_nodes[0].dialect.value}, Op: {commit_2.kir_nodes[0].op}")
    
    # 3. Plaintext Input
    raw_text = "Just some plaintext documentation about the architecture."
    print("\n3. Processing Plaintext Input:")
    parsed_text = ingest_registry.ingest("plaintext", raw_text)
    pprint(parsed_text)
    
    bundle_3 = build_bundle(
        parsed_text, 
        identity_registry, 
        temporal_index, 
        provenance_graph,
        derived_from_ids=[(bundle_2.observations[0].id, "documents")]
    )
    commit_3 = compile(bundle_3)
    store.commit(commit_3)
    print(f"  -> Lowered to Dialect: {commit_3.kir_nodes[0].dialect.value}, Op: {commit_3.kir_nodes[0].op}")
    
    # 4. Alias Scenario
    print("\n4. Processing Alias Scenario:")
    raw_soham_1 = {"channel": "general", "user": "soham", "text": "First message from soham."}
    parsed_soham_1 = ingest_registry.ingest("slack", raw_soham_1)
    bundle_soham_1 = build_bundle(parsed_soham_1, identity_registry, temporal_index, provenance_graph)
    store.commit(compile(bundle_soham_1))
    
    canonical_id = identity_registry.lookup_by_alias("soham")
    print(f"  Alias 'soham' resolved to: {canonical_id}")
    
    print("  Adding alias 'soham.shaikh' to same canonical ID...")
    identity_registry.add_alias(canonical_id, "soham.shaikh")
    
    raw_soham_2 = {"channel": "general", "user": "soham.shaikh", "text": "Second message from soham.shaikh."}
    parsed_soham_2 = ingest_registry.ingest("slack", raw_soham_2)
    bundle_soham_2 = build_bundle(parsed_soham_2, identity_registry, temporal_index, provenance_graph)
    store.commit(compile(bundle_soham_2))
    
    obs1_id = bundle_soham_1.observations[0].identity
    obs2_id = bundle_soham_2.observations[0].identity
    print(f"  Observation 1 identity: {obs1_id}")
    print(f"  Observation 2 identity: {obs2_id}")
    assert obs1_id == obs2_id
    print("  SUCCESS: Both aliases resolved to the identical canonical ID.")
    
    # 5. Merge Scenario
    print("\n5. Processing Merge Scenario:")
    raw_alice = {"channel": "general", "user": "alice", "text": "Alice here."}
    raw_alice_temp = {"channel": "general", "user": "alice_temp", "text": "Alice temp here."}
    
    bundle_a = build_bundle(ingest_registry.ingest("slack", raw_alice), identity_registry, temporal_index, provenance_graph)
    store.commit(compile(bundle_a))
    bundle_b = build_bundle(ingest_registry.ingest("slack", raw_alice_temp), identity_registry, temporal_index, provenance_graph)
    store.commit(compile(bundle_b))
    
    id_a = bundle_a.observations[0].identity
    id_b = bundle_b.observations[0].identity
    print(f"  Before merge: 'alice' -> {id_a}, 'alice_temp' -> {id_b}")
    
    print("  Merging 'alice_temp' INTO 'alice'...")
    identity_registry.merge(id_b, id_a)
    
    print("  Running project_current_state to view facts...")
    proj = project_current_state(store)
    for fact in proj.facts:
        sender = fact.get("content", {}).get("sender")
        if sender in ("alice", "alice_temp"):
            resolved_id = identity_registry.get_entity(fact["identity"]).canonical_id
            print(f"  Fact sender: {sender}, Identity in fact: {fact['identity']}, Resolved canonical: {resolved_id}")
            
    # 6. Temporal Reconstruction Scenario
    print("\n6. Processing Temporal Reconstruction & Dependency Scenario:")
    
    # Compute the first projection BEFORE the 'cheese' fact is added
    proj_early = compute_tracked_projection(store, dependency_graph, "proj_early")
    print(f"  -> Computed tracked projection 'proj_early' with {len(proj_early.facts)} facts.")

    raw_correction_1 = {"channel": "general", "user": "editor", "text": "The moon is made of cheese."}
    parsed_corr_1 = ingest_registry.ingest("slack", raw_correction_1)
    bundle_corr_1 = build_bundle(parsed_corr_1, identity_registry, temporal_index, provenance_graph)
    store.commit(compile(bundle_corr_1))
    
    fact_id_1 = bundle_corr_1.observations[0].id
    
    # Compute the second projection AFTER the 'cheese' fact is added
    proj_late = compute_tracked_projection(store, dependency_graph, "proj_late")
    print(f"  -> Computed tracked projection 'proj_late' with {len(proj_late.facts)} facts.")
    
    print("  Sleeping for 1 second to create a time gap...")
    time.sleep(1)
    t_between = datetime.now(timezone.utc)
    print(f"  Time T_between: {t_between}")
    time.sleep(1)
    
    print("  Superseding original fact with a correction...")
    raw_correction_2 = {"channel": "general", "user": "editor_v2", "text": "Actually, the moon is made of rock."}
    parsed_corr_2 = ingest_registry.ingest("slack", raw_correction_2)
    bundle_corr_2 = build_bundle(parsed_corr_2, identity_registry, temporal_index, provenance_graph)
    store.commit(compile(bundle_corr_2))
    
    fact_id_2 = bundle_corr_2.observations[0].id
    t_supersede = datetime.now(timezone.utc)
    temporal_index.supersede(fact_id_1, fact_id_2, bundle_corr_2.observations[0].temporal, t_supersede)
    
    print("\n  [Dependency Tracking] Simulating selective invalidation via supersession:")
    stale_projs = dependency_graph.invalidate(fact_id_1)
    print(f"  -> Invalidating {fact_id_1} makes these projections stale: {stale_projs}")
    
    time.sleep(1)
    t_after = datetime.now(timezone.utc)
    
    proj_before = reconstruct_as_of(store, temporal_index, t_between)
    proj_after = reconstruct_as_of(store, temporal_index, t_after)
    
    print(f"  Facts at T_between (before correction):")
    for fact in proj_before.facts:
        if fact.get("content", {}).get("user") in ("editor", "editor_v2"):
            print(f"    - {fact['content']['text']}")
            
    print(f"  Facts at T_after (after correction):")
    for fact in proj_after.facts:
        if fact.get("content", {}).get("user") in ("editor", "editor_v2"):
            print(f"    - {fact['content']['text']}")

    print("\n7. Processing Provenance Chain Scenario (With Persistence):")
    import tempfile
    from nova.packages.provenance.persistence import SQLiteProvenanceGraph
    
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        prov_db_path = f.name
        
    persistent_prov = SQLiteProvenanceGraph(prov_db_path)
    
    # Rebuild the bundle to establish links in the persistent graph
    bundle_1 = build_bundle({"source_path": "plaintext/91a49059", "content": "Just some plaintext documentation about the architecture.", "sender": "unknown"}, identity_registry, temporal_index, persistent_prov)
    bundle_2 = build_bundle({"source_path": "git/commit/abc1234", "content": "Add runtime subscriptions and projection.", "sender": "Alice"}, identity_registry, temporal_index, persistent_prov, derived_from_ids=[(bundle_1.observations[0].id, "documents")])
    bundle_3 = build_bundle({"source_path": "slack/architecture", "content": "We decided to rebuild packages/kir to support MLIR-like dialects.", "sender": "architect"}, identity_registry, temporal_index, persistent_prov, derived_from_ids=[(bundle_2.observations[0].id, "implements")], semantic_type_override=SemanticType.DECISION)
    
    print("  Walking backward from Plaintext (bundle_3) -> Git (bundle_2) -> Slack (bundle_1)...")
    
    # Open NEW instance to prove it survived
    print("  [Verification] Opening a NEW SQLiteProvenanceGraph instance to explain...")
    persistent_prov_new = SQLiteProvenanceGraph(prov_db_path)
    print("\n  Explain Output:")
    print(persistent_prov_new.explain(bundle_3.observations[0].id))
    
    import os
    os.unlink(prov_db_path)

    print("\n8. Processing Decision Dialect Scenario:")
    raw_decision = {"channel": "architecture", "user": "architect", "text": "We decided to rebuild packages/kir to support MLIR-like dialects."}
    parsed_decision = ingest_registry.ingest("slack", raw_decision)
    bundle_decision = build_bundle(
        parsed_decision, 
        identity_registry, 
        temporal_index, 
        provenance_graph,
        semantic_type_override=SemanticType.DECISION
    )
    commit_decision = compile(bundle_decision)
    store.commit(commit_decision)
    print(f"  -> Lowered to Dialect: {commit_decision.kir_nodes[0].dialect.value}, Op: {commit_decision.kir_nodes[0].op}")

    print("\n--- Running First Intent (Keyword Filtering) ---")
    intent_1 = "What is the core architectural goal mentioned in Slack?"
    context_string_1 = compile_reasoning_context(intent_1, store)
    print("Compiled Reasoning Context 1:")
    print(context_string_1)
    
    print("\n--- Running Second Intent (Graceful Fallback) ---")
    intent_2 = "What did the database migration involve?"
    context_string_2 = compile_reasoning_context(intent_2, store)
    print("Compiled Reasoning Context 2:")
    print(context_string_2)
    
    print("\n9. Processing AI Boundary Scenario:")
    from nova.packages.ai_boundary import MockEntitySuggester, SuggestionReviewBoundary
    
    suggester = MockEntitySuggester()
    review_boundary = SuggestionReviewBoundary()
    
    sample_text = "Soham met Alice to discuss the NOVA architecture"
    print(f"  Running MockEntitySuggester on: '{sample_text}'")
    suggestions = suggester.suggest(sample_text)
    
    for s in suggestions:
        review_boundary.submit(s)
        
    pending = review_boundary.pending()
    print(f"  Pending suggestions in boundary: {len(pending)}")
    for p in pending:
        print(f"    - [{p.suggestion_type}] {p.payload} (confidence {p.confidence})")
        
    if len(pending) >= 2:
        print("\n  Accepting one suggestion (Soham)...")
        accepted_payload = review_boundary.accept(pending[0], accepted_by="architect")
        print(f"  -> Returned payload: {accepted_payload}")
        
        print("  Rejecting another suggestion (Alice)...")
        review_boundary.reject(pending[1], reason="Not a relevant entity.")
        
        print("\n  [Manual Bridge] Feeding accepted payload explicitly into IdentityRegistry...")
        # Treat the accepted payload's name as an alias/sender string
        new_id = identity_registry.resolve({"sender": accepted_payload["name"]}, alias_key="sender")
        print(f"  -> Registered manually under canonical ID: {new_id}")
    
    print("\n10. Processing Persistence Scenario:")
    import tempfile
    from nova.packages.runtime.persistence import SQLiteCommitStore, migrate_to_sqlite
    
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
        
    print(f"  [Migration] Migrating in-memory KnowledgeStore to SQLite at: {db_path}")
    sql_store = SQLiteCommitStore(db_path)
    migrate_to_sqlite(store, sql_store)
    
    persisted_chain = sql_store.get_chain()
    print(f"  -> Successfully persisted {len(persisted_chain)} commits.")
    
    print("  [Verification] Opening a brand NEW SQLiteCommitStore instance on the same file...")
    sql_store_new = SQLiteCommitStore(db_path)
    verified_chain = sql_store_new.get_chain()
    print(f"  -> New instance loaded {len(verified_chain)} commits.")
    
    assert len(persisted_chain) == len(verified_chain) == len(store.get_chain())
    print("  -> Proof successful: Knowledge survived outside memory!")
    
    import os
    os.unlink(db_path)
    
    print("\n--- Pipeline Complete ---")

if __name__ == "__main__":
    main()
