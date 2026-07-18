import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional

from nova.packages.identity import Entity, IdentityMergeError, UnknownAliasError

import threading

class SQLiteIdentityRegistry:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

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
                CREATE TABLE IF NOT EXISTS entities (
                    canonical_id TEXT PRIMARY KEY,
                    known_aliases_json TEXT,
                    created_at TEXT,
                    merged_into TEXT
                )
            ''')
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS merges (
                    source_id TEXT,
                    target_id TEXT,
                    PRIMARY KEY (source_id, target_id)
                )
            ''')
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS merge_suggestions (
                    id TEXT PRIMARY KEY,
                    new_alias TEXT,
                    suggested_canonical_id TEXT,
                    ratio REAL,
                    source TEXT,
                    status TEXT,
                    created_at TEXT
                )
            ''')

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        return Entity(
            canonical_id=row["canonical_id"],
            known_aliases=json.loads(row["known_aliases_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            merged_into=row["merged_into"]
        )

    def _get_entity_raw(self, canonical_id: str) -> Optional[Entity]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM entities WHERE canonical_id = ?", (canonical_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_entity(row)

    def get_entity(self, canonical_id: str) -> Entity:
        current = self._get_entity_raw(canonical_id)
        if current is None:
            raise ValueError(f"Unknown canonical_id: {canonical_id}")
            
        visited = set()
        while current.merged_into is not None:
            if current.canonical_id in visited:
                raise IdentityMergeError("Merge cycle detected while walking entity chain.")
            visited.add(current.canonical_id)
            current = self._get_entity_raw(current.merged_into)
            
        if current.canonical_id in visited:
            raise IdentityMergeError("Merge cycle detected while walking entity chain.")
            
        return current

    def _normalize(self, s: str) -> str:
        import string
        return str(s).lower().strip().translate(str.maketrans('', '', string.punctuation))

    def resolve(self, raw_object: dict, alias_key: str) -> str:
        alias = raw_object.get(alias_key)
        if alias is None:
            alias = str(raw_object)
            
        canonical_id = self.lookup_by_alias(alias)
        if canonical_id is not None:
            entity = self.get_entity(canonical_id)
            return entity.canonical_id
            
        import difflib
        norm_new = self._normalize(alias)
        best_ratio = 0.0
        best_canonical_id = None

        cursor = self._conn.cursor()
        cursor.execute("SELECT canonical_id, known_aliases_json FROM entities WHERE merged_into IS NULL")
        for row in cursor.fetchall():
            c_id = row["canonical_id"]
            aliases = json.loads(row["known_aliases_json"])
            for known in aliases:
                norm_known = self._normalize(known)
                ratio = difflib.SequenceMatcher(None, norm_new, norm_known).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_canonical_id = c_id

        # TIER 1: AUTO-MERGE
        if best_ratio >= 0.92 and best_canonical_id:
            self.add_alias(best_canonical_id, alias)
            return best_canonical_id

        # TIER 3: NO-MATCH (Create entity)
        new_id = str(uuid.uuid4())
        new_entity = Entity(
            canonical_id=new_id,
            known_aliases=[alias]
        )
        
        with self._conn:
            self._conn.execute(
                "INSERT INTO entities (canonical_id, known_aliases_json, created_at, merged_into) VALUES (?, ?, ?, ?)",
                (new_id, json.dumps([alias]), new_entity.created_at.isoformat(), None)
            )
            
            # TIER 2: SUGGEST
            if 0.6 <= best_ratio < 0.92 and best_canonical_id:
                # Check if this pair was already dismissed
                cursor.execute(
                    "SELECT 1 FROM merge_suggestions WHERE new_alias = ? AND suggested_canonical_id = ? AND status = 'dismissed'",
                    (alias, best_canonical_id)
                )
                if not cursor.fetchone():
                    s_id = str(uuid.uuid4())
                    self._conn.execute(
                        "INSERT INTO merge_suggestions (id, new_alias, suggested_canonical_id, ratio, source, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (s_id, alias, best_canonical_id, best_ratio, "string_similarity", "pending", datetime.now().isoformat())
                    )
            
        return new_id

    def lookup_by_alias(self, alias: str) -> Optional[str]:
        # Using JSON1 extension or just fetching all if JSON1 not guaranteed.
        # But for robustness against varying sqlite versions, let's just fetch all rows and build a map or filter
        # It's a prototype, but JSON1 is standard in Python 3.9+. 
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT canonical_id FROM entities, json_each(entities.known_aliases_json) WHERE json_each.value = ?", (alias,))
            row = cursor.fetchone()
            if row:
                return self.get_entity(row["canonical_id"]).canonical_id
        except sqlite3.OperationalError:
            # Fallback if json_each not available
            cursor.execute("SELECT * FROM entities")
            for row in cursor.fetchall():
                ent = self._row_to_entity(row)
                if alias in ent.known_aliases:
                    return self.get_entity(ent.canonical_id).canonical_id
        return None

    def add_alias(self, canonical_id: str, new_alias: str) -> None:
        entity = self.get_entity(canonical_id)
        if new_alias not in entity.known_aliases:
            updated_aliases = list(entity.known_aliases) + [new_alias]
            with self._conn:
                self._conn.execute(
                    "UPDATE entities SET known_aliases_json = ? WHERE canonical_id = ?",
                    (json.dumps(updated_aliases), entity.canonical_id)
                )

    def merge(self, source_id: str, target_id: str) -> None:
        source = self._get_entity_raw(source_id)
        if not source:
            raise IdentityMergeError(f"Source {source_id} not found.")
        target = self._get_entity_raw(target_id)
        if not target:
            raise IdentityMergeError(f"Target {target_id} not found.")
            
        if source.canonical_id == target.canonical_id:
            raise IdentityMergeError("Cannot merge entity into itself.")
            
        # Try merge temporarily in memory to detect cycle
        # We can simulate the cycle by temporarily updating the DB in a transaction and rolling back if error
        try:
            with self._conn:
                self._conn.execute("UPDATE entities SET merged_into = ? WHERE canonical_id = ?", (target.canonical_id, source.canonical_id))
                # Cycle check
                self.get_entity(source_id)
                
                # If valid, transfer aliases
                new_aliases = sorted(list(set(target.known_aliases + source.known_aliases)))
                self._conn.execute("UPDATE entities SET known_aliases_json = ? WHERE canonical_id = ?", (json.dumps(new_aliases), target.canonical_id))
                self._conn.execute("INSERT INTO merges (source_id, target_id) VALUES (?, ?)", (source.canonical_id, target.canonical_id))
        except IdentityMergeError:
            # Rollback automatically happens if exception raised within `with self._conn:` context
            raise

    def history(self, canonical_id: str) -> list[str]:
        final_id = self.get_entity(canonical_id).canonical_id
        cursor = self._conn.cursor()
        cursor.execute("SELECT source_id, target_id FROM merges")
        result = []
        for row in cursor.fetchall():
            try:
                tgt_final = self.get_entity(row["target_id"]).canonical_id
                if tgt_final == final_id:
                    result.append(row["source_id"])
            except ValueError:
                pass
        return result
