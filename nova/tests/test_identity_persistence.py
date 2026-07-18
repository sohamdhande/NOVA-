import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.identity.persistence import SQLiteIdentityRegistry

def test_identity_persistence():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
        
    try:
        # Instance 1
        reg1 = SQLiteIdentityRegistry(db_path)
        id1 = reg1.resolve({"name": "Alice"}, alias_key="name")
        id2 = reg1.resolve({"name": "Bob"}, alias_key="name")
        
        reg1.add_alias(id1, "Alice Smith")
        reg1.merge(id2, id1)
        
        # Instance 2
        reg2 = SQLiteIdentityRegistry(db_path)
        
        # Check aliases survived
        assert reg2.lookup_by_alias("Alice Smith") == id1
        
        # Check merge survived
        assert reg2.get_entity(id2).canonical_id == id1
        
        # Check history
        assert id2 in reg2.history(id1)
        
    finally:
        Path(db_path).unlink()

if __name__ == "__main__":
    print("--- Testing Identity Persistence ---")
    test_identity_persistence()
    print("All Identity Persistence tests passed!\n")
