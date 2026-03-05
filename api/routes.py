import sqlite3
import os
import json
from fastapi import APIRouter
from core.event_bus import event_bus, NovaEvent

router = APIRouter()
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")

def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Create events table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            type TEXT,
            payload TEXT,
            priority INTEGER,
            timestamp TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    return conn

# Automatically save approval_required events to SQLite so the queue can fetch them
async def _on_approval_required(event: NovaEvent):
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (source, type, payload, priority, timestamp, status) VALUES (?, ?, ?, ?, ?, ?)",
        (event.source, event.type, json.dumps(event.payload), event.priority, event.timestamp.isoformat(), "pending")
    )
    conn.commit()
    conn.close()

# Subscribe the listener to catch the events from Controller
event_bus.subscribe("approval_required", _on_approval_required)


@router.get("/approvals")
def get_approvals():
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE type='approval_required' AND status='pending'")
    rows = cursor.fetchall()
    conn.close()
    
    approvals = []
    for r in rows:
        payload = {}
        try:
            payload = json.loads(r["payload"]) if r["payload"] else {}
        except:
            pass
            
        approvals.append({
            "id": r["id"],
            "source": r["source"],
            "type": r["type"],
            "payload": payload,
            "priority": r["priority"],
            "timestamp": r["timestamp"],
            "status": r["status"]
        })
    return approvals

@router.post("/approvals/{event_id}/approve")
async def approve_action(event_id: int):
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET status='approved' WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    
    await event_bus.publish(NovaEvent(
        source="dashboard",
        type="action_approved",
        payload={"id": event_id},
        priority=8
    ))
    return {"status": "approved"}

@router.post("/approvals/{event_id}/deny")
async def deny_action(event_id: int):
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET status='denied' WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    
    await event_bus.publish(NovaEvent(
        source="dashboard",
        type="action_denied",
        payload={"id": event_id},
        priority=8
    ))
    return {"status": "denied"}


# === DASHBOARD STUB ROUTES ===
# These return realistic mock data so the frontend can be built
# without waiting on backend feature implementation.
# Replace each stub with real logic as features are completed.

from fastapi.responses import JSONResponse
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
from core.biometric import biometric_auth
from datetime import datetime
import asyncio as _asyncio
import json as _json


# ─────────────────────────────────────────
# WebSocket Event Stream (stub)
# ─────────────────────────────────────────

@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    """WebSocket event stream for dashboard real-time updates."""
    await websocket.accept()
    try:
        while True:
            # Keep-alive heartbeat every 30 seconds
            await _asyncio.sleep(30)
            await websocket.send_text(_json.dumps({
                "type": "heartbeat",
                "source": "api_server",
                "payload": {},
                "priority": 0
            }))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ─────────────────────────────────────────
# Biometric Authentication
# ─────────────────────────────────────────

@router.post("/auth/biometric")
async def biometric_login():
    """Trigger TouchID and return a session JWT on success."""
    import asyncio
    from functools import partial

    loop = asyncio.get_event_loop()
    try:
        # Run the blocking biometric call in a thread pool
        # so it doesn't freeze the event loop
        result = await loop.run_in_executor(
            None,
            partial(
                biometric_auth.request_biometric_sync,
                "Unlock N.O.V.A Dashboard"
            )
        )
        if result:
            token = biometric_auth.create_session()
            return JSONResponse(content={
                "status": "granted",
                "token": token,
                "expires_in": 1800
            })
        else:
            return JSONResponse(
                status_code=401,
                content={"status": "denied", "reason": "Biometric failed"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "reason": str(e)}
        )


@router.get("/auth/verify")
async def biometric_verify():
    """Verify the current biometric session is still active."""
    from core.biometric import _active_session
    if biometric_auth.is_session_valid():
        expires_at = _active_session.get("expires_at")
        remaining = int((expires_at - datetime.utcnow()).total_seconds()) if expires_at else 0
        return JSONResponse(content={
            "status": "valid",
            "expires_in": max(remaining, 0)
        })
    else:
        return JSONResponse(
            status_code=401,
            content={"status": "expired", "reason": "Session expired or not started"}
        )


# ─────────────────────────────────────────
# GET /api/status  — already exists in core/api_server.py, skipped here
# ─────────────────────────────────────────


# STUB - replace with real data
@router.get("/metrics")
def get_metrics():
    return JSONResponse(content={
        "cpu": 34.5,
        "ram": 61.2,
        "disk": 48.0,
        "battery": 87,
        "battery_charging": False,
        "processes": [
            {"name": "Python", "cpu": 12.3, "pid": 1234},
            {"name": "Ollama", "cpu": 8.1, "pid": 5678},
            {"name": "Chrome", "cpu": 5.4, "pid": 9012}
        ],
        "network_up_kb": 120,
        "network_down_kb": 540
    })


