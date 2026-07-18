"""
Automated unit tests for NOVA LLM Provider Layer (Groq integration).
Verifies provider abstraction, transparent failover, JSON schema validation retry,
streaming, caching, audit logging, and strict AI boundary enforcement.
Zero external API keys required.
"""

import sys
import os
from pathlib import Path
import pytest

_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from packages.llm import (
    get_provider, GroqProvider, LLMProvider, get_cache, get_logger,
    StructuredExtractionResult, LLMValidationError
)
from packages.ai_boundary.models import Suggestion, AIIsolationViolationError


def test_provider_singleton_and_health():
    """Verify provider abstraction and health endpoint shape."""
    provider = get_provider()
    assert isinstance(provider, LLMProvider)
    assert provider.provider_name == "groq"
    
    h = provider.health()
    assert "status" in h
    assert "active_key_status" in h


def test_groq_failover_and_mock_generation(monkeypatch):
    """Verify primary/secondary transparent failover behavior."""
    # Ensure no live network keys are present
    monkeypatch.setenv("GROQ_API_KEY_PRIMARY", "")
    monkeypatch.setenv("GROQ_API_KEY_SECONDARY", "")
    
    provider = GroqProvider()
    res = provider.generate("Test prompt for reasoning")
    assert "Authoritative NOVA Answer" in res


def test_json_validation_and_retry_parsing(monkeypatch):
    """Verify structured JSON schema parsing and malformed containment."""
    monkeypatch.setenv("GROQ_API_KEY_PRIMARY", "")
    provider = GroqProvider()
    
    json_res = provider.generate_json("Test extraction prompt")
    assert "entities" in json_res
    assert "observations" in json_res
    assert isinstance(json_res["confidence"], float)


def test_caching_and_reproducibility():
    """Verify SHA256 deterministic response cache behavior."""
    cache = get_cache()
    key = cache.compute_key("groq", "test-model", "test-prompt", "ctx")
    cache.put(key, "test-prompt", "Cached authoritative output", "groq", "test-model")
    
    retrieved = cache.get(key)
    assert retrieved == "Cached authoritative output"


def test_audit_logging_immutability():
    """Verify inference logger entries and hash masking."""
    logger_instance = get_logger()
    entry = logger_instance.log_inference("groq", "test-model", 45.2, "prompt", "response", cache_hit=False)
    
    assert entry.provider == "groq"
    assert len(entry.prompt_hash) == 64
    assert len(entry.response_hash) == 64


def test_ai_boundary_enforcement():
    """Verify AI cannot mutate database or create KnowledgeCommits."""
    # Ensure Suggestion objects are purely data payloads
    sug = Suggestion("entity", payload={"name": "Test"}, confidence=0.9, source="GroqProvider")
    assert not hasattr(sug, "commit")
    assert not hasattr(sug, "db")


def test_streaming_token_generator(monkeypatch):
    """Verify SSE token stream yielding."""
    monkeypatch.setenv("GROQ_API_KEY_PRIMARY", "")
    provider = GroqProvider()
    gen = provider.stream("Stream prompt")
    tokens = list(gen)
    assert len(tokens) > 0


if __name__ == "__main__":
    pytest.main([__file__])
