import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.ingestion import (
    SlackAdapter, GitCommitAdapter, PlaintextAdapter, IngestionRegistry,
    IngestionParseError, UnknownSourceTypeError
)

def test_slack_adapter():
    adapter = SlackAdapter()
    
    # Valid
    valid_input = {"channel": "general", "user": "Alice", "text": "Hello"}
    parsed = adapter.parse(valid_input)
    assert parsed == {"sender": "Alice", "content": "Hello", "source_path": "slack/general"}
    
    # Missing key
    try:
        adapter.parse({"channel": "general", "user": "Alice"})
        assert False, "Should raise IngestionParseError"
    except IngestionParseError:
        pass
        
    # Determinism
    parsed2 = adapter.parse(valid_input)
    assert parsed == parsed2

def test_git_adapter():
    adapter = GitCommitAdapter()
    
    # Valid
    valid_input = {"author": "Bob", "message": "Fix bug", "sha": "1234567"}
    parsed = adapter.parse(valid_input)
    assert parsed == {"sender": "Bob", "content": "Fix bug", "source_path": "git/commit/1234567"}
    
    # Missing key
    try:
        adapter.parse({"author": "Bob", "message": "Fix bug"})
        assert False, "Should raise IngestionParseError"
    except IngestionParseError:
        pass
        
    # Determinism
    parsed2 = adapter.parse(valid_input)
    assert parsed == parsed2

def test_plaintext_adapter():
    adapter = PlaintextAdapter()
    
    # Valid
    text = "Hello world"
    parsed = adapter.parse(text)
    assert parsed["sender"] == "unknown"
    assert parsed["content"] == "Hello world"
    assert parsed["source_path"].startswith("plaintext/")
    
    # Empty
    try:
        adapter.parse("")
        assert False, "Should raise IngestionParseError"
    except IngestionParseError:
        pass
        
    # Determinism
    parsed2 = adapter.parse(text)
    assert parsed == parsed2

def test_registry():
    registry = IngestionRegistry()
    registry.register(SlackAdapter())
    
    # Valid ingest
    parsed = registry.ingest("slack", {"channel": "test", "user": "test", "text": "test"})
    assert parsed["source_path"] == "slack/test"
    
    # Unknown source
    try:
        registry.ingest("git", {})
        assert False, "Should raise UnknownSourceTypeError"
    except UnknownSourceTypeError:
        pass

if __name__ == "__main__":
    print("--- Testing Ingestion ---")
    test_slack_adapter()
    test_git_adapter()
    test_plaintext_adapter()
    test_registry()
    print("All Ingestion tests passed!\n")
