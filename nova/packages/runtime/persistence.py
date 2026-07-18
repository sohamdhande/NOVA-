import sqlite3
import json
import dataclasses
import threading
from datetime import datetime, timezone
from typing import Optional

from nova.packages.compiler import KnowledgeCommit
from nova.packages.kir import KIRNode, Dialect
from nova.packages.runtime.store import KnowledgeStore, ChainIntegrityError
from nova.packages.runtime.subscriptions import SubscriptionCallback

class SQLiteCommitStore:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._subscriptions: list[SubscriptionCallback] = []
        self._local = threading.local()
        self._init_db()
        self._compute_integrity()

    @property
    def _conn(self):
        if self.db_path == ":memory:":
            if not hasattr(self, "_memory_conn"):
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn
        
    def _init_db(self):
        with self._conn:
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS commits (
                    commit_hash TEXT PRIMARY KEY,
                    parent_hash TEXT,
                    kir_nodes_json TEXT,
                    created_at TEXT
                )
            ''')
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS node_review_state (
                    node_id TEXT PRIMARY KEY,
                    verification_status TEXT,
                    verified_at TEXT
                )
            ''')
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS lineage_edges (
                    from_id TEXT,
                    to_id TEXT,
                    verb TEXT,
                    created_at TEXT,
                    PRIMARY KEY (from_id, to_id, verb)
                )
            ''')
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS node_lineages (
                    node_id TEXT PRIMARY KEY,
                    lineage_id TEXT,
                    occurrence_time TEXT
                )
            ''')
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS master_report_sections (
                    category TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    rendered_markdown TEXT NOT NULL,
                    last_updated_at TEXT NOT NULL
                )
            ''')
            
    def subscribe(self, callback: SubscriptionCallback):
        self._subscriptions.append(callback)
        
    def _compute_integrity(self):
        try:
            from nova.packages.runtime.integrity import compute_integrity_snapshot
            self.integrity_snapshot = compute_integrity_snapshot(self)
        except ImportError:
            self.integrity_snapshot = None
        
    def _serialize_nodes(self, nodes: list[KIRNode]) -> str:
        serialized = []
        for node in nodes:
            serialized.append({
                "op": node.op,
                "inputs": node.inputs,
                "output_id": node.output_id,
                "metadata": node.metadata,
                "dialect": node.dialect.value
            })
        return json.dumps(serialized)
        
    def _deserialize_nodes(self, nodes_json: str) -> list[KIRNode]:
        raw_list = json.loads(nodes_json)
        nodes = []
        
        # Gather node IDs for batch lookup
        node_ids = [raw["output_id"] for raw in raw_list]
        review_states = {}
        
        if node_ids:
            placeholders = ",".join(["?"] * len(node_ids))
            cursor = self._conn.cursor()
            cursor.execute(f"SELECT node_id, verification_status, verified_at FROM node_review_state WHERE node_id IN ({placeholders})", node_ids)
            for row in cursor.fetchall():
                review_states[row["node_id"]] = (row["verification_status"], row["verified_at"])
                
        for raw in raw_list:
            v_status, v_at = review_states.get(raw["output_id"], ("unverified", None))
            nodes.append(KIRNode(
                op=raw["op"],
                inputs=raw["inputs"],
                output_id=raw["output_id"],
                metadata=raw["metadata"],
                dialect=Dialect(raw["dialect"]),
                verification_status=v_status,
                verified_at=v_at
            ))
        return nodes
        
    def _row_to_commit(self, row: sqlite3.Row) -> KnowledgeCommit:
        return KnowledgeCommit(
            commit_hash=row["commit_hash"],
            parent_hash=row["parent_hash"],
            kir_nodes=self._deserialize_nodes(row["kir_nodes_json"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )

    def commit(self, kc: KnowledgeCommit):
        latest = self.get_latest()
        latest_hash = latest.commit_hash if latest else None
        
        kc = dataclasses.replace(kc, parent_hash=latest_hash)
        
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO commits (commit_hash, parent_hash, kir_nodes_json, created_at) VALUES (?, ?, ?, ?)",
                (
                    kc.commit_hash,
                    kc.parent_hash,
                    self._serialize_nodes(kc.kir_nodes),
                    kc.created_at.isoformat()
                )
            )
            
        self._compute_integrity()
            
        for sub in self._subscriptions:
            sub(kc)

    def get_latest(self) -> Optional[KnowledgeCommit]:
        # To find the latest in a chain we could trace it, but since we append, 
        # sqlite rowid logic or timestamps usually works. However, best is to 
        # load the chain and get the last one. 
        # Alternatively, find the commit that no other commit has as parent.
        # But for simplicity, we can just load the chain.
        chain = self.get_chain()
        return chain[-1] if chain else None

    def get_chain(self) -> list[KnowledgeCommit]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM commits")
        rows = cursor.fetchall()
        
        if not rows:
            return []
            
        # Reconstruct chain in memory to preserve integrity checks
        # Assuming rows could theoretically be unordered, let's map them
        commits_by_parent = {row["parent_hash"]: self._row_to_commit(row) for row in rows}
        
        chain = []
        expected_parent = None
        
        while expected_parent in commits_by_parent:
            commit = commits_by_parent[expected_parent]
            chain.append(commit)
            expected_parent = commit.commit_hash
            
        if len(chain) != len(rows):
            # If there's a disjoint chain, we raise an integrity error or similar.
            # But the prompt says "preserve the EXACT same chain integrity checks KnowledgeStore already does".
            # KnowledgeStore iterates over self._history in order of insertion.
            pass
            
        # Let's strictly mirror KnowledgeStore validation:
        # If we just sort by rowid (insertion order)
        cursor.execute("SELECT * FROM commits ORDER BY rowid ASC")
        ordered_rows = cursor.fetchall()
        
        ordered_commits = [self._row_to_commit(row) for row in ordered_rows]
        
        expected_parent = None
        for commit in ordered_commits:
            if commit.parent_hash != expected_parent:
                raise ChainIntegrityError(f"Broken link: expected parent {expected_parent}, got {commit.parent_hash}")
            expected_parent = commit.commit_hash
            
        return ordered_commits

    def add_lineage_edge(self, from_id: str, to_id: str, verb: str, occurrence_time: str):
        cursor = self._conn.cursor()
        cursor.execute("SELECT lineage_id FROM node_lineages WHERE node_id = ?", (from_id,))
        row = cursor.fetchone()
        
        lineage_id = row["lineage_id"] if row else from_id
        
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO lineage_edges (from_id, to_id, verb, created_at) VALUES (?, ?, ?, ?)",
                (from_id, to_id, verb, datetime.now(timezone.utc).isoformat())
            )
            if not row:
                self._conn.execute(
                    "INSERT OR IGNORE INTO node_lineages (node_id, lineage_id, occurrence_time) VALUES (?, ?, ?)",
                    (from_id, lineage_id, occurrence_time)
                )
            
            self._conn.execute(
                "INSERT OR REPLACE INTO node_lineages (node_id, lineage_id, occurrence_time) VALUES (?, ?, ?)",
                (to_id, lineage_id, occurrence_time)
            )

    def get_lineage(self, lineage_id: str) -> list[dict]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT node_id, occurrence_time FROM node_lineages WHERE lineage_id = ? ORDER BY occurrence_time ASC", (lineage_id,))
        return [dict(row) for row in cursor.fetchall()]
        
    def get_node_lineage(self, node_id: str) -> Optional[dict]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT lineage_id, occurrence_time FROM node_lineages WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_lineage_edges(self) -> list[dict]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM lineage_edges")
        return [dict(row) for row in cursor.fetchall()]

    def register_fresh_lineage(self, node_id: str, occurrence_time: str):
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO node_lineages (node_id, lineage_id, occurrence_time) VALUES (?, ?, ?)",
                (node_id, node_id, occurrence_time)
            )

    def get_cached_section(self, category: str) -> Optional[dict]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT category, content_hash, rendered_markdown, last_updated_at FROM master_report_sections WHERE category = ?", (category,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_section(self, category: str, content_hash: str, rendered_markdown: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO master_report_sections (category, content_hash, rendered_markdown, last_updated_at) VALUES (?, ?, ?, ?)",
                (category, content_hash, rendered_markdown, datetime.now(timezone.utc).isoformat())
            )

def migrate_to_sqlite(source: KnowledgeStore, target: SQLiteCommitStore) -> None:
    chain = source.get_chain()
    for commit in chain:
        # Since target.commit injects latest_hash, we can just pass the commit
        # The target's commit function will naturally preserve the chain if order is preserved
        target.commit(commit)
