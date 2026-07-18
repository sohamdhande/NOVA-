from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
# Override auth dependency if there is one?
# The prompt said no auth decorators on existing routes. The global auth might be in api/main.py
response = client.get("/api/knowledge/master-report/status")
print(response.status_code, response.text)
