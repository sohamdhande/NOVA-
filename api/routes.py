import sqlite3
import os
import json
from fastapi import APIRouter, Request, HTTPException, Form
from core.event_bus import event_bus, NovaEvent
from core.security_officer import security_officer
from datetime import datetime

router = APIRouter()

@router.get("/status")
async def get_status():
    return {
        "status": "online",
        "model": os.getenv("GROQ_MODEL_LARGE", "llama-3.3-70b-versatile")
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
    conn = sqlite3.connect("nova_logs.db", check_same_thread=False)
    rows = conn.execute("""
        SELECT id, timestamp, payload 
        FROM events 
        WHERE type = 'approval_required'
        ORDER BY timestamp DESC 
        LIMIT 20
    """).fetchall()

    items = []
    for row in rows:
        try:
            payload = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            items.append({
                "id": payload.get("id", row[0]),
                "command": payload.get("command", payload.get("action", "Unknown")),
                "risk": payload.get("risk", "MEDIUM"),
                "reason": payload.get("reason", "Requires authorization"),
                "source": payload.get("source", "system"),
                "timestamp": row[1],
                "status": "pending"
            })
        except:
            pass

    return JSONResponse({"approvals": items})

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

@router.get("/health")
async def get_health():
    import psutil
    
    # Calculate real health score
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    battery = psutil.sensors_battery()
    bat = battery.percent if battery else 100
    
    # Score: start at 100, deduct for bad metrics
    score = 100
    if cpu > 80: score -= 20
    elif cpu > 60: score -= 10
    if mem > 80: score -= 20
    elif mem > 60: score -= 10
    if disk > 90: score -= 20
    elif disk > 70: score -= 10
    if bat < 20: score -= 15
    elif bat < 40: score -= 5
    score = max(0, min(100, score))
    
    # Zone
    if score >= 80: zone = "STABLE"
    elif score >= 60: zone = "CONTROLLED"
    elif score >= 40: zone = "ELEVATED"
    else: zone = "CRITICAL"
    
    # Advisories based on metrics
    advisories = []
    if cpu > 80:
        advisories.append(f"CPU at {cpu:.0f}% — performance degraded")
    if mem > 80:
        advisories.append(f"Memory pressure at {mem:.0f}%")
    if disk > 80:
        advisories.append(f"Disk at {disk:.0f}% — cleanup recommended")
    
    return JSONResponse({
        "score": score,
        "zone": zone,
        "cpu": cpu,
        "memory": mem,
        "disk": disk,
        "battery": bat,
        "advisories": advisories
    })

@router.get("/briefing")
async def get_briefing():
    import psutil
    from datetime import datetime
    
    now = datetime.now()
    hour = now.hour
    
    items = []
    
    # System status item
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    items.append({
        "id": "sys",
        "type": "info",
        "severity": "low",
        "message": f"System nominal. CPU {cpu:.0f}%, RAM {mem:.0f}%."
    })
    
    # Downloads check
    import os
    downloads = os.path.expanduser("~/Downloads")
    if os.path.exists(downloads):
        count = len(os.listdir(downloads))
        if count > 30:
            items.append({
                "id": "dl",
                "type": "warning", 
                "severity": "medium",
                "message": f"Downloads folder has {count} files. Organization recommended."
            })
    
    # Task check from SQLite
    try:
        conn = sqlite3.connect("nova_logs.db", check_same_thread=False)
        task_count = conn.execute(
            "SELECT COUNT(*) FROM goals WHERE status='active'"
        ).fetchone()[0]
        if task_count > 0:
            items.append({
                "id": "tasks",
                "type": "info",
                "severity": "low", 
                "message": f"{task_count} active tasks in queue. Review recommended."
            })
    except:
        pass
    
    # Time-based greeting
    if 6 <= hour < 12:
        greeting = "Good morning."
    elif 12 <= hour < 17:
        greeting = "Good afternoon."
    else:
        greeting = "Good evening."
        
    items.insert(0, {
        "id": "greeting",
        "type": "info",
        "severity": "low",
        "message": f"{greeting} N.O.V.A systems online. {now.strftime('%A, %B %d')}."
    })
    
    return JSONResponse({
        "briefing": items,
        "generated_at": now.isoformat()
    })

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
    except (WebSocketDisconnect, _asyncio.CancelledError):
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

def _goals_db():
    import sqlite3, os
    db = os.path.join(
        os.path.dirname(__file__), 
        "../nova_logs.db"
    )
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            target TEXT,
            deadline TEXT,
            progress INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT 
                (datetime('now'))
        )
    """)
    conn.commit()
    return conn


@router.get("/goals")
def get_goals():
    import uuid
    conn = _goals_db()
    rows = conn.execute(
        "SELECT id, title, target, deadline, "
        "progress, status FROM goals "
        "ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return JSONResponse(content={
        "goals": [
            {
                "id": r[0], "title": r[1],
                "target": r[2], "deadline": r[3],
                "progress": r[4], "status": r[5]
            } for r in rows
        ]
    })


class GoalCreate(BaseModel):
    title: str
    target: str = ""
    deadline: str = ""


@router.post("/goals")
def create_goal(req: GoalCreate):
    import uuid
    goal_id = str(uuid.uuid4())[:8]
    conn = _goals_db()
    conn.execute(
        "INSERT INTO goals "
        "(id, title, target, deadline) "
        "VALUES (?,?,?,?)",
        (goal_id, req.title, 
         req.target, req.deadline)
    )
    conn.commit()
    conn.close()
    return JSONResponse(content={
        "status": "created", "id": goal_id
    })


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: str, req: dict = None):
    from fastapi import Request as Req
    conn = _goals_db()
    if req and "progress" in req:
        conn.execute(
            "UPDATE goals SET progress=? "
            "WHERE id=?",
            (req["progress"], goal_id)
        )
    if req and "status" in req:
        conn.execute(
            "UPDATE goals SET status=? "
            "WHERE id=?",
            (req["status"], goal_id)
        )
    conn.commit()
    conn.close()
    return JSONResponse(
        content={"status": "updated"}
    )


@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: str):
    conn = _goals_db()
    conn.execute(
        "DELETE FROM goals WHERE id=?",
        (goal_id,)
    )
    conn.commit()
    conn.close()
    return JSONResponse(
        content={"status": "deleted"}
    )


def _tasks_db():
    import sqlite3, os
    db = os.path.join(
        os.path.dirname(__file__),
        "../nova_logs.db"
    )
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            deadline TEXT,
            created_at TEXT DEFAULT 
                (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            order_index INTEGER DEFAULT 0,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)
    conn.commit()
    return conn


@router.get("/tasks")
def get_tasks():
    conn = _tasks_db()
    rows = conn.execute(
        "SELECT id, title, priority, "
        "status, deadline FROM tasks "
        "WHERE status != 'deleted' "
        "ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return JSONResponse(content={
        "tasks": [
            {
                "id": r[0], "title": r[1],
                "priority": r[2], "status": r[3],
                "deadline": r[4]
            } for r in rows
        ]
    })


class TaskCreate(BaseModel):
    title: str
    priority: str = "medium"
    deadline: str = ""


@router.post("/tasks")
def create_task(req: TaskCreate):
    import uuid
    task_id = str(uuid.uuid4())[:8]
    conn = _tasks_db()
    conn.execute(
        "INSERT INTO tasks "
        "(id, title, priority, deadline) "
        "VALUES (?,?,?,?)",
        (task_id, req.title,
         req.priority, req.deadline)
    )
    conn.commit()

    # Generate subtasks via LLM
    subtask_count = 0
    try:
        from llm import generate_subtasks
        subtask_titles = generate_subtasks(
            req.title, req.priority, req.deadline
        )
        for idx, st in enumerate(subtask_titles):
            conn.execute(
                "INSERT INTO subtasks "
                "(task_id, title, status, order_index) "
                "VALUES (?,?,?,?)",
                (task_id, st, "pending", idx)
            )
        conn.commit()
        subtask_count = len(subtask_titles)
    except Exception as e:
        print(f"[API] Subtask generation failed: {e}")

    conn.close()
    return JSONResponse(content={
        "status": "created",
        "id": task_id,
        "subtasks_generated": subtask_count
    })


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str, request: Request
):
    body = await request.json()
    conn = _tasks_db()
    if "status" in body:
        conn.execute(
            "UPDATE tasks SET status=? "
            "WHERE id=?",
            (body["status"], task_id)
        )
    if "priority" in body:
        conn.execute(
            "UPDATE tasks SET priority=? "
            "WHERE id=?",
            (body["priority"], task_id)
        )
    conn.commit()
    conn.close()
    return JSONResponse(
        content={"status": "updated"}
    )


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    conn = _tasks_db()
    conn.execute(
        "DELETE FROM tasks WHERE id=?",
        (task_id,)
    )
    conn.execute(
        "DELETE FROM subtasks WHERE task_id=?",
        (task_id,)
    )
    conn.commit()
    conn.close()
    return JSONResponse(
        content={"status": "deleted"}
    )


@router.get("/tasks/{task_id}/subtasks")
def get_subtasks(task_id: str):
    conn = _tasks_db()
    rows = conn.execute(
        "SELECT id, task_id, title, status, order_index "
        "FROM subtasks WHERE task_id=? "
        "ORDER BY order_index ASC",
        (task_id,)
    ).fetchall()
    conn.close()
    return JSONResponse(content={
        "task_id": task_id,
        "subtasks": [
            {
                "id": r[0],
                "task_id": r[1],
                "title": r[2],
                "status": r[3],
                "order_index": r[4]
            } for r in rows
        ]
    })


@router.patch("/tasks/{task_id}/subtasks/{subtask_id}")
async def update_subtask(
    task_id: str, subtask_id: int, request: Request
):
    body = await request.json()
    conn = _tasks_db()
    if "status" in body:
        conn.execute(
            "UPDATE subtasks SET status=? "
            "WHERE id=? AND task_id=?",
            (body["status"], subtask_id, task_id)
        )
    conn.commit()
    conn.close()
    return JSONResponse(
        content={"status": "updated"}
    )


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
        "open .", "open -a",
        "check processes", "nova status", "system scan",
        "ps -ef", "netstat", "lsof -i", "sw_vers"
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
    import subprocess, shlex
    try:
        result = subprocess.run(
            shlex.split(command),
            shell=False,
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
        "model": os.getenv("GROQ_MODEL_LARGE", "llama-3.3-70b-versatile"),
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
@router.post("/security/scan")
async def run_security_scan():
    try:
        result = await security_officer.deep_scan_with_ai()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={
            "threat_score": 0,
            "processes_checked": 0,
            "suspicious_files": 0,
            "open_ports": 0,
            "vulnerabilities": 0,
            "findings": [f"Scan error: {str(e)}"],
            "ai_analysis": "Scan failed.",
            "scanned_at": datetime.now().isoformat()
        })

# STUB - replace with real data

@router.get("/security/settings")
def get_security_settings():
    import sqlite3, json, os
    db_path = os.path.expanduser("~/.nova/security.db")
    defaults = {
        "auto_cleanup": "true",
        "auto_reasoning": "true", 
        "auto_reply": "false",
        "risk_threshold": "balanced",
        "autonomy": "controlled"
    }
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS 
            security_settings (
                key TEXT PRIMARY KEY, 
                value TEXT
            )""")
        # Insert defaults if not exist
        for k, v in defaults.items():
            c.execute(
                "INSERT OR IGNORE INTO security_settings VALUES (?,?)",
                (k, v)
            )
        conn.commit()
        rows = dict(c.execute(
            "SELECT key, value FROM security_settings"
        ).fetchall())
        conn.close()
        return JSONResponse(content={
            "auto_cleanup": rows.get("auto_cleanup", "true") == "true",
            "auto_reasoning": rows.get("auto_reasoning", "true") == "true",
            "auto_reply": rows.get("auto_reply", "false") == "true",
            "risk_threshold": rows.get("risk_threshold", "balanced"),
            "autonomy_level": rows.get("autonomy", "controlled")
        })
    except Exception as e:
        return JSONResponse(content=defaults)

