"""
NOVA LLM Provider Layer package.
Implements read-only probabilistic inference components behind the AI Boundary.
Never mutates deterministic compiler state, runtime, or provenance graphs.
"""

from .provider import LLMProvider
from .groq import GroqProvider
from .gemini import GeminiProvider
from .exceptions import (
    LLMException, LLMTimeoutError, LLMRateLimitError,
    LLMProviderError, LLMValidationError, LLMFailoverExhaustedError
)
from .models import StructuredExtractionResult, ExtractionEntity, ExtractionRelationship, ExtractionObservation
from .cache import get_cache, DeterministicInferenceCache
from .logger import get_logger, InferenceLogger
from .prompts import format_extraction_prompt, format_reasoning_prompt, EXTRACTION_SYSTEM_PROMPT, REASONING_SYSTEM_PROMPT

_provider_singleton: LLMProvider = None


def get_provider() -> LLMProvider:
    global _provider_singleton
    if _provider_singleton is None:
        _provider_singleton = GroqProvider()
    return _provider_singleton


def set_provider(provider: LLMProvider) -> None:
    global _provider_singleton
    _provider_singleton = provider


__all__ = [
    "LLMProvider",
    "GroqProvider",
    "get_provider",
    "set_provider",
    "LLMException",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMProviderError",
    "LLMValidationError",
    "LLMFailoverExhaustedError",
    "StructuredExtractionResult",
    "ExtractionEntity",
    "ExtractionRelationship",
    "ExtractionObservation",
    "get_cache",
    "DeterministicInferenceCache",
    "get_logger",
    "InferenceLogger",
    "format_extraction_prompt",
    "format_reasoning_prompt",
    "EXTRACTION_SYSTEM_PROMPT",
    "REASONING_SYSTEM_PROMPT"
]
