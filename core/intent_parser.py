import json
import httpx
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedIntent:
    intent: str
    tool: str
    params: dict
    risk: str
    raw_message: str

class IntentParser:
    async def parse(self, message: str) -> ParsedIntent:
        system_prompt = """You are N.O.V.A's intent parser. Analyze the user message 
and return ONLY a JSON object with no explanation.

JSON schema:
{
  "intent": "<intent_type>",
  "tool": "<tool_name>", 
  "params": {
    // extracted parameters relevant to the intent
  },
  "risk": "LOW|MEDIUM|HIGH"
}

If unsure, default to intent="conversation", tool="llm"
"""
        prompt = f"SYSTEM:\n{system_prompt}\n\nUSER: {message}"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=15.0
                )
                response_text = resp.json().get("response", "")
            
            # Clean up potential markdown fences
            cleaned = response_text
            if "```json" in response_text:
                cleaned = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                cleaned = response_text.split("```")[1].split("```")[0]
                
            data = json.loads(cleaned.strip())
            
            return ParsedIntent(
                intent=data.get("intent", "conversation"),
                tool=data.get("tool", "llm"),
                params=data.get("params", {}),
                risk=data.get("risk", "LOW"),
                raw_message=message
            )
        except Exception as e:
            print(f"[IntentParser Error] {e}")
            return ParsedIntent(
                intent="conversation",
                tool="llm",
                params={},
                risk="LOW",
                raw_message=message
            )

intent_parser = IntentParser()
