import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any

logger = logging.getLogger("nova.packages.llm.audit")


@dataclass(frozen=True)
class InferenceAuditEntry:
    provider: str
    model: str
    latency_ms: float
    prompt_hash: str
    response_hash: str
    token_usage: dict[str, int]
    cache_hit: bool
    timestamp: str


class InferenceLogger:
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self._entries: list[InferenceAuditEntry] = []

    def log_inference(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        prompt: str,
        response: str,
        token_usage: dict[str, int] = None,
        cache_hit: bool = False
    ) -> InferenceAuditEntry:
        p_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        r_hash = hashlib.sha256(response.encode('utf-8')).hexdigest()
        ts = datetime.now(timezone.utc).isoformat()

        entry = InferenceAuditEntry(
            provider=provider,
            model=model,
            latency_ms=round(latency_ms, 2),
            prompt_hash=p_hash,
            response_hash=r_hash,
            token_usage=token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            cache_hit=cache_hit,
            timestamp=ts
        )
        self._entries.append(entry)

        if self.debug_mode:
            logger.debug(f"[LLM Audit DEBUG] Inference: {entry} | Prompt: {prompt[:100]}... | Response: {response[:100]}...")
        else:
            logger.info(f"[LLM Audit] {provider}/{model} | Latency: {entry.latency_ms}ms | CacheHit: {cache_hit} | Hash: {r_hash[:8]}")

        return entry

    def get_entries(self) -> list[InferenceAuditEntry]:
        return list(self._entries)


_default_logger = InferenceLogger()


def get_logger() -> InferenceLogger:
    return _default_logger
