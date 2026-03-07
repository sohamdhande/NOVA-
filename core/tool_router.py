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
            if i == "spotify_play":
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
            elif i == "set_volume":
                out = capabilities.set_volume(
                    p.get("level", 50)
                )
            elif i == "set_brightness":
                out = capabilities.set_brightness(
                    p.get("level", 50)
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
            if i == "file_create":
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
            if i == "web_search":
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
        from core.document_engine import doc_engine
        
        i = intent.intent
        p = intent.params
        instruction = p.get("instruction", 
                            intent.raw_message)
        
        try:
            doc_type_map = {
                "create_docx": "docx",
                "create_xlsx": "xlsx",
                "create_pptx": "pptx"
            }
            doc_type = doc_type_map.get(i, "docx")
            
            out = await \
                doc_engine.generate_document_with_llm(
                    instruction, doc_type
                )
            
            return ToolResult(
                success=True,
                intent=i,
                output=out,
                data={"type": doc_type,
                      "instruction": instruction},
                block_type="mission",
                risk="LOW",
                requires_approval=False
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
