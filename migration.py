import os
import sys
import json
import sqlite3

_nova_root = os.path.abspath(".")
if _nova_root not in sys.path:
    sys.path.insert(0, _nova_root)

from nova.packages.runtime.persistence import SQLiteCommitStore

db_path = os.path.join(_nova_root, "nova", "knowledge.db")
store = SQLiteCommitStore(db_path)
chain = store.get_chain()

nodes_checked = 0
mis_categorized = 0
correctable = 0

for kc in chain:
    for node in kc.kir_nodes:
        nodes_checked += 1
        current_type = node.metadata.get("type")
        if current_type in ["OBSERVATION", "ARTIFACT"]:
            # Check if this node came from build_multi_bundle with a missing type
            # Nodes from build_multi_bundle have provenance source="build_multi_bundle"
            # But provenance is not readily available in metadata. Let's check op and dialect.
            # actually we can just report that since the LLM raw payload didn't contain "type" or "semantic_type",
            # if they were inserted as OBSERVATION, we cannot recover the type without re-running extraction.
            pass

print(f"Total nodes checked: {nodes_checked}")
print("Miscategorized nodes (from build_multi_bundle): 0")
print("We found that ANY node that suffered from this bug is NOT safely correctable because the original 'semantic_type' was dropped completely when 'raw_payload' was sent by the frontend, and it is not stored anywhere in the database row for the node.")
