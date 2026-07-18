import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import time

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.temporal import TemporalIndex, TemporalRecord, TemporalInterval, IntervalAlreadyClosedError, UnknownFactError
from nova.packages.runtime import KnowledgeStore, reconstruct_as_of
from nova.packages.compiler import compile
from nova.packages.observation import build_bundle
from nova.packages.identity import IdentityRegistry
from nova.packages.provenance import ProvenanceGraph

def test_basic_validity():
    index = TemporalIndex()
    now = datetime.now(timezone.utc)
    t1 = now - timedelta(hours=2)
    
    record = TemporalRecord(assertion_time=TemporalInterval(start=t1))
    index.register("fact_1", record)
    
    assert "fact_1" not in index.valid_facts_as_of(t1 - timedelta(hours=1))
    assert "fact_1" in index.valid_facts_as_of(t1 + timedelta(hours=1))
    assert "fact_1" in index.valid_facts_as_of(now)

def test_supersession():
    index = TemporalIndex()
    now = datetime.now(timezone.utc)
    t1 = now - timedelta(hours=4)
    t2 = now - timedelta(hours=2)
    
    record_a = TemporalRecord(assertion_time=TemporalInterval(start=t1))
    index.register("fact_a", record_a)
    
    record_b = TemporalRecord(assertion_time=TemporalInterval(start=t2))
    index.supersede("fact_a", "fact_b", record_b, at_time=t2)
    
    t_1_5 = t1 + timedelta(hours=1)
    t_2_5 = t2 + timedelta(hours=1)
    
    assert "fact_a" in index.valid_facts_as_of(t_1_5)
    assert "fact_b" not in index.valid_facts_as_of(t_1_5)
    
    assert "fact_b" in index.valid_facts_as_of(t_2_5)
    assert "fact_a" not in index.valid_facts_as_of(t_2_5)

def test_point_in_time_reconstruction():
    store = KnowledgeStore()
    registry = IdentityRegistry()
    index = TemporalIndex()
    provenance_graph = ProvenanceGraph()
    
    raw1 = {"sender": "test", "content": "fact 1"}
    bundle1 = build_bundle(raw1, registry, index, provenance_graph)
    store.commit(compile(bundle1))
    fact_id_1 = bundle1.observations[0].id
    
    time.sleep(0.1)
    t_between = datetime.now(timezone.utc)
    time.sleep(0.1)
    
    raw2 = {"sender": "test2", "content": "fact 2"}
    bundle2 = build_bundle(raw2, registry, index, provenance_graph)
    
    fact_id_2 = bundle2.observations[0].id
    t_supersede = bundle2.observations[0].temporal.assertion_time.start
    
    index.supersede(fact_id_1, fact_id_2, bundle2.observations[0].temporal, t_supersede)
    store.commit(compile(bundle2))
    
    t_after = datetime.now(timezone.utc)
    
    proj_between = reconstruct_as_of(store, index, t_between)
    contents_between = [f.get("content", {}).get("content") for f in proj_between.facts]
    assert "fact 1" in contents_between
    assert "fact 2" not in contents_between
    
    proj_after = reconstruct_as_of(store, index, t_after)
    contents_after = [f.get("content", {}).get("content") for f in proj_after.facts]
    assert "fact 1" not in contents_after
    assert "fact 2" in contents_after

def test_double_close_rejection():
    index = TemporalIndex()
    now = datetime.now(timezone.utc)
    record = TemporalRecord()
    index.register("fact_x", record)
    
    record2 = TemporalRecord()
    index.supersede("fact_x", "fact_y", record2, at_time=now)
    
    try:
        index.supersede("fact_x", "fact_z", record2, at_time=now)
        assert False, "Should have raised IntervalAlreadyClosedError"
    except IntervalAlreadyClosedError:
        pass

def test_unknown_fact():
    index = TemporalIndex()
    record = TemporalRecord()
    try:
        index.supersede("unknown_id", "new_id", record, at_time=datetime.now(timezone.utc))
        assert False, "Should have raised UnknownFactError"
    except UnknownFactError:
        pass

if __name__ == "__main__":
    print("--- Testing Temporal Subsystem ---")
    test_basic_validity()
    test_supersession()
    test_point_in_time_reconstruction()
    test_double_close_rejection()
    test_unknown_fact()
    print("All Temporal tests passed!\n")
