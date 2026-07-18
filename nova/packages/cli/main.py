import argparse
import sys
import json
import os
from pathlib import Path

# Adjust path if run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from nova.packages.ingestion import IngestionRegistry, SlackAdapter, GitCommitAdapter, PlaintextAdapter
from nova.packages.observation import build_bundle
from nova.packages.compiler import compile
from nova.packages.identity.persistence import SQLiteIdentityRegistry
from nova.packages.temporal.persistence import SQLiteTemporalIndex
from nova.packages.provenance.persistence import SQLiteProvenanceGraph
from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.runtime.dependency_persistence import SQLiteDependencyGraph
from nova.packages.reasoning import compile_reasoning_context

DEFAULT_DIR = Path(__file__).parent.parent.parent / "nova"
DEFAULT_DB_PATH = DEFAULT_DIR / "knowledge.db"
DEFAULT_IDENTITY_PATH = DEFAULT_DIR / "identity.db"
DEFAULT_TEMPORAL_PATH = DEFAULT_DIR / "temporal.db"
DEFAULT_PROVENANCE_PATH = DEFAULT_DIR / "provenance.db"
DEFAULT_DEPENDENCY_PATH = DEFAULT_DIR / "dependency.db"

def _ensure_dir():
    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)

def get_store(db_path=None) -> SQLiteCommitStore:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteCommitStore(str(path))

def get_identity() -> SQLiteIdentityRegistry:
    _ensure_dir()
    return SQLiteIdentityRegistry(str(DEFAULT_IDENTITY_PATH))

def get_temporal() -> SQLiteTemporalIndex:
    _ensure_dir()
    return SQLiteTemporalIndex(str(DEFAULT_TEMPORAL_PATH))

def get_provenance() -> SQLiteProvenanceGraph:
    _ensure_dir()
    return SQLiteProvenanceGraph(str(DEFAULT_PROVENANCE_PATH))

def get_dependency() -> SQLiteDependencyGraph:
    _ensure_dir()
    return SQLiteDependencyGraph(str(DEFAULT_DEPENDENCY_PATH))

def setup_ingestion() -> IngestionRegistry:
    registry = IngestionRegistry()
    registry.register(SlackAdapter())
    registry.register(GitCommitAdapter())
    registry.register(PlaintextAdapter())
    return registry

def ingest_command(args):
    source_type = args.source_type.lower()
    input_data = args.input_data
    
    registry = setup_ingestion()
    
    if source_type in ["slack", "git"]:
        try:
            with open(input_data, "r") as f:
                raw_data = json.load(f)
        except Exception as e:
            print(f"Error reading JSON file '{input_data}': {e}")
            sys.exit(1)
    elif source_type == "plaintext":
        raw_data = input_data
    else:
        print(f"Unknown source type: {source_type}. Use 'slack', 'git', or 'plaintext'.")
        sys.exit(1)
        
    try:
        parsed = registry.ingest(source_type, raw_data)
        if source_type == "plaintext" and parsed.get("sender") == "unknown":
            parsed["sender"] = f"unknown_{parsed.get('source_path', 'unknown').split('/')[-1]}"
    except Exception as e:
        print(f"Ingestion failed: {e}")
        sys.exit(1)
        
    id_reg = get_identity()
    temp_idx = get_temporal()
    prov_graph = get_provenance()
    dep_graph = get_dependency()
    
    store = get_store(args.db_path)
    latest = store.get_latest()
    derived_from_ids = None
    if latest and latest.kir_nodes:
        raw_output_id = latest.kir_nodes[0].output_id
        if raw_output_id.startswith("kir_obs_"):
            prev_fact_id = "obs_" + raw_output_id[len("kir_obs_"):]
        else:
            prev_fact_id = raw_output_id
        derived_from_ids = [(prev_fact_id, "follows")]
    
    bundle = build_bundle(parsed, id_reg, temp_idx, prov_graph, derived_from_ids=derived_from_ids)
    commit = compile(bundle)
    
    store.commit(commit)
    
    # We could also thread dependency graph logically, but since this mirrors
    # the existing `build_bundle -> compile -> commit` flow perfectly:
    print(f"Successfully committed: {commit.commit_hash}")
    for node in commit.kir_nodes:
        print(f"  -> {node.dialect.value} | {node.op} | {node.output_id}")

