import sqlite3, json, os, re
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Memory:
    id: str
    category: str    # preference|fact|command|context
    key: str
    value: str
    confidence: float = 1.0
    created_at: str = ""
    updated_at: str = ""
    access_count: int = 0

class MemoryEngine:
    
    DB_PATH = os.path.expanduser("~/.nova/memory.db")
    
    def __init__(self):
        os.makedirs(
            os.path.dirname(self.DB_PATH),
            exist_ok=True
        )
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                category TEXT,
                key TEXT UNIQUE,
                value TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TEXT,
                updated_at TEXT,
                access_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                summary TEXT,
                date TEXT,
                message_count INTEGER
            )
        """)
        conn.commit()
        conn.close()
    
    def remember(self, key: str, value: str, category: str = "fact") -> str:
        """Store a memory."""
        import uuid
        conn = sqlite3.connect(self.DB_PATH)
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT OR REPLACE INTO memories
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            str(uuid.uuid4())[:8],
            category, key, value,
            1.0, now, now, 0
        ))
        conn.commit()
        conn.close()
        return f"Remembered: {key} = {value}"
    
    def recall(self, key: str) -> Optional[str]:
        """Retrieve a specific memory."""
        conn = sqlite3.connect(self.DB_PATH)
        row = conn.execute(
            "SELECT value FROM memories "
            "WHERE key LIKE ? "
            "ORDER BY access_count DESC LIMIT 1",
            (f"%{key}%",)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE memories SET access_count = access_count + 1 WHERE key LIKE ?",
                (f"%{key}%",)
            )
            conn.commit()
        conn.close()
        return row[0] if row else None
    
    def get_all(self, category: str = None) -> List[Memory]:
        """Get all memories optionally filtered."""
        conn = sqlite3.connect(self.DB_PATH)
        if category:
            rows = conn.execute(
                "SELECT * FROM memories WHERE category=? ORDER BY access_count DESC",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY access_count DESC LIMIT 50"
            ).fetchall()
        conn.close()
        return [Memory(
            id=r[0], category=r[1],
            key=r[2], value=r[3],
            confidence=r[4],
            created_at=r[5], updated_at=r[6],
            access_count=r[7]
        ) for r in rows]
    
    def get_context_summary(self) -> str:
        """
        Generate context string for LLM prompts.
        Includes key facts N.O.V.A knows about user.
        """
        memories = self.get_all()
        if not memories:
            return ""
        
        facts = [
            f"- {m.key}: {m.value}"
            for m in memories[:10]
        ]
        return (
            "What I know about you:\n" +
            "\n".join(facts)
        )
    
    def save_conversation_summary(self, messages: list) -> str:
        """Summarize and save a conversation."""
        import uuid
        if len(messages) < 3:
            return ""
        
        # Extract key facts from conversation
        for msg in messages:
            content = msg.get("content", "").lower()
            
            # Detect name
            name_match = re.search(r"my name is (\w+)", content)
            if name_match:
                self.remember(
                    "user_name",
                    name_match.group(1).title(),
                    "preference"
                )
            
            # Detect preferences
            if "i prefer" in content or "i like" in content:
                self.remember(
                    f"preference_{len(messages)}",
                    content[:100],
                    "preference"
                )
        
        # Save summary
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            "INSERT INTO conversations VALUES (?,?,?,?)",
            (
                str(uuid.uuid4())[:8],
                f"Conversation with {len(messages)} messages",
                datetime.now().isoformat(),
                len(messages)
            )
        )
        conn.commit()
        conn.close()
        return "Conversation saved to memory."
    
    def forget(self, key: str) -> str:
        """Delete a memory."""
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            "DELETE FROM memories WHERE key LIKE ?",
            (f"%{key}%",)
        )
        conn.commit()
        conn.close()
        return f"Forgot: {key}"
    
    def inject_into_prompt(self, prompt: str) -> str:
        """
        Add memory context to any LLM prompt.
        Makes N.O.V.A remember who it's talking to.
        """
        context = self.get_context_summary()
        if not context:
            return prompt
        return f"{context}\n\n{prompt}"

memory_engine = MemoryEngine()
