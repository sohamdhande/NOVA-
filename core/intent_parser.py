import json
import re as re_module
import httpx
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedIntent:
    intent: str
    tool: str
    params: dict
    risk: str
    raw_message: str

class IntentParser:
    async def parse(self, message: str) -> Optional[ParsedIntent]:
        # ALWAYS try deterministic first
        # This bypasses LLM entirely for known commands
        result = self._deterministic_parse(message)
        if result:
            print(f"[Intent] Deterministic: "
                  f"{result.intent} → {result.tool}")
            return result
        
        # Only use LLM for unknown commands
        print(f"[Intent] LLM fallback for: {message}")
        return await self._llm_parse(message)

    def _deterministic_parse(self, message: str) -> Optional[ParsedIntent]:
        msg = message.lower().strip()

        
        # ─── SLASH COMMANDS (SKILLS) ──────────────────────
        if msg.startswith("/"):
            parts = message.split(" ", 1)
            cmd = parts[0]
            from core.skill_engine import skill_engine
            skill = skill_engine.find_skill(cmd)
            if skill:
                return ParsedIntent(
                    intent="execute_skill",
                    tool="skills",
                    params={"skill_id": skill.id, "args": parts[1] if len(parts) > 1 else ""},
                    risk="LOW",
                    raw_message=message
                )

        # ─── PARALLEL EXECUTION ───────────────────────────
        if " and also do " in msg or " and then " in msg:
            if " and also do " in msg:
                instructions = [p.strip() for p in message.split(" and also do ")]
            else:
                instructions = [p.strip() for p in message.split(" and then ")]
            
            if len(instructions) > 1:
                return ParsedIntent(
                    intent="parallel_execute",
                    tool="task_planner",
                    params={"instructions": instructions},
                    risk="MEDIUM",
                    raw_message=message
                )

        # ─── DATA ANALYSIS ────────────────────────────────
        if msg.startswith("analyze csv") or "analyze data" in msg:
            words = message.split()
            path = ""
            for w in words:
                if w.endswith(".csv"):
                    path = w
                    break
            return ParsedIntent(
                intent="analyze_csv",
                tool="data_analysis",
                params={"path": path},
                risk="LOW",
                raw_message=message
            )
            
        if msg.startswith("generate chart") or "create chart" in msg:
            words = message.split()
            path = ""
            for w in words:
                if w.endswith(".csv"):
                    path = w
                    break
            chart_type = "bar"
            if "pie" in msg: chart_type = "pie"
            elif "line" in msg: chart_type = "line"
            elif "scatter" in msg: chart_type = "scatter"
            
            return ParsedIntent(
                intent="generate_chart",
                tool="data_analysis",
                params={"path": path, "chart_type": chart_type, "x_col": None, "y_col": None},
                risk="LOW",
                raw_message=message
            )

        # ─── MEMORY ───────────────────────────────────────
        if any(msg.startswith(p) for p in [
            "remember ", "remember that ",
            "note that ", "save that ",
            "my name is ", "i am ",
            "i prefer ", "i like ",
            "don't forget "
        ]):
            # Extract the value
            value = message.strip()
            for t in [
                "remember that ", "remember ",
                "note that ", "save that ",
                "don't forget "
            ]:
                if msg.startswith(t):
                    value = message[len(t):].strip()
                    break
            
            # Extract key from value
            key = value[:50]
            if " is " in value:
                parts = value.split(" is ", 1)
                key = parts[0].strip()
                value = parts[1].strip()
            
            return ParsedIntent(
                intent="memory_save",
                tool="memory",
                params={"key": key, "value": value},
                risk="LOW",
                raw_message=message
            )
            
        if any(msg.startswith(p) for p in [
            "what is my ", "who am i",
            "do you remember ", "what do you know",
            "recall ", "remind me of my ",
            "what's my "
        ]):
            query = msg
            for t in [
                "what is my ", "what's my ",
                "do you remember ", "recall ",
                "remind me of my "
            ]:
                if msg.startswith(t):
                    query = message[len(t):].strip()
                    break
            return ParsedIntent(
                intent="memory_recall",
                tool="memory",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )

        # ─── BATCH FILE OPS ───────────────────────────────
        if msg.startswith("batch convert "):
            return ParsedIntent(
                intent="batch_convert_images",
                tool="file_manager",
                params={"instruction": message},
                risk="MEDIUM",
                raw_message=message
            )
            
        if msg.startswith("batch rename "):
            return ParsedIntent(
                intent="batch_rename_numbered",
                tool="file_manager",
                params={"instruction": message},
                risk="MEDIUM",
                raw_message=message
            )
            
        if "find large files" in msg:
            return ParsedIntent(
                intent="get_large_files",
                tool="file_manager",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )
        
        # ─── SECURITY COMMANDS ───────────────────────────
        if any(p in msg for p in [
            "scan system security", "security scan",
            "run security scan", "check security",
            "scan for threats", "security check",
            "full security scan"
        ]):
            return ParsedIntent(
                intent="security_full_scan",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "scan downloads", "check downloads",
            "scan download folder"
        ]):
            return ParsedIntent(
                intent="security_scan_downloads",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "show processes", "running processes",
            "list processes", "check processes",
            "what's running", "whats running",
            "show running apps"
        ]):
            return ParsedIntent(
                intent="security_processes",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "check network", "network connections",
            "show connections", "network activity",
            "what's connecting", "check connections"
        ]):
            return ParsedIntent(
                intent="security_network",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "scan file ", "check file ",
            "is this file safe", "analyze file"
        ]):
            path_match = re_module.search(r'(~/[^\s]+|/[^\s]+)', message)
            path = path_match.group(1) if path_match else ""
            return ParsedIntent(
                intent="security_scan_file",
                tool="security",
                params={"path": path},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "quarantine file", "quarantine "
        ]):
            path_match = re_module.search(r'(~/[^\s]+|/[^\s]+)', message)
            path = path_match.group(1) if path_match else ""
            return ParsedIntent(
                intent="security_quarantine",
                tool="security",
                params={"path": path},
                risk="MEDIUM",
                raw_message=message
            )

        if any(p in msg for p in [
            "enable secure mode", "secure mode on",
            "activate secure mode", "lockdown"
        ]):
            return ParsedIntent(
                intent="security_secure_mode",
                tool="security",
                params={"enable": True},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "disable secure mode", "secure mode off",
            "deactivate secure mode"
        ]):
            return ParsedIntent(
                intent="security_secure_mode",
                tool="security",
                params={"enable": False},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "check vulnerabilities", "vulnerability scan",
            "outdated packages", "check updates",
            "scan vulnerabilities"
        ]):
            return ParsedIntent(
                intent="security_vulnerabilities",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "kill process", "terminate process",
            "stop process", "kill pid"
        ]):
            pid_match = re_module.search(r'\b(\d{3,6})\b', msg)
            pid = int(pid_match.group(1)) if pid_match else 0
            return ParsedIntent(
                intent="security_kill_process",
                tool="security",
                params={"pid": pid},
                risk="HIGH",
                raw_message=message
            )

        if any(p in msg for p in [
            "check privacy", "privacy scan",
            "app permissions", "who has camera access",
            "who has microphone access"
        ]):
            return ParsedIntent(
                intent="security_privacy",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "threat level", "am i safe",
            "security status", "security report",
            "how secure", "security summary"
        ]):
            return ParsedIntent(
                intent="security_status",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        # ─── DOCUMENT GENERATION ─────────────────────────
        # Check this EARLY — before other patterns

        # Document generation — highest priority check
        msg_lower = message.lower()
        if any(p in msg_lower for p in [
            "word doc", "word document", ".docx",
            "as a doc", "as a document", "as a word",
            "in word", "docx file"
        ]):
            return ParsedIntent(
                intent="create_docx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg_lower for p in [
            "spreadsheet", ".xlsx", "excel file",
            "as a spreadsheet", "in excel"
        ]):
            return ParsedIntent(
                intent="create_xlsx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg_lower for p in [
            "presentation", "powerpoint", ".pptx",
            "slide deck", "as slides", "as a presentation"
        ]):
            return ParsedIntent(
                intent="create_pptx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        # Word doc
        if any(p in msg_lower for p in [
            "word doc", "word document", ".docx",
            "create report", "write a report", 
            "make a report", "generate report",
            "create document", "write document",
            "create a report", "write report",
            "as a doc", "as a document",
            "as a word", "in word format"
        ]):
            return ParsedIntent(
                intent="create_docx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        # Spreadsheet
        if any(p in msg for p in [
            "spreadsheet", "excel", ".xlsx",
            "create sheet", "make sheet",
            "as a spreadsheet", "in excel",
            "excel file", "xlsx file"
        ]):
            return ParsedIntent(
                intent="create_xlsx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        # Presentation
        if any(p in msg for p in [
            "presentation", "powerpoint", "slides",
            ".pptx", "slide deck", "deck",
            "create slides", "make slides",
            "as a presentation", "in powerpoint"
        ]):
            return ParsedIntent(
                intent="create_pptx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )
        
        # APP OPENING - highest priority
        APP_MAP = {
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "safari": "Safari",
            "firefox": "Firefox",
            "slack": "Slack",
            "vscode": "Visual Studio Code",
            "vs code": "Visual Studio Code",
            "code": "Visual Studio Code",
            "terminal": "Terminal",
            "finder": "Finder",
            "spotify": "Spotify",
            "notes": "Notes",
            "mail": "Mail",
            "calendar": "Calendar",
            "figma": "Figma",
            "notion": "Notion",
            "discord": "Discord",
            "whatsapp": "WhatsApp",
            "telegram": "Telegram",
            "instagram": "Instagram",
            "youtube": "YouTube", 
            "twitter": "Twitter",
            "x": "X",
            "zoom": "zoom.us",
            "teams": "Microsoft Teams",
            "word": "Microsoft Word",
            "excel": "Microsoft Excel",
            "powerpoint": "Microsoft PowerPoint",
            "outlook": "Microsoft Outlook",
            "photoshop": "Adobe Photoshop",
            "premiere": "Adobe Premiere Pro",
            "after effects": "Adobe After Effects",
            "xcode": "Xcode",
            "android studio": "Android Studio",
            "docker": "Docker Desktop",
            "postman": "Postman",
            "iterm": "iTerm",
            "iterm2": "iTerm2",
            "warp": "Warp",
            "arc": "Arc",
            "brave": "Brave Browser",
            "opera": "Opera",
            "vlc": "VLC",
            "obsidian": "Obsidian",
            "linear": "Linear",
            "bear": "Bear",
            "things": "Things 3",
            "1password": "1Password",
            "bitwarden": "Bitwarden",
            "raycast": "Raycast",
            "alfred": "Alfred",
            "cleanmymac": "CleanMyMac",
            "screenflow": "ScreenFlow",
            "loom": "Loom",
            "grammarly": "Grammarly",
            "cursor": "Cursor",
            "antigravity": "Antigravity"
        }
        
        # Multi-app + action commands
        # "open spotify and play X"
        if "spotify" in msg and any(p in msg for p in [
            "play", "listen", "put on", "start"
        ]):
            # Extract what to play
            query = ""
            for trigger in ["play ", "listen to ",
                            "put on "]:
                if trigger in msg:
                    query = message[
                        msg.index(trigger)+len(trigger):
                    ].strip()
                    # Remove trailing words like 
                    # "on spotify"
                    query = query.replace(
                        "on spotify", ""
                    ).replace(
                        "in spotify", ""
                    ).strip()
                    break
            
            if not query or query in [
                "music", "something", "a song",
                "songs", "the song"
            ]:
                # Just open and play
                return ParsedIntent(
                    intent="spotify_play",
                    tool="system_control",
                    params={},
                    risk="LOW",
                    raw_message=message
                )
            else:
                return ParsedIntent(
                    intent="spotify_search",
                    tool="system_control",
                    params={"query": query},
                    risk="LOW",
                    raw_message=message
                )

        # "play X on spotify" or "play X"
        if msg.startswith("play "):
            query = message[5:].strip()
            query = query.replace(
                "on spotify", ""
            ).strip()
            return ParsedIntent(
                intent="spotify_search",
                tool="system_control",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )
        
        # "open X" or "launch X" or "start X"
        for trigger in ["open ", "launch ", "start "]:
            if msg.startswith(trigger):
                remainder = msg[len(trigger):].strip()
                # Strip trailing "app" word
                if remainder.endswith(" app"):
                    remainder = remainder[:-4].strip()
                if remainder.endswith(" application"):
                    remainder = remainder[:-12].strip()

                # Check for URL
                if remainder.startswith("http") or \
                   "." in remainder and " " not in remainder:
                    url = remainder if \
                        remainder.startswith("http") \
                        else "https://" + remainder
                    return ParsedIntent(
                        intent="browser_open",
                        tool="browser",
                        params={"url": url},
                        risk="LOW",
                        raw_message=message
                    )
                # Check for app
                for app_key, app_name in APP_MAP.items():
                    if remainder.startswith(app_key):
                        return ParsedIntent(
                            intent="browser_open",
                            tool="browser",
                            params={"app": app_name},
                            risk="LOW",
                            raw_message=message
                        )
                
                # If no app matched, try opening as URL search
                if not any(remainder.startswith(k) 
                           for k in APP_MAP):
                    # Could be a website - try opening in browser
                    if len(remainder.split()) <= 3:
                        url = "https://" + remainder\
                              .replace(" ", "") + ".com" \
                              if "." not in remainder \
                              else "https://" + remainder
                        return ParsedIntent(
                            intent="browser_open",
                            tool="browser",
                            params={"url": url},
                            risk="LOW",
                            raw_message=message
                        )
        
        # "go to X.com" or "navigate to X"
        for trigger in ["go to ", "navigate to ", 
                        "open website ", "visit "]:
            if trigger in msg:
                idx = msg.index(trigger) + len(trigger)
                url = message[idx:].strip()
                if not url.startswith("http"):
                    url = "https://" + url
                return ParsedIntent(
                    intent="browser_open",
                    tool="browser",
                    params={"url": url},
                    risk="LOW",
                    raw_message=message
                )
        
        # MULTI-STEP: "open X and go to Y"
        if " and " in msg and \
           any(msg.startswith(t) for t in 
               ["open ", "launch "]):
            # This is a complex task - use task planner
            return ParsedIntent(
                intent="task_execute",
                tool="task_planner",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )
        
        # SKILLS
        if any(p in msg for p in [
            "show skills", "list skills",
            "available skills", "what skills",
            "my skills", "installed skills",
            "what can you do", "skill list"
        ]):
            return ParsedIntent(
                intent="list_skills",
                tool="skills",
                params={},
                risk="LOW",
                raw_message=message
            )

        # SYSTEM
        if any(p in msg for p in [
            "check system", "system status",
            "system health", "system scan",
            "how is my system", "check cpu",
            "check ram", "check memory",
            "check disk", "check battery",
            "show metrics"
        ]):
            return ParsedIntent(
                intent="system_status",
                tool="system",
                params={},
                risk="LOW",
                raw_message=message
            )
        
        # CLEANUP
        if "yes execute cleanup" not in msg and            "clean my desktop" not in msg and            "clean docs" not in msg and            any(p in msg for p in [
            "run cleanup", "clean system",
            "clean my system", "cleanup",
            "clear cache", "clean downloads",
            "organize downloads"
        ]):
            return ParsedIntent(
                intent="system_cleanup",
                tool="system",
                params={},
                risk="LOW",
                raw_message=message
            )
        
        # TASK DELETE
        if any(p in msg for p in [
            "delete task", "remove task",
            "cancel task", "drop task"
        ]):
            title = ""
            for trigger in [
                "delete task", "remove task",
                "cancel task", "drop task"
            ]:
                if trigger in msg:
                    title = message[
                        msg.index(trigger)
                        + len(trigger):
                    ].strip(" :")
                    break
            return ParsedIntent(
                intent="task_delete",
                tool="tasks",
                params={"title": title},
                risk="LOW",
                raw_message=message
            )
        
        # TASK COMPLETE
        if any(p in msg for p in [
            "complete task", "finish task",
            "mark task done", "done with task",
            "task done"
        ]):
            title = ""
            for trigger in [
                "complete task", "finish task",
                "mark task done", "done with task",
                "task done"
            ]:
                if trigger in msg:
                    title = message[
                        msg.index(trigger)
                        + len(trigger):
                    ].strip(" :")
                    break
            return ParsedIntent(
                intent="task_complete",
                tool="tasks",
                params={"title": title},
                risk="LOW",
                raw_message=message
            )

        # TASKS
        if any(p in msg for p in [
            "create task", "add task", "new task",
            "remind me to", "create a task",
            "schedule meeting", "book meeting"
        ]):
            title = message
            for trigger in ["create task:", "create task",
                            "add task:", "add task",
                            "new task:", "new task",
                            "remind me to"]:
                if trigger in msg:
                    title = message[
                        msg.index(trigger)+len(trigger):
                    ].strip(" :")
                    break
            return ParsedIntent(
                intent="task_create",
                tool="tasks",
                params={"title": title,
                        "priority": "medium"},
                risk="LOW",
                raw_message=message
            )
        
        if any(msg == p or msg.startswith(p) for p in [
            "show tasks", "list tasks", "my tasks",
            "what are my tasks", "show my tasks"
        ]):
            return ParsedIntent(
                intent="task_list",
                tool="tasks",
                params={},
                risk="LOW",
                raw_message=message
            )
        
        # FILES
        if ("~/" in msg or ".py" in msg or 
            ".txt" in msg or ".pdf" in msg) and \
           any(p in msg for p in [
               "read ", "open file", "show file", 
               "cat ", "view "
           ]):
            path = next(
                (w for w in reversed(msg.split())
                 if "/" in w or w.startswith("~")),
                ""
            )
            return ParsedIntent(
                intent="file_read",
                tool="file_system",
                params={"path": path},
                risk="LOW",
                raw_message=message
            )
        
        if any(p in msg for p in [
            "search files", "find files",
            "find file", "search for file"
        ]):
            query = msg.replace(
                "search files", ""
            ).replace("find files", "").strip()
            return ParsedIntent(
                intent="file_search",
                tool="file_system",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )
        
        # ─── FILE MANAGEMENT ─────────────────────────────
        if any(p in msg for p in [
            "organize folder", "organize my downloads",
            "organize downloads", "clean up folder",
            "sort folder", "organize files"
        ]):
            path_match = re_module.search(
                r'(~/[^\s]+|downloads|desktop|documents)',
                msg
            )
            path = "~/Downloads"
            if path_match:
                p_str = path_match.group(1)
                if p_str in [
                    "downloads", "desktop", "documents"
                ]:
                    path = f"~/{p_str.title()}"
                else:
                    path = p_str
            return ParsedIntent(
                intent="organize_folder",
                tool="file_manager",
                params={"path": path},
                risk="MEDIUM",
                raw_message=message
            )

        if any(p in msg for p in [
            "find duplicates", "find duplicate files",
            "show duplicates", "remove duplicates"
        ]):
            return ParsedIntent(
                intent="find_duplicates",
                tool="file_manager",
                params={"path": "~/Downloads"},
                risk="LOW",
                raw_message=message
            )

        # ─── PDF TOOLS ───────────────────────────────────
        if "merge pdf" in msg or "combine pdf" in msg:
            return ParsedIntent(
                intent="pdf_merge",
                tool="file_manager",
                params={},
                risk="LOW",
                raw_message=message
            )

        if "compress pdf" in msg:
            url_match = re_module.search(r'(~/[^\s]+\.pdf)', msg)
            path = url_match.group(1) if url_match else ""
            return ParsedIntent(
                intent="pdf_compress",
                tool="file_manager",
                params={"path": path},
                risk="LOW",
                raw_message=message
            )

        # ─── SCHEDULING ──────────────────────────────────
        if any(p in msg for p in [
            "schedule task", "schedule every",
            "run every day", "run daily",
            "run every week", "run weekly",
            "automate every", "schedule automation"
        ]):
            return ParsedIntent(
                intent="schedule_task",
                tool="scheduler",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "show scheduled", "list scheduled",
            "my scheduled tasks", "show automations"
        ]):
            return ParsedIntent(
                intent="list_scheduled",
                tool="scheduler",
                params={},
                risk="LOW",
                raw_message=message
            )

        # ─── GOOGLE ──────────────────────────────────────
        if any(p in msg for p in [
            "check gmail", "check email",
            "show emails", "read emails",
            "unread emails", "my emails"
        ]):
            return ParsedIntent(
                intent="gmail_check",
                tool="google",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "create calendar event", "add to calendar",
            "schedule on calendar", "add event",
            "create event"
        ]):
            return ParsedIntent(
                intent="calendar_create",
                tool="google",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        # ─── SPOTIFY CONTROL ──────────────────────────────
        SPOTIFY_COMMANDS = {
            "play spotify": ("spotify_play", {}),
            "pause spotify": ("spotify_pause", {}),
            "stop spotify": ("spotify_pause", {}),
            "next song": ("spotify_next", {}),
            "next track": ("spotify_next", {}),
            "previous song": ("spotify_prev", {}),
            "previous track": ("spotify_prev", {}),
            "skip song": ("spotify_next", {}),
            "volume up": ("volume_up", {}),
            "volume down": ("volume_down", {}),
        }
        for cmd, (intent, params) in SPOTIFY_COMMANDS.items():
            if cmd in msg:
                return ParsedIntent(
                    intent=intent,
                    tool="system_control",
                    params=params,
                    risk="LOW",
                    raw_message=message
                )

        # Play specific song
        if any(p in msg for p in [
            "play ", "put on ", "listen to "
        ]) and any(p in msg for p in [
            "song", "music", "spotify", "track",
            "album", "artist", "playlist"
        ]):
            query = msg
            for t in ["play ", "put on ", 
                      "listen to "]:
                if t in msg:
                    query = message[
                        msg.index(t)+len(t):
                    ].strip()
                    break
            return ParsedIntent(
                intent="spotify_search",
                tool="system_control",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )

        # ─── VOLUME / BRIGHTNESS ─────────────────────────
        vol_match = re_module.search(
            r'(set |turn )?(volume|vol)\s*(to\s*)?(\d+)',
            msg
        )
        if vol_match:
            level = int(vol_match.group(4))
            level = max(0, min(100, level))
            return ParsedIntent(
                intent="set_volume",
                tool="system_control",
                params={"level": level},
                risk="LOW",
                raw_message=message
            )

        bright_match = re_module.search(
            r'(set |turn )?(brightness)\s*(to\s*)?(\d+)',
            msg
        )
        if bright_match:
            level = int(bright_match.group(4))
            return ParsedIntent(
                intent="set_brightness",
                tool="system_control",
                params={"level": level},
                risk="LOW",
                raw_message=message
            )

        # Mute/unmute
        if any(p in msg for p in [
            "mute", "unmute", "silence"
        ]):
            return ParsedIntent(
                intent="set_volume",
                tool="system_control",
                params={"level": 0 if "mute" in msg 
                        and "unmute" not in msg else 50},
                risk="LOW",
                raw_message=message
            )

        # ─── SYSTEM TOGGLES ──────────────────────────────
        if any(p in msg for p in [
            "dark mode", "light mode",
            "turn on dark", "turn off dark",
            "enable dark", "disable dark"
        ]):
            enable = "light" not in msg and \
                     "off" not in msg and \
                     "disable" not in msg
            return ParsedIntent(
                intent="toggle_dark_mode",
                tool="system_control",
                params={"enable": enable},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "wifi on", "wifi off",
            "turn on wifi", "turn off wifi",
            "enable wifi", "disable wifi",
            "toggle wifi"
        ]):
            enable = "off" not in msg and \
                     "disable" not in msg
            return ParsedIntent(
                intent="toggle_wifi",
                tool="system_control",
                params={"enable": enable},
                risk="MEDIUM",
                raw_message=message
            )

        if any(p in msg for p in [
            "bluetooth on", "bluetooth off",
            "turn on bluetooth", "turn off bluetooth",
            "enable bluetooth", "disable bluetooth"
        ]):
            enable = "off" not in msg and \
                     "disable" not in msg
            return ParsedIntent(
                intent="toggle_bluetooth",
                tool="system_control",
                params={"enable": enable},
                risk="LOW",
                raw_message=message
            )

        # Do not disturb
        if any(p in msg for p in [
            "do not disturb", "dnd on", "dnd off",
            "focus mode", "turn on dnd", 
            "turn off dnd"
        ]):
            enable = "off" not in msg
            return ParsedIntent(
                intent="toggle_dnd",
                tool="system_control",
                params={"enable": enable},
                risk="LOW",
                raw_message=message
            )

        # ─── FILE CREATION ───────────────────────────────
        if any(p in msg for p in [
            "create file", "new file", 
            "make file", "create a file"
        ]):
            # Extract filename
            fname_match = re_module.search(
                r'(?:called|named|file)\s+([^\s]+\.\w+)',
                msg
            )
            fname = fname_match.group(1) \
                    if fname_match else "untitled.txt"
            path_match = re_module.search(
                r'(?:in|at|to)\s+(~?/[^\s]+)', msg
            )
            path = path_match.group(1) \
                   if path_match else f"~/Desktop/{fname}"
            content_match = re_module.search(
                r'(?:with|containing)\s+"([^"]+)"', 
                message
            )
            content = content_match.group(1) \
                      if content_match else ""
            return ParsedIntent(
                intent="file_create",
                tool="file_ops",
                params={
                    "path": path,
                    "content": content,
                    "filename": fname
                },
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "create folder", "new folder",
            "make folder", "make directory",
            "create directory"
        ]):
            fname_match = re_module.search(
                r'(?:called|named|folder)\s+([^\s/]+)', msg
            )
            fname = fname_match.group(1) \
                    if fname_match else "NewFolder"
            path = f"~/Desktop/{fname}"
            return ParsedIntent(
                intent="folder_create",
                tool="file_ops",
                params={"path": path, "name": fname},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "clean my desktop", "cleanup desktop",
            "clean desktop", "analyze desktop",
            "clean docs_local", "cleanup docs",
            "clean my docs", "analyze docs_local",
            "clean downloads", "cleanup downloads",
            "clean my downloads"
        ]):
            # Determine which folder
            if "desktop" in msg:
                folder = "~/Desktop"
            elif "docs_local" in msg or "docs" in msg:
                folder = "~/Docs_Local"
            else:
                folder = "~/Downloads"
            
            return ParsedIntent(
                intent="ai_cleanup_analyze",
                tool="file_ops",
                params={"folder": folder},
                risk="LOW",
                raw_message=message
            )
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedIntent:
    intent: str
    tool: str
    params: dict
    risk: str
    raw_message: str

