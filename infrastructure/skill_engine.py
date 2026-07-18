import os, json, glob
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class SkillStep:
    action: str
    params: dict
    description: str = ""

@dataclass
class Skill:
    id: str
    name: str
    description: str
    author: str = "user"
    triggers: List[str] = field(default_factory=list)
    slash_command: str = ""
    steps: List[SkillStep] = field(default_factory=list)
    enabled: bool = True
    run_count: int = 0

class SkillEngine:
    SKILLS_DIR = os.path.expanduser("~/.nova/skills")

    def __init__(self):
        os.makedirs(self.SKILLS_DIR, exist_ok=True)
        self._skills: Dict[str, Skill] = {}
        self._load_skills()
        print(f"[Skills] Loaded {len(self._skills)} "
              f"skills")

    def _load_skills(self):
        self._skills = {}
        for path in glob.glob(
            os.path.join(self.SKILLS_DIR, "*.json")
        ):
            try:
                with open(path) as f:
                    data = json.load(f)
                steps = [
                    SkillStep(**s)
                    for s in data.get("steps", [])
                ]
                skill = Skill(
                    id=data["id"],
                    name=data["name"],
                    description=data.get(
                        "description", ""
                    ),
                    triggers=data.get("triggers", []),
                    slash_command=data.get(
                        "slash_command", ""
                    ),
                    steps=steps,
                    enabled=data.get("enabled", True)
                )
                self._skills[skill.id] = skill
            except Exception as e:
                print(f"[Skills] Load error: {e}")

    def find_skill(self, 
                    message: str) -> Optional[Skill]:
        msg = message.lower().strip()
        # Slash command match
        if msg.startswith("/"):
            for skill in self._skills.values():
                if skill.slash_command and \
                   msg.startswith(
                       skill.slash_command.lower()
                   ):
                    return skill
        # Trigger match
        for skill in self._skills.values():
            if not skill.enabled:
                continue
            for trigger in skill.triggers:
                if trigger.lower() in msg:
                    return skill
        return None

    def list_skills(self) -> List[Skill]:
        return list(self._skills.values())

    async def execute_skill(self, skill: Skill,
                             context: str = "") -> str:
        skill.run_count += 1
        results = []
        step_context = context

        print(f"[Skills] Running: {skill.name} "
              f"({len(skill.steps)} steps)")

        for idx, step in enumerate(skill.steps):
            try:
                print(f"[Skills] Step {idx+1}: "
                      f"{step.description}")
                result = await self._run_step(
                    step, step_context
                )
                if result and str(result).strip():
                    step_context = str(result)
                    results.append(
                        f"✓ {step.description}:\n"
                        f"{str(result).strip()}"
                    )
                else:
                    results.append(
                        f"✓ {step.description}"
                    )
            except Exception as e:
                results.append(
                    f"✗ {step.description}: {e}"
                )

        header = f"**{skill.name}**\n" + "─" * 40
        body = "\n\n".join(results)
        return header + "\n" + body

    async def _run_step(self, step: SkillStep,
                         context: str) -> str:
        import subprocess

        if step.action == "shell":
            import shlex
            cmd = step.params.get("command", "")
            result = subprocess.run(
                shlex.split(cmd), shell=False,
                capture_output=True, text=True,
                timeout=30
            )
            out = result.stdout or result.stderr
            return out.strip()[:500] or "(no output)"

        elif step.action == "llm":
            from llm import _chat
            prompt = step.params.get("prompt", "")
            if context and context != prompt:
                prompt = (f"{prompt}\n\n"
                         f"Context:\n{context}")
            return _chat(
                system="You are a helpful assistant.",
                user=prompt
            )

        elif step.action == "system":
            cmd = step.params.get("command", "")
            from core.capabilities import capabilities
            if cmd == "status":
                import psutil
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                return (f"CPU: {cpu}% | "
                        f"RAM: {mem}% | "
                        f"Disk: {disk}%")
            elif cmd == "toggle_dnd":
                enable = step.params.get("enable", True)
                return capabilities.toggle_dnd(enable)
            elif cmd == "spotify_play":
                return capabilities.spotify_command("play")
            return f"System: {cmd} done"

        elif step.action == "file":
            action = step.params.get("action", "")
            path = step.params.get(
                "path", "~/Downloads"
            )
            if action == "organize_folder":
                from core.file_manager import (
                    file_manager
                )
                return file_manager.organize_folder(
                    path
                )
            elif action == "read":
                import os
                expanded = os.path.expanduser(path)
                if os.path.exists(expanded):
                    with open(expanded) as f:
                        return f.read(2000)
                return f"File not found: {path}"
            return f"File action: {action}"

        elif step.action == "web":
            from core.capabilities import capabilities
            query = context or step.params.get(
                "query", ""
            )
            return await capabilities.web_search(query)

        elif step.action == "document":
            from core.document_engine import doc_engine
            doc_type = step.params.get("type", "docx")
            return await \
                doc_engine.generate_document_with_llm(
                    context, doc_type
                )

        elif step.action == "tool":
            tool_name = step.params.get("tool", "")
            action = step.params.get("action", "")
            kwargs = step.params.get("params", {})
            try:
                import importlib
                module = importlib.import_module(f"tools.{tool_name}")
                class_name = "".join(word.capitalize() for word in tool_name.split("_"))
                tool_class = getattr(module, class_name)
                tool_instance = tool_class()
                if hasattr(tool_instance, "execute"):
                    res = tool_instance.execute(action, kwargs)
                    return str(res)
                else:
                    return f"Tool {tool_name} does not have an execute method."
            except Exception as e:
                return f"Tool execution failed: {e}"

        return f"Unknown action: {step.action}"

    def create_skill(self, name: str,
                      description: str,
                      trigger: str,
                      steps: list) -> str:
        import uuid
        skill_id = f"custom_{uuid.uuid4().hex[:6]}"
        skill_data = {
            "id": skill_id,
            "name": name,
            "description": description,
            "triggers": [trigger.lower()],
            "slash_command":
                f"/{trigger.replace(' ', '_')}",
            "steps": steps,
            "enabled": True
        }
        path = os.path.join(
            self.SKILLS_DIR, f"{skill_id}.json"
        )
        with open(path, 'w') as f:
            json.dump(skill_data, f, indent=2)
        self._load_skills()
        return f"Skill created: {name}"

skill_engine = SkillEngine()
