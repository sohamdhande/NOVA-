import os
import json
import sqlite3
import subprocess
import httpx
from dataclasses import dataclass
from datetime import datetime

# Provided interfaces
from core.intent_parser import ParsedIntent

@dataclass
class ToolResult:
    success: bool
    intent: str
    output: str
    data: dict
    block_type: str
    risk: str
    requires_approval: bool

class ToolRouter:
    async def route(self, intent: ParsedIntent, context: dict = None) -> ToolResult:
        context = context or {}
        
        if intent.risk == "HIGH":
            return ToolResult(
                success=False,
                intent=intent.intent,
                output="Authorization required. High-risk operation detected.",
                data={"command": intent.params, "risk": "HIGH"},
                block_type="approval",
                risk="HIGH",
                requires_approval=True
            )
            
        handlers = {
            "file_system": self._handle_file,
            "terminal":    self._handle_shell,
            "workspace":   self._handle_workspace,
            "system":      self._handle_system,
            "tasks":       self._handle_tasks,
            "comms":       self._handle_comms,
            "jira":        self._handle_jira,
            "memory":      self._handle_memory,
            "browser":     self._handle_browser,
            "navigation":  self._handle_navigation,
            "llm":         self._handle_conversation,
        }
        
        handler = handlers.get(intent.tool, self._handle_conversation)
        return await handler(intent)
        
    async def _handle_file(self, intent: ParsedIntent):
        path = intent.params.get("path", "")
        path = os.path.expanduser(path)
        
        if intent.intent == "file_read":
            try:
                with open(path, 'r') as f:
                    content = f.read(5000)
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output="Mission acknowledged. File read complete.",
                    data={"path": path, "content": content, "lines": content.count('\n')},
                    block_type="files",
                    risk="LOW",
                    requires_approval=False
                )
            except Exception as e:
                return self._error(intent, str(e))
                
        elif intent.intent == "file_search":
            query = intent.params.get("query", intent.params.get("path", ""))
            search_path = os.path.expanduser("~/")
            results = []
            try:
                for root, dirs, files in os.walk(search_path):
                    dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '.venv', 'venv', '__pycache__', '.Trash']]
                    for f in files:
                        if query.lower() in f.lower():
                            results.append(os.path.join(root, f))
                        if len(results) >= 20:
                            break
                    if len(results) >= 20:
                        break
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=f"Search complete. Found {len(results)} files.",
                    data={"query": query, "results": results},
                    block_type="files",
                    risk="LOW",
                    requires_approval=False
                )
            except Exception as e:
                return self._error(intent, str(e))
                
        elif intent.intent == "file_summarize":
            try:
                with open(path, 'r') as f:
                    content = f.read(8000)
                # Send to LLM for summary
                try:
                    from core.llm import llm
                    summary = await llm.generate_summary(f"Summarize this file concisely:\n{content}")
                except Exception:
                    # Fallback if core.llm isn't what we expect
                    summary = f"(LLM summary fallback) File content preview: {content[:100]}..."
                    
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=summary,
                    data={"path": path, "summary": summary},
                    block_type="text",
                    risk="LOW",
                    requires_approval=False
                )
            except Exception as e:
                return self._error(intent, str(e))
        
        return self._error(intent, "Unsupported file intent")

    async def _handle_shell(self, intent: ParsedIntent):
        command = intent.params.get("command", "")
        
        ALLOWED_PREFIXES = [
            "ls", "pwd", "echo", "cat", "grep", "find",
            "ps", "top", "df", "du", "uname", "whoami",
            "git status", "git log", "git branch",
            "brew list", "brew info",
            "pip list", "python --version",
            "node --version", "npm list"
        ]
        
        allowed = any(command.strip().startswith(p) for p in ALLOWED_PREFIXES)
        
        if not allowed:
            return ToolResult(
                success=False,
                intent=intent.intent,
                output="Command not in whitelist. Requires approval.",
                data={"command": command, "risk": "MEDIUM"},
                block_type="approval",
                risk="MEDIUM",
                requires_approval=True
            )
            
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            output = result.stdout or result.stderr
            output = output[:2000]
            return ToolResult(
                success=True,
                intent=intent.intent,
                output="Command executed.",
                data={"command": command, "output": output, "exit_code": result.returncode},
                block_type="shell",
                risk="MEDIUM",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_workspace(self, intent: ParsedIntent):
        project = intent.params.get("project", "")
        actions_taken = []
        
        try:
            subprocess.Popen(["code", "."])
            actions_taken.append("VSCode launched")
        except:
            actions_taken.append("VSCode not found in PATH")
            
        try:
            subprocess.Popen(["open", "-a", "Safari"])
            actions_taken.append("Browser opened")
        except:
            pass
            
        try:
            subprocess.Popen(["open", "-a", "Slack"])
            actions_taken.append("Slack launched")
        except:
            actions_taken.append("Slack not installed")
            
        return ToolResult(
            success=True,
            intent=intent.intent,
            output=f"Workspace ready. {project} environment active.",
            data={"project": project, "actions": actions_taken},
            block_type="mission",
            risk="MEDIUM",
            requires_approval=False
        )

    async def _handle_system(self, intent: ParsedIntent):
        try:
            import psutil
        except ImportError:
            return self._error(intent, "psutil not installed")
            
        if intent.intent == "system_cleanup":
            try:
                from core.system_optimizer import system_optimizer
                await system_optimizer.run_cleanup()
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output="Mission acknowledged. System cleanup complete.",
                    data={"action": "cleanup"},
                    block_type="mission",
                    risk="LOW",
                    requires_approval=False
                )
            except Exception as e:
                return self._error(intent, str(e))
        else:
            try:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                battery = psutil.sensors_battery()
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output="System scan complete.",
                    data={
                        "cpu": cpu,
                        "memory": mem.percent,
                        "disk": disk.percent,
                        "battery": battery.percent if battery else 100,
                        "block_type": "system"
                    },
                    block_type="system",
                    risk="LOW",
                    requires_approval=False
                )
            except Exception as e:
                return self._error(intent, str(e))

    async def _handle_tasks(self, intent: ParsedIntent):
        try:
            conn = sqlite3.connect("nova_logs.db", check_same_thread=False)
            
            if intent.intent == "task_create":
                title = intent.params.get("title", "")
                priority = intent.params.get("priority", "medium")
                import uuid
                task_id = str(uuid.uuid4())[:8]
                conn.execute(
                    "INSERT INTO goals VALUES (?,?,?,?,?)",
                    (task_id, title, "active", None, datetime.utcnow().isoformat())
                )
                conn.commit()
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=f"Task created: {title}",
                    data={"task_id": task_id, "title": title, "priority": priority},
                    block_type="mission",
                    risk="LOW",
                    requires_approval=False
                )
            else:
                rows = conn.execute(
                    "SELECT id, description, status FROM goals WHERE status='active' LIMIT 10"
                ).fetchall()
                tasks = [{"id": r[0], "title": r[1], "status": r[2]} for r in rows]
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=f"Found {len(tasks)} active tasks.",
                    data={"tasks": tasks},
                    block_type="tasks",
                    risk="LOW",
                    requires_approval=False
                )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_comms(self, intent: ParsedIntent):
        try:
            conn = sqlite3.connect("nova_logs.db", check_same_thread=False)
            rows = conn.execute(
                "SELECT payload FROM events WHERE type='email_received' ORDER BY timestamp DESC LIMIT 5"
            ).fetchall()
            emails = [json.loads(r[0]) for r in rows]
            return ToolResult(
                success=True,
                intent=intent.intent,
                output=f"Found {len(emails)} recent messages.",
                data={"emails": emails},
                block_type="text",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_jira(self, intent: ParsedIntent):
        jira_url = os.getenv("JIRA_URL", "")
        jira_email = os.getenv("JIRA_EMAIL", "")
        jira_token = os.getenv("JIRA_TOKEN", "")
        
        if not all([jira_url, jira_email, jira_token]):
            return ToolResult(
                success=False,
                intent=intent.intent,
                output="Jira credentials not configured. Add JIRA_URL, JIRA_EMAIL, JIRA_TOKEN to .env",
                data={},
                block_type="error",
                risk="LOW",
                requires_approval=False
            )
            
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{jira_url}/rest/api/3/search?jql=assignee=currentUser()+AND+status!=Done&maxResults=10",
                    auth=(jira_email, jira_token),
                    headers={"Accept": "application/json"}
                )
                data = resp.json()
                issues = [{
                    "key": i["key"],
                    "summary": i["fields"]["summary"],
                    "status": i["fields"]["status"]["name"],
                    "priority": i["fields"]["priority"]["name"]
                } for i in data.get("issues", [])]
                
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=f"Retrieved {len(issues)} Jira issues.",
                    data={"issues": issues},
                    block_type="tasks",
                    risk="LOW",
                    requires_approval=False
                )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_memory(self, intent: ParsedIntent):
        try:
            query = intent.params.get("query", intent.raw_message)
            conn = sqlite3.connect("nova_logs.db", check_same_thread=False)
            rows = conn.execute(
                "SELECT timestamp, type, payload FROM events ORDER BY timestamp DESC LIMIT 20"
            ).fetchall()
            events = [{"time": r[0], "type": r[1], "payload": r[2]} for r in rows]
            return ToolResult(
                success=True,
                intent=intent.intent,
                output=f"Memory retrieved. {len(events)} recent events.",
                data={"events": events, "query": query},
                block_type="text",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_browser(self, intent: ParsedIntent):
        try:
            url = intent.params.get("url", "")
            if not url.startswith("http"):
                url = "https://" + url
            subprocess.Popen(["open", url])
            return ToolResult(
                success=True,
                intent=intent.intent,
                output=f"Browser directed to {url}",
                data={"url": url},
                block_type="mission",
                risk="MEDIUM",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_navigation(self, intent: ParsedIntent):
        try:
            panel = intent.params.get("panel", "hq")
            return ToolResult(
                success=True,
                intent=intent.intent,
                output=f"Navigating to {panel.upper()} panel.",
                data={"navigate_to": panel},
                block_type="navigation",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_conversation(self, intent: ParsedIntent):
        JARVIS_SYSTEM = """You are N.O.V.A, an autonomous 
AI assistant running on macOS. You speak like JARVIS — 
precise, efficient, mission-focused. Keep responses 
concise and operational. Never break character."""
        
        try:
            # Try to route through the core LLM wrapper
            try:
                from core.llm import llm
                response = await llm.generate_summary(f"{JARVIS_SYSTEM}\n\nUser: {intent.raw_message}")
            except Exception:
                # Fallback directly to local Ollama if core.llm isn't available
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "llama3.2",
                            "prompt": f"{JARVIS_SYSTEM}\n\nUser: {intent.raw_message}",
                            "stream": False
                        },
                        timeout=30.0
                    )
                    response = resp.json().get("response", "")
                    
            return ToolResult(
                success=True,
                intent="conversation",
                output=response,
                data={"response": response},
                block_type="text",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    def _error(self, intent: ParsedIntent, error: str) -> ToolResult:
        return ToolResult(
            success=False,
            intent=intent.intent,
            output=f"Mission failed. {error}",
            data={"error": error},
            block_type="error",
            risk=intent.risk,
            requires_approval=False
        )

tool_router = ToolRouter()