@router.post("/security/autonomy")
def update_autonomy(req: dict):
    import sqlite3, json, os
    db_path = os.path.expanduser("~/.nova/security.db")
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS 
            security_settings (
                key TEXT PRIMARY KEY, 
                value TEXT
            )""")
            
        # Parse inputs
        for k, v in req.items():
            # Convert booleans to strings for sqlite
            str_val = str(v).lower() if isinstance(v, bool) else str(v)
            c.execute(
                "INSERT OR REPLACE INTO security_settings VALUES (?,?)",
                (k, str_val)
            )
        conn.commit()
        conn.close()
        
        # Reload scheduler if cleanup/reasoning changed
        if 'auto_cleanup' in req or 'auto_reasoning' in req:
            try:
                from core.scheduler import scheduler
                import schedule
                schedule.clear('auto_cleanup')
                schedule.clear('auto_reasoning')
                scheduler.start_auto_jobs()
            except Exception as e:
                print(f"[Scheduler] Reload error: {e}")
                
        return JSONResponse(content={"status": "updated"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.get("/security")
def get_security():
    import sqlite3, os
    db_path = os.path.expanduser("~/.nova/security.db")
    
    # default fallback
    autonomy_level = "controlled"
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS 
            security_settings (
                key TEXT PRIMARY KEY, 
                value TEXT
            )""")
        rows = dict(c.execute(
            "SELECT key, value FROM security_settings"
        ).fetchall())
        conn.close()
        
        autonomy_level = rows.get("autonomy", "controlled")
    except:
        pass
        
    return JSONResponse(content={
        "autonomy_level": autonomy_level,
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
        
        from core.memory_engine import memory_engine
        
        # Inject memory into conversation intents
        if intent.tool == "llm":
            intent.params["memory_context"] = \
                memory_engine.get_context_summary()
        
        
        # Safety override — catch document requests
        # that slip through
        msg_l = message.lower()
        if any(p in msg_l for p in [
            "word doc", "word document", ".docx",
            "as a doc", "as a document"
        ]) and intent.tool != "documents":
            intent.intent = "create_docx"
            intent.tool = "documents"
            intent.params = {"instruction": message}
            print(f"[CHAT] Override → documents/create_docx")

        if any(p in msg_l for p in [
            "spreadsheet", "excel", ".xlsx"
        ]) and intent.tool != "documents":
            intent.intent = "create_xlsx"
            intent.tool = "documents"
            intent.params = {"instruction": message}

        if any(p in msg_l for p in [
            "presentation", "powerpoint", "slides",
            ".pptx"
        ]) and intent.tool != "documents":
            intent.intent = "create_pptx"
            intent.tool = "documents"
            intent.params = {"instruction": message}
            
        print(f"[CHAT] Message: '{message}'")
        print(f"[CHAT] Tool: {intent.tool}")
        print(f"[CHAT] Params: {intent.params}")
        
        result = await tool_router.route(intent)
        
        # Guard against None result from handlers
        if result is None:
            from core.tool_router import ToolResult
            result = ToolResult(
                success=False,
                intent=intent.intent,
                output="Unable to process that request.",
                data={},
                block_type="error",
                risk="LOW",
                requires_approval=False
            )
        
        # Auto-save important facts from conversation
        memory_engine.save_conversation_summary([
            {"role": "user", "content": message},
            {"role": "assistant", "content": 
             str(result.output)}
        ])
        
        print(f"[Chat] Sending output: "
              f"{result.output[:200] if result.output else 'EMPTY'}")
        
        return JSONResponse({
            "message": str(result.output),
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

@router.post("/nova/execute")
async def execute_task(request: Request):
    """
    Execute a natural language task autonomously.
    N.O.V.A will plan and execute it step by step.
    """
    body = await request.json()
    instruction = body.get("instruction", "")
    
    if not instruction.strip():
        return JSONResponse(
            {"error": "No instruction provided"},
            status_code=400
        )
    
    from core.task_planner import task_planner
    import asyncio
    
    # Generate plan
    task = await task_planner.plan(instruction)
    
    # Execute in background
    asyncio.create_task(
        task_planner.execute(task)
    )
    
    return JSONResponse({
        "task_id": task.id,
        "title": task.title,
        "steps": [{
            "id": s.id,
            "index": s.index,
            "description": s.description,
            "action_type": s.action_type,
            "risk": s.risk,
            "status": s.status.value
        } for s in task.steps],
        "status": task.status.value,
        "message": f"Task queued. "
                  f"{len(task.steps)} steps planned."
    })

from fastapi.responses import StreamingResponse
import asyncio, json

@router.get("/nova/tasks/stream")
async def stream_task_progress():
    """
    SSE endpoint — streams live task progress
    to the dashboard frontend.
    """
    async def event_generator():
        from core.task_planner import task_planner
        
        while True:
            tasks = task_planner.get_active_tasks()
            
            data = {
                "timestamp": 
                    datetime.now().isoformat(),
                "active_count": len(tasks),
                "tasks": [{
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "progress": t.progress,
                    "current_step": 
                        t.current_step_index,
                    "total_steps": len(t.steps),
                    "current_step_name": (
                        t.steps[
                            t.current_step_index
                        ].description
                        if t.steps and 
                        t.current_step_index < 
                        len(t.steps)
                        else ""
                    )
                } for t in tasks]
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/nova/tasks/active")
async def get_active_tasks():
    """Get all currently running tasks."""
    from core.task_planner import task_planner
    
    tasks = task_planner.get_active_tasks()
    return JSONResponse({
        "tasks": [{
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "progress": t.progress,
            "current_step": t.current_step_index,
            "total_steps": len(t.steps),
            "steps": [{
                "description": s.description,
                "status": s.status.value,
                "result": s.result
            } for s in t.steps]
        } for t in tasks]
    })

@router.get("/nova/tasks/history")
async def get_task_history():
    """Get completed task history."""
    from core.task_planner import task_planner
    
    history = task_planner.get_history()
    return JSONResponse({
        "history": [{
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "steps_count": len(t.steps),
            "result": t.result_summary,
            "completed_at": t.completed_at.isoformat()
                if t.completed_at else None
        } for t in history]
    })

@router.post("/nova/tasks/{task_id}/pause")
async def pause_task(task_id: str):
    from core.task_planner import task_planner
    task_planner.pause()
    return JSONResponse({"status": "paused"})

@router.post("/nova/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    from core.task_planner import task_planner
    task_planner.resume()
    return JSONResponse({"status": "resumed"})

@router.get("/voice/status")
async def voice_status():
    try:
        from core.voice_daemon import voice_daemon
        from core.voice import voice
        return JSONResponse({
            "active": voice_daemon.is_active,
            "wake_word": voice.config.wake_word,
            "tts_voice": voice.config.tts_voice,
            "stt_model": voice.config.whisper_model,
            "recent_commands": 
                voice_daemon.get_command_log()[-5:]
        })
    except Exception as e:
        return JSONResponse({
            "active": False,
            "error": str(e)
        })

@router.post("/voice/speak")
async def voice_speak(request: Request):
    """Make N.O.V.A speak a message."""
    body = await request.json()
    text = body.get("text", "")
    if not text:
        return JSONResponse(
            {"error": "No text"}, 
            status_code=400
        )
    try:
        from core.voice import voice
        import threading
        threading.Thread(
            target=voice.speak,
            args=(text,),
            daemon=True
        ).start()
        return JSONResponse({
            "status": "speaking",
            "text": text
        })
    except Exception as e:
        return JSONResponse({"error": str(e)})

@router.post("/voice/toggle")
async def voice_toggle():
    """Start or stop voice listening."""
    try:
        from core.voice_daemon import voice_daemon
        import threading
        if voice_daemon.is_active:
            voice_daemon.stop()
            return JSONResponse({
                "status": "stopped"
            })
        else:
            threading.Thread(
                target=voice_daemon.start,
                daemon=True
            ).start()
            return JSONResponse({
                "status": "started"
            })
    except Exception as e:
        return JSONResponse({"error": str(e)})

from core.security_officer import security_officer

# Security endpoints

@router.get("/api/security/summary")
async def get_security_summary():
    return security_officer.get_security_summary()

@router.get("/api/security/events")
async def get_security_events(limit: int = 20):
    return {
        "events": security_officer
            .get_recent_events(limit)
    }

@router.post("/api/security/scan")
async def run_security_scan():
    result = security_officer.full_scan()
    return {"result": result}

@router.post("/api/security/scan/downloads")
async def scan_downloads():
    result = security_officer.scan_downloads()
    return {"result": result}

@router.post("/api/security/scan/file")
async def scan_file(body: dict):
    path = body.get("path", "")
    result = security_officer.scan_file(path)
    return result

@router.post("/api/security/scan/processes")
async def scan_processes():
    return security_officer.scan_processes()

@router.post("/api/security/scan/network")
async def scan_network():
    return security_officer.scan_network()

@router.post("/api/security/kill/{pid}")
async def kill_process(pid: int):
    result = security_officer.kill_process(pid)
    return {"result": result}

@router.post("/api/security/quarantine")
async def quarantine_file(body: dict):
    path = body.get("path", "")
    result = security_officer.quarantine_file(path)
    return {"result": result}

@router.post("/api/security/secure-mode")
async def toggle_secure_mode(body: dict):
    enable = body.get("enable", True)
    if enable:
        result = security_officer.enable_secure_mode()
    else:
        result = security_officer.disable_secure_mode()
    return {"result": result}

@router.get("/api/security/vulnerabilities")
async def scan_vulnerabilities():
    result = security_officer.scan_vulnerabilities()
    return {"result": result}

@router.get("/api/security/privacy")
async def check_privacy():
    return security_officer.check_privacy()