# ─────────────────────────────────────────
# Goals
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/goals")
def get_goals():
    return JSONResponse(content={
        "goals": [
            {"id": "g1", "title": "Code 4hrs daily", "progress": 65, "status": "active"},
            {"id": "g2", "title": "Learn Playwright", "progress": 30, "status": "active"},
            {"id": "g3", "title": "Clear backlog", "progress": 100, "status": "completed"}
        ]
    })


class GoalCreate(BaseModel):
    title: str
    target: str
    deadline: str


# STUB - replace with real data
@router.post("/goals")
def create_goal(req: GoalCreate):
    return JSONResponse(content={"status": "created", "id": "g_new"})


# ─────────────────────────────────────────
# Automations
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/automations")
def get_automations():
    return JSONResponse(content={
        "automations": [
            {"id": "a1", "name": "Clean Downloads", "category": "system", "enabled": True, "last_run": "2h ago"},
            {"id": "a2", "name": "Empty Trash", "category": "system", "enabled": True, "last_run": "1d ago"},
            {"id": "a3", "name": "Update Brew Packages", "category": "system", "enabled": False, "last_run": "never"},
            {"id": "a4", "name": "Start Focus Mode", "category": "productivity", "enabled": True, "last_run": "today"},
            {"id": "a5", "name": "Close Distracting Apps", "category": "productivity", "enabled": True, "last_run": "today"},
            {"id": "a6", "name": "Open Coding Workspace", "category": "productivity", "enabled": True, "last_run": "3h ago"}
        ]
    })


# STUB - replace with real data
@router.post("/automations/{automation_id}/run")
def run_automation(automation_id: str):
    return JSONResponse(content={"status": "triggered", "automation_id": automation_id})


# STUB - replace with real data
@router.patch("/automations/{automation_id}/toggle")
def toggle_automation(automation_id: str):
    return JSONResponse(content={"status": "updated", "enabled": True})


# ─────────────────────────────────────────
# Terminal
# ─────────────────────────────────────────

class TerminalCommand(BaseModel):
    command: str


# STUB - replace with real data
@router.post("/terminal")
def run_terminal(req: TerminalCommand):
    return JSONResponse(content={
        "command": req.command,
        "output": "total 48\ndrwxr-xr-x  12 user  staff   384 Mar  5 09:00 .\n...",
        "risk_level": "LOW",
        "status": "executed",
        "duration_ms": 42
    })


# ─────────────────────────────────────────
# Memory
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/memory")
def get_memory():
    return JSONResponse(content={
        "events": [
            {"id": "e1", "timestamp": "2025-03-05T08:00:00Z", "type": "daemon_started", "source": "daemon"},
            {"id": "e2", "timestamp": "2025-03-05T08:05:00Z", "type": "email_received", "source": "daemon"},
            {"id": "e3", "timestamp": "2025-03-05T08:10:00Z", "type": "action_executed", "source": "controller"}
        ],
        "decisions": [
            {"id": "d1", "timestamp": "2025-03-05T08:00:00Z", "summary": "Scheduled morning cleanup", "outcome": "success"},
            {"id": "d2", "timestamp": "2025-03-05T08:05:00Z", "summary": "Email summarized and staged", "outcome": "pending"}
        ],
        "reflections": [
            {"date": "2025-03-04", "summary": "Productive day. 3 tasks completed. No anomalies detected.", "score": 82}
        ]
    })


# ─────────────────────────────────────────
# Reasoning
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/reasoning")
def get_reasoning():
    return JSONResponse(content={
        "current_plan": [
            {"step": 1, "action": "check_inbox", "status": "completed"},
            {"step": 2, "action": "summarize_emails", "status": "in_progress"},
            {"step": 3, "action": "update_notion_tasks", "status": "pending"}
        ],
        "confidence": 87,
        "last_inference_ms": 1840,
        "model": "mistral:7b-instruct",
        "recent_thoughts": [
            "No urgent emails detected.",
            "Task deadline approaching in 2h.",
            "System memory within normal range."
        ]
    })


# ─────────────────────────────────────────
# Productivity
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/productivity")
def get_productivity():
    return JSONResponse(content={
        "score_today": 74,
        "coding_hours": 2.5,
        "deep_work_sessions": 2,
        "task_completion_rate": 66,
        "distractions_detected": 3,
        "daily_report": {
            "date": "2025-03-05",
            "summary": "2 tasks completed. 2.5hrs coding detected. 3 distraction events.",
            "missed_goals": ["Code 4hrs daily"]
        },
        "weekly_report": {
            "week": "Mar 3-9 2025",
            "avg_score": 71,
            "best_day": "Monday",
            "total_coding_hours": 14.5
        }
    })


