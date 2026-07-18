import os
from nova.packages.runtime.store import KnowledgeStore
from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.runtime.state_resolution import get_state_snapshot
from nova.packages.runtime.master_report_renderers import SECTION_RENDERERS

# Using the store API to get state snapshot with an isolated memory DB for testing
store = KnowledgeStore(SQLiteCommitStore(db_path=":memory:"))

try:
    snapshot = get_state_snapshot(store)
    
    # We want to test only these 4:
    sections_to_test = ["market_opportunity", "competitive_landscape", "team", "financials_ask"]
    
    for section_name in sections_to_test:
        func, _ = SECTION_RENDERERS[section_name]
        out = func(snapshot)
        print(f"=== {section_name.upper()} ===")
        print(out)
except Exception as e:
    print(f"Error querying DB: {e}")
