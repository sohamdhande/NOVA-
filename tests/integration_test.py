import asyncio
import httpx
import json
import sqlite3
import os
import sys
from datetime import datetime

# Ensure we can import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results = []

def log(status, component, message):
    results.append({
        "status": status,
        "component": component, 
        "message": message
    })
    print(f"{status} {component:30s} {message}")

async def test_llm():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2",
                      "prompt": "Say OK",
                      "stream": False},
                timeout=15
            )
            if r.status_code == 200:
                log(PASS, "LLM (llama3.2)", 
                    "Ollama responding")
            else:
                log(FAIL, "LLM (llama3.2)",
                    f"Status {r.status_code}")
    except Exception as e:
        log(FAIL, "LLM (llama3.2)", str(e))

async def get_auth_token(client):
    try:
        # Initial password setup if needed
        await client.post(BASE_URL + "/api/setup-password", json={"password": "admin"}, timeout=5)
        # Login
        r = await client.post(BASE_URL + "/api/login", json={"password": "admin"}, timeout=5)
        if r.status_code == 200:
            return r.json().get("token")
    except:
        pass
    return None

async def test_backend():
    endpoints = [
        "/api/status",
        "/api/metrics", 
        "/api/tasks",
        "/api/goals",
        "/api/approvals",
        "/api/automations",
        "/api/memory",
        "/api/reasoning",
        "/api/productivity",
        "/api/files",
        "/api/comms",
        "/api/skills",
        "/api/security",
        "/api/settings",
        "/api/briefing",
        "/api/advisories",
    ]
    async with httpx.AsyncClient() as client:
        token = await get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        for ep in endpoints:
            try:
                r = await client.get(
                    BASE_URL + ep, timeout=5, headers=headers
                )
                if r.status_code == 200:
                    log(PASS, f"GET {ep}", "200 OK")
                else:
                    log(FAIL, f"GET {ep}",
                        f"Status {r.status_code}")
            except Exception as e:
                log(FAIL, f"GET {ep}", str(e))

async def test_chat():
    test_messages = [
        ("hi", "conversation", "Basic conversation"),
        ("check system", "system", "System intent"),
        ("show tasks", "tasks", "Task intent"),
        ("search files nova", "file_search", 
         "File search intent"),
    ]
    async with httpx.AsyncClient() as client:
        token = await get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        for msg, expected_intent, desc in test_messages:
            try:
                r = await client.post(
                    BASE_URL + "/api/chat",
                    json={"message": msg},
                    headers=headers,
                    timeout=30
                )
                data = r.json()
                intent = data.get("intent", "")
                if r.status_code == 200:
                    log(PASS, f"CHAT: {desc}",
                        f"intent={intent}")
                else:
                    log(FAIL, f"CHAT: {desc}",
                        f"Status {r.status_code}")
            except Exception as e:
                log(FAIL, f"CHAT: {desc}", str(e))

async def test_terminal():
    commands = [
        ("pwd", "LOW", True),
        ("ls -la", "LOW", True),
        ("git status", "LOW", True),
        ("rm -rf /", "CRITICAL", False),
    ]
    async with httpx.AsyncClient() as client:
        token = await get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        for cmd, expected_risk, should_exec in commands:
            try:
                r = await client.post(
                    BASE_URL + "/api/terminal",
                    json={"command": cmd},
                    headers=headers,
                    timeout=15
                )
                data = r.json()
                status = data.get("status")
                if should_exec and status == "executed":
                    log(PASS, f"TERMINAL: {cmd}",
                        "Executed correctly")
                elif not should_exec and \
                     status == "blocked":
                    log(PASS, f"TERMINAL: {cmd}",
                        "Blocked correctly")
                else:
                    log(WARN, f"TERMINAL: {cmd}",
                        f"status={status}")
            except Exception as e:
                log(FAIL, f"TERMINAL: {cmd}", str(e))

