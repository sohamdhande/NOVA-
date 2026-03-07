
from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
import sys
import os

# Add parent directory to path to import nova
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nova import NovaApp
from core.daemon import NovaDaemon

# --- Imports ---
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.health import HealthEngine
from core.auth import AuthManager
from core.context_engine import ContextEngine
from core.chat_engine import ChatEngine

# Global state
nova_app = None
daemon = None
daemon_thread = None
auth_manager = None
health_engine = None
context_engine = None
chat_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global nova_app, daemon, daemon_thread, auth_manager, health_engine, context_engine, chat_engine
    print("[API] Initializing NovaApp...")
    nova_app = NovaApp()
    
    print("[API] Initializing Authn...")
    auth_manager = AuthManager()

    print("[API] Initializing HealthEngine...")
    health_engine = HealthEngine()

    print("[API] Initializing ContextEngine...")
    context_engine = ContextEngine(
        notion_tool=nova_app.notion_tool,
        expense_manager=nova_app.expense_manager,
        daemon=None,  # Set after daemon init below
        health_engine=health_engine,
    )
    
    print("[API] Starting Daemon in background thread...")
    daemon = NovaDaemon(
        memory_tool=nova_app.memory_tool,
        notion_tool=nova_app.notion_tool,
        pdf_tool=nova_app.pdf_tool
    )
    # Run daemon with handle_signals=False so it doesn't steal SIGINT from uvicorn
    daemon_thread = threading.Thread(target=daemon.run, args=(False,), daemon=True)
    daemon_thread.start()

    if context_engine:
        context_engine.daemon = daemon

    print("[API] Initializing ChatEngine...")
    chat_engine = ChatEngine(
        controller=nova_app.controller,
        health_engine=health_engine,
        context_engine=context_engine,
    )
    
    yield
    
    # Shutdown
    print("[API] Shutting down...")
    if daemon:
        daemon.stop()
        if daemon_thread and daemon_thread.is_alive():
            daemon_thread.join(timeout=5)
    print("[API] Shutdown complete.")

app = FastAPI(lifespan=lifespan)

from api.routes import router as approvals_router
app.include_router(approvals_router, prefix="/api")

# --- Middleware ---
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Whitelist
    # Public endpoints including status (which will self-sanitize)
    if request.url.path in ["/api/login", "/api/setup-password", "/docs", "/openapi.json", "/api/status", "/api/auth/biometric", "/api/auth/verify"] or request.url.path.startswith("/api/ws/"):
         return await call_next(request)
         
    # Options (CORS preflight) - let it pass or handle via CORSMiddleware (not added yet but good practice)
    if request.method == "OPTIONS":
        return await call_next(request)

    # Check for authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid token"}
        )
    
    try:
        parts = auth_header.split(" ")
        if len(parts) != 2:
            raise ValueError("Invalid Header Format")
        token = parts[1]
    except Exception:
         return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid Authorization header format"}
        )
    
    # Validate token — try password auth first, then biometric session
    from core.biometric import biometric_auth as _bio_auth
    token_valid = (auth_manager and auth_manager.validate_token(token)) or _bio_auth.is_session_valid()
    
    if not token_valid:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Token expired or invalid"}
        )
        
    return await call_next(request)

# --- CORS ---
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Endpoints ---

class PasswordRequest(BaseModel):
    password: str

@app.post("/api/setup-password")
def setup_password(req: PasswordRequest):
    if not auth_manager.is_setup_required():
        raise HTTPException(status_code=400, detail="Password already set")
        
    auth_manager.set_password(req.password)
    return {"message": "Password set successfully"}

@app.post("/api/login")
def login(req: PasswordRequest):
    # If setup required, block login
    if auth_manager.is_setup_required():
        raise HTTPException(status_code=403, detail="Setup required first")

    if auth_manager.verify_password(req.password):
        # Generate token
        result = auth_manager.create_token()
        return result
    else:
        raise HTTPException(status_code=401, detail="Invalid password")

