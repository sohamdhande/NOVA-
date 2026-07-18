import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.ingestion import (
    Artifact, ArtifactRegistry, DuplicateArtifactError,
    SlackAdapter, GitCommitAdapter, PlaintextAdapter, MarkdownAdapter,
    PDFAdapter, EmailAdapter, CalendarAdapter, JSONAdapter, CSVAdapter,
    extract_observation_bundle
)
from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex
from nova.packages.provenance import ProvenanceGraph
from nova.packages.ai_boundary import Suggestion, SuggestionReviewBoundary, AIIsolationViolationError

def test_artifact_registry_and_duplicates():
    reg = ArtifactRegistry()
    art1 = Artifact(
        artifact_id="art_1",
        artifact_type="plaintext",
        source_system="test",
        source_identifier="id1",
        created_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        checksum="chk_123",
        version=1,
        metadata={},
        raw_payload="Hello world"
    )
    reg.register_artifact(art1)
    assert reg.get_artifact("art_1") == art1
    
    art_dup = Artifact(
        artifact_id="art_2",
        artifact_type="plaintext",
        source_system="test",
        source_identifier="id2",
        created_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        checksum="chk_123", # same checksum
        version=1,
        metadata={},
        raw_payload="Hello world"
    )
    try:
        reg.register_artifact(art_dup)
        assert False, "Should raise DuplicateArtifactError"
    except DuplicateArtifactError:
        pass

def test_all_adapters():
    reg = ArtifactRegistry()
    reg.register(SlackAdapter())
    reg.register(GitCommitAdapter())
    reg.register(PlaintextAdapter())
    reg.register(MarkdownAdapter())
    reg.register(PDFAdapter())
    reg.register(EmailAdapter())
    reg.register(CalendarAdapter())
    reg.register(JSONAdapter())
    reg.register(CSVAdapter())
    
    id_reg = IdentityRegistry()
    temp_idx = TemporalIndex()
    prov_graph = ProvenanceGraph()
    
    # Test Email Ingestion Pipeline
    email_art = Artifact(
        artifact_id="email_1",
        artifact_type="email",
        source_system="mail",
        source_identifier="msg1",
        created_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        checksum="chk_email",
        version=1,
        metadata={},
        raw_payload={"from": "alice@test.com", "subject": "Hello", "body": "Platform test"}
    )
    
    bundle = extract_observation_bundle(email_art, reg, id_reg, temp_idx, prov_graph)
    assert len(bundle.observations) == 1
    assert "alice@test.com" in bundle.observations[0].content["sender"]

def test_ai_boundary_isolation():
    b = SuggestionReviewBoundary()
    bad_sug = Suggestion(
        suggestion_type="authority",
        payload={"commit_hash": "sha256_fake"},
        confidence=0.99,
        source="RogueAI"
    )
    try:
        b.submit(bad_sug)
        assert False, "Should raise AIIsolationViolationError"
    except AIIsolationViolationError:
        pass

if __name__ == "__main__":
    print("--- Testing Ingestion Platform ---")
    test_artifact_registry_and_duplicates()
    test_all_adapters()
    test_ai_boundary_isolation()
    print("All ingestion platform tests passed!\n")