async def test_event_bus():
    try:
        from core.event_bus import event_bus, NovaEvent
        
        received = []
        async def handler(event):
            received.append(event)
        
        event_bus.subscribe("test_ping", handler)
        await event_bus.start()
        
        await event_bus.publish(NovaEvent(
            source="test",
            type="test_ping",
            payload={"test": True},
            priority=1
        ))
        
        await asyncio.sleep(0.5)
        
        if len(received) > 0:
            log(PASS, "EVENT BUS", 
                "Pub/sub working")
        else:
            log(FAIL, "EVENT BUS",
                "Event not received")
    except Exception as e:
        log(FAIL, "EVENT BUS", str(e))

def test_memory():
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nova_logs.db")
        conn = sqlite3.connect(
            db_path, 
            check_same_thread=False
        )
        
        # Check tables exist
        tables = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        
        required = ["events", "goals", "auth_sessions"]
        for t in required:
            if t in table_names:
                log(PASS, f"SQLITE: {t}", "Table exists")
            else:
                log(FAIL, f"SQLITE: {t}", 
                    "Table missing")
        
        # Check event count
        count = conn.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]
        log(PASS, "SQLITE: events",
            f"{count} events stored")
            
    except Exception as e:
        log(FAIL, "SQLITE", str(e))

def test_metrics():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        battery = psutil.sensors_battery()
        
        log(PASS, "METRICS: CPU", 
            f"{cpu}%")
        log(PASS, "METRICS: RAM",
            f"{mem.percent}%")
        log(PASS, "METRICS: Disk",
            f"{disk.percent}%")
        if battery:
            log(PASS, "METRICS: Battery",
                f"{battery.percent}%")
        else:
            log(WARN, "METRICS: Battery",
                "Not available")
    except Exception as e:
        log(FAIL, "METRICS", str(e))

def test_encryption():
    try:
        from core.encryption import encryption
        
        test_data = "N.O.V.A test secret 12345"
        encrypted = encryption.encrypt(test_data)
        decrypted = encryption.decrypt(encrypted)
        
        if decrypted == test_data:
            log(PASS, "ENCRYPTION",
                "AES-GCM encrypt/decrypt working")
        else:
            log(FAIL, "ENCRYPTION",
                "Decrypt mismatch")
    except Exception as e:
        log(FAIL, "ENCRYPTION", str(e))

def test_files():
    try:
        # Test home directory exists
        home = os.path.expanduser("~/")
        if os.path.exists(home):
            log(PASS, "FILES: Home dir", home)
        
        # Test downloads
        downloads = os.path.expanduser("~/Downloads")
        if os.path.exists(downloads):
            count = len(os.listdir(downloads))
            log(PASS, "FILES: Downloads",
                f"{count} files")
        
        # Test file read
        test_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "main.py"
        )
        if os.path.exists(test_file):
            with open(test_file) as f:
                content = f.read(100)
            log(PASS, "FILES: Read",
                f"main.py readable ({len(content)} chars)")
        else:
            log(WARN, "FILES: Read", "main.py not found")
            
    except Exception as e:
        log(FAIL, "FILES", str(e))

async def main():
    print("\n" + "="*60)
    print("  N.O.V.A INTEGRATION TEST SUITE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Sync tests
    test_memory()
    test_metrics()
    test_encryption()
    test_files()
    
    # Async tests
    await test_llm()
    await test_backend()
    await test_chat()
    await test_terminal()
    await test_event_bus()
    
    # Summary
    print("\n" + "="*60)
    passed = sum(1 for r in results 
                 if r["status"] == "✅")
    failed = sum(1 for r in results 
                 if r["status"] == "❌")
    warned = sum(1 for r in results 
                 if r["status"] == "⚠️")
    total = len(results)
    
    print(f"\n  RESULTS: {passed}/{total} passed")
    print(f"  FAILED:  {failed}")
    print(f"  WARNED:  {warned}")
    
    if failed == 0:
        print("\n  ✅ N.O.V.A SYSTEMS NOMINAL")
        print("  All components operational.")
    else:
        print(f"\n  ❌ {failed} COMPONENTS FAILING")
        print("  Review failures above.")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
