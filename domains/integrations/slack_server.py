import os
import time
import hmac
import hashlib
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("slack_server")

app = FastAPI()

# Configuration
from pathlib import Path
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
    except Exception as e:
        logger.warning(f"Failed to load .env file: {e}")

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

async def verify_signature(request: Request, body_bytes: bytes):
    """
    Verify Slack request signature.
    Raises HTTPException(403) if verification fails.
    """
    if not SLACK_SIGNING_SECRET:
        logger.error("SLACK_SIGNING_SECRET not set")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    # 1. Get headers
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not signature:
        logger.warning("Missing Slack signature headers")
        raise HTTPException(status_code=403, detail="Missing signature headers")

    # 2. Check timestamp (replay attack protection)
    # Reject if more than 5 minutes old
    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            logger.warning(f"Request timestamp too old: {timestamp}")
            raise HTTPException(status_code=403, detail="Request timestamp out of range")
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid timestamp")

    # 3. Verify signature
    # Format: v0:{timestamp}:{body}
    decoded_body = body_bytes.decode("utf-8")
    
    base_string = f"v0:{timestamp}:{decoded_body}".encode("utf-8")
    
    # Compute HMAC SHA256
    # Signing secret key
    secret_key = SLACK_SIGNING_SECRET.encode("utf-8")
    
    my_signature = "v0=" + hmac.new(secret_key, base_string, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(my_signature, signature):
        logger.warning("Invalid Slack signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

@app.post("/slack/events")
async def slack_events(request: Request):
    """
    Handle incoming Slack events.
    """
    # 1. Read body first
    try:
        body_bytes = await request.body()
        # Parse payload to check type
        import json
        payload = json.loads(body_bytes)
    except Exception:
         raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event_type = payload.get("type")
    
    # 2. Handle URL Verification (Challenge) - SKIP SIGNATURE CHECK
    if event_type == "url_verification":
        logger.info("Received url_verification challenge (skipping signature verification)")
        return JSONResponse(content={"challenge": payload.get("challenge")})
    
    # 3. Verify request for all other events
    await verify_signature(request, body_bytes)
    
    # Handle Event Callback
    if event_type == "event_callback":
        event = payload.get("event", {})
        event_id = payload.get("event_id")
        event_time = payload.get("event_time")
        
        logger.info(f"Received event: type={event.get('type')}, id={event_id}, time={event_time}")
        logger.debug(f"Event payload: {payload}")
        
        # TODO: Phase 2 - Integrate with Controller/Task System
        
        return JSONResponse(content={"status": "ok"})
    
    # Default fallback
    logger.info(f"Received unhandled event type: {event_type}")
    return JSONResponse(content={"status": "ok"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
