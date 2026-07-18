from abc import ABC, abstractmethod
from typing import Generator, Optional, Any


class LLMProvider(ABC):
    """
    Abstract interface for NOVA probabilistic inference engines.
    No component outside nova.packages.llm may communicate directly with external APIs.
    """
    provider_name: str

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """Synchronous text generation."""
        pass

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> dict[str, Any]:
        """Synchronous structured JSON generation."""
        pass

    @abstractmethod
    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Token streaming generator."""
        pass

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Provider health and failover status payload."""
        pass

    def extract_organizational_knowledge(
        self,
        content: str,
        title: str = "",
        source_type: str = "plaintext"
    ) -> dict[str, Any]:
        """Orchestrate consolidated grouped intelligence extraction prompts."""
        import time
        from .prompts import format_grouped_prompts, EXTRACTION_SYSTEM_PROMPT
        
        # Chunking to avoid 6000 TPM limit on Groq free tier
        CHUNK_SIZE = 6000
        chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)] if content else [""]
        
        result = {}
        for idx, chunk in enumerate(chunks):
            chunk_title = f"{title} (Part {idx+1}/{len(chunks)})" if len(chunks) > 1 else title
            prompts = format_grouped_prompts(source_type, chunk_title, chunk)
            
            for p_name, p_text in prompts.items():
                for attempt in range(3):
                    try:
                        res = self.generate_json(p_text, system_prompt=EXTRACTION_SYSTEM_PROMPT)
                        if isinstance(res, dict):
                            for k, v in res.items():
                                if isinstance(v, list):
                                    result.setdefault(k, []).extend(v)
                        break
                    except Exception as e:
                        err_str = str(e).lower()
                        if "429" in err_str or "rate_limit" in err_str or "too large" in err_str:
                            print(f"[llm provider] Rate limit hit for {p_name} chunk {idx+1}. Sleeping 20s... ({e})")
                            time.sleep(20)
                        else:
                            print(f"[llm provider] Extraction failed for {p_name} chunk {idx+1}: {e}")
                            break
        
        return result