@app.get("/api/status")
def get_status(request: Request):
    """
    Public Endpoint (Waitlisted).
    Returns basic info if unauthenticated, detailed if authenticated.
    """
    is_authenticated = False
    
    # Manually check auth
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            if auth_manager and auth_manager.validate_token(token):
                is_authenticated = True
        except:
            pass

    # Strict Public Info
    response = {
        "auth_setup_required": auth_manager.is_setup_required() if auth_manager else True
    }
    
    if is_authenticated:
        # Enriched response for authenticated users
        last_run = None
        if daemon and daemon.briefing:
            try:
                last_run = daemon.briefing.get_last_run()
            except Exception:
                pass
                
        # Check actual liveness
        is_alive = (daemon_thread is not None and daemon_thread.is_alive())
        
        # Log mismatch if any (thread dead but flag true)
        if daemon and daemon.running and not is_alive:
            print("[API] WARNING: Daemon thread dead but running flag is True. cleaning up...")
            
        response["mode"] = "api_server"
        response["daemon_running"] = is_alive
        response["daemon_last_error"] = daemon.last_error if daemon else None
        response["last_briefing_date"] = last_run
        response["authenticated"] = True

    return response

# --- Pydantic Models ---
# Imports moved to top

class ExpenseEntry(BaseModel):
    amount: float
    category: str
    description: str
    date: Optional[str] = None

# --- Dashboard Endpoints ---

# Briefing is now handled in api/routes.py

@app.get("/api/tasks")
def get_tasks():
    """Get active tasks with priority scores."""
    # We can use the notion tool directly via nova_app if we want "fresh" data
    # or use daemon.briefing._get_active_tasks() but that's internal.
    # nova_app is global.
    if not nova_app:
        return {"error": "App not initialized"}
        
    tasks = nova_app.notion_tool.read_open_tasks(limit=50).get("data", [])
    # Score them
    scored = nova_app.priority_engine.process_tasks(tasks)
    
    # Format for frontend
    result = []
    for t in scored:
        result.append({
            "id": t.get("id"),
            "title": t.get("title"),
            "due_date": t.get("due_date"),
            "status": t.get("status"),
            "score": t.get("computed_score", 0),
            "url": t.get("url")
        })
    return result

