import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.identity import IdentityRegistry, IdentityMergeError, UnknownAliasError

def test_rename_survival():
    registry = IdentityRegistry()
    id_1 = registry.resolve({"sender": "soham"}, alias_key="sender")
    
    # Add alias
    registry.add_alias(id_1, "soham.shaikh")
    
    # Resolve new object with new alias
    id_2 = registry.resolve({"sender": "soham.shaikh"}, alias_key="sender")
    
    assert id_1 == id_2, "Rename survival failed, returned different ID for alias"

def test_merge_survival():
    registry = IdentityRegistry()
    id_soham = registry.resolve({"sender": "soham"}, alias_key="sender")
    id_temp = registry.resolve({"sender": "soham_temp"}, alias_key="sender")
    
    assert id_soham != id_temp
    
    # Merge temp into soham
    registry.merge(source_id=id_temp, target_id=id_soham)
    
    # Resolving either should give id_soham
    id_1 = registry.resolve({"sender": "soham"}, alias_key="sender")
    id_2 = registry.resolve({"sender": "soham_temp"}, alias_key="sender")
    
    assert id_1 == id_soham
    assert id_2 == id_soham

def test_merge_chain_walking():
    registry = IdentityRegistry()
    id_a = registry.resolve({"sender": "A"}, alias_key="sender")
    id_b = registry.resolve({"sender": "B"}, alias_key="sender")
    id_c = registry.resolve({"sender": "C"}, alias_key="sender")
    
    registry.merge(id_a, id_b)
    registry.merge(id_b, id_c)
    
    # get_entity(A) should return C
    entity_a = registry.get_entity(id_a)
    assert entity_a.canonical_id == id_c
    
    # history(C) should include A and B
    hist = registry.history(id_c)
    assert id_a in hist
    assert id_b in hist

def test_merge_cycle_rejection():
    registry = IdentityRegistry()
    id_a = registry.resolve({"sender": "A"}, alias_key="sender")
    id_b = registry.resolve({"sender": "B"}, alias_key="sender")
    
    registry.merge(id_a, id_b)
    
    try:
        registry.merge(id_b, id_a)
        assert False, "Should have raised IdentityMergeError for cycle"
    except IdentityMergeError:
        pass

def test_unknown_alias():
    registry = IdentityRegistry()
    res = registry.lookup_by_alias("nonexistent")
    assert res is None, "Unknown alias should return None"

if __name__ == "__main__":
    print("--- Testing Identity ---")
    test_rename_survival()
    test_merge_survival()
    test_merge_chain_walking()
    test_merge_cycle_rejection()
    test_unknown_alias()
    print("All Identity tests passed!\n")
