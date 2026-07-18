import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY_PRIMARY"))
models = ["llama-3.1-8b-instant", "llama3-8b-8192", "mixtral-8x7b-32768"]
for model in models:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=10
        )
        print(f"{model} success")
    except Exception as e:
        print(f"{model} error: {e}")
