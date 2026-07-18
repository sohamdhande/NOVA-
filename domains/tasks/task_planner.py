import json
import asyncio
import httpx
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Callable
from enum import Enum

class StepStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    WAITING   = "waiting_approval"

class TaskStatus(Enum):
    QUEUED     = "queued"
    PLANNING   = "planning"
    RUNNING    = "running"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    FAILED     = "failed"

@dataclass
class TaskStep:
    id: str
    index: int
    description: str
    action_type: str    # click|type|open_app|open_url|
                        # shell|read_file|write_file|
                        # screenshot|wait|llm|applescript
    params: dict
    status: StepStatus = StepStatus.PENDING
    result: str = ""
    error: str = ""
    screenshot_before: str = ""
    screenshot_after: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requires_approval: bool = False
    risk: str = "LOW"

@dataclass
class AutoTask:
    id: str
    title: str
    original_instruction: str
    steps: List[TaskStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(
        default_factory=datetime.now
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_summary: str = ""
    progress: int = 0          # 0-100
    current_step_index: int = 0
    on_progress: Optional[Callable] = None

class TaskPlanner:
    """
    N.O.V.A's autonomous execution engine.
    Plans and executes multi-step tasks with
    vision feedback between each step.
    """
    
    
    def __init__(self):
        self._active_tasks: dict[str, AutoTask] = {}
        self._task_history: List[AutoTask] = []
        self._paused = False
    
    # ─────────────────────────────────────────
    # PLANNING:
    
    async def plan(self, 
                   instruction: str) -> AutoTask:
        """
        Take a natural language instruction and
        generate a step-by-step execution plan.
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        task = AutoTask(
            id=task_id,
            title=self._extract_title(instruction),
            original_instruction=instruction,
            status=TaskStatus.PLANNING
        )
        
        # Ask LLM to break into steps
        steps_json = await self._generate_plan(
            instruction
        )
        
        # Parse steps
        for i, step_data in enumerate(steps_json):
            step = TaskStep(
                id=f"{task_id}_s{i}",
                index=i,
                description=step_data.get(
                    "description", f"Step {i+1}"
                ),
                action_type=step_data.get(
                    "action_type", "llm"
                ),
                params=step_data.get("params", {}),
                requires_approval=step_data.get(
                    "requires_approval", False
                ),
                risk=step_data.get("risk", "LOW")
            )
            task.steps.append(step)
        
        task.status = TaskStatus.QUEUED
        self._active_tasks[task_id] = task
        return task
    
    async def _generate_plan(self, 
                              instruction: str) -> list:
        """
        Use LLM to generate execution steps as JSON.
        """
        SYSTEM = """You are N.O.V.A's task planner.
Break the user's instruction into concrete executable 
steps. Return ONLY a JSON array of steps.

Each step must have:
{
  "description": "what this step does",
  "action_type": one of:
    "open_app"    - open a macOS app
    "open_url"    - open URL in browser  
    "click"       - click screen element
    "type"        - type text
    "shell"       - run terminal command
    "read_file"   - read a file
    "write_file"  - write/create a file
    "screenshot"  - take screenshot
    "wait"        - wait N seconds
    "applescript" - run AppleScript
    "llm"         - ask LLM a question
  "params": {
    // for open_app: {"app": "app name"}
    // for open_url: {"url": "https://..."}
    // for click: {"target": "button/element text"}
    // for type: {"text": "text to type", 
    //            "clear_first": true}
    // for shell: {"command": "shell command"}
    // for read_file: {"path": "~/path/to/file"}
    // for write_file: {"path": "~/path", 
    //                  "content": "..."}
    // for wait: {"seconds": 2}
    // for applescript: {"script": "..."}
    // for llm: {"prompt": "question"}
  },
  "requires_approval": false,
  "risk": "LOW|MEDIUM|HIGH"
}

Risk rules:
- Deleting files = HIGH
- Writing/modifying files = MEDIUM  
- Reading/opening = LOW
- Shell commands = MEDIUM
- Browser navigation = LOW

Example for "open chrome and go to github":
[
  {"description": "Open Google Chrome",
   "action_type": "open_app",
   "params": {"app": "Google Chrome"},
   "requires_approval": false, "risk": "LOW"},
  {"description": "Wait for Chrome to load",
   "action_type": "wait", 
   "params": {"seconds": 2},
   "requires_approval": false, "risk": "LOW"},
  {"description": "Navigate to GitHub",
   "action_type": "open_url",
   "params": {"url": "https://github.com"},
   "requires_approval": false, "risk": "LOW"}
]

Return ONLY the JSON array. No explanation."""

        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from llm import _chat
            text = _chat(
                system=SYSTEM,
                user=f"Task: {instruction}",
                json_mode=True
            )
            
            # Clean JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            steps = json.loads(text.strip())
            if isinstance(steps, list):
                return steps
        except Exception as e:
            print(f"[Planner] Plan generation failed: {e}")
        
        # Fallback: single LLM step
        return [{
            "description": instruction,
            "action_type": "llm",
            "params": {"prompt": instruction},
            "requires_approval": False,
            "risk": "LOW"
        }]
    
    # ─────────────────────────────────────────
    # EXECUTION:
    
    async def execute(self, 
                      task: AutoTask,
                      on_step_complete: Optional[
                          Callable] = None) -> AutoTask:
        """
        Execute all steps of a task sequentially.
        Takes screenshot before/after each step.
        """
        from core.vision import vision
        from core.computer_control import computer
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        total = len(task.steps)
        
        for i, step in enumerate(task.steps):
            
            # Check if paused
            while self._paused:
                await asyncio.sleep(0.5)
            
            # Update progress
            task.current_step_index = i
            task.progress = int((i / total) * 100)
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now()
            
            print(f"[Planner] Step {i+1}/{total}: "
                  f"{step.description}")
            
            # Screenshot before
            try:
                img = vision.capture()
                path = vision.save_screenshot(
                    img, f"before_step{i}"
                )
                step.screenshot_before = path
            except Exception as e:
                print(f"[TaskPlanner] Screenshot before failed: {e}")
            
            # Check approval requirement
            if step.requires_approval or \
               step.risk == "HIGH":
                step.status = StepStatus.WAITING
                print(f"[Planner] ⚠ Step requires "
                      f"approval: {step.description}")
                # Publish to event bus
                await self._request_approval(step, task)
                # Wait for approval (max 5 min)
                approved = await self._wait_approval(
                    step, timeout=300
                )
                if not approved:
                    step.status = StepStatus.SKIPPED
                    step.result = "Denied by user"
                    continue
            
            # Execute step
            try:
                result = await self._execute_step(
                    step, vision, computer
                )
                step.result = result
                step.status = StepStatus.COMPLETED
            except Exception as e:
                step.error = str(e)
                step.status = StepStatus.FAILED
                print(f"[Planner] Step failed: {e}")
                
                # Try to recover
                recovered = await self._attempt_recovery(
                    step, task, str(e)
                )
                if not recovered:
                    # Skip this step, continue
                    pass
            
            step.completed_at = datetime.now()
            
            # Screenshot after
            try:
                img = vision.capture()
                path = vision.save_screenshot(
                    img, f"after_step{i}"
                )
                step.screenshot_after = path
            except Exception as e:
                print(f"[TaskPlanner] Screenshot after failed: {e}")
            
            # Callback for UI updates
            if on_step_complete:
                await on_step_complete(task, step)
            
            # Small delay between steps
            await asyncio.sleep(0.3)
        
        # Task complete
        task.progress = 100
        completed = sum(
            1 for s in task.steps 
            if s.status == StepStatus.COMPLETED
        )
        failed = sum(
            1 for s in task.steps
            if s.status == StepStatus.FAILED
        )
        
        if failed == 0:
            task.status = TaskStatus.COMPLETED
        elif completed == 0:
            task.status = TaskStatus.FAILED
        else:
            task.status = TaskStatus.COMPLETED
        
        task.completed_at = datetime.now()
        task.result_summary = (
            f"Completed {completed}/{total} steps. "
            f"{failed} failed."
        )
        
        # Move to history
        self._task_history.append(task)
        if task.id in self._active_tasks:
            del self._active_tasks[task.id]
        
        print(f"[Planner] Task complete: "
              f"{task.result_summary}")
        return task
    
    async def _execute_step(self, step: TaskStep,
                             vision, 
                             computer) -> str:
        """Execute a single step based on action_type."""
        p = step.params
        t = step.action_type
        
        if t == "open_app":
            app = p.get("app", "")
            success = computer.open_app(app)
            return f"Opened {app}" if success \
                   else f"Failed to open {app}"
        
        elif t == "open_url":
            url = p.get("url", "")
            success = computer.open_url(url)
            return f"Opened {url}" if success \
                   else f"Failed to open {url}"
        
        elif t == "click":
            target = p.get("target", "")
            if target:
                success = computer.click_button(target)
                if success:
                    return f"Clicked '{target}'"
                # Try coordinates if text not found
                x = p.get("x", 0)
                y = p.get("y", 0)
                if x and y:
                    computer.click(x, y)
                    return f"Clicked at ({x},{y})"
                return f"Could not find '{target}'"
            x = p.get("x", 0)
            y = p.get("y", 0)
            computer.click(x, y)
            return f"Clicked at ({x},{y})"
        
        elif t == "type":
            text = p.get("text", "")
            clear = p.get("clear_first", False)
            computer.type_in_field(
                text, clear_first=clear
            )
            return f"Typed: {text[:50]}"
        
        elif t == "shell":
            import subprocess, shlex
            cmd = p.get("command", "")
            result = subprocess.run(
                shlex.split(cmd), shell=False,
                capture_output=True, text=True,
                timeout=30
            )
            output = (result.stdout or 
                      result.stderr)[:500]
            return f"Command output: {output}"
        
        elif t == "read_file":
            import os
            path = os.path.expanduser(
                p.get("path", "")
            )
            with open(path, 'r') as f:
                content = f.read(5000)
            return f"File content: {content[:200]}..."
        
        elif t == "write_file":
            import os
            path = os.path.expanduser(
                p.get("path", "")
            )
            content = p.get("content", "")
            os.makedirs(
                os.path.dirname(path), 
                exist_ok=True
            )
            with open(path, 'w') as f:
                f.write(content)
            return f"Wrote {len(content)} chars to {path}"
        
        elif t == "screenshot":
            img = vision.capture()
            path = vision.save_screenshot(
                img, "task_screenshot"
            )
            return f"Screenshot saved: {path}"
        
        elif t == "wait":
            seconds = p.get("seconds", 1)
            await asyncio.sleep(seconds)
            return f"Waited {seconds}s"
        
        elif t == "applescript":
            script = p.get("script", "")
            result = computer.run_applescript(script)
            return f"AppleScript result: {result}"
        
        elif t == "llm":
            prompt = p.get("prompt", "")
            response = await self._ask_llm(prompt)
            return response
        
        else:
            return f"Unknown action type: {t}"
    
    async def _ask_llm(self, prompt: str) -> str:
        """Send prompt to local LLM."""
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from llm import _chat
            return _chat(system="", user=prompt)
        except Exception as e:
            return f"LLM error: {e}"
    
    async def _attempt_recovery(self, 
                                  step: TaskStep,
                                  task: AutoTask,
                                  error: str) -> bool:
        """Try to recover from a failed step."""
        print(f"[Planner] Attempting recovery for: "
              f"{step.description}")
        
        # Take screenshot to see current state
        from core.vision import vision
        state = vision.get_screen_state()
        
        # Ask LLM how to recover
        recovery_prompt = f"""
A task step failed. How should I recover?

Step: {step.description}
Action: {step.action_type}
Error: {error}
Current screen: {state.active_app} - {state.active_window}

Suggest a simple recovery action as JSON:
{{"action": "retry|skip|abort", "reason": "..."}}
"""
        try:
            response = await self._ask_llm(
                recovery_prompt
            )
            if "retry" in response.lower():
                # Retry once
                from core.computer_control import computer
                await self._execute_step(
                    step, vision, computer
                )
                return True
        except Exception as e:
            print(f"[TaskPlanner] Vision feedback analysis failed: {e}")
        return False
    
    async def _request_approval(self,
                                  step: TaskStep,
                                  task: AutoTask):
        """Publish approval request to event bus."""
        try:
            from core.event_bus import (
                event_bus, NovaEvent
            )
            await event_bus.publish(NovaEvent(
                source="task_planner",
                type="approval_required",
                payload={
                    "id": step.id,
                    "command": step.description,
                    "reason": f"Task: {task.title}",
                    "risk": step.risk,
                    "task_id": task.id
                },
                priority=8
            ))
        except Exception as e:
            print(f"[Planner] Approval request "
                  f"failed: {e}")
    
    async def _wait_approval(self,
                              step: TaskStep,
                              timeout: int = 300) -> bool:
        """Wait for approval decision."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            # Check if approved in DB
            import sqlite3
            try:
                conn = sqlite3.connect(
                    "nova_logs.db",
                    check_same_thread=False
                )
                row = conn.execute(
                    "SELECT payload FROM events "
                    "WHERE event_type='approval_granted' "
                    "ORDER BY timestamp DESC LIMIT 1"
                ).fetchone()
                if row:
                    import json
                    payload = json.loads(row[0])
                    if payload.get("step_id") == step.id:
                        return True
            except (OSError, KeyError, ValueError) as e:
                pass
            await asyncio.sleep(1)
        return False
    
    # ─────────────────────────────────────────
    # CONTROL METHODS:
    
    def pause(self):
        self._paused = True
        print("[Planner] Execution paused")
    
    def resume(self):
        self._paused = False
        print("[Planner] Execution resumed")
    
    def get_active_tasks(self) -> list:
        return list(self._active_tasks.values())
    
    def get_task(self, task_id: str) -> Optional[AutoTask]:
        return self._active_tasks.get(task_id)
    
    def get_history(self) -> list:
        return self._task_history[-20:]
    
    def _extract_title(self, 
                        instruction: str) -> str:
        """Extract short title from instruction."""
        words = instruction.split()[:6]
        return ' '.join(words).title()

    async def execute_parallel(
            self, tasks: List[AutoTask]) -> List[AutoTask]:
        """Run multiple tasks simultaneously."""
        print(f"[Planner] Running {len(tasks)} tasks "
              f"in parallel")
        results = await asyncio.gather(
            *[self.execute(task) for task in tasks],
            return_exceptions=True
        )
        return [
            r for r in results 
            if isinstance(r, AutoTask)
        ]
    
    async def plan_and_execute_parallel(
            self, instructions: List[str]
            ) -> str:
        """Plan and run multiple instructions at once."""
        tasks = await asyncio.gather(
            *[self.plan(i) for i in instructions]
        )
        results = await self.execute_parallel(
            list(tasks)
        )
        return "\n".join([
            f"✓ {t.title}: {t.result_summary}"
            for t in results
        ])

# Singleton
task_planner = TaskPlanner()
