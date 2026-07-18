import sqlite3
import threading

class SQLiteDependencyGraph:
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
                CREATE TABLE IF NOT EXISTS dependencies (
                    projection_id TEXT,
                    fact_id TEXT,
                    PRIMARY KEY (projection_id, fact_id)
                )
            ''')

    def record_dependency(self, projection_id: str, fact_id: str) -> None:
        # INSERT OR IGNORE avoids primary key duplicates if requested multiple times
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO dependencies (projection_id, fact_id) VALUES (?, ?)",
                (projection_id, fact_id)
            )

    def get_dependencies(self, projection_id: str) -> list[str]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT fact_id FROM dependencies WHERE projection_id = ?", (projection_id,))
        return [row["fact_id"] for row in cursor.fetchall()]

    def get_dependents(self, fact_id: str) -> list[str]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT projection_id FROM dependencies WHERE fact_id = ?", (fact_id,))
        return [row["projection_id"] for row in cursor.fetchall()]

    def invalidate(self, fact_id: str) -> list[str]:
        return self.get_dependents(fact_id)
