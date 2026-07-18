import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.runtime.state_resolution import find_ambiguous_alternative_links

store = SQLiteCommitStore("/Users/sohamdhande/Docs_Local/NOVA/nova/knowledge.db")
ambiguous = find_ambiguous_alternative_links(store)

print(f"Found {len(ambiguous)} ambiguous matches in the dev database:")
for m in ambiguous:
    print(f"- Alternative: {m.alternative.node.output_id}, Matched On: {m.matched_on}")
