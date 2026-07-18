import os
import re
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
    def __init__(self):
        self._pending_cleanup = None
    async def route(self, intent: ParsedIntent, context: dict = None) -> ToolResult:
        print(f"[Router] Routing to tool: "
              f"{intent.tool} / intent: {intent.intent}")
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
            "task_planner": self._handle_task_execute,
            "system_control": self._handle_system_control,
            "file_ops":       self._handle_file_ops,
            "web":            self._handle_web,
            "vision_action":  self._handle_vision_action,
            "messaging":      self._handle_messaging,
            "documents":      self._handle_documents,
            "file_manager":   self._handle_file_manager,
            "scheduler":      self._handle_scheduler,
            "google":         self._handle_google,
            "skills":         self._handle_skills,
            "data_analysis":  self._handle_data_analysis,
            "security":       self._handle_security,
            "gmail":          self._handle_gmail,
            "weather":        self._handle_weather,
            "reminder":       self._handle_reminder,
            "personality":    self._handle_personality,
            "briefing":       self._handle_briefing,
            "stats":          self._handle_stats,
            "blocked":        self._handle_blocked_scan,
            "github":         self._handle_github,
            "screen":         self._handle_screen,
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
                
        elif intent.intent == "file_list":
            if not path:
                path = os.path.expanduser("~/")
            try:
                import os
                files = os.listdir(path)
                
                # filter out hidden
                files = [f for f in files if not f.startswith('.')]
                
                out = f"Contents of {path}:\n" + "\n".join(f"• {f}" for f in files[:20])
                if len(files) > 20:
                    out += f"\n...and {len(files)-20} more items"
                if not files:
                    out += "\n(Empty folder)"
                    
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=out,
                    data={"path": path, "files": files},
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
            import shlex
            result = subprocess.run(shlex.split(command), shell=False, capture_output=True, text=True, timeout=10)
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
        import subprocess
        project = intent.params.get("project", "")
        app = intent.params.get("app", "")
        actions = []
        
        if app:
            result = subprocess.run(
                ["open", "-a", app],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                actions.append(f"{app} launched")
            else:
                actions.append(f"{app} not found")
        else:
            # Default workspace
            for a in ["Visual Studio Code", "Slack"]:
                try:
                    subprocess.Popen(["open", "-a", a])
                    actions.append(f"{a} launched")
                except:
                    pass
        
        return ToolResult(
            success=True,
            intent=intent.intent,
            output="\n".join(actions) if actions else "Workspace ready.",
            data={"actions": actions, "project": project},
            block_type="mission",
            risk="LOW",
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
            import sqlite3, uuid, os
            from datetime import datetime
            
            db_path = os.path.join(
                os.path.dirname(__file__),
                "../nova_logs.db"
            )
            conn = sqlite3.connect(
                db_path, 
                check_same_thread=False
            )
            
            # Ensure tasks table exists
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
            
            i = intent.intent
            p = intent.params
            
            if i == "task_create":
                title = p.get("title", "")
                priority = p.get("priority", "medium")
                deadline = p.get("deadline", "")
                task_id = str(uuid.uuid4())[:8]
                conn.execute(
                    "INSERT INTO tasks "
                    "(id, title, priority, "
                    "status, deadline) "
                    "VALUES (?,?,?,?,?)",
                    (task_id, title, priority,
                     "pending", deadline)
                )
                conn.commit()

                # Generate subtasks via LLM
                subtask_count = 0
                try:
                    from llm import generate_subtasks
                    subtask_titles = generate_subtasks(
                        title, priority, deadline
                    )
                    for idx, st in enumerate(subtask_titles):
                        conn.execute(
                            "INSERT INTO subtasks "
                            "(task_id, title, status, "
                            "order_index) "
                            "VALUES (?,?,?,?)",
                            (task_id, st, "pending", idx)
                        )
                    conn.commit()
                    subtask_count = len(subtask_titles)
                except Exception as e:
                    print("[LLM] Subtask generation skipped "
                          "- model warming up, try again")

                conn.close()

                sub_msg = ""
                if subtask_count > 0:
                    sub_msg = (
                        f"\n📋 {subtask_count} subtasks "
                        f"generated automatically."
                    )

                return ToolResult(
                    success=True,
                    intent=i,
                    output=(
                        f"✓ Task created: **{title}**"
                        f"{sub_msg}"
                    ),
                    data={
                        "task_id": task_id,
                        "title": title,
                        "priority": priority,
                        "subtasks_generated": subtask_count
                    },
                    block_type="text",
                    risk="LOW",
                    requires_approval=False
                )
            
            elif i == "task_delete":
                title_query = p.get("title", "").lower()
                # Find matching task
                rows = conn.execute(
                    "SELECT id, title FROM tasks "
                    "WHERE status != 'deleted'"
                ).fetchall()
                match = None
                for r in rows:
                    if title_query in r[1].lower():
                        match = r
                        break
                if match:
                    conn.execute(
                        "UPDATE tasks SET "
                        "status='deleted' WHERE id=?",
                        (match[0],)
                    )
                    conn.commit()
                    conn.close()
                    return ToolResult(
                        success=True,
                        intent=i,
                        output=f"✓ Deleted task: **{match[1]}**",
                        data={},
                        block_type="text",
                        risk="LOW",
                        requires_approval=False
                    )
                else:
                    conn.close()
                    return ToolResult(
                        success=False,
                        intent=i,
                        output=f"No task found matching: {title_query}",
                        data={},
                        block_type="text",
                        risk="LOW",
                        requires_approval=False
                    )
            
            elif i == "task_complete":
                title_query = p.get("title", "").lower()
                rows = conn.execute(
                    "SELECT id, title FROM tasks "
                    "WHERE status != 'deleted'"
                ).fetchall()
                match = None
                for r in rows:
                    if title_query in r[1].lower():
                        match = r
                        break
                if match:
                    conn.execute(
                        "UPDATE tasks SET "
                        "status='completed' WHERE id=?",
                        (match[0],)
                    )
                    conn.commit()
                    conn.close()
                    return ToolResult(
                        success=True,
                        intent=i,
                        output=f"✓ Completed: **{match[1]}**",
                        data={},
                        block_type="text",
                        risk="LOW",
                        requires_approval=False
                    )
                else:
                    conn.close()
                    return ToolResult(
                        success=False,
                        intent=i,
                        output=f"No task found matching: {title_query}",
                        data={},
                        block_type="text",
                        risk="LOW",
                        requires_approval=False
                    )
            
            elif i == "mission_plan":
                goal = p.get("goal", "")
                
                # Use AI to break into subtasks
                subtasks = []
                try:
                    import sys
                    import os
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from llm import generate_subtasks
                    subtasks = generate_subtasks(goal)
                    if not subtasks:
                        raise ValueError("No subtasks created")
                    print(f"[LLM] ✓ Generated {len(subtasks)} subtasks for: {goal}")
                except Exception as e:
                    print(f"[Tasks] AI error: {e}")
                    subtasks = [
                        f"Research {goal}",
                        f"Plan {goal}",
                        f"Execute {goal}",
                        f"Review {goal}"
                    ]
                
                # Create main task + subtasks in DB
                try:
                    import sqlite3, uuid, os
                    db_path = os.path.join(
                        os.path.dirname(__file__),
                        "../nova_logs.db"
                    )
                    task_id = str(uuid.uuid4())[:8]
                    conn = sqlite3.connect(db_path)
                    
                    try:
                        conn.execute(
                            "ALTER TABLE tasks ADD COLUMN "
                            "repeat TEXT DEFAULT ''"
                        )
                    except:
                        pass

                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            priority TEXT DEFAULT 'medium',
                            status TEXT DEFAULT 'pending',
                            deadline TEXT,
                            repeat TEXT DEFAULT '',
                            created_at TEXT DEFAULT 
                                (datetime('now'))
                        )
                    """)
                    conn.execute(
                        "INSERT INTO tasks "
                        "(id, title, priority, status) "
                        "VALUES (?,?,?,?)",
                        (task_id, goal, "high", "pending")
                    )
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS subtasks (
                            id TEXT PRIMARY KEY,
                            task_id TEXT NOT NULL,
                            title TEXT NOT NULL,
                            status TEXT DEFAULT 'pending',
                            created_at TEXT DEFAULT 
                                (datetime('now'))
                        )
                    """)
                    for step in subtasks:
                        sub_id = str(uuid.uuid4())[:8]
                        conn.execute(
                            "INSERT INTO subtasks "
                            "(id, task_id, title) VALUES (?,?,?)",
                            (sub_id, task_id, step)
                        )
                    conn.commit()
                except Exception as e:
                    print(f"[Tasks] DB Error during mission_plan task creation: {e}")
                finally:
                    conn.close()
                
                steps_text = "\n".join(
                    f"{j+1}. {s}" 
                    for j, s in enumerate(subtasks)
                )
                out = (
                    f"**Mission Plan: {goal}**\n\n"
                    f"{steps_text}\n\n"
                    f"✓ Created {len(subtasks)} subtasks. "
                    f"Check Tasks tab."
                )
                
                return ToolResult(
                    success=True,
                    intent=i,
                    output=out,
                    data={
                        "task_id": task_id,
                        "subtasks": subtasks
                    },
                    block_type="text",
                    risk="LOW",
                    requires_approval=False
                )

            elif i == "suggest_task":
                title = p.get("title", "")
                out = f"Create task: **{title}**?"
                return ToolResult(
                    success=True,
                    intent=i,
                    output=out,
                    data={
                        "approval_action": "task_create",
                        "title": title,
                        "suggest": True
                    },
                    block_type="task_suggestion",
                    risk="LOW",
                    requires_approval=False
                )
            
            else:
                # task_list
                rows = conn.execute(
                    "SELECT id, title, priority, "
                    "status, deadline FROM tasks "
                    "WHERE status NOT IN "
                    "('deleted') "
                    "ORDER BY created_at DESC "
                    "LIMIT 10"
                ).fetchall()
                tasks = [
                    {
                        "id": r[0], "title": r[1],
                        "priority": r[2], 
                        "status": r[3],
                        "deadline": r[4]
                    } for r in rows
                ]
                conn.close()
                
                if not tasks:
                    out = "No active tasks."
                else:
                    lines = [
                        f"{'✓' if t['status']=='completed' else '●'} "
                        f"**{t['title']}** "
                        f"[{t['priority']}]"
                        + (f" — due {t['deadline']}" 
                           if t['deadline'] else "")
                        for t in tasks
                    ]
                    out = (
                        f"**Your Tasks ({len(tasks)}):**\n"
                        + "\n".join(lines)
                    )
                
                return ToolResult(
                    success=True,
                    intent=i,
                    output=out,
                    data={"tasks": tasks},
                    block_type="text",
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

    async def _handle_memory(self, intent: ParsedIntent) -> ToolResult:
        from core.memory_engine import memory_engine
        
        i = intent.intent
        p = intent.params
        
        try:
            if i == "memory_save":
                key = p.get("key", "unknown")
                value = p.get("value", 
                              intent.raw_message)
                out = memory_engine.remember(
                    key, value, "user_fact"
                )
                # Confirm back to user
                out = f"Got it. I'll remember: " \
                      f"{key} = {value}"
            
            elif i == "memory_recall":
                query = p.get("query", "")
                result = memory_engine.recall(query)
                if result:
                    out = f"I remember: {result}"
                else:
                    # Try getting all memories
                    all_mem = memory_engine.get_all()
                    if all_mem:
                        relevant = [
                            m for m in all_mem
                            if query.lower() in 
                            m.key.lower() or
                            query.lower() in 
                            m.value.lower()
                        ]
                        if relevant:
                            out = "\n".join([
                                f"• {m.key}: {m.value}"
                                for m in relevant[:5]
                            ])
                        else:
                            out = (f"I don't have "
                                   f"'{query}' in memory.")
                    else:
                        out = "No memories stored yet."
            
            elif i == "memory_forget":
                key = p.get("key", "")
                out = memory_engine.forget(key)
            
            else:
                out = "Unknown memory operation."
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data={},
                block_type="text",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_browser(self, intent: ParsedIntent):
        import subprocess
        url = intent.params.get("url", "")
        app = intent.params.get("app", "")
        
        try:
            if url:
                if not url.startswith("http"):
                    url = "https://" + url
                subprocess.Popen(["open", url])
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=f"Opening {url}",
                    data={"url": url, "action": "opened"},
                    block_type="mission",
                    risk="LOW",
                    requires_approval=False
                )
            elif app:
                result = subprocess.run(
                    ["open", "-a", app],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return ToolResult(
                        success=True,
                        intent=intent.intent,
                        output=f"{app} launched.",
                        data={"app": app, "action": "opened"},
                        block_type="mission",
                        risk="LOW",
                        requires_approval=False
                    )
                else:
                    return self._error(intent, f"Could not open {app}. Is it installed?")
            else:
                return self._error(intent, "No URL or application specified.")
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
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from llm import _chat
            response = _chat(system=JARVIS_SYSTEM, user=intent.raw_message)
                    
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

    async def _handle_task_execute(self, intent: ParsedIntent):
        from core.task_planner import task_planner
        import asyncio
        
        instruction = intent.raw_message
        
        if intent.intent == "parallel_execute":
            instructions = intent.params.get("instructions", [])
            out = await task_planner.plan_and_execute_parallel(instructions)
            return ToolResult(
                success=True,
                intent="parallel_execute",
                output=f"Parallel execution initiated:\n{out}",
                data={"instructions": instructions},
                block_type="mission",
                risk=intent.risk,
                requires_approval=False
            )
            
        try:
            task = await task_planner.plan(instruction)
            
            # Execute in background
            asyncio.create_task(
                task_planner.execute(task)
            )
            
            steps = "\n".join([
                f"  {i+1}. {s.description}"
                for i, s in enumerate(task.steps[:5])
            ])
            
            return ToolResult(
                success=True,
                intent="task_execute",
                output=f"Mission accepted. {len(task.steps)} steps planned:\n{steps}",
                data={
                    "task_id": task.id,
                    "title": task.title,
                    "steps": [{
                        "description": s.description,
                        "action_type": s.action_type,
                        "risk": s.risk
                    } for s in task.steps]
                },
                block_type="mission",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_system_control(self,
            intent: ParsedIntent) -> ToolResult:
        from core.capabilities import capabilities
        
        i = intent.intent
        p = intent.params
        
        try:
            from tools import system_control as sys_ctrl
            if i == "get_running_apps":
                out = sys_ctrl.get_running_apps()
            elif i == "open_app":
                out = sys_ctrl.open_app(p.get("app_name"))
            elif i == "close_app":
                out = sys_ctrl.close_app(p.get("app_name"))
            elif i == "lock_mac":
                out = sys_ctrl.lock_mac()
            elif i == "get_volume":
                out = sys_ctrl.get_volume()
            elif i == "empty_trash":
                out = sys_ctrl.empty_trash()
            elif i == "sleep_mac":
                out = sys_ctrl.sleep_mac()
            elif i == "take_screenshot":
                out = sys_ctrl.take_screenshot()
            elif i == "set_volume":
                out = sys_ctrl.set_volume(p.get("level", 50))
            elif i == "set_brightness":
                out = sys_ctrl.set_brightness(p.get("level", 50))
            elif i == "spotify_play":
                out = capabilities.spotify_command("play")
            elif i == "spotify_pause":
                out = capabilities.spotify_command("pause")
            elif i == "spotify_next":
                out = capabilities.spotify_command("next")
            elif i == "spotify_prev":
                out = capabilities.spotify_command("prev")
            elif i == "spotify_search":
                out = capabilities.spotify_search_play(
                    p.get("query", "")
                )
            elif i == "toggle_dark_mode":
                out = capabilities.toggle_dark_mode(
                    p.get("enable", True)
                )
            elif i == "toggle_wifi":
                out = capabilities.toggle_wifi(
                    p.get("enable", True)
                )
            elif i == "toggle_bluetooth":
                out = capabilities.toggle_bluetooth(
                    p.get("enable", True)
                )
            elif i == "toggle_dnd":
                out = capabilities.toggle_dnd(
                    p.get("enable", True)
                )
            elif i == "set_reminder":
                out = capabilities.set_reminder(
                    p.get("label", "Reminder"),
                    p.get("time", "")
                )
            elif i == "volume_up":
                script = '''
                set curVol to output volume of \
                    (get volume settings)
                set volume output volume (curVol + 10)
                '''
                import subprocess
                subprocess.run(
                    ['osascript', '-e', script]
                )
                out = "Volume increased"
            elif i == "volume_down":
                script = '''
                set curVol to output volume of \
                    (get volume settings)
                set volume output volume (curVol - 10)
                '''
                import subprocess
                subprocess.run(
                    ['osascript', '-e', script]
                )
                out = "Volume decreased"
            else:
                out = f"Unknown system command: {i}"
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data={"action": i, "params": p},
                block_type="mission",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_file_ops(self,
            intent: ParsedIntent) -> ToolResult:
        from core.capabilities import capabilities
        
        i = intent.intent
        p = intent.params
        
        try:
            if i == "ai_cleanup_analyze":
                folder = p.get("folder", "~/Desktop")
                
                from core.file_manager import file_manager
                
                # Store report in memory for approval
                report = await file_manager.ai_cleanup_analysis(
                    folder
                )
                
                # Store pending report
                import json, os
                cache_path = os.path.expanduser(
                    "~/.nova/pending_cleanup.json"
                )
                with open(cache_path, 'w') as f:
                    # Remove non-serializable data
                    json.dump(report, f, indent=2, 
                              default=str)
                print(f"[Cleanup] Report saved: "
                      f"{len(report.get('junk',[]))} junk, "
                      f"{len(report.get('to_archive',[]))} archive, "
                      f"{len(report.get('to_organize',[]))} organize")
                
                if "error" in report:
                    out = f"Error: {report['error']}"
                else:
                    out = (
                        f"**AI Cleanup Analysis: "
                        f"{report['folder']}**\n"
                        f"{'─' * 40}\n\n"
                        f"📊 **Scanned:** "
                        f"{report['total_files']} files "
                        f"({report['total_size_mb']} MB)\n\n"
                        f"🗑 **Junk to delete:** "
                        f"{len(report['junk'])} files "
                        f"({report['junk_size_mb']} MB)\n"
                        f"♻️ **Duplicates:** "
                        f"{len(report['duplicates'])} files\n"
                        f"📦 **Archive** "
                        f"(30+ days old): "
                        f"{len(report['to_archive'])} files "
                        f"({report['archive_size_mb']} MB)\n"
                        f"📁 **Organize:** "
                        f"{len(report['to_organize'])} files\n\n"
                        f"**AI Assessment:**\n"
                        f"{report['ai_summary']}\n\n"
                        f"─────────────────────────────\n"
                        f"Type **'yes execute cleanup'** "
                        f"to proceed or ignore to cancel."
                    )
                
                return ToolResult(
                    success=True,
                    intent=i,
                    output=out,
                    data={
                        "approval_action": "ai_cleanup_execute",
                        "pending_report": True,
                        "folder": report.get("folder", ""),
                        "stats": {
                            "junk": len(report.get("junk", [])),
                            "duplicates": len(report.get("duplicates", [])),
                            "archive": len(report.get("to_archive", [])),
                            "organize": len(report.get("to_organize", [])),
                            "freed_mb": report.get("junk_size_mb", 0)
                        }
                    },
                    block_type="cleanup_approval",
                    risk="MEDIUM",
                    requires_approval=True
                )

            elif i == "ai_cleanup_execute":
                import json, os
                cache_path = os.path.expanduser(
                    "~/.nova/pending_cleanup.json"
                )
                report = None
                if os.path.exists(cache_path):
                    try:
                        with open(cache_path) as f:
                            report = json.load(f)
                        print(f"[Cleanup] Loaded report: "
                              f"{report.get('folder')}")
                    except Exception as e:
                        print(f"[Cleanup] Load error: {e}")
                if not report:
                    out = ("No pending cleanup report. "
                           "Run 'clean my desktop' first.")
                else:
                    from core.file_manager import file_manager
                    out = await file_manager.ai_cleanup_execute(
                        report
                    )
                    # After ai_cleanup_execute completes
                    try:
                        os.remove(cache_path)
                    except:
                        pass
                
                return ToolResult(
                    success=True,
                    intent=i,
                    output=out,
                    data={},
                    block_type="text",
                    risk="MEDIUM",
                    requires_approval=False
                )

            elif i == "file_create":
                out = capabilities.create_file(
                    p.get("path", "~/Desktop/nova.txt"),
                    p.get("content", "")
                )
            elif i == "folder_create":
                out = capabilities.create_folder(
                    p.get("path", "~/Desktop/NewFolder")
                )
            else:
                out = f"Unknown file op: {i}"
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data=p,
                block_type="mission",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_web(self,
            intent: ParsedIntent) -> ToolResult:
        from core.capabilities import capabilities
        
        i = intent.intent
        p = intent.params
        
        try:
            if i in ["get_news", "news_fetch"]:
                category = p.get("category") or p.get("topic") or "general"
                out = await capabilities.get_news(category)
            elif i == "intel_briefing":
                out = await capabilities.intel_briefing(
                    p.get("query", "global threats")
                )
            elif i == "web_search":
                out = await capabilities.web_search(
                    p.get("query", "")
                )
            elif i == "read_webpage":
                out = await capabilities.read_webpage(
                    p.get("url", "")
                )
            else:
                out = f"Unknown web action: {i}"
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data={"result": out},
                block_type="text",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_vision_action(self,
            intent: ParsedIntent) -> ToolResult:
        from core.capabilities import capabilities
        
        p = intent.params
        try:
            out = capabilities.take_screenshot(
                path=p.get("path"),
                annotate=p.get("annotate", False)
            )
            return ToolResult(
                success=True,
                intent=intent.intent,
                output=out,
                data={"path": p.get("path")},
                block_type="mission",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_messaging(self,
            intent: ParsedIntent) -> ToolResult:
        from core.capabilities import capabilities
        
        i = intent.intent
        p = intent.params
        
        try:
            if i == "send_whatsapp":
                out = capabilities.send_whatsapp(
                    p.get("contact", ""),
                    p.get("message", "")
                )
            elif i == "send_email":
                out = capabilities.send_email(
                    p.get("to", ""),
                    p.get("subject", 
                          "Message from N.O.V.A"),
                    p.get("body", "")
                )
            else:
                out = f"Unknown messaging action: {i}"
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data=p,
                block_type="mission",
                risk="MEDIUM",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_documents(self,
            intent: ParsedIntent) -> ToolResult:
        i = intent.intent
        p = intent.params
        instruction = p.get("instruction",
                            intent.raw_message)

        try:
            # Extract topic from instruction
            topic = instruction
            for prefix in [
                "make a pdf on ", "create a pdf about ",
                "write a pdf on ", "make pdf on ",
                "create pdf about ", "generate pdf about ",
                "pdf about ", "pdf on ", "pdf of ",
                "make a presentation on ",
                "create a presentation about ",
                "create ppt about ", "make ppt on ",
                "make slides on ", "slides about ",
                "make a word doc on ",
                "create a document about ",
                "write a report on ",
                "create document about ",
                "make document on ", "write document on ",
                "make a word document on ",
                "create a word document about ",
            ]:
                if instruction.lower().startswith(prefix):
                    topic = instruction[len(prefix):].strip()
                    break

            # Generate content via LLM
            content = ""
            try:
                import sys, os
                sys.path.append(os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                ))
                from llm import _chat
                content = _chat(
                    system=(
                        "You are a professional content writer. "
                        "Write comprehensive, well-structured content "
                        "about the given topic. Use ## headings for "
                        "sections, - for bullet points. "
                        "Write at least 800 words covering key aspects."
                    ),
                    user=f"Write detailed content about: {topic}",
                    temperature=0.4,
                )
            except Exception as e:
                print(f"[Documents] LLM content generation "
                      f"failed: {e}")
                content = (
                    f"## Overview\n{topic} is a broad and "
                    f"important subject.\n\n"
                    f"## Key Points\n- Point 1\n- Point 2\n"
                    f"- Point 3\n\n## Conclusion\n"
                    f"This document covers {topic}."
                )

            # Route to correct tool
            if i == "create_pdf":
                from tools.pdf_tool import create_pdf
                filepath = create_pdf(topic, content)
                doc_type = "PDF"

            elif i == "create_pptx":
                from tools.pptx_tool import create_presentation
                filepath = create_presentation(
                    topic, content
                )
                doc_type = "Presentation"

            elif i == "create_docx":
                from tools.docx_tool import create_document
                filepath = create_document(topic, content)
                doc_type = "Document"

            else:
                # Default to PDF
                from tools.pdf_tool import create_pdf
                filepath = create_pdf(topic, content)
                doc_type = "PDF"

            import os
            filename = os.path.basename(filepath)
            folder = os.path.dirname(filepath)

            return ToolResult(
                success=True,
                intent=i,
                output=(
                    f"✅ **{doc_type} Created Successfully**\n\n"
                    f"📄 **File:** {filename}\n"
                    f"📂 **Location:** `{folder}/`\n"
                    f"📝 **Topic:** {topic}"
                ),
                data={
                    "type": doc_type.lower(),
                    "filepath": filepath,
                    "topic": topic,
                },
                block_type="text",
                risk="LOW",
                requires_approval=False,
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_file_manager(self,
            intent: ParsedIntent) -> ToolResult:
        from core.file_manager import file_manager
        
        i = intent.intent
        p = intent.params
        
        try:
            if i == "organize_folder":
                out = file_manager.organize_folder(
                    p.get("path", "~/Downloads")
                )
            elif i == "find_duplicates":
                dups = file_manager.find_duplicates(
                    p.get("path", "~/Downloads")
                )
                out = (
                    f"Found {len(dups)} duplicates.\n" +
                    "\n".join([
                        f"• {d['duplicate']}"
                        for d in dups[:5]
                    ])
                ) if dups else "No duplicates found."
            elif i == "pdf_compress":
                out = file_manager.compress_pdf(
                    p.get("path", "")
                )
            elif i == "pdf_merge":
                out = "Specify PDF paths to merge."
            else:
                out = f"Unknown file op: {i}"
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data=p,
                block_type="mission",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_scheduler(self,
            intent: ParsedIntent) -> ToolResult:
        from core.scheduler import scheduler
        
        i = intent.intent
        p = intent.params
        
        try:
            if i == "schedule_task":
                msg = p.get("instruction", "")
                
                # Parse schedule from instruction
                if "daily" in msg or "every day" in msg:
                    stype = "daily"
                elif "weekly" in msg or \
                     "every week" in msg:
                    stype = "weekly"
                elif "hourly" in msg or \
                     "every hour" in msg:
                    stype = "hourly"
                else:
                    stype = "daily"
                
                time_match = re.search(
                    r'(\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm))',
                    msg, re.IGNORECASE
                )
                stime = time_match.group(0) \
                        if time_match else "09:00"
                
                # Extract the actual task
                task_match = re.search(
                    r'(?:schedule|automate|run)\s+'
                    r'(?:task\s+)?["\']?(.+?)["\']?'
                    r'\s+(?:daily|weekly|hourly|every)',
                    msg, re.IGNORECASE
                )
                task_instruction = \
                    task_match.group(1) if task_match \
                    else msg
                
                task_id = scheduler.add_task(
                    name=task_instruction[:50],
                    instruction=task_instruction,
                    schedule_type=stype,
                    schedule_time=stime
                )
                
                out = (f"Scheduled task created.\n"
                       f"ID: {task_id}\n"
                       f"Runs: {stype} at {stime}\n"
                       f"Task: {task_instruction[:80]}")
            
            elif i == "list_scheduled":
                tasks = scheduler.get_tasks()
                if not tasks:
                    out = "No scheduled tasks."
                else:
                    out = "Scheduled tasks:\n" + \
                        "\n".join([
                            f"• {t.name} — "
                            f"{t.schedule_type} "
                            f"at {t.schedule_time} "
                            f"(runs: {t.run_count})"
                            for t in tasks
                        ])
            else:
                out = f"Unknown scheduler op: {i}"
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data=p,
                block_type="mission",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_google(self,
            intent: ParsedIntent) -> ToolResult:
        from core.google_integration import google
        
        i = intent.intent
        p = intent.params
        
        if not google._creds:
            if not google.authenticate():
                return ToolResult(
                    success=False,
                    intent=i,
                    output=(
                        "Google not connected. "
                        "Add credentials to "
                        "~/.nova/google_credentials"
                        ".json first."
                    ),
                    data={},
                    block_type="error",
                    risk="LOW",
                    requires_approval=False
                )
        
        try:
            if i == "gmail_check":
                emails = google.get_emails(5)
                if not emails:
                    out = "No unread emails."
                else:
                    out = f"{len(emails)} unread:\n" + \
                        "\n".join([
                            f"• {e['from'][:30]} — "
                            f"{e['subject'][:50]}"
                            for e in emails
                        ])
            elif i == "calendar_create":
                out = (
                    "Calendar event creation requires "
                    "more details. Specify: title, "
                    "date, and time."
                )
            else:
                out = f"Unknown Google op: {i}"
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data={},
                block_type="mission",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_gmail(self, intent: ParsedIntent) -> ToolResult:
        from tools.gmail_tool import GmailTool
        gmail = GmailTool()
        i = intent.intent
        p = intent.params
        out = ""
        
        try:
            if i == "summarize_inbox":
                out = gmail.summarize_inbox()
            elif i == "read_emails":
                res = gmail.read_emails(sender=p.get("sender"))
                if res.get("status") == "success":
                    emails = res.get("data", [])
                    if not emails:
                        out = "No unread emails found."
                    else:
                        out = "Unread Emails:\n" + "\n".join([f"From: {e['from']} | Subj: {e['subject']}" for e in emails])
                else:
                    out = res.get("message", "Error reading emails.")
            elif i == "send_email":
                res = gmail.send_email(
                    to=p.get("to", ""),
                    subject=p.get("subject", "Automated Message"),
                    body=p.get("body", "Sent from NOVA.")
                )
                if res.get("status") == "sent":
                    out = f"Email sent successfully to {p.get('to')}."
                else:
                    out = f"Failed to send email: {res.get('error')}"
            else:
                out = f"Unknown gmail action: {i}"
                
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data={"action": i},
                block_type="text",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, f"Gmail tool error: {e}")

    async def _handle_skills(self,
            intent: ParsedIntent) -> ToolResult:
        from core.skill_engine import skill_engine
        
        i = intent.intent
        p = intent.params
        
        try:
            if i == "list_skills":
                skills = skill_engine.list_skills()
                if not skills:
                    out = "No skills installed."
                else:
                    lines = [
                        f"• {s.name} — "
                        f"{s.slash_command}\n"
                        f"  {s.description}"
                        for s in skills
                    ]
                    out = (
                        f"{len(skills)} skills "
                        f"installed:\n\n" +
                        "\n\n".join(lines)
                    )
                return ToolResult(
                    success=True,
                    intent=i,
                    output=out,
                    data={},
                    block_type="text",
                    risk="LOW",
                    requires_approval=False
                )
            
            # Find the skill — try ALL methods
            skill = None
            raw = intent.raw_message.strip()
            
            # Method 1: by slash command
            raw_lower = raw.lower()
            for s in skill_engine._skills.values():
                if s.slash_command and \
                   raw_lower.startswith(
                       s.slash_command.lower()
                   ):
                    skill = s
                    break
            
            # Method 2: by skill_id in params
            if not skill:
                skill_id = p.get("skill_id", "")
                if skill_id in skill_engine._skills:
                    skill = skill_engine._skills[
                        skill_id
                    ]
            
            # Method 3: by trigger keywords
            if not skill:
                skill = skill_engine.find_skill(raw)
            
            # Method 4: by context param
            if not skill:
                context_msg = p.get("context", "")
                if context_msg:
                    skill = skill_engine.find_skill(
                        context_msg
                    )
            
            if not skill:
                # Show available skills as help
                available = "\n".join([
                    f"  {s.slash_command} — {s.name}"
                    for s in skill_engine.list_skills()
                    if s.slash_command
                ])
                return ToolResult(
                    success=False,
                    intent=i,
                    output=(
                        f"Skill not found for: {raw}\n"
                        f"Available commands:\n"
                        f"{available}"
                    ),
                    data={},
                    block_type="text",
                    risk="LOW",
                    requires_approval=False
                )
            
            # Execute the skill
            context = p.get("context", raw)
            result = await skill_engine.execute_skill(
                skill, context
            )
            
            print(f"[Skills] Output length: {len(result)}")
            print(f"[Skills] Output preview: {result[:200]}")
            
            return ToolResult(
                success=True,
                intent=i,
                output=result,
                data={
                    "skill": skill.name,
                    "steps": len(skill.steps)
                },
                block_type="text",
                risk="LOW",
                requires_approval=False
            )
        
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_data_analysis(self, intent: ParsedIntent):
        from core.data_analyst import data_analyst
        
        try:
            op = intent.intent
            if op == "analyze_csv":
                path = intent.params.get("path", "")
                if not path:
                    return self._error(intent, "No CSV path provided")
                result_str = await data_analyst.analyze_csv(path)
                return ToolResult(
                    success=True,
                    intent=op,
                    output=result_str,
                    data={"path": path},
                    block_type="text",
                    risk="LOW",
                    requires_approval=False
                )
            elif op == "generate_chart":
                path = intent.params.get("path", "")
                chart = intent.params.get("chart_type", "bar")
                x_col = intent.params.get("x_col")
                y_col = intent.params.get("y_col")
                
                if not path:
                    return self._error(intent, "No CSV path provided")
                result_str = data_analyst.generate_chart(path, chart, x_col, y_col)
                return ToolResult(
                    success=True,
                    intent=op,
                    output=result_str,
                    data={"path": path, "chart": chart},
                    block_type="chart",
                    risk="LOW",
                    requires_approval=False
                )
            else:
                return self._error(intent, f"Unknown data operation: {op}")
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_security(self, intent: ParsedIntent) -> ToolResult:
        from core.security_officer import security_officer
        
        i = intent.intent
        p = intent.params
        
        try:
            if i == "security_full_scan":
                out = security_officer.full_scan()
            
            elif i == "security_scan_downloads":
                out = security_officer.scan_downloads()
            
            elif i == "security_processes":
                procs = security_officer.get_process_list(10)
                lines = [
                    f"• {proc.get('name','?')} "
                    f"(PID {proc.get('pid','?')}) "
                    f"CPU: {proc.get('cpu_percent',0):.1f}%"
                    for proc in procs
                ]
                out = "Top Processes:\n" + "\n".join(lines)
            
            elif i == "security_network":
                network = security_officer.scan_network()
                lines = [
                    f"• {c['process']} → {c['remote']}:{c['port']}"
                    for c in network['connections'][:8]
                ]
                suspicious = network['suspicious']
                header = f"Active Connections: {network['total_connections']}"
                if suspicious:
                    header += f"\n⚠ {len(suspicious)} suspicious!"
                out = header + "\n" + "\n".join(lines)
            
            elif i == "security_scan_file":
                path = p.get("path", "")
                if not path:
                    out = "Specify file path to scan."
                else:
                    result = security_officer.scan_file(path)
                    if result.get("safe"):
                        out = (f"File safe: {path}\n"
                               f"No threats detected. ✓")
                    else:
                        warnings = result.get("warnings", [])
                        out = (
                            f"⚠ Suspicious file: {path}\n"
                            f"Severity: {result.get('severity')}"
                            f"\nWarnings:\n" +
                            "\n".join(f"• {w}" for w in warnings)
                        )
            
            elif i == "security_quarantine":
                path = p.get("path", "")
                out = security_officer.quarantine_file(path)
            
            elif i == "security_secure_mode":
                enable = p.get("enable", True)
                if enable:
                    out = security_officer.enable_secure_mode()
                else:
                    out = security_officer.disable_secure_mode()
            
            elif i == "security_vulnerabilities":
                out = security_officer.scan_vulnerabilities()
            
            elif i == "security_kill_process":
                pid = p.get("pid", 0)
                if not pid:
                    out = ("Specify PID to kill. "
                           "Use 'show processes' to find it.")
                else:
                    out = security_officer.kill_process(pid)
            
            elif i == "security_privacy":
                privacy = security_officer.check_privacy()
                perms = privacy.get("permissions", {})
                if perms:
                    lines = [
                        f"• {service}: {', '.join(apps[:3])}"
                        for service, apps in perms.items()
                        if apps
                    ]
                    out = "App Permissions:\n" + "\n".join(lines)
                else:
                    out = "Privacy check complete. No unusual access detected."
            
            elif i == "security_status":
                threat = security_officer.get_threat_level()
                events = security_officer.get_recent_events(5)
                
                ICONS = {
                    "CLEAR": "✅",
                    "LOW": "🟡",
                    "MEDIUM": "🟠",
                    "HIGH": "🔴",
                    "CRITICAL": "🚨"
                }
                icon = ICONS.get(threat.level, "⚠")
                
                out = (
                    f"{icon} Threat Level: {threat.level} "
                    f"({threat.score}/100)\n"
                )
                if threat.reasons:
                    out += "Reasons:\n" + "\n".join(f"• {r}" for r in threat.reasons)
                if events:
                    out += "\n\nRecent Events:\n" + \
                        "\n".join(f"[{e['severity']}] {e['title']}" for e in events[:5])
                if not threat.reasons and not events:
                    out += "All systems nominal. ✓"
            
            else:
                out = f"Unknown security command: {i}"
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data={"intent": i},
                block_type="mission",
                risk="LOW",
                requires_approval=False
            )
        
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_weather(self, intent: ParsedIntent) -> ToolResult:
        """Handle weather queries via tools/weather_tool."""
        try:
            from tools.weather_tool import weather_summary, get_weather

            location = intent.params.get("location", "Pune, India")

            if intent.intent == "weather_summary":
                summary = await weather_summary(location)
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=summary,
                    data={"location": location},
                    block_type="text",
                    risk="LOW",
                    requires_approval=False,
                )
            else:
                data = await get_weather(location)
                return ToolResult(
                    success=True,
                    intent=intent.intent,
                    output=(
                        f"🌤 {data['location']}: {data['temp']}°C "
                        f"({data['condition']}), "
                        f"humidity {data['humidity']}%, "
                        f"wind {data['wind']} km/h"
                    ),
                    data=data,
                    block_type="text",
                    risk="LOW",
                    requires_approval=False,
                )
        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_reminder(self, intent: ParsedIntent) -> ToolResult:
        """Handle reminder set / list via tools/reminder_tool."""
        try:
            from tools.reminder_tool import (
                set_reminder, get_all_pending,
            )

            i = intent.intent
            p = intent.params

            if i == "set_reminder":
                msg = p.get("message", "")
                natural_time = p.get("natural_time", "in 1 hour")
                result = set_reminder(msg, natural_time)

                if result["status"] == "error":
                    return ToolResult(
                        success=False,
                        intent=i,
                        output=f"Could not parse time: {natural_time}",
                        data=result,
                        block_type="text",
                        risk="LOW",
                        requires_approval=False,
                    )

                return ToolResult(
                    success=True,
                    intent=i,
                    output=(
                        f"✓ Reminder set: **{msg}**\n"
                        f"⏰ Scheduled for: {result['at']}"
                    ),
                    data=result,
                    block_type="text",
                    risk="LOW",
                    requires_approval=False,
                )

            elif i == "list_reminders":
                reminders = get_all_pending()
                if not reminders:
                    out = "No pending reminders."
                else:
                    lines = [
                        f"🔔 **{r['message']}** — {r['remind_at']}"
                        for r in reminders
                    ]
                    out = (
                        f"**Pending Reminders ({len(reminders)}):**\n"
                        + "\n".join(lines)
                    )
                return ToolResult(
                    success=True,
                    intent=i,
                    output=out,
                    data={"reminders": reminders},
                    block_type="text",
                    risk="LOW",
                    requires_approval=False,
                )

            else:
                return self._error(intent, f"Unknown reminder intent: {i}")

        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_personality(self, intent: ParsedIntent) -> ToolResult:
        """Handle personality switching queries via core/personality."""
        try:
            from core.personality import get_personality, set_personality
            
            i = intent.intent
            p = intent.params
            
            if i == "set_personality":
                mode = p.get("mode", "jarvis")
                result = set_personality(mode)
                return ToolResult(
                    success=True,
                    intent=i,
                    output=result,
                    data={"mode": mode},
                    block_type="text",
                    risk="LOW",
                    requires_approval=False,
                )
            elif i == "get_personality":
                persona = get_personality()
                return ToolResult(
                    success=True,
                    intent=i,
                    output=f"I am currently operating in {persona['name']} mode.",
                    data=persona,
                    block_type="text",
                    risk="LOW",
                    requires_approval=False,
                )
            else:
                return self._error(intent, f"Unknown personality intent: {i}")

        except Exception as e:
            return self._error(intent, str(e))

    async def _handle_briefing(self, intent: ParsedIntent) -> ToolResult:
        try:
            from llm import generate_summary
            from tools.calendar_tool import CalendarTool
            from tools.weather_tool import get_weather
            
            cal = CalendarTool()
            cal_res = cal.get_today_events()
            
            context = {
                "events": cal_res.get("data", []) if cal_res.get("status") == "success" else [],
                "tasks": [],
                "weather": await get_weather("Pune")
            }
            briefing_text = generate_summary(context)
            
            return ToolResult(
                success=True,
                intent=intent.intent,
                output=briefing_text,
                data=context,
                block_type="text",
                risk="LOW",
                requires_approval=False,
            )
        except Exception as e:
            return self._error(intent, f"Briefing failed: {e}")

    async def _handle_stats(self, intent: ParsedIntent) -> ToolResult:
        try:
            from core.resource_monitor import get_nova_stats, format_stats_summary
            stats = get_nova_stats()
            summary = format_stats_summary(stats)
            return ToolResult(
                success=True,
                intent=intent.intent,
                output=summary,
                data=stats,
                block_type="text",
                risk="LOW",
                requires_approval=False,
            )
        except Exception as e:
            return self._error(intent, f"Stats failed: {e}")

    async def _handle_github(self, intent: ParsedIntent) -> ToolResult:
        from tools import github_tool
        
        i = intent.intent
        p = intent.params
        out = ""
        
        try:
            if i == "get_my_prs":
                out = github_tool.get_my_prs()
            elif i == "get_openmrs_prs":
                out = github_tool.get_openmrs_prs()
            elif i == "get_my_repos":
                out = github_tool.get_my_repos()
            elif i == "get_pr_status":
                out = github_tool.get_pr_status(p.get("repo", ""), p.get("pr_number", 0))
            elif i == "get_repo_issues":
                out = github_tool.get_repo_issues(p.get("repo", ""))
            elif i == "get_repo_stats":
                out = github_tool.get_repo_stats(p.get("repo", ""))
            elif i == "get_commit_activity":
                out = github_tool.get_commit_activity(p.get("repo", ""))
            elif i == "get_pr_reviews":
                out = github_tool.get_pr_reviews(p.get("repo", ""), p.get("pr_number", 0))
            else:
                return self._error(intent, f"Unknown GitHub intent: {i}")

            if isinstance(out, dict) and out.get("type") == "pr_list":
                formatted = []
                for pr in out["prs"]:
                    formatted.append(f"📦 {pr['repo']} — #{pr['number']}\n {pr['title']}\n 🔗 {pr['url']}\n ──────────────────")
                out = "\n".join(formatted) if formatted else "No open PRs found."

            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data={},
                block_type="text",
                risk="LOW",
                requires_approval=False
            )
        except Exception as e:
            return self._error(intent, f"GitHub tool failed: {str(e)}")

    async def _handle_screen(self, intent: ParsedIntent) -> ToolResult:
        from tools.screen_tool import get_screen_context, fix_screen_error, \
            ask_about_screen, click_element, type_text, scroll, start_passive_mode, stop_passive_mode
        
        i = intent.intent
        p = intent.params
        raw_input = intent.raw_message
        
        try:
            if i == "get_screen_context":
                out = get_screen_context()
            elif i == "fix_screen_error":
                out = fix_screen_error()
            elif i == "ask_about_screen":
                question = p.get("question", raw_input)
                out = ask_about_screen(question)
            elif i == "click_element":
                element = p.get("element", "")
                out = click_element(element)
            elif i == "type_text":
                text = p.get("text", "")
                out = type_text(text)
            elif i == "scroll" and p.get("direction") == "down":
                out = scroll("down")
            elif i == "scroll" and p.get("direction") == "up":
                out = scroll("up")
            elif i == "start_passive_mode":
                out = start_passive_mode()
            elif i == "stop_passive_mode":
                out = stop_passive_mode()
            else:
                out = get_screen_context()

            return ToolResult(
                success=True,
                intent=i,
                output=str(out),
                data={},
                block_type="text",
                risk=intent.risk,
                requires_approval=False
            )
        except Exception as e:
            return ToolResult(
                success=False,
                intent=i,
                output=f"Screen tool error: {str(e)}",
                data={},
                block_type="text",
                risk=intent.risk,
                requires_approval=False
            )

    async def _handle_blocked_scan(self, intent: ParsedIntent) -> ToolResult:
        return ToolResult(
            success=False,
            intent=intent.intent,
            output="File threat scanning is not a capability I have implemented. I will not simulate scan results. Use a real antivirus tool.",
            data={},
            block_type="error",
            risk="LOW",
            requires_approval=False,
        )

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