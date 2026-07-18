import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.knowledge_routes import router, PreviewRequest

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test():
    req = {
        "source_type": "markdown",
        "content": "# FounderCourt (FC)\n\n## Product Vision and System Definition\n\n### 1. Executive Definition\n\nFounderCourt (FC) is a Decision Integrity Platform designed to protect the integrity of consequential organizational decisions throughout their lifecycle. FC creates a living digital representation—a Decision Digital Twin—of important decisions, including why they were made, the assumptions they depend on, the evidence supporting them, their expected outcomes, their dependencies on other decisions, and the conditions that could invalidate them.",
        "title": "FC Strategy"
    }
    response = client.post("/preview", json=req)
    print("Response status:", response.status_code)
    try:
        data = response.json()
        print("Keys:", data.keys())
        # print("Observations:", len(data.get("observations", [])))
    except Exception as e:
        print("Error parsing JSON:", e)

test()
