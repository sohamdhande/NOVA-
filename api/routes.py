import sqlite3
import os
import json
from fastapi import APIRouter, Request, HTTPException, Form
from core.event_bus import event_bus, NovaEvent

router = APIRouter()

@router.get("/status")
async def get_status():
    return {
        "status": "online",
        "model": "llama3.2"
    }

@router.post("/nova/shutdown")
async def nova_shutdown():
    try:
        with open("shutdown.lock", "w") as f:
            f.write("SHUTDOWN_REQUESTED")
        return {"status": "shutting_down"}
    except Exception as e:
        return {"error": str(e), "status": 500}

@router.get("/files/list")
async def list_files(path: str = "~/"):
    try:
        import os
        expanded = os.path.expanduser(path)
        if not os.path.exists(expanded):
            return {"files": [], "error": "Path not found"}
        
        items = []
        for name in os.listdir(expanded):
            full_path = os.path.join(expanded, name)
            is_dir = os.path.isdir(full_path)
            size_kb = os.path.getsize(full_path) // 1024 if not is_dir else 0
            items.append({
                "name": name,
                "is_dir": is_dir,
                "size_kb": size_kb,
                "path": full_path
            })
            
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"files": items}
    except Exception as e:
        return {"files": [], "error": str(e)}
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")

def _get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

