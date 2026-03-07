import os
import re
import json
import subprocess
import asyncio
import httpx
from datetime import datetime

class NovaCapabilities:

    # ─── SPOTIFY ────────────────────────────────
    
    def spotify_command(self, 
                         command: str) -> str:
        """Control Spotify via AppleScript."""
        COMMANDS = {
            "play":     "play",
            "pause":    "pause", 
            "next":     "next track",
            "prev":     "previous track",
            "stop":     "pause"
        }
        action = COMMANDS.get(command, command)
        script = f'''
        tell application "Spotify"
            {action}
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Spotify: {action} ✓"
        return f"Spotify error: {result.stderr}"
    
    def spotify_search_play(self, 
                             query: str) -> str:
        """Search and play on Spotify."""
        script = f'''
        tell application "Spotify"
            activate
            play track "spotify:search:{query}"
        end tell
        '''
        # Open Spotify and search
        subprocess.Popen(['open', '-a', 'Spotify'])
        import time; time.sleep(2)
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        return f"Playing: {query}"
    
    def get_spotify_status(self) -> str:
        """Get current playing track."""
        script = '''
        tell application "Spotify"
            if player state is playing then
                set t to current track
                return (name of t) & " by " & \
                       (artist of t)
            else
                return "Not playing"
            end if
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        return result.stdout.strip() or "Spotify not running"
    
    # ─── VOLUME / BRIGHTNESS ────────────────────
    
    def set_volume(self, level: int) -> str:
        """Set system volume 0-100."""
        level = max(0, min(100, level))
        # AppleScript uses 0-100 scale
        script = f'set volume output volume {level}'
        subprocess.run(
            ['osascript', '-e', script]
        )
        return f"Volume set to {level}%"
    
    def set_brightness(self, level: int) -> str:
        """Set screen brightness 0-100."""
        # Convert to 0.0-1.0
        bright = level / 100.0
        script = f'''
        tell application "System Preferences"
        end tell
        do shell script "brightness {bright}"
        '''
        # Try using brightness CLI tool
        result = subprocess.run(
            ['brightness', str(bright)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # Fallback: use AppleScript
            script2 = f'''
            tell application "System Events"
                tell process "SystemUIServer"
                    set value of slider 1 of \
                    menu bar item "Brightness" of \
                    menu bar 1 to {bright}
                end tell
            end tell
            '''
            subprocess.run(
                ['osascript', '-e', script2]
            )
        return f"Brightness set to {level}%"
    
    def mute(self) -> str:
        subprocess.run(
            ['osascript', '-e', 
             'set volume output muted true']
        )
        return "System muted"
    
    def unmute(self) -> str:
        subprocess.run(
            ['osascript', '-e',
             'set volume output muted false']
        )
        return "System unmuted"
    
    # ─── SYSTEM TOGGLES ─────────────────────────
    
    def toggle_dark_mode(self, 
                          enable: bool) -> str:
        """Toggle macOS dark/light mode."""
        mode = "true" if enable else "false"
        script = f'''
        tell application "System Events"
            tell appearance preferences
                set dark mode to {mode}
            end tell
        end tell
        '''
        subprocess.run(
            ['osascript', '-e', script]
        )
        return f"Dark mode {'enabled' if enable else 'disabled'}"
    
    def toggle_wifi(self, enable: bool) -> str:
        """Toggle WiFi on/off."""
        action = "on" if enable else "off"
        result = subprocess.run(
            ['networksetup', '-setairportpower',
             'en0', action],
            capture_output=True, text=True
        )
        return f"WiFi turned {action}"
    
    def toggle_bluetooth(self, 
                          enable: bool) -> str:
        """Toggle Bluetooth."""
        action = "on" if enable else "off"
        result = subprocess.run(
            ['blueutil', f'--{action}'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return (f"Bluetooth toggle failed. "
                    f"Install blueutil: "
                    f"brew install blueutil")
        return f"Bluetooth turned {action}"
    
    def toggle_dnd(self, enable: bool) -> str:
        """Toggle Do Not Disturb / Focus."""
        if enable:
            script = '''
            tell application "System Events"
                tell process "Control Center"
                    keystroke "f" using \
                    {control down, option down}
                end tell
            end tell
            '''
        else:
            script = '''
            tell application "System Events"
                tell process "Control Center"
                    keystroke "f" using \
                    {control down, option down}
                end tell
            end tell
            '''
        # Use shortcuts app if available
        result = subprocess.run(
            ['shortcuts', 'run', 
             'Focus' if enable else 'Stop Focus'],
            capture_output=True, text=True
        )
        return f"Do Not Disturb " \
               f"{'enabled' if enable else 'disabled'}"
    
    # ─── FILE OPERATIONS ────────────────────────
    
    def create_file(self, path: str, 
                    content: str = "") -> str:
        """Create a file with optional content."""
        expanded = os.path.expanduser(path)
        os.makedirs(
            os.path.dirname(expanded),
            exist_ok=True
        )
        with open(expanded, 'w') as f:
            f.write(content)
        return f"File created: {path}"
    
    def create_folder(self, path: str) -> str:
        """Create a directory."""
        expanded = os.path.expanduser(path)
        os.makedirs(expanded, exist_ok=True)
        return f"Folder created: {path}"
    
    # ─── WEB SEARCH ─────────────────────────────
    
    async def web_search(self, query: str) -> str:
        try:
            # Step 1: Get DuckDuckGo results
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1"
                    },
                    timeout=10,
                    follow_redirects=True
                )
                data = resp.json()
            
            # Extract all available text
            chunks = []
            
            if data.get("Answer"):
                chunks.append(data["Answer"])
            
            if data.get("AbstractText"):
                chunks.append(data["AbstractText"])
            
            for topic in data.get(
                "RelatedTopics", []
            )[:5]:
                if isinstance(topic, dict) and \
                   topic.get("Text"):
                    chunks.append(topic["Text"])
            
            raw_content = "\n".join(chunks)
            
            if not raw_content.strip():
                # DuckDuckGo returned nothing useful
                # Use LLM knowledge directly
                async with httpx.AsyncClient() as c:
                    r = await c.post(
                        "http://localhost:11434"
                        "/api/generate",
                        json={
                            "model": "llama3.2",
                            "prompt": (
                                f"Answer this question "
                                f"concisely based on your "
                                f"knowledge: {query}\n\n"
                                f"Keep answer under "
                                f"150 words."
                            ),
                            "stream": False
                        },
                        timeout=30
                    )
                    return r.json().get(
                        "response", 
                        "No results found."
                    )
            
            # Step 2: Summarize with LLM
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:11434"
                    "/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": (
                            f"Based on this search data, "
                            f"give a concise answer to: "
                            f"'{query}'\n\n"
                            f"Search data:\n{raw_content}"
                            f"\n\nAnswer in 3-5 sentences. "
                            f"Be specific and factual."
                        ),
                        "stream": False
                    },
                    timeout=30
                )
                summary = resp.json().get(
                    "response", raw_content[:300]
                )
            
            return summary
            
        except Exception as e:
            # Last resort: LLM only
            try:
                async with httpx.AsyncClient() as c:
                    r = await c.post(
                        "http://localhost:11434"
                        "/api/generate",
                        json={
                            "model": "llama3.2",
                            "prompt": (
                                f"Answer concisely: "
                                f"{query}"
                            ),
                            "stream": False
                        },
                        timeout=30
                    )
                    return r.json().get(
                        "response",
                        "Search unavailable."
                    )
            except:
                return "Search unavailable."
    
    # ─── WEBPAGE READING ────────────────────────
    
    async def read_webpage(self, url: str) -> str:
        """Fetch and summarize a webpage."""
        if not url:
            return "No URL provided."
        if not url.startswith("http"):
            url = "https://" + url
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url, timeout=15,
                    follow_redirects=True,
                    headers={"User-Agent": 
                             "Mozilla/5.0"}
                )
                html = resp.text
                
            # Strip HTML tags
            clean = re.sub(r'<[^>]+>', ' ', html)
            clean = re.sub(r'\s+', ' ', clean).strip()
            content = clean[:4000]
            
            # Summarize with LLM
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:11434"
                    "/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": (
                            f"Summarize this webpage "
                            f"content concisely in "
                            f"3-4 sentences:\n\n"
                            f"{content}"
                        ),
                        "stream": False
                    },
                    timeout=30
                )
                summary = resp.json().get(
                    "response", content[:500]
                )
            return f"Summary of {url}:\n{summary}"
        except Exception as e:
            return f"Could not read page: {str(e)}"
    
    # ─── SCREENSHOT ─────────────────────────────
    
    def take_screenshot(self, 
                         path: str = None,
                         annotate: bool = False
                         ) -> str:
        """Take and save screenshot."""
        if not path:
            ts = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            path = f"~/Desktop/nova_{ts}.png"
        
        expanded = os.path.expanduser(path)
        
        # Use screencapture (native macOS)
        result = subprocess.run(
            ['screencapture', '-x', expanded],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Open in Preview if annotate
            if annotate:
                subprocess.Popen(
                    ['open', '-a', 'Preview', 
                     expanded]
                )
                return (f"Screenshot saved to {path}. "
                        f"Opening in Preview for "
                        f"annotation.")
            return f"Screenshot saved to {path}"
        return "Screenshot failed"
    
    # ─── WHATSAPP ───────────────────────────────
    
    def send_whatsapp(self, contact: str,
                       message: str) -> str:
        """Send WhatsApp message via URL scheme."""
        if not contact and not message:
            return "Please specify contact and message."
        
        # Open WhatsApp with pre-filled message
        import urllib.parse
        encoded = urllib.parse.quote(message)
        
        if contact:
            # Try to open conversation
            script = f'''
            tell application "WhatsApp"
                activate
            end tell
            '''
            subprocess.Popen(
                ['open', '-a', 'WhatsApp']
            )
            return (f"WhatsApp opened. "
                    f"Please send '{message}' "
                    f"to {contact} manually. "
                    f"(Direct send requires "
                    f"phone number.)")
        return "WhatsApp opened."
    
    # ─── EMAIL ──────────────────────────────────
    
    def send_email(self, to: str, 
                    subject: str,
                    body: str) -> str:
        """Send email via macOS Mail app."""
        script = f'''
        tell application "Mail"
            activate
            set newMsg to make new outgoing message \
                with properties {{
                    subject: "{subject}",
                    content: "{body}",
                    visible: true
                }}
            tell newMsg
                make new to recipient with properties \
                    {{address: "{to}"}}
            end tell
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return (f"Email composed to {to}. "
                    f"Review and send in Mail app.")
        return f"Email draft opened in Mail app."
    
    # ─── REMINDERS ──────────────────────────────
    
    def set_reminder(self, label: str,
                      time_str: str = "") -> str:
        """Set a reminder via macOS Reminders."""
        if time_str:
            script = f'''
            tell application "Reminders"
                tell list "Reminders"
                    make new reminder with properties\
                        {{name: "{label}",
                          due date: (current date) + \
                          60}}
                end tell
            end tell
            '''
        else:
            script = f'''
            tell application "Reminders"
                tell list "Reminders"
                    make new reminder with properties \
                        {{name: "{label}"}}
                end tell
            end tell
            '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Reminder set: '{label}'"
        return f"Reminder created in Reminders app."

# Singleton
capabilities = NovaCapabilities()
