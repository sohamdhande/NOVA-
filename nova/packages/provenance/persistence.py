import sqlite3
import threading

from nova.packages.provenance import ProvenanceLink, ProvenanceCycleError

class SQLiteProvenanceGraph:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._local = threading.local()
        self._forward: dict[str, list[ProvenanceLink]] = {}
        self._backward: dict[str, list[ProvenanceLink]] = {}
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
                CREATE TABLE IF NOT EXISTS provenance_links (
                    from_fact_id TEXT,
                    to_fact_id TEXT,
                    relation TEXT,
                    PRIMARY KEY (from_fact_id, to_fact_id, relation)
                )
            ''')
        self._load_from_db()

    def _load_from_db(self):
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM provenance_links")
        for row in cursor.fetchall():
            link = ProvenanceLink(
                from_fact_id=row["from_fact_id"],
                to_fact_id=row["to_fact_id"],
                relation=row["relation"]
            )
            self._forward.setdefault(link.from_fact_id, []).append(link)
            self._backward.setdefault(link.to_fact_id, []).append(link)

    def add_link(self, link: ProvenanceLink) -> None:
        if self._is_reachable(start_id=link.to_fact_id, target_id=link.from_fact_id, direction="forward"):
            raise ProvenanceCycleError(f"Adding link {link} creates a cycle.")
            
        with self._conn:
            self._conn.execute(
                "INSERT INTO provenance_links (from_fact_id, to_fact_id, relation) VALUES (?, ?, ?)",
                (link.from_fact_id, link.to_fact_id, link.relation)
            )
            
        self._forward.setdefault(link.from_fact_id, []).append(link)
        self._backward.setdefault(link.to_fact_id, []).append(link)

    def _is_reachable(self, start_id: str, target_id: str, direction: str) -> bool:
        if start_id == target_id:
            return True
            
        visited = set()
        queue = [start_id]
        
        while queue:
            current = queue.pop(0)
            if current == target_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            
            links = self._forward.get(current, []) if direction == "forward" else self._backward.get(current, [])
            next_nodes = [l.to_fact_id if direction == "forward" else l.from_fact_id for l in links]
            
            for n in next_nodes:
                if n not in visited:
                    queue.append(n)
                    
        return False

    def walk_backward(self, fact_id: str) -> list[ProvenanceLink]:
        links_found = []
        visited_nodes = set([fact_id])
        queue = [fact_id]
        
        while queue:
            current = queue.pop(0)
            back_links = self._backward.get(current, [])
            for link in back_links:
                if link not in links_found:
                    links_found.append(link)
                if link.from_fact_id not in visited_nodes:
                    visited_nodes.add(link.from_fact_id)
                    queue.append(link.from_fact_id)
                    
        links_found.reverse()
        return links_found

    def walk_forward(self, fact_id: str) -> list[ProvenanceLink]:
        links_found = []
        visited_nodes = set([fact_id])
        queue = [fact_id]
        
        while queue:
            current = queue.pop(0)
            fwd_links = self._forward.get(current, [])
            for link in fwd_links:
                if link not in links_found:
                    links_found.append(link)
                if link.to_fact_id not in visited_nodes:
                    visited_nodes.add(link.to_fact_id)
                    queue.append(link.to_fact_id)
                    
        return links_found

    def explain(self, fact_id: str) -> str:
        backward_links = self.walk_backward(fact_id)
        if not backward_links:
            return fact_id
            
        lines = []
        for link in backward_links:
            lines.append(f"{link.from_fact_id} --[{link.relation}]--> {link.to_fact_id}")
            
        return "\n".join(lines)
