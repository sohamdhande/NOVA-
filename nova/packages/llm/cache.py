import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Any


import threading

class DeterministicInferenceCache:
    """
    SQLite-backed deterministic response cache for LLM provider layer.
    Ensures reproducibility across identical inference runs.
    """
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
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS inference_cache (
                    cache_key TEXT PRIMARY KEY,
                    prompt_hash TEXT,
                    response TEXT,
                    timestamp TEXT,
                    provider TEXT,
                    model TEXT
                )
            """)

    @staticmethod
    def compute_key(provider: str, model: str, prompt: str, compiled_context: str = "") -> str:
        raw = f"{provider}:{model}:{prompt}:{compiled_context}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def get(self, cache_key: str) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT response FROM inference_cache WHERE cache_key = ?", (cache_key,))
        row = cur.fetchone()
        return row["response"] if row else None

    def put(self, cache_key: str, prompt: str, response: str, provider: str, model: str):
        prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute("""
                INSERT OR REPLACE INTO inference_cache 
                (cache_key, prompt_hash, response, timestamp, provider, model)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cache_key, prompt_hash, response, ts, provider, model))


_default_cache = DeterministicInferenceCache()


def get_cache() -> DeterministicInferenceCache:
    return _default_cache