# ─────────────────────────────────────────
# Files
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/files")
def get_files():
    return JSONResponse(content={
        "downloads_count": 47,
        "downloads_size_mb": 2340,
        "large_files": [
            {"name": "project_backup.zip", "size_mb": 890, "path": "~/Downloads/project_backup.zip"},
            {"name": "screen_recording.mov", "size_mb": 540, "path": "~/Desktop/screen_recording.mov"}
        ],
        "duplicates_detected": 3,
        "trash_size_mb": 120
    })


# ─────────────────────────────────────────
# Comms
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/comms")
def get_comms():
    return JSONResponse(content={
        "emails": [
            {"id": "m1", "subject": "Project update", "sender": "team@company.com", "preview": "Hi, wanted to update you on...", "draft_reply": "Thanks for the update. I'll review and respond by EOD.", "priority": 6},
            {"id": "m2", "subject": "Invoice #1042", "sender": "billing@service.com", "preview": "Your invoice is ready...", "draft_reply": None, "priority": 3}
        ],
        "slack_messages": [
            {"id": "s1", "channel": "#general", "sender": "john", "preview": "Can you review the PR?", "draft_reply": "On it, will check now."}
        ],
        "whatsapp_messages": []
    })


# STUB - replace with real data
@router.post("/comms/{message_id}/approve")
def approve_comm(message_id: str):
    return JSONResponse(content={"status": "sent", "message_id": message_id})


# ─────────────────────────────────────────
# Skills
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/skills")
def get_skills():
    return JSONResponse(content={
        "installed": [
            {"id": "sk1", "name": "PDF Summarizer", "version": "1.0", "status": "active", "runs": 14},
            {"id": "sk2", "name": "Calendar Sync", "version": "1.2", "status": "active", "runs": 89}
        ],
        "available": [
            {"id": "sk3", "name": "Web Scraper", "description": "Scrape and parse any webpage"},
            {"id": "sk4", "name": "Repo Summarizer", "description": "Summarize any GitHub repo"},
            {"id": "sk5", "name": "File Organizer", "description": "Auto-organize files by type and date"}
        ]
    })


class SkillInstall(BaseModel):
    skill_id: str


# STUB - replace with real data
@router.post("/skills/install")
def install_skill(req: SkillInstall):
    return JSONResponse(content={"status": "installing", "skill_id": req.skill_id})


# ─────────────────────────────────────────
# Security
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/security")
def get_security():
    return JSONResponse(content={
        "autonomy_level": "controlled",
        "biometric_session_active": True,
        "session_expires_in_minutes": 24,
        "command_whitelist": ["ls", "pwd", "git status", "brew list", "ps aux"],
        "blocked_commands": ["rm -rf", "format", "dd if="],
        "recent_blocked": [
            {"command": "rm -rf /tmp/nova", "blocked_at": "2025-03-05T07:45:00Z", "reason": "CRITICAL tier"}
        ]
    })


class WhitelistAdd(BaseModel):
    command: str


# STUB - replace with real data
@router.post("/security/whitelist")
def add_to_whitelist(req: WhitelistAdd):
    return JSONResponse(content={"status": "added"})


# STUB - replace with real data
@router.delete("/security/whitelist/{command}")
def remove_from_whitelist(command: str):
    return JSONResponse(content={"status": "removed"})


# ─────────────────────────────────────────
# Settings
# ─────────────────────────────────────────

# STUB - replace with real data
@router.get("/settings")
def get_settings():
    return JSONResponse(content={
        "reasoning_interval_minutes": 60,
        "battery_threshold": 15,
        "telemetry_interval_seconds": 300,
        "notifications_enabled": True,
        "auto_cleanup_enabled": True,
        "cleanup_interval_hours": 24,
        "model": "mistral:7b-instruct",
        "log_retention_days": 30
    })


# STUB - replace with real data
@router.post("/settings")
def update_settings(req: dict):
    return JSONResponse(content={"status": "updated"})


# ─────────────────────────────────────────
# Nova Control
# ─────────────────────────────────────────

# STUB - replace with real data
@router.post("/nova/pause")
def pause_nova():
    return JSONResponse(content={"status": "paused", "autonomy": False})


# STUB - replace with real data
@router.post("/nova/resume")
def resume_nova():
    return JSONResponse(content={"status": "resumed", "autonomy": True})


# STUB - replace with real data
@router.post("/nova/reasoning-cycle")
def trigger_reasoning_cycle():
    return JSONResponse(content={"status": "triggered", "cycle_id": "rc_123"})


# STUB - replace with real data
@router.post("/nova/cleanup")
def trigger_cleanup():
    return JSONResponse(content={"status": "triggered"})


# STUB - replace with real data
@router.post("/nova/biometric-unlock")
def biometric_unlock():
    return JSONResponse(content={"status": "unlocked", "expires_in_minutes": 30})
