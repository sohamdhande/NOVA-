import os
import time
import hmac
import hashlib
import json
import unittest
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# --- MOCK FASTAPI ---
mock_fastapi = MagicMock()
mock_app = MagicMock()
mock_fastapi.FastAPI.return_value = mock_app

# Define a pass-through decorator for app.post
def mock_post_decorator(*args, **kwargs):
    def wrapper(func):
        return func
    return wrapper

mock_app.post.side_effect = mock_post_decorator

# Mock HTTPException to be a standard exception we can catch
class MockHTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail

mock_fastapi.HTTPException = MockHTTPException

# Mock JSONResponse
def mock_json_response(content, status_code=200):
    return {"content": content, "status_code": status_code}

mock_responses = MagicMock()
mock_responses.JSONResponse = mock_json_response

sys.modules["fastapi"] = mock_fastapi
sys.modules["fastapi.responses"] = mock_responses
sys.modules["uvicorn"] = MagicMock()

# Set env var before import
os.environ["SLACK_SIGNING_SECRET"] = "test_secret"

# Import system under test
from core.slack_server import verify_signature, slack_events

class TestSlackServer(unittest.IsolatedAsyncioTestCase):
    
    def _generate_signature(self, timestamp, body):
        secret = "test_secret".encode("utf-8")
        base_string = f"v0:{timestamp}:{body}".encode("utf-8")
        signature = "v0=" + hmac.new(secret, base_string, hashlib.sha256).hexdigest()
        return signature

    async def test_url_verification(self):
        # Even with invalid signature or timestamp, this should pass
        timestamp = str(int(time.time()))
        body_dict = {"type": "url_verification", "challenge": "test_challenge_123"}
        body_str = json.dumps(body_dict)
        
        # Mock Request with invalid signature to prove check is skipped
        request = MagicMock()
        request.headers = {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": "v0=invalid_signature_skipped" 
        }
        request.body = AsyncMock(return_value=body_str.encode("utf-8"))
        
        # Note: we handle json parsing manually now in the handler using json.loads(body_bytes)
        # request.json check is removed from handler, so mock not strictly needed but good for completeness
        
        response = await slack_events(request)
        
        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["content"], {"challenge": "test_challenge_123"})

    async def test_valid_event_callback(self):
        timestamp = str(int(time.time()))
        body_dict = {
            "type": "event_callback",
            "event": {"type": "message", "text": "Hello"},
            "event_id": "Ev12345",
            "event_time": int(time.time())
        }
        body_str = json.dumps(body_dict)
        
        signature = self._generate_signature(timestamp, body_str)
        
        request = MagicMock()
        request.headers = {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature
        }
        request.body = AsyncMock(return_value=body_str.encode("utf-8"))
        request.json = AsyncMock(return_value=body_dict)
        
        response = await slack_events(request)
        
        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["content"], {"status": "ok"})

    async def test_invalid_signature(self):
        timestamp = str(int(time.time()))
        body_dict = {"type": "event_callback"}
        body_str = json.dumps(body_dict)
        body_bytes = body_str.encode("utf-8")
        
        request = MagicMock()
        request.headers = {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": "v0=invalid_signature"
        }
        request.body = AsyncMock(return_value=body_bytes)
        
        # Handler calls verify_signature internally for event_callback
        # We can test verify_signature directly or via handler. 
        # Testing via handler ensures integration.
        
        with self.assertRaises(MockHTTPException) as cm:
             await slack_events(request)
        
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "Invalid signature")

    async def test_stale_timestamp(self):
        # 6 minutes ago
        timestamp = str(int(time.time()) - 60 * 6)
        body_dict = {"type": "event_callback"}
        body_str = json.dumps(body_dict)
        body_bytes = body_str.encode("utf-8")
        
        request = MagicMock()
        request.headers = {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": "irrelevant"
        }
        request.body = AsyncMock(return_value=body_bytes)
        
        with self.assertRaises(MockHTTPException) as cm:
            await verify_signature(request, body_bytes)
            
        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("timestamp", cm.exception.detail.lower())

if __name__ == "__main__":
    unittest.main()
