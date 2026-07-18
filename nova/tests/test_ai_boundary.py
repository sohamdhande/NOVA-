import sys
import ast
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.ai_boundary import (
    MockEntitySuggester, MockRelationshipSuggester, SuggestionReviewBoundary,
    SuggestionAlreadyDecidedError, SuggestionAlreadyRejectedError
)
from nova.packages.runtime import KnowledgeStore
from nova.packages.identity import IdentityRegistry

def test_suggester():
    suggester = MockEntitySuggester()
    sugs = suggester.suggest("Alice went to the Moon")
    
    assert len(sugs) == 2
    assert sugs[0].payload["name"] == "Alice"
    assert sugs[1].payload["name"] == "Moon"
    
def test_review_boundary():
    boundary = SuggestionReviewBoundary()
    suggester = MockEntitySuggester()
    
    sugs = suggester.suggest("Bob built a System")
    for s in sugs:
        boundary.submit(s)
        
    pending = boundary.pending()
    assert len(pending) == 2
    
    # Accept one
    payload = boundary.accept(pending[0], accepted_by="human_1")
    assert payload["name"] == "Bob"
    assert payload["_accepted_by"] == "human_1"
    
    # Double decide
    try:
        boundary.accept(pending[0], accepted_by="human_2")
        assert False, "Should have raised SuggestionAlreadyDecidedError"
    except SuggestionAlreadyDecidedError:
        pass
        
    # Reject the other
    boundary.reject(pending[1], reason="Testing rejection")
    try:
        boundary.accept(pending[1], accepted_by="human_1")
        assert False, "Should have raised SuggestionAlreadyRejectedError"
    except SuggestionAlreadyRejectedError:
        pass

def test_side_effects():
    store = KnowledgeStore()
    registry = IdentityRegistry()
    boundary = SuggestionReviewBoundary()
    suggester = MockEntitySuggester()
    
    sug = suggester.suggest("Charlie")[0]
    boundary.submit(sug)
    payload = boundary.accept(sug, accepted_by="test")
    
    # Assert nothing touched
    assert len(store.get_chain()) == 0, "Accept triggered a commit!"
    assert len(registry._entities) == 0, "Accept triggered an identity registration!"

def test_import_boundary():
    """
    Check the AST of all .py files in ai_boundary/ to ensure they do not import
    forbidden packages (identity, temporal, provenance, runtime, compiler, passes).
    """
    ai_boundary_dir = Path(__file__).parent.parent / "packages" / "ai_boundary"
    py_files = list(ai_boundary_dir.rglob("*.py"))
    
    forbidden = {"identity", "temporal", "provenance", "runtime", "compiler", "passes"}
    
    print("\n  [AST Import Check] Scanning files for forbidden imports:")
    for py_file in py_files:
        print(f"    - Checking {py_file.name}...")
        with open(py_file, "r") as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for fbd in forbidden:
                        assert fbd not in alias.name, f"Forbidden import found in {py_file.name}: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for fbd in forbidden:
                        assert fbd not in node.module, f"Forbidden import found in {py_file.name}: {node.module}"

if __name__ == "__main__":
    print("--- Testing AI Boundary ---")
    test_suggester()
    test_review_boundary()
    test_side_effects()
    test_import_boundary()
    print("All AI Boundary tests passed!\n")
