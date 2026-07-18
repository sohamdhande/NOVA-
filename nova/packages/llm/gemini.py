import os
import json
from typing import Generator, Optional, Any
from google import genai
from google.genai import types

from .provider import LLMProvider
from .exceptions import LLMRateLimitError, LLMProviderError

class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self):
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            from dotenv import load_dotenv
            load_dotenv()
            gemini_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=gemini_key)
        self.default_model = "gemini-2.5-flash"

    def _build_config(self, system_prompt: str, temperature: Optional[float], max_tokens: Optional[int], json_mode: bool = False) -> types.GenerateContentConfig:
        kwargs = {}
        if system_prompt:
            kwargs["system_instruction"] = system_prompt
        if temperature is not None:
            kwargs["temperature"] = temperature
        else:
            kwargs["temperature"] = 0.2
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if json_mode:
            kwargs["response_mime_type"] = "application/json"
        
        return types.GenerateContentConfig(**kwargs)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        config = self._build_config(system_prompt, temperature, max_tokens)
        try:
            response = self.client.models.generate_content(
                model=model or self.default_model,
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            raise LLMProviderError(f"Gemini generation failed: {str(e)}")

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> dict[str, Any]:
        config = self._build_config(system_prompt, temperature, max_tokens, json_mode=True)
        try:
            response = self.client.models.generate_content(
                model=model or self.default_model,
                contents=prompt,
                config=config,
            )
            return json.loads(response.text)
        except Exception as e:
            raise LLMProviderError(f"Gemini JSON generation failed: {str(e)}")

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> Generator[str, None, None]:
        config = self._build_config(system_prompt, temperature, max_tokens)
        try:
            response = self.client.models.generate_content_stream(
                model=model or self.default_model,
                contents=prompt,
                config=config,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise LLMProviderError(f"Gemini streaming failed: {str(e)}")

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "provider": self.provider_name}
