from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

class IntervalAlreadyClosedError(Exception):
    pass

class UnknownFactError(Exception):
    pass

@dataclass(frozen=True)
class TemporalInterval:
    start: datetime
    end: Optional[datetime] = None
    
    def is_valid_at(self, as_of: datetime) -> bool:
        return self.start <= as_of and (self.end is None or as_of < self.end)
        
    def close(self, end_time: datetime) -> "TemporalInterval":
        if self.end is not None:
            raise IntervalAlreadyClosedError("Interval is already closed.")
        return TemporalInterval(start=self.start, end=end_time)

@dataclass(frozen=True)
class TemporalRecord:
    occurrence_time: TemporalInterval = field(default_factory=lambda: TemporalInterval(start=datetime.now(timezone.utc)))
    observation_time: TemporalInterval = field(default_factory=lambda: TemporalInterval(start=datetime.now(timezone.utc)))
    assertion_time: TemporalInterval = field(default_factory=lambda: TemporalInterval(start=datetime.now(timezone.utc)))
    compilation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class TemporalIndex:
    def __init__(self):
        self._records: dict[str, TemporalRecord] = {}
        
    def register(self, fact_id: str, record: TemporalRecord) -> None:
        self._records[fact_id] = record
        
    def supersede(self, fact_id: str, new_fact_id: str, new_record: TemporalRecord, at_time: datetime) -> None:
        if fact_id not in self._records:
            raise UnknownFactError(f"Fact ID {fact_id} is unknown.")
            
        old_record = self._records[fact_id]
        
        closed_assertion = old_record.assertion_time.close(at_time)
        updated_old_record = TemporalRecord(
            occurrence_time=old_record.occurrence_time,
            observation_time=old_record.observation_time,
            assertion_time=closed_assertion,
            compilation_time=old_record.compilation_time
        )
        
        self._records[fact_id] = updated_old_record
        self._records[new_fact_id] = new_record
        
    def valid_facts_as_of(self, as_of: datetime) -> list[str]:
        return sorted([
            fid for fid, record in self._records.items()
            if record.assertion_time.is_valid_at(as_of)
        ])
        
    def get_record(self, fact_id: str) -> TemporalRecord:
        if fact_id not in self._records:
            raise UnknownFactError(f"Fact ID {fact_id} is unknown.")
        return self._records[fact_id]


__all__ = [
    "IntervalAlreadyClosedError",
    "UnknownFactError",
    "TemporalInterval",
    "TemporalRecord",
    "TemporalIndex"
]