def log_command(args):
    store = get_store(args.db_path)
    chain = store.get_chain()
    
    if not chain:
        print("No knowledge commits found.")
        return
        
    for kc in chain:
        short_hash = kc.commit_hash[:8]
        ts = kc.created_at.strftime("%Y-%m-%d %H:%M:%S")
        
        # Summarize nodes
        node_summaries = []
        for n in kc.kir_nodes:
            content_str = str(n.metadata.get("content", ""))
            if len(content_str) > 40:
                content_str = content_str[:37] + "..."
            node_summaries.append(f"{n.dialect.value}:{n.op} '{content_str}'")
            
        summary = " | ".join(node_summaries)
        print(f"commit {short_hash} - {ts} - {summary}")

def show_command(args):
    store = get_store(args.db_path)
    chain = store.get_chain()
    
    matches = [kc for kc in chain if kc.commit_hash.startswith(args.prefix)]
    
    if not matches:
        print(f"Error: No commit found starting with '{args.prefix}'")
        sys.exit(1)
    elif len(matches) > 1:
        print(f"Error: Ambiguous prefix '{args.prefix}'. Found {len(matches)} matching commits.")
        sys.exit(1)
        
    kc = matches[0]
    print(f"Commit: {kc.commit_hash}")
    print(f"Parent: {kc.parent_hash}")
    print(f"Date:   {kc.created_at}")
    print("-" * 40)
    for n in kc.kir_nodes:
        print(f"KIRNode ({n.dialect.value} - {n.op})")
        print(f"  ID: {n.output_id}")
        print(f"  Inputs: {n.inputs}")
        print(f"  Metadata: {json.dumps(n.metadata, indent=2)}")
        print()

def ask_command(args):
    store = get_store(args.db_path)
    
    try:
        context = compile_reasoning_context(args.intent, store)
        print(context)
    except Exception as e:
        print(f"Error during reasoning: {e}")
        sys.exit(1)

def explain_command(args):
    prov_graph = get_provenance()
    fact_id = args.fact_id
    if fact_id.startswith("kir_obs_"):
        fact_id = "obs_" + fact_id[len("kir_obs_"):]
    explanation = prov_graph.explain(fact_id)
    print(explanation)

def reset_command(args):
    path = Path(args.db_path) if args.db_path else DEFAULT_DB_PATH
    if not path.exists():
        print("No database found. Nothing to reset.")
        return
        
    resp = input(f"Are you sure you want to delete {path}? (y/N): ")
    if resp.lower().strip() == 'y':
        path.unlink()
        
        # Also clean up auxiliary databases
        for db in [DEFAULT_IDENTITY_PATH, DEFAULT_TEMPORAL_PATH, DEFAULT_PROVENANCE_PATH, DEFAULT_DEPENDENCY_PATH]:
            if db.exists():
                db.unlink()
                
        print("Databases deleted.")
    else:
        print("Reset cancelled.")

def entities_command(args):
    store = get_store(args.db_path)
    entities = set()
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            if "sender" in n.metadata:
                entities.add(n.metadata["sender"])
    for e in sorted(entities):
        print(e)

def artifacts_command(args):
    store = get_store(args.db_path)
    paths = set()
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            p = n.metadata.get("source_path")
            if p:
                paths.add(p)
    for p in sorted(paths):
        print(p)

def observations_command(args):
    store = get_store(args.db_path)
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            print(f"{n.output_id} ({n.dialect.value}:{n.op})")

def commits_command(args):
    log_command(args)

def timeline_command(args):
    store = get_store(args.db_path)
    for kc in store.get_chain():
        print(f"[{kc.created_at.strftime('%Y-%m-%d %H:%M:%S')}] Commit {kc.commit_hash[:8]} ({len(kc.kir_nodes)} nodes)")

