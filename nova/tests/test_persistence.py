import sys
import tempfile
import dataclasses
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.runtime.persistence import SQLiteCommitStore, migrate_to_sqlite
from nova.packages.runtime.store import KnowledgeStore, ChainIntegrityError
from nova.packages.compiler import KnowledgeCommit
from nova.packages.kir import KIRNode, Dialect

def create_mock_commit(hash_val: str, dialect: Dialect = Dialect.GENERIC, parent: str = None) -> KnowledgeCommit:
    node = KIRNode(
        op="TEST_OP",
        inputs=[],
        output_id=f"out_{hash_val}",
        metadata={"key": hash_val},
        dialect=dialect
    )
    return KnowledgeCommit(
        commit_hash=hash_val,
        kir_nodes=[node],
        parent_hash=parent,
        created_at=datetime.now(timezone.utc)
    )

def test_round_trip():
    store = SQLiteCommitStore()
    commit = create_mock_commit("hash1", Dialect.DECISION)
    
    store.commit(commit)
    
    chain = store.get_chain()
    assert len(chain) == 1
    
    recovered = chain[0]
    assert recovered.commit_hash == "hash1"
    assert recovered.parent_hash is None
    assert len(recovered.kir_nodes) == 1
    
    rec_node = recovered.kir_nodes[0]
    assert rec_node.op == "TEST_OP"
    assert rec_node.output_id == "out_hash1"
    assert rec_node.metadata == {"key": "hash1"}
    assert rec_node.dialect == Dialect.DECISION
    assert recovered.created_at == commit.created_at

def test_chain_integrity():
    store = SQLiteCommitStore()
    
    commit1 = create_mock_commit("hash1")
    store.commit(commit1)
    
    commit2 = create_mock_commit("hash2", parent="wrong_parent")
    # Actually, store.commit() auto-injects the correct parent_hash (latest_hash)
    # To test chain integrity reading failure, we must force a bad insert or bypass auto-inject.
    # Let's bypass auto-inject to insert a bad row, then read it back.
    with store._conn:
        store._conn.execute(
            "INSERT INTO commits (commit_hash, parent_hash, kir_nodes_json, created_at) VALUES (?, ?, ?, ?)",
            ("hash2", "wrong_parent", store._serialize_nodes(commit2.kir_nodes), commit2.created_at.isoformat())
        )
        
    try:
        store.get_chain()
        assert False, "Should have raised ChainIntegrityError"
    except ChainIntegrityError:
        pass

def test_persistence_across_instances():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
        
    try:
        # Instance 1
        store1 = SQLiteCommitStore(db_path)
        store1.commit(create_mock_commit("hash_A"))
        store1.commit(create_mock_commit("hash_B"))
        
        # Instance 2
        store2 = SQLiteCommitStore(db_path)
        chain = store2.get_chain()
        
        assert len(chain) == 2
        assert chain[0].commit_hash == "hash_A"
        assert chain[1].commit_hash == "hash_B"
        assert chain[1].parent_hash == "hash_A"
        
    finally:
        Path(db_path).unlink()

def test_migrate_to_sqlite():
    mem_store = KnowledgeStore()
    mem_store.commit(create_mock_commit("m1"))
    mem_store.commit(create_mock_commit("m2"))
    mem_store.commit(create_mock_commit("m3"))
    
    sql_store = SQLiteCommitStore()
    migrate_to_sqlite(mem_store, sql_store)
    
    mem_chain = mem_store.get_chain()
    sql_chain = sql_store.get_chain()
    
    assert len(mem_chain) == 3
    assert len(sql_chain) == 3
    
    for m_c, s_c in zip(mem_chain, sql_chain):
        assert m_c.commit_hash == s_c.commit_hash
        assert m_c.parent_hash == s_c.parent_hash

if __name__ == "__main__":
    print("--- Testing Persistence ---")
    test_round_trip()
    test_chain_integrity()
    test_persistence_across_instances()
    test_migrate_to_sqlite()
    print("All Persistence tests passed!\n")