class IntentParser:
    async def parse(self, message: str) -> Optional[ParsedIntent]:
        # ALWAYS try deterministic first
        # This bypasses LLM entirely for known commands
        result = self._deterministic_parse(message)
        if result:
            print(f"[Intent] Deterministic: "
                  f"{result.intent} → {result.tool}")
            return result
        
        # Only use LLM for unknown commands
        print(f"[Intent] LLM fallback for: {message}")
        return await self._llm_parse(message)

    def _deterministic_parse(self, message: str) -> Optional[ParsedIntent]:
        msg = message.lower().strip()
        
        # ─── SLASH COMMANDS (SKILLS) ──────────────────────
        if msg.startswith("/"):
            parts = message.split(" ", 1)
            cmd = parts[0]
            from core.skill_engine import skill_engine
            skill = skill_engine.find_skill(cmd)
            if skill:
                return ParsedIntent(
                    intent="execute_skill",
                    tool="skills",
                    params={"skill_id": skill.id, "args": parts[1] if len(parts) > 1 else ""},
                    risk="LOW",
                    raw_message=message
                )

        # ─── PARALLEL EXECUTION ───────────────────────────
        if " and also do " in msg or " and then " in msg:
            if " and also do " in msg:
                instructions = [p.strip() for p in message.split(" and also do ")]
            else:
                instructions = [p.strip() for p in message.split(" and then ")]
            
            if len(instructions) > 1:
                return ParsedIntent(
                    intent="parallel_execute",
                    tool="task_planner",
                    params={"instructions": instructions},
                    risk="MEDIUM",
                    raw_message=message
                )

        # ─── DATA ANALYSIS ────────────────────────────────
        if msg.startswith("analyze csv") or "analyze data" in msg:
            words = message.split()
            path = ""
            for w in words:
                if w.endswith(".csv"):
                    path = w
                    break
            return ParsedIntent(
                intent="analyze_csv",
                tool="data_analysis",
                params={"path": path},
                risk="LOW",
                raw_message=message
            )
            
        if msg.startswith("generate chart") or "create chart" in msg:
            words = message.split()
            path = ""
            for w in words:
                if w.endswith(".csv"):
                    path = w
                    break
            chart_type = "bar"
            if "pie" in msg: chart_type = "pie"
            elif "line" in msg: chart_type = "line"
            elif "scatter" in msg: chart_type = "scatter"
            
            return ParsedIntent(
                intent="generate_chart",
                tool="data_analysis",
                params={"path": path, "chart_type": chart_type, "x_col": None, "y_col": None},
                risk="LOW",
                raw_message=message
            )

        # ─── MEMORY ───────────────────────────────────────
        if any(msg.startswith(p) for p in [
            "remember ", "remember that ",
            "note that ", "save that ",
            "my name is ", "i am ",
            "i prefer ", "i like ",
            "don't forget "
        ]):
            # Extract the value
            value = message.strip()
            for t in [
                "remember that ", "remember ",
                "note that ", "save that ",
                "don't forget "
            ]:
                if msg.startswith(t):
                    value = message[len(t):].strip()
                    break
            
            # Extract key from value
            key = value[:50]
            if " is " in value:
                parts = value.split(" is ", 1)
                key = parts[0].strip()
                value = parts[1].strip()
            
            return ParsedIntent(
                intent="memory_save",
                tool="memory",
                params={"key": key, "value": value},
                risk="LOW",
                raw_message=message
            )
            
        if any(msg.startswith(p) for p in [
            "what is my ", "who am i",
            "do you remember ", "what do you know",
            "recall ", "remind me of my ",
            "what's my "
        ]):
            query = msg
            for t in [
                "what is my ", "what's my ",
                "do you remember ", "recall ",
                "remind me of my "
            ]:
                if msg.startswith(t):
                    query = message[len(t):].strip()
                    break
            return ParsedIntent(
                intent="memory_recall",
                tool="memory",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )

        # ─── BATCH FILE OPS ───────────────────────────────
        if msg.startswith("batch convert "):
            return ParsedIntent(
                intent="batch_convert_images",
                tool="file_manager",
                params={"instruction": message},
                risk="MEDIUM",
                raw_message=message
            )
            
        if msg.startswith("batch rename "):
            return ParsedIntent(
                intent="batch_rename_numbered",
                tool="file_manager",
                params={"instruction": message},
                risk="MEDIUM",
                raw_message=message
            )
            
        if "find large files" in msg:
            return ParsedIntent(
                intent="get_large_files",
                tool="file_manager",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )
        
        # ─── SECURITY COMMANDS ───────────────────────────
        if any(p in msg for p in [
            "scan system security", "security scan",
            "run security scan", "check security",
            "scan for threats", "security check",
            "full security scan"
        ]):
            return ParsedIntent(
                intent="security_full_scan",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "scan downloads", "check downloads",
            "scan download folder"
        ]):
            return ParsedIntent(
                intent="security_scan_downloads",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "show processes", "running processes",
            "list processes", "check processes",
            "what's running", "whats running",
            "show running apps"
        ]):
            return ParsedIntent(
                intent="security_processes",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "check network", "network connections",
            "show connections", "network activity",
            "what's connecting", "check connections"
        ]):
            return ParsedIntent(
                intent="security_network",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "scan file ", "check file ",
            "is this file safe", "analyze file"
        ]):
            path_match = re_module.search(r'(~/[^\s]+|/[^\s]+)', message)
            path = path_match.group(1) if path_match else ""
            return ParsedIntent(
                intent="security_scan_file",
                tool="security",
                params={"path": path},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "quarantine file", "quarantine "
        ]):
            path_match = re_module.search(r'(~/[^\s]+|/[^\s]+)', message)
            path = path_match.group(1) if path_match else ""
            return ParsedIntent(
                intent="security_quarantine",
                tool="security",
                params={"path": path},
                risk="MEDIUM",
                raw_message=message
            )

        if any(p in msg for p in [
            "enable secure mode", "secure mode on",
            "activate secure mode", "lockdown"
        ]):
            return ParsedIntent(
                intent="security_secure_mode",
                tool="security",
                params={"enable": True},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "disable secure mode", "secure mode off",
            "deactivate secure mode"
        ]):
            return ParsedIntent(
                intent="security_secure_mode",
                tool="security",
                params={"enable": False},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "check vulnerabilities", "vulnerability scan",
            "outdated packages", "check updates",
            "scan vulnerabilities"
        ]):
            return ParsedIntent(
                intent="security_vulnerabilities",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "kill process", "terminate process",
            "stop process", "kill pid"
        ]):
            pid_match = re_module.search(r'\b(\d{3,6})\b', msg)
            pid = int(pid_match.group(1)) if pid_match else 0
            return ParsedIntent(
                intent="security_kill_process",
                tool="security",
                params={"pid": pid},
                risk="HIGH",
                raw_message=message
            )

        if any(p in msg for p in [
            "check privacy", "privacy scan",
            "app permissions", "who has camera access",
            "who has microphone access"
        ]):
            return ParsedIntent(
                intent="security_privacy",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "threat level", "am i safe",
            "security status", "security report",
            "how secure", "security summary"
        ]):
            return ParsedIntent(
                intent="security_status",
                tool="security",
                params={},
                risk="LOW",
                raw_message=message
            )

        # ─── DOCUMENT GENERATION ─────────────────────────
        # Check this EARLY — before other patterns

        # Document generation — highest priority check
        msg_lower = message.lower()
        if any(p in msg_lower for p in [
            "word doc", "word document", ".docx",
            "as a doc", "as a document", "as a word",
            "in word", "docx file"
        ]):
            return ParsedIntent(
                intent="create_docx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg_lower for p in [
            "spreadsheet", ".xlsx", "excel file",
            "as a spreadsheet", "in excel"
        ]):
            return ParsedIntent(
                intent="create_xlsx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg_lower for p in [
            "presentation", "powerpoint", ".pptx",
            "slide deck", "as slides", "as a presentation"
        ]):
            return ParsedIntent(
                intent="create_pptx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        # Word doc
        if any(p in msg_lower for p in [
            "word doc", "word document", ".docx",
            "create report", "write a report", 
            "make a report", "generate report",
            "create document", "write document",
            "create a report", "write report",
            "as a doc", "as a document",
            "as a word", "in word format"
        ]):
            return ParsedIntent(
                intent="create_docx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        # Spreadsheet
        if any(p in msg for p in [
            "spreadsheet", "excel", ".xlsx",
            "create sheet", "make sheet",
            "as a spreadsheet", "in excel",
            "excel file", "xlsx file"
        ]):
            return ParsedIntent(
                intent="create_xlsx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        # Presentation
        if any(p in msg for p in [
            "presentation", "powerpoint", "slides",
            ".pptx", "slide deck", "deck",
            "create slides", "make slides",
            "as a presentation", "in powerpoint"
        ]):
            return ParsedIntent(
                intent="create_pptx",
                tool="documents",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )
        
        # APP OPENING - highest priority
        APP_MAP = {
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "safari": "Safari",
            "firefox": "Firefox",
            "slack": "Slack",
            "vscode": "Visual Studio Code",
            "vs code": "Visual Studio Code",
            "code": "Visual Studio Code",
            "terminal": "Terminal",
            "finder": "Finder",
            "spotify": "Spotify",
            "notes": "Notes",
            "mail": "Mail",
            "calendar": "Calendar",
            "figma": "Figma",
            "notion": "Notion",
            "discord": "Discord",
            "whatsapp": "WhatsApp",
            "telegram": "Telegram",
            "instagram": "Instagram",
            "youtube": "YouTube", 
            "twitter": "Twitter",
            "x": "X",
            "zoom": "zoom.us",
            "teams": "Microsoft Teams",
            "word": "Microsoft Word",
            "excel": "Microsoft Excel",
            "powerpoint": "Microsoft PowerPoint",
            "outlook": "Microsoft Outlook",
            "photoshop": "Adobe Photoshop",
            "premiere": "Adobe Premiere Pro",
            "after effects": "Adobe After Effects",
            "xcode": "Xcode",
            "android studio": "Android Studio",
            "docker": "Docker Desktop",
            "postman": "Postman",
            "iterm": "iTerm",
            "iterm2": "iTerm2",
            "warp": "Warp",
            "arc": "Arc",
            "brave": "Brave Browser",
            "opera": "Opera",
            "vlc": "VLC",
            "obsidian": "Obsidian",
            "linear": "Linear",
            "bear": "Bear",
            "things": "Things 3",
            "1password": "1Password",
            "bitwarden": "Bitwarden",
            "raycast": "Raycast",
            "alfred": "Alfred",
            "cleanmymac": "CleanMyMac",
            "screenflow": "ScreenFlow",
            "loom": "Loom",
            "grammarly": "Grammarly",
            "cursor": "Cursor",
            "antigravity": "Antigravity"
        }
        
        # Multi-app + action commands
        # "open spotify and play X"
        if "spotify" in msg and any(p in msg for p in [
            "play", "listen", "put on", "start"
        ]):
            # Extract what to play
            query = ""
            for trigger in ["play ", "listen to ",
                            "put on "]:
                if trigger in msg:
                    query = message[
                        msg.index(trigger)+len(trigger):
                    ].strip()
                    # Remove trailing words like 
                    # "on spotify"
                    query = query.replace(
                        "on spotify", ""
                    ).replace(
                        "in spotify", ""
                    ).strip()
                    break
            
            if not query or query in [
                "music", "something", "a song",
                "songs", "the song"
            ]:
                # Just open and play
                return ParsedIntent(
                    intent="spotify_play",
                    tool="system_control",
                    params={},
                    risk="LOW",
                    raw_message=message
                )
            else:
                return ParsedIntent(
                    intent="spotify_search",
                    tool="system_control",
                    params={"query": query},
                    risk="LOW",
                    raw_message=message
                )

        # "play X on spotify" or "play X"
        if msg.startswith("play "):
            query = message[5:].strip()
            query = query.replace(
                "on spotify", ""
            ).strip()
            return ParsedIntent(
                intent="spotify_search",
                tool="system_control",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )
        
        # "open X" or "launch X" or "start X"
        for trigger in ["open ", "launch ", "start "]:
            if msg.startswith(trigger):
                remainder = msg[len(trigger):].strip()
                # Strip trailing "app" word
                if remainder.endswith(" app"):
                    remainder = remainder[:-4].strip()
                if remainder.endswith(" application"):
                    remainder = remainder[:-12].strip()

                # Check for URL
                if remainder.startswith("http") or \
                   "." in remainder and " " not in remainder:
                    url = remainder if \
                        remainder.startswith("http") \
                        else "https://" + remainder
                    return ParsedIntent(
                        intent="browser_open",
                        tool="browser",
                        params={"url": url},
                        risk="LOW",
                        raw_message=message
                    )
                # Check for app
                for app_key, app_name in APP_MAP.items():
                    if remainder.startswith(app_key):
                        return ParsedIntent(
                            intent="browser_open",
                            tool="browser",
                            params={"app": app_name},
                            risk="LOW",
                            raw_message=message
                        )
                
                # If no app matched, try opening as URL search
                if not any(remainder.startswith(k) 
                           for k in APP_MAP):
                    # Could be a website - try opening in browser
                    if len(remainder.split()) <= 3:
                        url = "https://" + remainder\
                              .replace(" ", "") + ".com" \
                              if "." not in remainder \
                              else "https://" + remainder
                        return ParsedIntent(
                            intent="browser_open",
                            tool="browser",
                            params={"url": url},
                            risk="LOW",
                            raw_message=message
                        )
        
        # "go to X.com" or "navigate to X"
        for trigger in ["go to ", "navigate to ", 
                        "open website ", "visit "]:
            if trigger in msg:
                idx = msg.index(trigger) + len(trigger)
                url = message[idx:].strip()
                if not url.startswith("http"):
                    url = "https://" + url
                return ParsedIntent(
                    intent="browser_open",
                    tool="browser",
                    params={"url": url},
                    risk="LOW",
                    raw_message=message
                )
        
        # MULTI-STEP: "open X and go to Y"
        if " and " in msg and \
           any(msg.startswith(t) for t in 
               ["open ", "launch "]):
            # This is a complex task - use task planner
            return ParsedIntent(
                intent="task_execute",
                tool="task_planner",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )
        
        # SKILLS
        if any(p in msg for p in [
            "show skills", "list skills",
            "available skills", "what skills",
            "my skills", "installed skills",
            "what can you do", "skill list"
        ]):
            return ParsedIntent(
                intent="list_skills",
                tool="skills",
                params={},
                risk="LOW",
                raw_message=message
            )

        # SYSTEM
        if any(p in msg for p in [
            "check system", "system status",
            "system health", "system scan",
            "how is my system", "check cpu",
            "check ram", "check memory",
            "check disk", "check battery",
            "show metrics"
        ]):
            return ParsedIntent(
                intent="system_status",
                tool="system",
                params={},
                risk="LOW",
                raw_message=message
            )
        
        # CLEANUP
        if "yes execute cleanup" not in msg and            "clean my desktop" not in msg and            "clean docs" not in msg and            any(p in msg for p in [
            "run cleanup", "clean system",
            "clean my system", "cleanup",
            "clear cache", "clean downloads",
            "organize downloads"
        ]):
            return ParsedIntent(
                intent="system_cleanup",
                tool="system",
                params={},
                risk="LOW",
                raw_message=message
            )
        
        # TASK DELETE
        if any(p in msg for p in [
            "delete task", "remove task",
            "cancel task", "drop task"
        ]):
            title = ""
            for trigger in [
                "delete task", "remove task",
                "cancel task", "drop task"
            ]:
                if trigger in msg:
                    title = message[
                        msg.index(trigger)+len(trigger):
                    ].strip(" :")
                    break
            return ParsedIntent(
                intent="task_delete",
                tool="tasks",
                params={"title": title},
                risk="LOW",
                raw_message=message
            )

        # TASK COMPLETE
        if any(p in msg for p in [
            "complete task", "finish task",
            "mark task done", "task done"
        ]):
            title = ""
            for trigger in [
                "complete task", "finish task",
                "mark task done", "task done"
            ]:
                if trigger in msg:
                    title = message[
                        msg.index(trigger)+len(trigger):
                    ].strip(" :")
                    break
            return ParsedIntent(
                intent="task_complete",
                tool="tasks",
                params={"title": title},
                risk="LOW",
                raw_message=message
            )

        # TASKS
        if any(p in msg for p in [
            "create task", "add task", "new task",
            "remind me to", "create a task",
            "schedule meeting", "book meeting"
        ]):
            title = message
            for trigger in ["create task:", "create task",
                            "add task:", "add task",
                            "new task:", "new task",
                            "remind me to"]:
                if trigger in msg:
                    title = message[
                        msg.index(trigger)+len(trigger):
                    ].strip(" :")
                    break
            return ParsedIntent(
                intent="task_create",
                tool="tasks",
                params={"title": title,
                        "priority": "medium"},
                risk="LOW",
                raw_message=message
            )
        
        if any(msg == p or msg.startswith(p) for p in [
            "show tasks", "list tasks", "my tasks",
            "what are my tasks", "show my tasks"
        ]):
            return ParsedIntent(
                intent="task_list",
                tool="tasks",
                params={},
                risk="LOW",
                raw_message=message
            )
        
        # FILES
        if ("~/" in msg or ".py" in msg or 
            ".txt" in msg or ".pdf" in msg) and \
           any(p in msg for p in [
               "read ", "open file", "show file", 
               "cat ", "view "
           ]):
            path = next(
                (w for w in reversed(msg.split())
                 if "/" in w or w.startswith("~")),
                ""
            )
            return ParsedIntent(
                intent="file_read",
                tool="file_system",
                params={"path": path},
                risk="LOW",
                raw_message=message
            )
        
        if any(p in msg for p in [
            "search files", "find files",
            "find file", "search for file"
        ]):
            query = msg.replace(
                "search files", ""
            ).replace("find files", "").strip()
            return ParsedIntent(
                intent="file_search",
                tool="file_system",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )
        
        # ─── FILE MANAGEMENT ─────────────────────────────
        if any(p in msg for p in [
            "organize folder", "organize my downloads",
            "organize downloads", "clean up folder",
            "sort folder", "organize files"
        ]):
            path_match = re_module.search(
                r'(~/[^\s]+|downloads|desktop|documents)',
                msg
            )
            path = "~/Downloads"
            if path_match:
                p_str = path_match.group(1)
                if p_str in [
                    "downloads", "desktop", "documents"
                ]:
                    path = f"~/{p_str.title()}"
                else:
                    path = p_str
            return ParsedIntent(
                intent="organize_folder",
                tool="file_manager",
                params={"path": path},
                risk="MEDIUM",
                raw_message=message
            )

        if any(p in msg for p in [
            "find duplicates", "find duplicate files",
            "show duplicates", "remove duplicates"
        ]):
            return ParsedIntent(
                intent="find_duplicates",
                tool="file_manager",
                params={"path": "~/Downloads"},
                risk="LOW",
                raw_message=message
            )

        # ─── PDF TOOLS ───────────────────────────────────
        if "merge pdf" in msg or "combine pdf" in msg:
            return ParsedIntent(
                intent="pdf_merge",
                tool="file_manager",
                params={},
                risk="LOW",
                raw_message=message
            )

        if "compress pdf" in msg:
            url_match = re_module.search(r'(~/[^\s]+\.pdf)', msg)
            path = url_match.group(1) if url_match else ""
            return ParsedIntent(
                intent="pdf_compress",
                tool="file_manager",
                params={"path": path},
                risk="LOW",
                raw_message=message
            )

        # ─── SCHEDULING ──────────────────────────────────
        if any(p in msg for p in [
            "schedule task", "schedule every",
            "run every day", "run daily",
            "run every week", "run weekly",
            "automate every", "schedule automation"
        ]):
            return ParsedIntent(
                intent="schedule_task",
                tool="scheduler",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "show scheduled", "list scheduled",
            "my scheduled tasks", "show automations"
        ]):
            return ParsedIntent(
                intent="list_scheduled",
                tool="scheduler",
                params={},
                risk="LOW",
                raw_message=message
            )

        # ─── GOOGLE ──────────────────────────────────────
        if any(p in msg for p in [
            "check gmail", "check email",
            "show emails", "read emails",
            "unread emails", "my emails"
        ]):
            return ParsedIntent(
                intent="gmail_check",
                tool="google",
                params={},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "create calendar event", "add to calendar",
            "schedule on calendar", "add event",
            "create event"
        ]):
            return ParsedIntent(
                intent="calendar_create",
                tool="google",
                params={"instruction": message},
                risk="LOW",
                raw_message=message
            )

        # ─── SPOTIFY CONTROL ──────────────────────────────
        SPOTIFY_COMMANDS = {
            "play spotify": ("spotify_play", {}),
            "pause spotify": ("spotify_pause", {}),
            "stop spotify": ("spotify_pause", {}),
            "next song": ("spotify_next", {}),
            "next track": ("spotify_next", {}),
            "previous song": ("spotify_prev", {}),
            "previous track": ("spotify_prev", {}),
            "skip song": ("spotify_next", {}),
            "volume up": ("volume_up", {}),
            "volume down": ("volume_down", {}),
        }
        for cmd, (intent, params) in SPOTIFY_COMMANDS.items():
            if cmd in msg:
                return ParsedIntent(
                    intent=intent,
                    tool="system_control",
                    params=params,
                    risk="LOW",
                    raw_message=message
                )

        # Play specific song
        if any(p in msg for p in [
            "play ", "put on ", "listen to "
        ]) and any(p in msg for p in [
            "song", "music", "spotify", "track",
            "album", "artist", "playlist"
        ]):
            query = msg
            for t in ["play ", "put on ", 
                      "listen to "]:
                if t in msg:
                    query = message[
                        msg.index(t)+len(t):
                    ].strip()
                    break
            return ParsedIntent(
                intent="spotify_search",
                tool="system_control",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )

        # ─── VOLUME / BRIGHTNESS ─────────────────────────
        vol_match = re_module.search(
            r'(set |turn )?(volume|vol)\s*(to\s*)?(\d+)',
            msg
        )
        if vol_match:
            level = int(vol_match.group(4))
            level = max(0, min(100, level))
            return ParsedIntent(
                intent="set_volume",
                tool="system_control",
                params={"level": level},
                risk="LOW",
                raw_message=message
            )

        bright_match = re_module.search(
            r'(set |turn )?(brightness)\s*(to\s*)?(\d+)',
            msg
        )
        if bright_match:
            level = int(bright_match.group(4))
            return ParsedIntent(
                intent="set_brightness",
                tool="system_control",
                params={"level": level},
                risk="LOW",
                raw_message=message
            )

        # Mute/unmute
        if any(p in msg for p in [
            "mute", "unmute", "silence"
        ]):
            return ParsedIntent(
                intent="set_volume",
                tool="system_control",
                params={"level": 0 if "mute" in msg 
                        and "unmute" not in msg else 50},
                risk="LOW",
                raw_message=message
            )

        # ─── SYSTEM TOGGLES ──────────────────────────────
        if any(p in msg for p in [
            "dark mode", "light mode",
            "turn on dark", "turn off dark",
            "enable dark", "disable dark"
        ]):
            enable = "light" not in msg and \
                     "off" not in msg and \
                     "disable" not in msg
            return ParsedIntent(
                intent="toggle_dark_mode",
                tool="system_control",
                params={"enable": enable},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "wifi on", "wifi off",
            "turn on wifi", "turn off wifi",
            "enable wifi", "disable wifi",
            "toggle wifi"
        ]):
            enable = "off" not in msg and \
                     "disable" not in msg
            return ParsedIntent(
                intent="toggle_wifi",
                tool="system_control",
                params={"enable": enable},
                risk="MEDIUM",
                raw_message=message
            )

        if any(p in msg for p in [
            "bluetooth on", "bluetooth off",
            "turn on bluetooth", "turn off bluetooth",
            "enable bluetooth", "disable bluetooth"
        ]):
            enable = "off" not in msg and \
                     "disable" not in msg
            return ParsedIntent(
                intent="toggle_bluetooth",
                tool="system_control",
                params={"enable": enable},
                risk="LOW",
                raw_message=message
            )

        # Do not disturb
        if any(p in msg for p in [
            "do not disturb", "dnd on", "dnd off",
            "focus mode", "turn on dnd", 
            "turn off dnd"
        ]):
            enable = "off" not in msg
            return ParsedIntent(
                intent="toggle_dnd",
                tool="system_control",
                params={"enable": enable},
                risk="LOW",
                raw_message=message
            )

        # ─── FILE CREATION ───────────────────────────────
        if any(p in msg for p in [
            "create file", "new file", 
            "make file", "create a file"
        ]):
            # Extract filename
            fname_match = re_module.search(
                r'(?:called|named|file)\s+([^\s]+\.\w+)',
                msg
            )
            fname = fname_match.group(1) \
                    if fname_match else "untitled.txt"
            path_match = re_module.search(
                r'(?:in|at|to)\s+(~?/[^\s]+)', msg
            )
            path = path_match.group(1) \
                   if path_match else f"~/Desktop/{fname}"
            content_match = re_module.search(
                r'(?:with|containing)\s+"([^"]+)"', 
                message
            )
            content = content_match.group(1) \
                      if content_match else ""
            return ParsedIntent(
                intent="file_create",
                tool="file_ops",
                params={
                    "path": path,
                    "content": content,
                    "filename": fname
                },
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "create folder", "new folder",
            "make folder", "make directory",
            "create directory"
        ]):
            fname_match = re_module.search(
                r'(?:called|named|folder)\s+([^\s/]+)', msg
            )
            fname = fname_match.group(1) \
                    if fname_match else "NewFolder"
            path = f"~/Desktop/{fname}"
            return ParsedIntent(
                intent="folder_create",
                tool="file_ops",
                params={"path": path, "name": fname},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "clean my desktop", "cleanup desktop",
            "clean desktop", "analyze desktop",
            "clean docs_local", "cleanup docs",
            "clean my docs", "analyze docs_local",
            "clean downloads", "cleanup downloads",
            "clean my downloads"
        ]):
            # Determine which folder
            if "desktop" in msg:
                folder = "~/Desktop"
            elif "docs_local" in msg or "docs" in msg:
                folder = "~/Docs_Local"
            else:
                folder = "~/Downloads"
            
            return ParsedIntent(
                intent="ai_cleanup_analyze",
                tool="file_ops",
                params={"folder": folder},
                risk="LOW",
                raw_message=message
            )

        if any(p in msg for p in [
            "yes execute cleanup", "approve cleanup",
            "yes clean", "execute the cleanup",
            "yes do it", "confirm cleanup",
            "proceed with cleanup"
        ]):
            return ParsedIntent(
                intent="ai_cleanup_execute",
                tool="file_ops",
                params={},
                risk="MEDIUM",
                raw_message=message
            )

        # ─── WEB SEARCH ──────────────────────────────────
        if any(msg.startswith(p) for p in [
            "search ", "search for ", "google ",
            "look up ", "find information about ",
            "what is ", "who is ", "how to ",
            "when did ", "where is ", "why is ",
            "tell me about "
        ]) or msg.endswith("?"):
            query = message
            for t in ["search for ", "search ",
                      "google ", "look up ",
                      "find information about ",
                      "tell me about "]:
                if msg.startswith(t):
                    query = message[len(t):].strip()
                    break
            return ParsedIntent(
                intent="web_search",
                tool="web",
                params={"query": query},
                risk="LOW",
                raw_message=message
            )


        # ─── NEWS / INTELLIGENCE ──────────────────────────
        if any(p in msg for p in [
            "todays geopolitics", "intel briefing",
            "spy news", "intelligence briefing",
            "geopolitics news"
        ]):
            return ParsedIntent(
                intent="intel_briefing",
                tool="web",
                params={"query": msg},
                risk="LOW",
                raw_message=message
            )

        # ─── GMAIL ───────────────────────────────────────
        if any(p in msg for p in [
            "check my mails", "check my email",
            "summarize inbox", "my inbox",
            "check my inbox", "unread emails"
        ]):
            return ParsedIntent(
                intent="summarize_inbox",
                tool="gmail",
                params={},
                risk="LOW",
                raw_message=message
            )

        if msg.startswith("send email to ") or "send an email to" in msg:
            def parse_send_email(command: str) -> dict:
                pattern = r'send email to (.+?) subject (.+?) body (.+)'
                match = re_module.match(pattern, command.strip(), re_module.IGNORECASE)
                if match:
                    return {
                        "to": match.group(1).strip(),
                        "subject": match.group(2).strip(),
                        "body": match.group(3).strip()
                    }
                return {"raw": command}

            params = parse_send_email(message)
            return ParsedIntent(
                intent="send_email",
                tool="gmail",
                params=params,
                risk="MEDIUM",
                raw_message=message
            )

        # ─── WEBPAGE READING ─────────────────────────────
        if any(p in msg for p in [
            "read page", "summarize page",
            "summarize website", "read website",
            "what does this page say",
            "read this url", "summarize url",
            "read this link"
        ]) or (any(p in msg for p in [
            "summarize ", "read "
        ]) and ("http" in msg or "www." in msg)):
            url_match = re_module.search(
                r'https?://[^\s]+|www\.[^\s]+', message
            )
            url = url_match.group(0) \
                  if url_match else ""
            return ParsedIntent(
                intent="read_webpage",
                tool="web",
                params={"url": url},
                risk="LOW",
                raw_message=message
            )

        # ─── SCREENSHOTS ─────────────────────────────────
        if any(p in msg for p in [
            "take screenshot", "take a screenshot",
            "screenshot", "capture screen",
            "capture my screen"
        ]):
            annotate = any(p in msg for p in [
                "annotate", "mark", "highlight",
                "draw", "label"
            ])
            save_path = "~/Desktop/screenshot.png"
            path_match = re_module.search(
                r'(?:save to|save at|to)\s+(~?/[^\s]+)',
                msg
            )
            if path_match:
                save_path = path_match.group(1)
            return ParsedIntent(
                intent="take_screenshot",
                tool="vision_action",
                params={
                    "path": save_path,
                    "annotate": annotate
                },
                risk="LOW",
                raw_message=message
            )

        # ─── WHATSAPP ────────────────────────────────────
        if any(p in msg for p in [
            "send whatsapp", "whatsapp ",
            "message on whatsapp",
            "send message to ", "text "
        ]):
            contact_match = re_module.search(
                r'(?:to|message)\s+([A-Z][a-z]+(?:\s+'
                r'[A-Z][a-z]+)?)', message
            )
            contact = contact_match.group(1) \
                      if contact_match else ""
            msg_match = re_module.search(
                r'(?:saying|message|:)\s+"([^"]+)"',
                message
            )
            text = msg_match.group(1) \
                   if msg_match else ""
            return ParsedIntent(
                intent="send_whatsapp",
                tool="messaging",
                params={
                    "contact": contact,
                    "message": text
                },
                risk="MEDIUM",
                raw_message=message
            )

        # ─── EMAIL ───────────────────────────────────────
        if any(p in msg for p in [
            "send email", "send an email",
            "email ", "compose email",
            "write email", "draft email"
        ]):
            to_match = re_module.search(
                r'(?:to|email)\s+([\w.]+@[\w.]+)', message
            )
            to_email = to_match.group(1) \
                       if to_match else ""
            subj_match = re_module.search(
                r'(?:subject|about)\s+"([^"]+)"', message
            )
            subject = subj_match.group(1) \
                      if subj_match else "Message from N.O.V.A"
            body_match = re_module.search(
                r'(?:body|saying|message)\s+"([^"]+)"',
                message
            )
            body = body_match.group(1) if body_match else ""
            return ParsedIntent(
                intent="send_email",
                tool="messaging",
                params={
                    "to": to_email,
                    "subject": subject,
                    "body": body
                },
                risk="MEDIUM",
                raw_message=message
            )

        # ─── REMINDERS / ALARMS ──────────────────────────
        if any(p in msg for p in [
            "remind me", "set reminder",
            "set alarm", "alarm at",
            "wake me up", "remind me at",
            "remind me to"
        ]):
            time_match = re_module.search(
                r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?'
                r'|\d{1,2}\s*(?:minutes?|hours?)'
                r'(?:\s*from\s*now)?)',
                msg, re_module.IGNORECASE
            )
            time_str = time_match.group(0) \
                       if time_match else ""
            label_match = re_module.search(
                r'(?:to|about|for)\s+(.+?)(?:\s+at\s+'
                r'|\s+in\s+|$)',
                msg
            )
            label = label_match.group(1) \
                    if label_match else message
            return ParsedIntent(
                intent="set_reminder",
                tool="system_control",
                params={
                    "time": time_str,
                    "label": label
                },
                risk="LOW",
                raw_message=message
            )

        # SHELL - direct commands
        SHELL_STARTS = [
            "ls", "pwd", "cat ", "grep ", "find ",
            "ps ", "df ", "du ", "git ", "brew ",
            "pip ", "python ", "node ", "npm ",
            "echo ", "uname", "whoami", "which ",
            "ollama "
        ]
        if any(msg.startswith(p) for p in SHELL_STARTS):
            return ParsedIntent(
                intent="shell_exec",
                tool="terminal",
                params={"command": message.strip()},
                risk="LOW",
                raw_message=message
            )
        
        # No match - return None to use LLM
        return None

    async def _llm_parse(self, message: str) -> ParsedIntent:
        system_prompt = """You are N.O.V.A's intent parser. Analyze the user message 
and return ONLY a JSON object with no explanation.

JSON schema:
{
  "intent": "<intent_type>",
  "tool": "<tool_name>", 
  "params": {
    // extracted parameters relevant to the intent
  },
  "risk": "LOW|MEDIUM|HIGH"
}

Available tools: file_system, terminal, workspace, system, tasks, comms, 
jira, memory, browser, navigation, llm, task_planner, system_control, 
file_ops, web, messaging, documents, file_manager, scheduler, google, 
skills, data_analysis, security

TASK EXAMPLES (tool="tasks"):

User: "delete the NOVA dashboard task"
→ {"intent": "task_delete", "tool": "tasks", "params": {"title": "NOVA dashboard"}, "risk": "LOW"}

User: "remove fgh"
→ {"intent": "task_delete", "tool": "tasks", "params": {"title": "fgh"}, "risk": "LOW"}

User: "I finished the dashboard task"
→ {"intent": "task_complete", "tool": "tasks", "params": {"title": "dashboard"}, "risk": "LOW"}

User: "mark NOVA task as done"
→ {"intent": "task_complete", "tool": "tasks", "params": {"title": "NOVA"}, "risk": "LOW"}

User: "add a task to learn Python"
→ {"intent": "task_create", "tool": "tasks", "params": {"title": "learn Python", "priority": "medium"}, "risk": "LOW"}

User: "what tasks do I have"
→ {"intent": "task_list", "tool": "tasks", "params": {}, "risk": "LOW"}


User: "check my inbox"
→ {"intent": "summarize_inbox", "tool": "gmail", "params": {}, "risk": "LOW"}

User: "send email to sohamdhande17@gmail.com subject test body hello"
→ {"intent": "send_email", "tool": "gmail", "params": {"to": "sohamdhande17@gmail.com subject test body hello", "raw": "send email to sohamdhande17@gmail.com subject test body hello"}, "risk": "MEDIUM"}

If unsure, default to intent="conversation", tool="llm" 
"""
        prompt = f"SYSTEM:\n{system_prompt}\n\nUSER: {message}"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=15.0
                )
                response_text = resp.json().get("response", "")
            
            # Clean up potential markdown fences
            cleaned = response_text
            if "```json" in response_text:
                cleaned = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                cleaned = response_text.split("```")[1].split("```")[0]
                
            data = json.loads(cleaned.strip())
            
            return ParsedIntent(
                intent=data.get("intent", "conversation"),
                tool=data.get("tool", "llm"),
                params=data.get("params", {}),
                risk=data.get("risk", "LOW"),
                raw_message=message
            )
        except Exception as e:
            print(f"[IntentParser Error] {e}")
            return ParsedIntent(
                intent="conversation",
                tool="llm",
                params={},
                risk="LOW",
                raw_message=message
            )

intent_parser = IntentParser()
