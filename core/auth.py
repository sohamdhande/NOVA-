
import sqlite3
import os
import logging
import secrets
import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict

# Constants
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")
logger = logging.getLogger(__name__)

class AuthManager:
    """
    Manages simple local password authentication.
    - Persists password hash in SQLite.
    - Manages in-memory session tokens.
    """
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # Harden concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._create_table()
        
        # In-memory session store: token -> expiry (datetime)
        self._sessions: Dict[str, datetime] = {}

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def is_setup_required(self) -> bool:
        """Check if password is already set."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT password_hash FROM auth_config WHERE id = 1")
        row = cursor.fetchone()
        return row is None

    def set_password(self, plaintext: str) -> bool:
        """Set or update the password. Only allowed if not set (for now, or logic handled by API)."""
        # Hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plaintext.encode('utf-8'), salt).decode('utf-8')
        
        cursor = self.conn.cursor()
        # Upsert
        cursor.execute("""
            INSERT INTO auth_config (id, password_hash, created_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                password_hash = excluded.password_hash,
                created_at = excluded.created_at
        """, (hashed, datetime.now().isoformat()))
        self.conn.commit()
        return True

    def verify_password(self, plaintext: str) -> bool:
        """Verify provided password against stored hash."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT password_hash FROM auth_config WHERE id = 1")
        row = cursor.fetchone()
        
        if not row:
            return False
            
        stored_hash = row[0].encode('utf-8')
        return bcrypt.checkpw(plaintext.encode('utf-8'), stored_hash)

    def create_token(self) -> dict:
        """Generate a new session token."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=30)
        
        # Store in memory
        self._sessions[token] = expires_at
        
        # Clean up expired tokens lazily
        self._cleanup_tokens()
        
        return {
            "token": token,
            "expires_at": expires_at.isoformat()
        }

    def validate_token(self, token: str) -> bool:
        """Check if token exists and is valid."""
        if token not in self._sessions:
            return False
            
        expires_at = self._sessions[token]
        if datetime.now() > expires_at:
            del self._sessions[token]
            return False
            
        return True

    def _cleanup_tokens(self):
        """Remove expired tokens."""
        now = datetime.now()
        expired = [t for t, exp in self._sessions.items() if now > exp]
        for t in expired:
            del self._sessions[t]