@app.get("/api/summary")
def get_summary():
    """
    Mission Status Summary + System Health.
    """
    if not nova_app:
        return {"error": "App not initialized"}

    # 1. Daemon Status
    is_alive = (daemon_thread is not None and daemon_thread.is_alive())
    last_error = daemon.last_error if daemon else None

    # 2. Expense Status
    exp_status = nova_app.expense_manager.get_status()
    expense_logged_today = exp_status.get("today_logged", False)
    missing_expense_days_count = exp_status.get("missing_days_count", 0)
    last_7_day_streak = exp_status.get("last_7_day_streak", False)

    # 3. Task Metrics
    tasks_resp = nova_app.notion_tool.read_open_tasks(limit=100)
    tasks = tasks_resp.get("data", []) if tasks_resp else []
    
    active_tasks_count = len(tasks)
    overdue_count = 0
    deadlines_48h_count = 0
    deadlines_24h_count = 0
    
    now = datetime.now()
    one_day = now + timedelta(hours=24)
    two_days = now + timedelta(hours=48)
    
    for t in tasks:
        due_str = t.get("due_date")
        if due_str:
            try:
                is_date_only = len(due_str) == 10
                
                if is_date_only:
                    due_dt = datetime.strptime(due_str, "%Y-%m-%d")
                    today_start = datetime(now.year, now.month, now.day)
                    if due_dt < today_start:
                        overdue_count += 1
                    elif due_dt <= (today_start + timedelta(hours=24)):
                        deadlines_24h_count += 1
                        deadlines_48h_count += 1
                    elif due_dt <= (today_start + timedelta(hours=48)):
                        deadlines_48h_count += 1
                else:
                    due_dt = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                    if due_dt.tzinfo:
                         due_dt = due_dt.replace(tzinfo=None)
                    
                    if due_dt < now:
                        overdue_count += 1
                    elif due_dt <= one_day:
                        deadlines_24h_count += 1
                        deadlines_48h_count += 1
                    elif due_dt <= two_days:
                        deadlines_48h_count += 1
            except Exception:
                pass

    # 4. Daemon health metrics
    daemon_crash_recent = last_error is not None
    daemon_uptime_hours = 0.0
    if daemon and hasattr(daemon, 'get_uptime_hours'):
        daemon_uptime_hours = daemon.get_uptime_hours()

    # 5. Calculate Health
    metrics = {
        "overdue_count": overdue_count,
        "deadlines_48h": deadlines_48h_count,
        "deadlines_24h": deadlines_24h_count,
        "active_tasks": active_tasks_count,
        "expense_logged_today": expense_logged_today,
        "missed_days_this_month": missing_expense_days_count,
        "last_7_day_streak": last_7_day_streak,
        "daemon_crash_recent": daemon_crash_recent,
        "daemon_uptime_hours": daemon_uptime_hours,
    }
    
    health_data = {}
    if health_engine:
        health_data = health_engine.calculate_health(metrics)

    # 6. Proactive Advisory
    proactive_data = {"triggered": False, "payload": None}
    if context_engine and health_data:
        snapshot = context_engine.get_context_snapshot(
            health_result=health_data,
            overdue_count=overdue_count,
            deadlines_24h=deadlines_24h_count,
            deadlines_48h=deadlines_48h_count,
            active_tasks=active_tasks_count,
            expense_logged_today=expense_logged_today,
            missed_days_month=missing_expense_days_count,
            daemon_uptime_hours=daemon_uptime_hours,
        )
        proactive_data = context_engine.evaluate(snapshot)

    return {
        "active_tasks_count": active_tasks_count,
        "overdue_count": overdue_count,
        "deadlines_48h_count": deadlines_48h_count,
        "expenses_missing_today": not expense_logged_today,
        "missing_expense_days_count": missing_expense_days_count,
        "daemon_running": is_alive,
        "daemon_last_error": last_error,
        **health_data,  # system_health, health_zone, health_trigger
        "proactive": proactive_data,
    }

@app.post("/api/daemon/restart")
def restart_daemon():
    """Safety-checked daemon restart."""
    global daemon, daemon_thread
    
    # Check actual thread liveness
    if daemon_thread and daemon_thread.is_alive():
        raise HTTPException(
            status_code=400, 
            detail="Daemon already running"
        )
        
    print("[API] Restarting Daemon...")
    
    # Instantiate new daemon using existing NovaApp tools
    if not nova_app:
        raise HTTPException(status_code=500, detail="NovaApp not initialized")
        
    daemon = NovaDaemon(
        memory_tool=nova_app.memory_tool,
        notion_tool=nova_app.notion_tool,
        pdf_tool=nova_app.pdf_tool
    )
    
    # Start thread
    daemon_thread = threading.Thread(target=daemon.run, args=(False,), daemon=True)
    daemon_thread.start()
    
    return {"status": "restarted"}

@app.get("/api/expense-status")
def get_expense_status():
    if not nova_app:
        return {"error": "App not initialized"}
    return nova_app.expense_manager.get_status()

@app.post("/api/expense")
def log_expense(entry: ExpenseEntry):
    if not nova_app:
        return {"error": "App not initialized"}
    
    return nova_app.expense_manager.add_expense(
        amount=entry.amount,
        category=entry.category,
        description=entry.description,
        date=entry.date
    )

@app.get("/api/expense-report")
def get_expense_report(start: str, end: str):
    if not nova_app:
        return {"error": "App not initialized"}
    return nova_app.expense_manager.get_report(start, end)


# --- Chat Endpoint ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