def search_command(args):
    q_low = args.query.lower()
    store = get_store(args.db_path)
    for kc in store.get_chain():
        if q_low in kc.commit_hash.lower():
            print(f"COMMIT: {kc.commit_hash}")
        for n in kc.kir_nodes:
            txt = str(n.metadata.get("content", ""))
            sender = str(n.metadata.get("sender", ""))
            path = str(n.metadata.get("source_path", ""))
            if q_low in n.output_id.lower() or q_low in txt.lower() or q_low in sender.lower() or q_low in path.lower():
                print(f"OBSERVATION [{n.output_id}]: {sender} -> {txt[:60]}")

def inspect_command(args):
    id = args.id
    store = get_store(args.db_path)
    prov = get_provenance()
    for kc in store.get_chain():
        if kc.commit_hash.startswith(id):
            print(f"Object Type: Commit\nSummary: Knowledge Commit {kc.commit_hash}\nParent: {kc.parent_hash}\nCreated At: {kc.created_at.isoformat()}")
            return
        for n in kc.kir_nodes:
            raw_id = n.output_id
            norm_id = raw_id[4:] if raw_id.startswith("kir_") else raw_id
            src = n.metadata.get("source_path", "")
            if id in (raw_id, norm_id, src):
                obj_type = "Artifact" if id == src else "Observation"
                print(f"Object Type: {obj_type}\nID: {id}\nOperation: {n.op}\nMetadata: {json.dumps(n.metadata, indent=2)}\nCompiled Into: {kc.commit_hash}")
                if obj_type == "Observation":
                    print(f"Provenance Chain: {prov.explain(norm_id)}")
                return
    print(f"Object Type: Entity\nSummary: Compiled identity {id}")

def main():
    parser = argparse.ArgumentParser(description="NOVA Knowledge Compiler CLI")
    parser.add_argument("--db-path", help="Path to SQLite DB (defaults to ~/.nova/knowledge.db)", default=None)
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest a file or text")
    p_ingest.add_argument("source_type", choices=["slack", "git", "plaintext"], help="Type of source")
    p_ingest.add_argument("input_data", help="File path (for slack/git) or raw text (for plaintext)")
    
    # log
    p_log = subparsers.add_parser("log", help="Show commit history")
    
    # show
    p_show = subparsers.add_parser("show", help="Show commit details")
    p_show.add_argument("prefix", help="Commit hash prefix")
    
    # ask
    p_ask = subparsers.add_parser("ask", help="Ask the system a question")
    p_ask.add_argument("intent", help="The intent or question to compile context for")
    
    # explain
    p_explain = subparsers.add_parser("explain", help="Explain provenance of a fact")
    p_explain.add_argument("fact_id", help="Fact ID to explain")
    
    # reset
    p_reset = subparsers.add_parser("reset", help="Delete the knowledge databases")
    
    # productization commands
    subparsers.add_parser("entities", help="List entities")
    subparsers.add_parser("artifacts", help="List artifacts")
    subparsers.add_parser("observations", help="List observations")
    subparsers.add_parser("commits", help="List commits")
    subparsers.add_parser("timeline", help="Show timeline")
    
    p_search = subparsers.add_parser("search", help="Search graph")
    p_search.add_argument("query", help="Search string")
    
    p_inspect = subparsers.add_parser("inspect", help="Inspect object")
    p_inspect.add_argument("id", help="Object ID")
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        ingest_command(args)
    elif args.command == "log":
        log_command(args)
    elif args.command == "show":
        show_command(args)
    elif args.command == "ask":
        ask_command(args)
    elif args.command == "explain":
        explain_command(args)
    elif args.command == "reset":
        reset_command(args)
    elif args.command == "entities":
        entities_command(args)
    elif args.command == "artifacts":
        artifacts_command(args)
    elif args.command == "observations":
        observations_command(args)
    elif args.command == "commits":
        commits_command(args)
    elif args.command == "timeline":
        timeline_command(args)
    elif args.command == "search":
        search_command(args)
    elif args.command == "inspect":
        inspect_command(args)

if __name__ == "__main__":
    main()