@router.post("/terminal")
async def terminal_execute(request: Request):
    body = await request.json()
    command = body.get("command", "").strip()
    
    if not command:
        return JSONResponse(
            {"error": "Empty command"}, 
            status_code=400
        )
    
    WHITELIST = [
        "ls", "pwd", "echo", "cat", "grep", "find",
        "ps", "df", "du", "uname", "whoami", "which",
        "git status", "git log", "git branch", "git diff",
        "brew list", "brew info", "brew doctor",
        "pip list", "pip show", "python --version",
        "node --version", "npm list", "npm --version",
        "ollama list", "ollama ps",
        "top -l 1", "uptime", "date", "cal",
        "open .", "open -a"
    ]
    
    BLOCKED = [
        "rm -rf /", "format", "mkfs", "dd if=",
        "chmod 777 /", "sudo rm", "> /dev/sda"
    ]
    
    # Check blocked first
    if any(command.startswith(b) for b in BLOCKED):
        return JSONResponse({
            "status": "blocked",
            "message": "Command blocked by security policy.",
            "risk": "CRITICAL",
            "requires_approval": False,
            "output": "",
            "exit_code": -1
        })
    
    # Check whitelist
    is_whitelisted = any(
        command.strip().startswith(w) 
        for w in WHITELIST
    )
    
    if not is_whitelisted:
        # Publish approval request to event bus
        from core.event_bus import event_bus, NovaEvent
        import uuid
        approval_id = str(uuid.uuid4())[:8]
        
        await event_bus.publish(NovaEvent(
            source="terminal",
            type="approval_required",
            payload={
                "id": approval_id,
                "command": command,
                "reason": "Command not in whitelist",
                "risk": "MEDIUM"
            },
            priority=7
        ))
        
        return JSONResponse({
            "status": "pending_approval",
            "message": f"Command requires approval. Check Approval Panel.",
            "risk": "MEDIUM",
            "requires_approval": True,
            "approval_id": approval_id,
            "output": "",
            "exit_code": -1
        })
    
    # Execute whitelisted command
    import subprocess
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.path.expanduser("~")
        )
        output = result.stdout or result.stderr
        output = output[:3000]
        
        return JSONResponse({
            "status": "executed",
            "command": command,
            "output": output,
            "exit_code": result.returncode,
            "risk": "LOW",
            "requires_approval": False,
            "message": "Command executed."
        })
    except subprocess.TimeoutExpired:
        return JSONResponse({
            "status": "timeout",
            "message": "Command timed out after 15s.",
            "output": "",
            "exit_code": -1,
            "risk": "LOW",
            "requires_approval": False
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "output": "",
            "exit_code": -1,
            "risk": "LOW",
            "requires_approval": False
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
        "model": "llama3.2",
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

@router.post("/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    
    if not message.strip():
        return JSONResponse(
            {"error": "Empty message"}, 
            status_code=400
        )
    
    from core.intent_parser import intent_parser
    from core.tool_router import tool_router
    
    try:
        intent = await intent_parser.parse(message)
        result = await tool_router.route(intent)
        
        return JSONResponse({
            "message": result.output,
            "intent": result.intent,
            "block_type": result.block_type,
            "data": result.data,
            "requires_approval": result.requires_approval,
            "risk": result.risk,
            "success": result.success
        })
    except Exception as e:
        return JSONResponse({
            "message": f"N.O.V.A encountered an error: {str(e)}",
            "intent": "error",
            "block_type": "error",
            "data": {"error": str(e)},
            "requires_approval": False,
            "risk": "LOW",
            "success": False
        })

@router.get("/files/autocomplete")
async def file_autocomplete(q: str = ""):
    """Return file/folder suggestions for a partial path."""
    import os, glob
    
    if not q:
        # Return home directory contents
        q = "~/"
    
    expanded = os.path.expanduser(q)
    
    try:
        # Get matches
        matches = glob.glob(expanded + "*")
        
        # Filter out hidden + heavy dirs
        SKIP = ['node_modules', '.git', '__pycache__', 
                '.venv', 'venv', '.Trash']
        
        results = []
        for m in matches[:15]:
            name = os.path.basename(m)
            if name in SKIP or name.startswith('.'):
                continue
            results.append({
                "path": m.replace(
                    os.path.expanduser("~"), "~"
                ),
                "is_dir": os.path.isdir(m),
                "name": name
            })
        
        return JSONResponse({"suggestions": results})
    except Exception as e:
        return JSONResponse({"suggestions": []})


@router.get("/advisories")
async def get_advisories():
    """
    Generate proactive advisories based on system state.
    Runs deterministically — no LLM needed.
    """
    import psutil, os
    from datetime import datetime
    
    advisories = []
    
    # Check CPU
    cpu = psutil.cpu_percent(interval=0.1)
    if cpu > 85:
        advisories.append({
            "id": "cpu_high",
            "type": "warning",
            "message": f"CPU usage at {cpu:.0f}%. "
                      f"Recommend terminating heavy processes.",
            "action": "show processes",
            "priority": 8
        })
    
    # Check Memory
    mem = psutil.virtual_memory()
    if mem.percent > 85:
        advisories.append({
            "id": "mem_high", 
            "type": "warning",
            "message": f"Memory pressure at {mem.percent:.0f}%. "
                      f"System performance degrading.",
            "action": "check system",
            "priority": 7
        })
    
    # Check Disk
    disk = psutil.disk_usage('/')
    if disk.percent > 80:
        advisories.append({
            "id": "disk_high",
            "type": "warning", 
            "message": f"Disk at {disk.percent:.0f}%. "
                      f"Cleanup recommended.",
            "action": "run cleanup",
            "priority": 6
        })
    
    # Check Downloads folder
    downloads = os.path.expanduser("~/Downloads")
    if os.path.exists(downloads):
        count = len(os.listdir(downloads))
        if count > 50:
            advisories.append({
                "id": "downloads_full",
                "type": "info",
                "message": f"Downloads folder contains "
                          f"{count} files. Organization suggested.",
                "action": "clean downloads",
                "priority": 4
            })
    
    # Check Battery
    battery = psutil.sensors_battery()
    if battery and battery.percent < 20 \
       and not battery.power_plugged:
        advisories.append({
            "id": "battery_low",
            "type": "critical",
            "message": f"Battery at {battery.percent:.0f}%. "
                      f"Connect power immediately.",
            "action": None,
            "priority": 9
        })
    
    # Time-based advisory (8PM coding reminder)
    hour = datetime.now().hour
    if hour >= 20:
        advisories.append({
            "id": "evening_check",
            "type": "info",
            "message": "Evening check-in. "
                      "Review today's task completion.",
            "action": "show tasks",
            "priority": 3
        })
    
    # Sort by priority
    advisories.sort(key=lambda x: x["priority"], reverse=True)
    
    return JSONResponse({"advisories": advisories[:5]})
