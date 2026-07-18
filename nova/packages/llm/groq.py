import os
from typing import Generator, Optional, Any
from groq import Groq

from .provider import LLMProvider
from .exceptions import LLMRateLimitError, LLMProviderError

class GroqProvider(LLMProvider):
    provider_name = "groq"

    def __init__(self):
        self.clients = []
        if os.getenv("GROQ_API_KEY_PRIMARY"):
            self.clients.append(Groq(api_key=os.getenv("GROQ_API_KEY_PRIMARY")))
        if os.getenv("GROQ_API_KEY_FALLBACK"):
            self.clients.append(Groq(api_key=os.getenv("GROQ_API_KEY_FALLBACK")))
        if not self.clients:
            self.clients.append(Groq()) # Will try to use GROQ_API_KEY

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        from groq import RateLimitError, APIError, APIStatusError
        for i, client in enumerate(self.clients):
            try:
                response = client.chat.completions.create(
                    model=model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    messages=messages,
                    temperature=temperature or 0.2,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            except (RateLimitError, APIError, APIStatusError) as e:
                if i == len(self.clients) - 1:
                    raise
        raise LLMProviderError("All Groq clients failed.")

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        from groq import RateLimitError, APIError, APIStatusError
        import json
        
        for i, client in enumerate(self.clients):
            try:
                response = client.chat.completions.create(
                    model=model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    messages=messages,
                    temperature=temperature or 0.2,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            except (RateLimitError, APIError, APIStatusError) as e:
                if i == len(self.clients) - 1:
                    raise
        raise LLMProviderError("All Groq clients failed.")

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=messages,
            temperature=temperature or 0.2,
            max_tokens=max_tokens,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "provider": self.provider_name}
