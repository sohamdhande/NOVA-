class LLMException(Exception):
    """Base exception for LLM provider layer."""
    pass


class LLMTimeoutError(LLMException):
    """Raised when an API inference request times out."""
    pass


class LLMRateLimitError(LLMException):
    """Raised when provider returns HTTP 429 Rate Limit Exceeded."""
    pass


class LLMProviderError(LLMException):
    """Raised when provider returns 5xx or connection failure."""
    pass


class LLMValidationError(LLMException):
    """Raised when AI JSON output fails schema validation."""
    pass


class LLMFailoverExhaustedError(LLMException):
    """Raised when both primary and secondary API keys fail."""
    pass
