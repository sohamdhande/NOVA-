import sqlite3
from datetime import datetime, timezone
from typing import Optional

from nova.packages.temporal import TemporalRecord, TemporalInterval, UnknownFactError, IntervalAlreadyClosedError

import threading

class SQLiteTemporalIndex:
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
                CREATE TABLE IF NOT EXISTS temporal_records (
                    fact_id TEXT PRIMARY KEY,
                    occurrence_start TEXT,
                    occurrence_end TEXT,
                    observation_start TEXT,
                    observation_end TEXT,
                    assertion_start TEXT,
                    assertion_end TEXT,
                    compilation_time TEXT
                )
            ''')

    def _format_time(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None

    def _parse_time(self, s: Optional[str]) -> Optional[datetime]:
        return datetime.fromisoformat(s) if s else None

    def _row_to_record(self, row: sqlite3.Row) -> TemporalRecord:
        return TemporalRecord(
            occurrence_time=TemporalInterval(
                start=self._parse_time(row["occurrence_start"]),
                end=self._parse_time(row["occurrence_end"])
            ),
            observation_time=TemporalInterval(
                start=self._parse_time(row["observation_start"]),
                end=self._parse_time(row["observation_end"])
            ),
            assertion_time=TemporalInterval(
                start=self._parse_time(row["assertion_start"]),
                end=self._parse_time(row["assertion_end"])
            ),
            compilation_time=self._parse_time(row["compilation_time"])
        )

    def register(self, fact_id: str, record: TemporalRecord) -> None:
        with self._conn:
            self._conn.execute('''
                INSERT OR REPLACE INTO temporal_records (
                    fact_id, occurrence_start, occurrence_end,
                    observation_start, observation_end,
                    assertion_start, assertion_end, compilation_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fact_id,
                self._format_time(record.occurrence_time.start),
                self._format_time(record.occurrence_time.end),
                self._format_time(record.observation_time.start),
                self._format_time(record.observation_time.end),
                self._format_time(record.assertion_time.start),
                self._format_time(record.assertion_time.end),
                self._format_time(record.compilation_time)
            ))

    def supersede(self, fact_id: str, new_fact_id: str, new_record: TemporalRecord, at_time: datetime) -> None:
        old_record = self.get_record(fact_id)
        
        # Validates and raises IntervalAlreadyClosedError if already closed
        closed_assertion = old_record.assertion_time.close(at_time)
        
        with self._conn:
            # Update old record
            self._conn.execute('''
                UPDATE temporal_records
                SET assertion_end = ?
                WHERE fact_id = ?
            ''', (self._format_time(closed_assertion.end), fact_id))
            
            # Insert new record
            self._conn.execute('''
                INSERT INTO temporal_records (
                    fact_id, occurrence_start, occurrence_end,
                    observation_start, observation_end,
                    assertion_start, assertion_end, compilation_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                new_fact_id,
                self._format_time(new_record.occurrence_time.start),
                self._format_time(new_record.occurrence_time.end),
                self._format_time(new_record.observation_time.start),
                self._format_time(new_record.observation_time.end),
                self._format_time(new_record.assertion_time.start),
                self._format_time(new_record.assertion_time.end),
                self._format_time(new_record.compilation_time)
            ))

    def valid_facts_as_of(self, as_of: datetime) -> list[str]:
        # Perform memory fetch to use standard interval logic from dataclass
        # A more optimal way would be an SQL query, but the prompt says 
        # "must preserve exact interval semantics". We can fetch all and filter in Python
        # or use SQL if precise. SQL logic: 
        # assertion_start <= as_of AND (assertion_end IS NULL OR as_of < assertion_end)
        
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM temporal_records")
        valid_facts = []
        for row in cursor.fetchall():
            rec = self._row_to_record(row)
            if rec.assertion_time.is_valid_at(as_of):
                valid_facts.append(row["fact_id"])
                
        return sorted(valid_facts)

    def get_record(self, fact_id: str) -> TemporalRecord:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM temporal_records WHERE fact_id = ?", (fact_id,))
        row = cursor.fetchone()
        if not row:
            raise UnknownFactError(f"Fact ID {fact_id} is unknown.")
        return self._row_to_record(row)
