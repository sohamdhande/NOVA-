import os
import json
from google import genai
from google.genai import types

gemini_key = os.getenv("GEMINI_API_KEY")
if not gemini_key:
    from dotenv import load_dotenv
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=gemini_key)
for m in ['gemini-1.5-flash-002', 'gemini-1.5-flash-latest', 'gemini-1.5-flash']:
    try:
        response = client.models.generate_content(
            model=m,
            contents='Respond with a JSON object containing {"hello": "world"}',
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        print(f"Success with {m}:", response.text.strip())
        break
    except Exception as e:
        print(f"Failed with {m}:", e)
